#!/usr/bin/env python3
"""Download JRE transcripts from the ScribeSalad GitHub repository.

ScribeSalad is an open data project with 940k+ YouTube transcripts.
Repository: https://github.com/wa3dbk/ScribeSalad

This script:
1. Clones/pulls the ScribeSalad repo (sparse checkout for JRE only)
2. Finds all JRE transcript files (.txt, .srt, .vtt)
3. Converts them to our JSON format
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


# Configuration
REPO_URL = "https://github.com/wa3dbk/ScribeSalad.git"
CLONE_DIR = Path("data/scribesalad")
OUTPUT_DIR = Path("data/transcripts")

# JRE channel paths within the repo
JRE_PATHS = [
    "transcripts/en/Joe_Rogan_Experience",
    "transcripts/en/JRE_Clips",
    "transcripts/en/Joe_Rogan_MMA_Show",
]


def run_command(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def clone_or_update_repo(clone_dir: Path) -> bool:
    """Clone the ScribeSalad repo or update if exists.

    Uses sparse checkout to only get JRE transcripts.
    """
    if clone_dir.exists() and (clone_dir / ".git").exists():
        print("Repository exists, pulling latest...")
        code, out, err = run_command(["git", "pull"], cwd=str(clone_dir))
        if code != 0:
            print(f"Warning: git pull failed: {err}")
        return True

    print(f"Cloning ScribeSalad repository to {clone_dir}...")
    print("(This may take a while - the repo is large)")

    # Create directory
    clone_dir.mkdir(parents=True, exist_ok=True)

    # Initialize with sparse checkout
    run_command(["git", "init"], cwd=str(clone_dir))
    run_command(["git", "remote", "add", "origin", REPO_URL], cwd=str(clone_dir))
    run_command(["git", "config", "core.sparseCheckout", "true"], cwd=str(clone_dir))

    # Configure sparse checkout paths
    sparse_file = clone_dir / ".git" / "info" / "sparse-checkout"
    sparse_file.parent.mkdir(parents=True, exist_ok=True)
    with open(sparse_file, "w") as f:
        for path in JRE_PATHS:
            f.write(f"{path}/\n")

    # Pull only the specified directories
    print("Fetching JRE transcripts (sparse checkout)...")
    code, out, err = run_command(["git", "pull", "origin", "master", "--depth=1"], cwd=str(clone_dir))

    if code != 0:
        print(f"Error cloning repo: {err}")
        # Fallback: try full clone
        print("Sparse checkout failed. Trying alternative approach...")
        return clone_full_repo(clone_dir)

    return True


def clone_full_repo(clone_dir: Path) -> bool:
    """Fallback: clone the full repo with depth=1."""
    import shutil

    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    print("Cloning full repository (shallow)...")
    code, out, err = run_command([
        "git", "clone", "--depth=1", REPO_URL, str(clone_dir)
    ])

    if code != 0:
        print(f"Error: {err}")
        return False

    return True


def parse_srt(content: str) -> str:
    """Parse SRT subtitle format and extract plain text."""
    lines = []
    # SRT format: index, timestamp, text, blank line
    # Skip index and timestamp lines
    for line in content.split("\n"):
        line = line.strip()
        # Skip empty lines, index numbers, and timestamps
        if not line:
            continue
        if line.isdigit():
            continue
        if re.match(r"\d{2}:\d{2}:\d{2}", line):
            continue
        # Remove HTML-like tags
        line = re.sub(r"<[^>]+>", "", line)
        if line:
            lines.append(line)

    return " ".join(lines)


def parse_vtt(content: str) -> str:
    """Parse VTT (WebVTT) subtitle format and extract plain text."""
    lines = []
    in_cue = False

    for line in content.split("\n"):
        line = line.strip()

        # Skip header
        if line == "WEBVTT" or line.startswith("Kind:") or line.startswith("Language:"):
            continue

        # Skip timestamps
        if "-->" in line:
            in_cue = True
            continue

        # Skip empty lines
        if not line:
            in_cue = False
            continue

        # Skip cue identifiers (usually numbers or timestamps at start of cue)
        if re.match(r"^\d+$", line):
            continue

        if in_cue or not re.match(r"\d{2}:\d{2}", line):
            # Remove HTML-like tags
            line = re.sub(r"<[^>]+>", "", line)
            if line:
                lines.append(line)

    return " ".join(lines)


def extract_episode_info(filepath: Path, text: str) -> dict:
    """Extract episode metadata from filepath and content."""
    filename = filepath.stem

    # Try to extract episode number from filename
    # Common patterns: "JRE #1234", "1234 - Guest Name", etc.
    episode_number = 0
    guest = "Unknown"
    title = filename

    # Pattern: video ID (YouTube IDs are 11 chars)
    # The actual episode info might be in the folder structure
    parent = filepath.parent.name

    # Try to find episode number in filename or path
    ep_match = re.search(r"#?(\d{3,4})", filename) or re.search(r"#?(\d{3,4})", parent)
    if ep_match:
        episode_number = int(ep_match.group(1))

    # Try to extract guest name
    # Pattern: "Episode Title - Guest Name" or "Guest Name - Episode"
    name_match = re.search(r"[–-]\s*(.+?)(?:\s*[–-]|$)", filename)
    if name_match:
        guest = name_match.group(1).strip()

    return {
        "episode_number": episode_number,
        "title": title,
        "guest": guest,
        "youtube_id": filename if len(filename) == 11 else None,
        "source": "ScribeSalad",
        "source_file": str(filepath.relative_to(CLONE_DIR)) if CLONE_DIR in filepath.parents else str(filepath),
        "text": text,
    }


def find_transcript_files(base_dir: Path) -> list[Path]:
    """Find all transcript files in the JRE directories."""
    files = []

    for jre_path in JRE_PATHS:
        search_dir = base_dir / jre_path
        if not search_dir.exists():
            print(f"  Path not found: {search_dir}")
            continue

        # Find .txt files (preferred), then .srt, then .vtt
        for pattern in ["**/*.txt", "**/*.srt", "**/*.vtt"]:
            files.extend(search_dir.glob(pattern))

    return files


def convert_transcript(filepath: Path) -> dict | None:
    """Convert a transcript file to our JSON format."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return None

    # Parse based on file type
    suffix = filepath.suffix.lower()
    if suffix == ".srt":
        text = parse_srt(content)
    elif suffix == ".vtt":
        text = parse_vtt(content)
    else:  # .txt
        text = content.strip()

    if not text or len(text) < 100:
        return None  # Skip very short/empty transcripts

    return extract_episode_info(filepath, text)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Download JRE transcripts from ScribeSalad")
    parser.add_argument(
        "--clone-dir",
        type=Path,
        default=CLONE_DIR,
        help=f"Directory to clone repo (default: {CLONE_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Directory for converted transcripts (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading, only convert existing files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of transcripts to convert",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("ScribeSalad JRE Transcript Downloader")
    print("=" * 50)
    print()

    # Step 1: Clone/update repository
    if not args.skip_download:
        print("Step 1: Downloading from GitHub...")
        if not clone_or_update_repo(args.clone_dir):
            print("Failed to download repository.")
            print("\nAlternative: manually clone the repo:")
            print(f"  git clone --depth=1 {REPO_URL} {args.clone_dir}")
            sys.exit(1)
        print()

    # Step 2: Find transcript files
    print("Step 2: Finding JRE transcript files...")
    files = find_transcript_files(args.clone_dir)
    print(f"  Found {len(files)} transcript files")

    if not files:
        print("\nNo transcript files found. Make sure the repo was cloned correctly.")
        print(f"Expected paths: {JRE_PATHS}")
        sys.exit(1)

    # Apply limit
    if args.limit:
        files = files[:args.limit]
        print(f"  Limited to {args.limit} files")
    print()

    # Step 3: Convert to JSON
    print("Step 3: Converting transcripts to JSON...")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    skipped = 0

    for i, filepath in enumerate(files, 1):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(files)}")

        transcript = convert_transcript(filepath)
        if transcript is None:
            skipped += 1
            continue

        # Save JSON file
        out_name = f"jre-{transcript['episode_number']:04d}-{filepath.stem}.json"
        out_path = args.output_dir / out_name

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, indent=2, ensure_ascii=False)

        success += 1

    print()
    print("=" * 50)
    print(f"Done! Converted {success} transcripts")
    print(f"  Skipped: {skipped} (empty or too short)")
    print(f"  Output: {args.output_dir}")
    print()
    print("Next steps:")
    print("  1. python scripts/process_chunks.py")
    print("  2. python scripts/embed_and_index.py")


if __name__ == "__main__":
    main()
