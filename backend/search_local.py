"""Local search functionality using ChromaDB + sentence-transformers.

This provides a fully local alternative to Pinecone + Cohere.
"""

import math
import time
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from backend.models import QuoteResult, SearchRequest, SearchResponse

# Configuration
CHROMA_DIR = Path("data/chromadb")
COLLECTION_NAME = "jre_quotes"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Global instances (lazy loaded)
_model = None
_collection = None


def get_model() -> SentenceTransformer:
    """Get or initialize the sentence transformer model."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def get_collection():
    """Get or initialize the ChromaDB collection."""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def search_quotes_local(request: SearchRequest) -> SearchResponse:
    """Execute semantic search using local ChromaDB.

    Args:
        request: Search request with query and parameters.

    Returns:
        SearchResponse with matching quotes and metadata.
    """
    start_time = time.perf_counter()

    # Generate embedding for query
    model = get_model()
    query_embedding = model.encode([request.query])[0].tolist()

    # Build where filter if needed
    where_filter = None
    if request.episode_filter:
        where_filter = {"episode_number": {"$in": request.episode_filter}}

    # Query ChromaDB
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=request.top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    # Transform results
    quote_results = []
    if results["ids"] and results["ids"][0]:
        for i, chunk_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            document = results["documents"][0][i] if results["documents"] else ""
            distance = results["distances"][0][i] if results["distances"] else 0

            # Convert L2 distance to similarity score
            # Using exponential decay for better score distribution
            score = math.exp(-distance / 10)

            result = QuoteResult(
                text=document,
                highlight=metadata.get("highlight") or None,
                episode_number=metadata.get("episode_number", 0),
                episode_title=metadata.get("episode_title", "Unknown"),
                guest=metadata.get("guest", "Unknown"),
                youtube_id=metadata.get("youtube_id") or None,
                timestamp=None,
                score=score,
                chunk_id=chunk_id,
            )
            quote_results.append(result)

    # Calculate search time
    search_time_ms = (time.perf_counter() - start_time) * 1000

    return SearchResponse(
        query=request.query,
        results=quote_results,
        total_results=len(quote_results),
        search_time_ms=round(search_time_ms, 2),
    )


def get_local_index_stats() -> dict:
    """Get statistics about the local ChromaDB index."""
    collection = get_collection()
    count = collection.count()

    return {
        "total_vectors": count,
        "dimension": 384,  # all-MiniLM-L6-v2 dimension
        "backend": "chromadb",
    }


def check_local_health() -> bool:
    """Check if local search is available."""
    try:
        collection = get_collection()
        collection.count()
        return True
    except Exception:
        return False
