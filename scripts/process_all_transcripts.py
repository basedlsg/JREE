#!/usr/bin/env python3
"""Process ALL transcripts with quote extraction for better search.

This script:
1. Indexes ALL transcripts (not just those with README metadata)
2. Creates smaller chunks (~100 tokens) for more focused results
3. Extracts a "highlight" sentence for each chunk
"""

import json
import re
from pathlib import Path

import tiktoken

# Configuration
CHUNK_SIZE = 100  # tokens - smaller for more focused quotes
CHUNK_OVERLAP = 20  # tokens
ENCODING_NAME = "cl100k_base"

SCRIBESALAD_DIR = Path("data/scribesalad/transcripts/en/Joe_Rogan_Experience")
METADATA_FILE = Path("data/episode_metadata_full.json")  # Full metadata from YouTube
OUTPUT_DIR = Path("data/chunks_v4")  # New version with better metadata


def get_tokenizer():
    return tiktoken.get_encoding(ENCODING_NAME)


def count_tokens(text: str, tokenizer) -> int:
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
        # Remove speaker labels like "Speaker 1:" at the start
        line = re.sub(r"^Speaker\s*\d+:\s*", "", line)
        # Remove timestamp patterns like "00:00:00"
        line = re.sub(r"\d{2}:\d{2}:\d{2}", "", line)
        if line:
            lines.append(line)
    return " ".join(lines)


def parse_vtt(content: str) -> str:
    """Parse VTT subtitle format."""
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
            line = re.sub(r"^Speaker\s*\d+:\s*", "", line)
            line = re.sub(r"\d{2}:\d{2}:\d{2}", "", line)
            if line:
                lines.append(line)

    return " ".join(lines)


def clean_text(text: str) -> str:
    """Clean up transcript text."""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove speaker labels
    text = re.sub(r'Speaker\s*\d+:\s*', '', text)
    # Remove timestamps
    text = re.sub(r'\d{2}:\d{2}:\d{2}', '', text)
    return text.strip()


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    # Better sentence splitting
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]


def extract_highlight(chunk_text: str, max_length: int = 200) -> str:
    """Extract the most quotable sentence from a chunk."""
    sentences = split_into_sentences(chunk_text)
    if not sentences:
        return chunk_text[:max_length]

    # Score sentences by length (prefer medium-length) and content
    scored = []
    for sent in sentences:
        score = 0
        length = len(sent)

        # Prefer sentences 50-150 chars
        if 50 <= length <= 150:
            score += 10
        elif 30 <= length <= 200:
            score += 5

        # Bonus for sentences that look like quotes/statements
        if not sent.startswith(('Um', 'Uh', 'Like', 'Yeah', 'So', 'And', 'But', 'I mean')):
            score += 3

        # Bonus for complete thoughts (ends with period)
        if sent.endswith('.'):
            score += 2

        scored.append((score, sent))

    scored.sort(reverse=True)
    best = scored[0][1] if scored else sentences[0]

    if len(best) > max_length:
        best = best[:max_length-3] + "..."

    return best


def create_chunks(
    text: str,
    tokenizer,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """Create chunks with highlights."""
    sentences = split_into_sentences(text)
    if not sentences:
        return []

    chunks = []
    current_sentences = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence, tokenizer)

        if sentence_tokens > chunk_size:
            if current_sentences:
                chunk_text = " ".join(current_sentences)
                chunks.append({
                    "text": chunk_text,
                    "highlight": extract_highlight(chunk_text),
                })
                current_sentences = []
                current_tokens = 0

            # Split long sentence
            tokens = tokenizer.encode(sentence)
            for i in range(0, len(tokens), chunk_size - overlap):
                chunk_tokens = tokens[i:i + chunk_size]
                chunk_text = tokenizer.decode(chunk_tokens)
                chunks.append({
                    "text": chunk_text,
                    "highlight": extract_highlight(chunk_text),
                })
            continue

        if current_tokens + sentence_tokens > chunk_size:
            if current_sentences:
                chunk_text = " ".join(current_sentences)
                chunks.append({
                    "text": chunk_text,
                    "highlight": extract_highlight(chunk_text),
                })

            # Overlap
            overlap_sentences = []
            overlap_tokens = 0
            for sent in reversed(current_sentences):
                sent_tokens = count_tokens(sent, tokenizer)
                if overlap_tokens + sent_tokens <= overlap:
                    overlap_sentences.insert(0, sent)
                    overlap_tokens += sent_tokens
                else:
                    break

            current_sentences = overlap_sentences + [sentence]
            current_tokens = overlap_tokens + sentence_tokens
        else:
            current_sentences.append(sentence)
            current_tokens += sentence_tokens

    if current_sentences:
        chunk_text = " ".join(current_sentences)
        chunks.append({
            "text": chunk_text,
            "highlight": extract_highlight(chunk_text),
        })

    return chunks


def load_metadata() -> dict[str, dict]:
    """Load episode metadata from JSON file."""
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def find_all_transcripts(base_dir: Path) -> list[tuple[str, Path]]:
    """Find all transcript files and return (youtube_id, path) pairs."""
    transcripts = {}

    # Prefer txt > srt > vtt
    for subdir, priority in [("txt", 3), ("srt", 2), ("vtt", 1)]:
        dir_path = base_dir / subdir
        if not dir_path.exists():
            continue
        for filepath in dir_path.glob("*"):
            youtube_id = filepath.stem
            if youtube_id not in transcripts or priority > transcripts[youtube_id][1]:
                transcripts[youtube_id] = (filepath, priority)

    return [(yt_id, info[0]) for yt_id, info in transcripts.items()]


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
        text = parse_srt(content)
    elif suffix == ".vtt":
        text = parse_vtt(content)
    else:
        text = content.strip()

    return clean_text(text)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Process ALL transcripts")
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
        help="Limit number of transcripts to process",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Processing ALL Transcripts with Quote Extraction")
    print("=" * 60)
    print()

    # Load metadata (for episodes that have it)
    print("Loading episode metadata...")
    metadata = load_metadata()
    print(f"  Found metadata for {len(metadata)} episodes")
    print()

    # Find ALL transcript files
    print("Finding all transcript files...")
    transcripts = find_all_transcripts(args.scribesalad_dir)
    print(f"  Found {len(transcripts)} unique transcripts")

    if args.limit:
        transcripts = transcripts[:args.limit]
        print(f"  Limited to {args.limit} transcripts")
    print()

    # Initialize tokenizer
    print("Initializing tokenizer...")
    tokenizer = get_tokenizer()
    print()

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Process each transcript
    print(f"Processing transcripts (chunk size: {args.chunk_size} tokens)...")

    processed = 0
    skipped = 0
    total_chunks = 0
    all_chunks = []

    with_metadata = 0
    without_metadata = 0

    for youtube_id, filepath in transcripts:
        # Read transcript
        text = read_transcript(filepath)
        if not text or len(text) < 500:
            skipped += 1
            continue

        # Get metadata if available
        info = metadata.get(youtube_id, {})
        episode_number = info.get("episode_number", 0)
        episode_title = info.get("title", f"JRE - {youtube_id}")
        guest = info.get("guest", "Unknown")

        if episode_number > 0:
            with_metadata += 1
        else:
            without_metadata += 1

        # Create chunks
        chunks = create_chunks(text, tokenizer, chunk_size=args.chunk_size)
        if not chunks:
            skipped += 1
            continue

        # Create records
        for i, chunk_data in enumerate(chunks):
            chunk_id = f"jre-{youtube_id}-{i:04d}"
            record = {
                "chunk_id": chunk_id,
                "text": chunk_data["text"],
                "highlight": chunk_data["highlight"],
                "episode_number": episode_number,
                "episode_title": episode_title,
                "guest": guest,
                "youtube_id": youtube_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "token_count": count_tokens(chunk_data["text"], tokenizer),
            }
            all_chunks.append(record)

        total_chunks += len(chunks)
        processed += 1

        if processed % 100 == 0:
            print(f"  Processed {processed} transcripts, {total_chunks} chunks...")

    # Write all chunks
    output_file = args.output_dir / "all_chunks.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for record in all_chunks:
            f.write(json.dumps(record) + "\n")

    print()
    print("=" * 60)
    print(f"Done!")
    print(f"  Transcripts processed: {processed}")
    print(f"    - With episode metadata: {with_metadata}")
    print(f"    - Without metadata (using YouTube ID): {without_metadata}")
    print(f"  Transcripts skipped: {skipped}")
    print(f"  Total chunks created: {total_chunks}")
    print(f"  Average chunks per transcript: {total_chunks / processed:.1f}")
    print(f"  Output: {output_file}")


if __name__ == "__main__":
    main()
