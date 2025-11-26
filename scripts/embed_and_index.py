#!/usr/bin/env python3
"""Generate embeddings and index chunks in Pinecone.

This script reads chunk files, generates embeddings using Cohere,
and upserts vectors to Pinecone for semantic search.
"""

import json
import sys
import time
from pathlib import Path

import cohere
from pinecone import Pinecone

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import get_settings

# Configuration
BATCH_SIZE = 96  # Cohere recommends batches of 96 for embed-english-v3.0
UPSERT_BATCH_SIZE = 100  # Pinecone upsert batch size
EMBED_MODEL = "embed-english-v3.0"
EMBEDDING_DIMENSION = 1024


def load_chunks(chunks_dir: Path) -> list[dict]:
    """Load all chunk records from JSONL files.

    Args:
        chunks_dir: Directory containing chunk JSONL files.

    Returns:
        List of chunk records.
    """
    all_chunks = []

    for filepath in sorted(chunks_dir.glob("*.jsonl")):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    all_chunks.append(json.loads(line))

    return all_chunks


def generate_embeddings_batch(
    texts: list[str],
    cohere_client: cohere.Client,
    model: str = EMBED_MODEL,
) -> list[list[float]]:
    """Generate embeddings for a batch of texts.

    Args:
        texts: List of text strings to embed.
        cohere_client: Cohere client instance.
        model: Embedding model name.

    Returns:
        List of embedding vectors.
    """
    response = cohere_client.embed(
        texts=texts,
        model=model,
        input_type="search_document",  # Use search_document for indexing
    )
    return response.embeddings


def create_pinecone_vectors(
    chunks: list[dict],
    embeddings: list[list[float]],
) -> list[dict]:
    """Create Pinecone vector records from chunks and embeddings.

    Args:
        chunks: List of chunk records.
        embeddings: Corresponding embedding vectors.

    Returns:
        List of Pinecone vector dicts.
    """
    vectors = []
    for chunk, embedding in zip(chunks, embeddings):
        vector = {
            "id": chunk["chunk_id"],
            "values": embedding,
            "metadata": {
                "text": chunk["text"],
                "episode_number": chunk["episode_number"],
                "episode_title": chunk["episode_title"],
                "guest": chunk["guest"],
                "chunk_index": chunk["chunk_index"],
                "total_chunks": chunk["total_chunks"],
            },
        }
        vectors.append(vector)
    return vectors


def upsert_vectors(
    index,
    vectors: list[dict],
    batch_size: int = UPSERT_BATCH_SIZE,
) -> int:
    """Upsert vectors to Pinecone in batches.

    Args:
        index: Pinecone index instance.
        vectors: List of vector dicts.
        batch_size: Number of vectors per upsert call.

    Returns:
        Total number of vectors upserted.
    """
    total_upserted = 0

    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch)
        total_upserted += len(batch)

    return total_upserted


def main():
    """Main entry point for embedding and indexing."""
    import argparse

    parser = argparse.ArgumentParser(description="Embed chunks and index in Pinecone")
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        default=Path("data/chunks"),
        help="Directory containing chunk JSONL files",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Embedding batch size (default: {BATCH_SIZE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process chunks but don't upsert to Pinecone",
    )
    args = parser.parse_args()

    # Load settings
    print("Loading configuration...")
    settings = get_settings()

    # Initialize clients
    print("Initializing Cohere client...")
    cohere_client = cohere.Client(api_key=settings.cohere_api_key)

    print("Initializing Pinecone client...")
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index = pc.Index(settings.pinecone_index_name)

    # Load chunks
    print(f"Loading chunks from {args.chunks_dir}...")
    chunks = load_chunks(args.chunks_dir)
    if not chunks:
        print("No chunks found!")
        return

    print(f"Loaded {len(chunks)} chunks")

    # Process in batches
    all_vectors = []
    total_chunks = len(chunks)

    print(f"\nGenerating embeddings (batch size: {args.batch_size})...")
    start_time = time.time()

    for i in range(0, total_chunks, args.batch_size):
        batch_chunks = chunks[i:i + args.batch_size]
        batch_texts = [c["text"] for c in batch_chunks]

        # Generate embeddings
        embeddings = generate_embeddings_batch(batch_texts, cohere_client)

        # Create vectors
        vectors = create_pinecone_vectors(batch_chunks, embeddings)
        all_vectors.extend(vectors)

        # Progress
        processed = min(i + args.batch_size, total_chunks)
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        print(f"  Processed {processed}/{total_chunks} chunks ({rate:.1f} chunks/sec)")

        # Rate limiting - Cohere has rate limits
        time.sleep(0.1)

    embed_time = time.time() - start_time
    print(f"\nEmbedding complete in {embed_time:.1f}s")

    # Upsert to Pinecone
    if args.dry_run:
        print("\nDry run - skipping Pinecone upsert")
        print(f"Would upsert {len(all_vectors)} vectors")
    else:
        print(f"\nUpserting {len(all_vectors)} vectors to Pinecone...")
        upsert_start = time.time()
        upserted = upsert_vectors(index, all_vectors)
        upsert_time = time.time() - upsert_start
        print(f"Upserted {upserted} vectors in {upsert_time:.1f}s")

    # Final stats
    stats = index.describe_index_stats()
    print(f"\nIndex stats:")
    print(f"  Total vectors: {stats.total_vector_count}")
    print(f"  Dimension: {stats.dimension}")


if __name__ == "__main__":
    main()
