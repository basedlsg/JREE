#!/usr/bin/env python3
"""Process transcript files into overlapping chunks for embedding.

This script reads raw transcript files and splits them into chunks
suitable for embedding and indexing in Pinecone.

Chunking strategy:
- Target chunk size: 512 tokens
- Overlap: 128 tokens
- Preserves sentence boundaries where possible
"""

import json
import re
from pathlib import Path

import tiktoken

# Configuration
CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 128  # tokens
ENCODING_NAME = "cl100k_base"  # GPT-4 / text-embedding-ada-002 compatible


def get_tokenizer():
    """Get tiktoken tokenizer."""
    return tiktoken.get_encoding(ENCODING_NAME)


def count_tokens(text: str, tokenizer) -> int:
    """Count tokens in text."""
    return len(tokenizer.encode(text))


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences, preserving punctuation."""
    # Simple sentence splitting on .!? followed by space or end
    sentence_pattern = r'(?<=[.!?])\s+'
    sentences = re.split(sentence_pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def create_chunks(
    text: str,
    tokenizer,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks respecting sentence boundaries.

    Args:
        text: Full transcript text.
        tokenizer: Tiktoken tokenizer instance.
        chunk_size: Target chunk size in tokens.
        overlap: Number of overlapping tokens between chunks.

    Returns:
        List of text chunks.
    """
    sentences = split_into_sentences(text)
    if not sentences:
        return []

    chunks = []
    current_chunk = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence, tokenizer)

        # If single sentence exceeds chunk size, split it forcefully
        if sentence_tokens > chunk_size:
            # Flush current chunk first
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_tokens = 0

            # Split long sentence by tokens
            tokens = tokenizer.encode(sentence)
            for i in range(0, len(tokens), chunk_size - overlap):
                chunk_tokens = tokens[i:i + chunk_size]
                chunks.append(tokenizer.decode(chunk_tokens))
            continue

        # Check if adding sentence exceeds chunk size
        if current_tokens + sentence_tokens > chunk_size:
            # Save current chunk
            if current_chunk:
                chunks.append(" ".join(current_chunk))

            # Start new chunk with overlap from previous
            # Find sentences to include for overlap
            overlap_sentences = []
            overlap_tokens = 0
            for sent in reversed(current_chunk):
                sent_tokens = count_tokens(sent, tokenizer)
                if overlap_tokens + sent_tokens <= overlap:
                    overlap_sentences.insert(0, sent)
                    overlap_tokens += sent_tokens
                else:
                    break

            current_chunk = overlap_sentences + [sentence]
            current_tokens = overlap_tokens + sentence_tokens
        else:
            current_chunk.append(sentence)
            current_tokens += sentence_tokens

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def process_transcript_file(
    input_path: Path,
    output_dir: Path,
    tokenizer,
) -> dict:
    """Process a single transcript file into chunks.

    Args:
        input_path: Path to transcript JSON file.
        output_dir: Directory to write chunk files.
        tokenizer: Tiktoken tokenizer instance.

    Returns:
        Dict with processing statistics.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    episode_number = transcript.get("episode_number", 0)
    episode_title = transcript.get("title", "Unknown")
    guest = transcript.get("guest", "Unknown")
    text = transcript.get("text", "")

    if not text:
        return {"episode": episode_number, "chunks": 0, "skipped": True}

    chunks = create_chunks(text, tokenizer)

    # Create output records
    chunk_records = []
    for i, chunk_text in enumerate(chunks):
        chunk_id = f"jre-{episode_number}-chunk-{i:04d}"
        record = {
            "chunk_id": chunk_id,
            "text": chunk_text,
            "episode_number": episode_number,
            "episode_title": episode_title,
            "guest": guest,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "token_count": count_tokens(chunk_text, tokenizer),
        }
        chunk_records.append(record)

    # Write chunks to JSONL file
    output_path = output_dir / f"jre-{episode_number}-chunks.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for record in chunk_records:
            f.write(json.dumps(record) + "\n")

    return {
        "episode": episode_number,
        "chunks": len(chunks),
        "output_file": str(output_path),
    }


def main():
    """Main entry point for chunk processing."""
    import argparse

    parser = argparse.ArgumentParser(description="Process transcripts into chunks")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/transcripts"),
        help="Directory containing transcript JSON files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/chunks"),
        help="Directory to write chunk files",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=CHUNK_SIZE,
        help=f"Target chunk size in tokens (default: {CHUNK_SIZE})",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=CHUNK_OVERLAP,
        help=f"Overlap between chunks in tokens (default: {CHUNK_OVERLAP})",
    )
    args = parser.parse_args()

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize tokenizer
    print("Initializing tokenizer...")
    tokenizer = get_tokenizer()

    # Find all transcript files
    transcript_files = list(args.input_dir.glob("*.json"))
    if not transcript_files:
        print(f"No transcript files found in {args.input_dir}")
        return

    print(f"Found {len(transcript_files)} transcript files")

    # Process each file
    total_chunks = 0
    for i, filepath in enumerate(sorted(transcript_files), 1):
        print(f"Processing [{i}/{len(transcript_files)}]: {filepath.name}")
        result = process_transcript_file(filepath, args.output_dir, tokenizer)

        if result.get("skipped"):
            print(f"  Skipped (no text)")
        else:
            print(f"  Created {result['chunks']} chunks")
            total_chunks += result["chunks"]

    print(f"\nDone! Created {total_chunks} total chunks in {args.output_dir}")


if __name__ == "__main__":
    main()
