"""Search functionality using Cohere embeddings and Pinecone vector search."""

import time

from backend.config import get_cohere_client, get_pinecone_index, get_settings
from backend.models import QuoteResult, SearchRequest, SearchResponse


def generate_embedding(text: str) -> list[float]:
    """Generate embedding for a text query using Cohere.

    Args:
        text: The text to embed.

    Returns:
        List of floats representing the embedding vector.
    """
    settings = get_settings()
    cohere_client = get_cohere_client()

    response = cohere_client.embed(
        texts=[text],
        model=settings.cohere_embed_model,
        input_type="search_query",
    )

    return response.embeddings[0]


def build_metadata_filter(
    episode_filter: list[int] | None = None,
    guest_filter: str | None = None,
) -> dict | None:
    """Build Pinecone metadata filter from search parameters.

    Args:
        episode_filter: Optional list of episode numbers.
        guest_filter: Optional guest name substring.

    Returns:
        Pinecone filter dict or None if no filters.
    """
    filters = {}

    if episode_filter:
        filters["episode_number"] = {"$in": episode_filter}

    if guest_filter:
        # Case-insensitive substring match on guest field
        filters["guest"] = {"$eq": guest_filter}

    return filters if filters else None


def search_quotes(request: SearchRequest) -> SearchResponse:
    """Execute semantic search for quotes.

    Args:
        request: Search request with query and parameters.

    Returns:
        SearchResponse with matching quotes and metadata.
    """
    start_time = time.perf_counter()

    # Generate embedding for query
    query_embedding = generate_embedding(request.query)

    # Build metadata filter
    metadata_filter = build_metadata_filter(
        episode_filter=request.episode_filter,
        guest_filter=request.guest_filter,
    )

    # Query Pinecone
    index = get_pinecone_index()
    query_response = index.query(
        vector=query_embedding,
        top_k=request.top_k,
        include_metadata=True,
        filter=metadata_filter,
    )

    # Transform results
    results = []
    for match in query_response.matches:
        metadata = match.metadata or {}
        result = QuoteResult(
            text=metadata.get("text", ""),
            episode_number=metadata.get("episode_number", 0),
            episode_title=metadata.get("episode_title", "Unknown"),
            guest=metadata.get("guest", "Unknown"),
            timestamp=metadata.get("timestamp"),
            score=match.score,
            chunk_id=match.id,
        )
        results.append(result)

    # Calculate search time
    search_time_ms = (time.perf_counter() - start_time) * 1000

    return SearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
        search_time_ms=round(search_time_ms, 2),
    )


def get_index_stats() -> dict:
    """Get statistics about the Pinecone index.

    Returns:
        Dict with index statistics.
    """
    index = get_pinecone_index()
    stats = index.describe_index_stats()

    return {
        "total_vectors": stats.total_vector_count,
        "dimension": stats.dimension,
        "namespaces": stats.namespaces,
    }
