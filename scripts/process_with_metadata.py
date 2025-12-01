#!/usr/bin/env python3
"""Process transcripts with proper metadata and smaller chunks.

This script:
1. Loads episode metadata from the parsed README
2. Converts transcripts to JSON with correct metadata
3. Creates smaller chunks (150 tokens) for better search relevance
"""

import json
import re
from pathlib import Path

import tiktoken

# Configuration
CHUNK_SIZE = 150  # tokens - smaller for more focused results
CHUNK_OVERLAP = 30  # tokens
ENCODING_NAME = "cl100k_base"

SCRIBESALAD_DIR = Path("data/scribesalad/transcripts/en/Joe_Rogan_Experience")
METADATA_FILE = Path("data/episode_metadata.json")
OUTPUT_DIR = Path("data/chunks_v2")


def get_tokenizer():
    """Get tiktoken tokenizer."""
    return tiktoken.get_encoding(ENCODING_NAME)


def count_tokens(text: str, tokenizer) -> int:
    """Count tokens in text."""
    return len(tokenizer.encode(text))


def parse_srt(content: str) -> str:
    """Parse SRT subtitle format and extract plain text."""
    lines = []
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.isdigit():
            continue
        if re.match(r"\d{2}:\d{2}:\d{2}", line):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if line:
            lines.append(line)
    return " ".join(lines)


def parse_vtt(content: str) -> str:
    """Parse VTT subtitle format and extract plain text."""
    lines = []
    in_cue = False

    for line in content.split("\n"):
        line = line.strip()
        if line == "WEBVTT" or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if "-->" in line:
            in_cue = True
            continue
        if not line:
            in_cue = False
            continue
        if re.match(r"^\d+$", line):
            continue
        if in_cue or not re.match(r"\d{2}:\d{2}", line):
            line = re.sub(r"<[^>]+>", "", line)
            if line:
                lines.append(line)

    return " ".join(lines)


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentence_pattern = r'(?<=[.!?])\s+'
    sentences = re.split(sentence_pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def create_chunks(
    text: str,
    tokenizer,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks respecting sentence boundaries."""
    sentences = split_into_sentences(text)
    if not sentences:
        return []

    chunks = []
    current_chunk = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence, tokenizer)

        # If single sentence exceeds chunk size, split it
        if sentence_tokens > chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_tokens = 0

            tokens = tokenizer.encode(sentence)
            for i in range(0, len(tokens), chunk_size - overlap):
                chunk_tokens = tokens[i:i + chunk_size]
                chunks.append(tokenizer.decode(chunk_tokens))
            continue

        if current_tokens + sentence_tokens > chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))

            # Start new chunk with overlap
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

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def load_metadata() -> dict[str, dict]:
    """Load episode metadata from JSON file."""
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def find_transcript_file(youtube_id: str, base_dir: Path) -> Path | None:
    """Find transcript file for a given YouTube ID."""
    # Try different formats/directories
    for subdir in ["txt", "srt", "vtt"]:
        filepath = base_dir / subdir / f"{youtube_id}.{subdir}"
        if filepath.exists():
            return filepath
    return None


def read_transcript(filepath: Path) -> str:
    """Read and parse transcript file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return ""

    suffix = filepath.suffix.lower()
    if suffix == ".srt":
        return parse_srt(content)
    elif suffix == ".vtt":
        return parse_vtt(content)
    else:
        return content.strip()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Process transcripts with metadata")
    parser.add_argument(
        "--scribesalad-dir",
        type=Path,
        default=SCRIBESALAD_DIR,
        help="ScribeSalad JRE directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for chunks",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=CHUNK_SIZE,
        help=f"Chunk size in tokens (default: {CHUNK_SIZE})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of episodes to process",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Processing Transcripts with Proper Metadata")
    print("=" * 60)
    print()

    # Load metadata
    print("Loading episode metadata...")
    metadata = load_metadata()
    print(f"  Found metadata for {len(metadata)} episodes")
    print()

    # Initialize tokenizer
    print("Initializing tokenizer...")
    tokenizer = get_tokenizer()
    print()

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Process each episode with metadata
    print(f"Processing episodes (chunk size: {args.chunk_size} tokens)...")

    processed = 0
    skipped = 0
    total_chunks = 0
    all_chunks = []

    episode_list = list(metadata.items())
    if args.limit:
        episode_list = episode_list[:args.limit]

    for youtube_id, info in episode_list:
        # Skip episodes without valid episode numbers (special episodes, recaps, etc.)
        if info["episode_number"] == 0:
            skipped += 1
            continue

        # Find transcript file
        transcript_file = find_transcript_file(youtube_id, args.scribesalad_dir)
        if not transcript_file:
            skipped += 1
            continue

        # Read transcript
        text = read_transcript(transcript_file)
        if not text or len(text) < 500:  # Skip very short transcripts
            skipped += 1
            continue

        # Create chunks
        chunks = create_chunks(text, tokenizer, chunk_size=args.chunk_size)
        if not chunks:
            skipped += 1
            continue

        # Create chunk records with proper metadata
        # Include youtube_id in chunk_id to ensure uniqueness (some episodes have multiple videos)
        for i, chunk_text in enumerate(chunks):
            chunk_id = f"jre-{info['episode_number']}-{youtube_id[:6]}-{i:04d}"
            record = {
                "chunk_id": chunk_id,
                "text": chunk_text,
                "episode_number": info["episode_number"],
                "episode_title": info["title"],
                "guest": info["guest"],
                "youtube_id": youtube_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "token_count": count_tokens(chunk_text, tokenizer),
            }
            all_chunks.append(record)

        total_chunks += len(chunks)
        processed += 1

        if processed % 50 == 0:
            print(f"  Processed {processed} episodes, {total_chunks} chunks so far...")

    # Write all chunks to single JSONL file
    output_file = args.output_dir / "all_chunks.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for record in all_chunks:
            f.write(json.dumps(record) + "\n")

    print()
    print("=" * 60)
    print(f"Done!")
    print(f"  Episodes processed: {processed}")
    print(f"  Episodes skipped: {skipped}")
    print(f"  Total chunks created: {total_chunks}")
    print(f"  Average chunks per episode: {total_chunks / processed:.1f}")
    print(f"  Output: {output_file}")
    print()
    print("Next: Run embed_local.py with --chunks-dir data/chunks_v2")


if __name__ == "__main__":
    main()
