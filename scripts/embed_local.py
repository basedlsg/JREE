#!/usr/bin/env python3
"""Generate embeddings and index chunks using local ChromaDB + sentence-transformers.

This script provides a fully local alternative to Pinecone + Cohere,
requiring no external API calls or network access.
"""

import json
import time
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Configuration
CHUNKS_DIR = Path("data/chunks")
CHROMA_DIR = Path("data/chromadb")
COLLECTION_NAME = "jre_quotes"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, good quality, 384 dimensions
BATCH_SIZE = 100


def load_chunks(chunks_dir: Path) -> list[dict]:
    """Load all chunk records from JSONL files."""
    all_chunks = []

    for filepath in sorted(chunks_dir.glob("*.jsonl")):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    all_chunks.append(json.loads(line))

    return all_chunks


def main():
    """Main entry point for local embedding and indexing."""
    import argparse

    parser = argparse.ArgumentParser(description="Embed chunks and index in ChromaDB (local)")
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        default=CHUNKS_DIR,
        help=f"Directory containing chunk JSONL files (default: {CHUNKS_DIR})",
    )
    parser.add_argument(
        "--chroma-dir",
        type=Path,
        default=CHROMA_DIR,
        help=f"Directory for ChromaDB storage (default: {CHROMA_DIR})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Batch size for embedding (default: {BATCH_SIZE})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of chunks to process (for testing)",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("Local Embedding & Indexing (ChromaDB)")
    print("=" * 50)
    print()

    # Load chunks
    print(f"Loading chunks from {args.chunks_dir}...")
    chunks = load_chunks(args.chunks_dir)
    if not chunks:
        print("No chunks found!")
        return

    if args.limit:
        chunks = chunks[:args.limit]
        print(f"Limited to {args.limit} chunks")

    print(f"Loaded {len(chunks)} chunks")
    print()

    # Initialize embedding model
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    print("(This may take a moment on first run to download the model)")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"Model loaded. Embedding dimension: {model.get_sentence_embedding_dimension()}")
    print()

    # Initialize ChromaDB
    print(f"Initializing ChromaDB at {args.chroma_dir}...")
    args.chroma_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(args.chroma_dir),
        settings=Settings(anonymized_telemetry=False),
    )

    # Create or get collection with cosine distance for better semantic search
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine", "description": "JRE podcast quotes"},
    )

    existing_count = collection.count()
    print(f"Collection '{COLLECTION_NAME}' has {existing_count} existing documents")
    print()

    # Process in batches
    print(f"Processing {len(chunks)} chunks in batches of {args.batch_size}...")
    start_time = time.time()

    total_added = 0
    for i in range(0, len(chunks), args.batch_size):
        batch = chunks[i:i + args.batch_size]

        # Prepare batch data
        ids = [chunk["chunk_id"] for chunk in batch]
        texts = [chunk["text"] for chunk in batch]
        metadatas = [
            {
                "episode_number": chunk["episode_number"],
                "episode_title": chunk["episode_title"],
                "guest": chunk["guest"],
                "chunk_index": chunk["chunk_index"],
                "total_chunks": chunk["total_chunks"],
                "highlight": chunk.get("highlight", ""),
                "youtube_id": chunk.get("youtube_id", ""),
            }
            for chunk in batch
        ]

        # Generate embeddings
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        # Upsert to ChromaDB
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        total_added += len(batch)
        elapsed = time.time() - start_time
        rate = total_added / elapsed if elapsed > 0 else 0

        print(f"  Processed {total_added}/{len(chunks)} ({rate:.1f} chunks/sec)")

    # Final stats
    total_time = time.time() - start_time
    final_count = collection.count()

    print()
    print("=" * 50)
    print(f"Done! Indexed {total_added} chunks in {total_time:.1f}s")
    print(f"Collection now has {final_count} documents")
    print(f"ChromaDB stored at: {args.chroma_dir}")
    print()
    print("Next: Start the backend with 'uvicorn backend.main:app --reload'")


if __name__ == "__main__":
    main()
