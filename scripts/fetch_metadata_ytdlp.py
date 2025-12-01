#!/usr/bin/env python3
"""Fetch metadata for all JRE videos using yt-dlp (no API key needed).

This is slower than the YouTube API but doesn't require authentication.
For 2000+ videos, this will take several hours.

Usage:
    python scripts/fetch_metadata_ytdlp.py
"""

import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional


def get_video_info_ytdlp(video_id: str) -> Optional[dict]:
    """Fetch video info using yt-dlp.

    Args:
        video_id: YouTube video ID

    Returns:
        Dict with video metadata or None if not found
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--skip-download",
                "--print", "%(title)s",
                "--print", "%(uploader)s",
                "--print", "%(upload_date)s",
                "--no-warnings",
                "-q",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return None

        lines = result.stdout.strip().split("\n")
        if len(lines) >= 1:
            return {
                "title": lines[0] if len(lines) > 0 else "",
                "uploader": lines[1] if len(lines) > 1 else "",
                "upload_date": lines[2] if len(lines) > 2 else "",
            }
    except subprocess.TimeoutExpired:
        print(f"  Timeout for {video_id}")
    except Exception as e:
        print(f"  Error for {video_id}: {e}")

    return None


def parse_jre_title(title: str) -> dict:
    """Parse a JRE video title to extract episode number and guest."""
    result = {"episode_number": 0, "guest": "Unknown", "title": title}

    if not title:
        return result

    # Try to extract episode number
    ep_patterns = [
        r'#(\d+)',
        r'Episode\s+(\d+)',
        r'Ep\s*\.?\s*(\d+)',
        r'JRE\s*(\d+)',
    ]

    for pattern in ep_patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            result["episode_number"] = int(match.group(1))
            break

    # Try to extract guest name (after " - ")
    guest_patterns = [
        r'(?:Joe Rogan Experience|JRE)\s*(?:#\d+)?\s*[-–—]\s*(.+?)(?:\s*\||$)',
        r'#\d+\s*[-–—]\s*(.+?)(?:\s*\||$)',
        r'[-–—]\s*(.+?)(?:\s*\||$)',
    ]

    for pattern in guest_patterns:
        match = re.search(pattern, title)
        if match:
            guest = match.group(1).strip()
            guest = re.sub(r'\s*\(.*?\)\s*$', '', guest)
            guest = guest.strip(' -–—')
            if guest and guest.lower() not in ['joe rogan', 'jre']:
                result["guest"] = guest
                break

    return result


def fetch_single_video(video_id: str, cache: dict) -> tuple[str, dict]:
    """Fetch metadata for a single video."""
    if video_id in cache:
        return video_id, cache[video_id]

    info = get_video_info_ytdlp(video_id)

    if info:
        parsed = parse_jre_title(info["title"])
        result = {
            "episode_number": parsed["episode_number"],
            "guest": parsed["guest"],
            "title": info["title"],
            "youtube_id": video_id,
        }
    else:
        result = {
            "episode_number": 0,
            "guest": "Unknown",
            "title": f"JRE - {video_id}",
            "youtube_id": video_id,
            "not_found": True,
        }

    return video_id, result


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch YouTube metadata using yt-dlp")
    parser.add_argument(
        "--srt-dir",
        type=Path,
        default=Path("data/scribesalad/transcripts/en/Joe_Rogan_Experience/srt"),
        help="Directory containing SRT files",
    )
    parser.add_argument(
        "--readme",
        type=Path,
        default=Path("data/scribesalad/transcripts/en/Joe_Rogan_Experience/README.md"),
        help="Path to ScribeSalad README.md",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path("data/youtube_metadata_cache.json"),
        help="Cache file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/episode_metadata_full.json"),
        help="Output JSON file",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of videos to fetch (0 = all)",
    )
    args = parser.parse_args()

    # Load README metadata first (this is reliable)
    readme_metadata = {}
    if args.readme.exists():
        print(f"Loading metadata from {args.readme}...")
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from parse_metadata import parse_readme
        readme_metadata = parse_readme(args.readme)
        print(f"Found {len(readme_metadata)} entries in README")

    # Load cache
    cache = {}
    if args.cache.exists():
        with open(args.cache, "r", encoding="utf-8") as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached entries")

    # Get all video IDs
    all_ids = [f.stem for f in args.srt_dir.glob("*.srt")]
    print(f"Found {len(all_ids)} SRT files")

    # Merge README metadata into cache (README is more reliable)
    for video_id, info in readme_metadata.items():
        cache[video_id] = {
            "episode_number": info["episode_number"],
            "guest": info["guest"],
            "title": info["title"],
            "youtube_id": video_id,
            "source": "readme",
        }

    # Find videos that still need fetching
    missing_ids = [vid for vid in all_ids if vid not in cache]
    print(f"Need to fetch metadata for {len(missing_ids)} videos")

    if args.limit > 0:
        missing_ids = missing_ids[:args.limit]
        print(f"Limited to {args.limit} videos")

    # Fetch missing metadata
    if missing_ids:
        print(f"\nFetching metadata with {args.workers} workers...")
        completed = 0

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(fetch_single_video, vid, cache): vid
                for vid in missing_ids
            }

            for future in as_completed(futures):
                video_id, result = future.result()
                cache[video_id] = result
                completed += 1

                if completed % 10 == 0:
                    print(f"  Progress: {completed}/{len(missing_ids)}")
                    # Save cache periodically
                    with open(args.cache, "w", encoding="utf-8") as f:
                        json.dump(cache, f, indent=2)

        # Final cache save
        with open(args.cache, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)

    # Build final metadata
    metadata = {}
    for video_id in all_ids:
        if video_id in cache:
            metadata[video_id] = {
                "episode_number": cache[video_id].get("episode_number", 0),
                "guest": cache[video_id].get("guest", "Unknown"),
                "title": cache[video_id].get("title", f"JRE - {video_id}"),
                "youtube_id": video_id,
            }
        else:
            metadata[video_id] = {
                "episode_number": 0,
                "guest": "Unknown",
                "title": f"JRE - {video_id}",
                "youtube_id": video_id,
            }

    # Save output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"\nSaved {len(metadata)} entries to {args.output}")

    # Stats
    with_episode = sum(1 for m in metadata.values() if m["episode_number"] > 0)
    with_guest = sum(1 for m in metadata.values() if m["guest"] != "Unknown")
    print(f"\nStats:")
    print(f"  Total videos: {len(metadata)}")
    print(f"  With episode number: {with_episode} ({100*with_episode/len(metadata):.1f}%)")
    print(f"  With guest name: {with_guest} ({100*with_guest/len(metadata):.1f}%)")


if __name__ == "__main__":
    main()
