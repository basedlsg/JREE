#!/usr/bin/env python3
"""Fetch metadata for all JRE videos from YouTube Data API.

This script fetches video titles and metadata for all YouTube IDs found
in the ScribeSalad transcripts, then extracts episode numbers and guest names.

Usage:
    # First, set your YouTube API key:
    export YOUTUBE_API_KEY="your-api-key-here"

    # Then run:
    python scripts/fetch_youtube_metadata.py

To get a YouTube API key:
1. Go to https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Enable "YouTube Data API v3"
4. Create credentials -> API Key
5. Copy the key and set as YOUTUBE_API_KEY environment variable
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error


def get_youtube_video_info(video_ids: list[str], api_key: str) -> dict[str, dict]:
    """Fetch video info from YouTube Data API for a batch of video IDs.

    Args:
        video_ids: List of YouTube video IDs (max 50 per request)
        api_key: YouTube Data API key

    Returns:
        Dict mapping video_id -> {title, description, channelTitle, publishedAt}
    """
    if not video_ids:
        return {}

    # YouTube API allows up to 50 IDs per request
    ids_param = ",".join(video_ids[:50])
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={ids_param}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        if e.code == 403:
            print("API quota exceeded or invalid API key")
        return {}
    except Exception as e:
        print(f"Error fetching videos: {e}")
        return {}

    results = {}
    for item in data.get("items", []):
        video_id = item["id"]
        snippet = item.get("snippet", {})
        results[video_id] = {
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channelTitle": snippet.get("channelTitle", ""),
            "publishedAt": snippet.get("publishedAt", ""),
        }

    return results


def parse_jre_title(title: str) -> dict:
    """Parse a JRE video title to extract episode number and guest.

    Examples:
        "Joe Rogan Experience #1169 - Elon Musk" -> {episode: 1169, guest: "Elon Musk"}
        "JRE #1169 - Elon Musk" -> {episode: 1169, guest: "Elon Musk"}
        "Joe Rogan Experience - 2018 Year in Review" -> {episode: 0, guest: "2018 Year in Review"}
    """
    result = {"episode_number": 0, "guest": "Unknown", "title": title}

    if not title:
        return result

    # Try to extract episode number
    # Patterns: "#1169", "Episode 1169", "#1169 -", etc.
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

    # Try to extract guest name
    # Usually after " - " in the title
    guest_patterns = [
        r'(?:Joe Rogan Experience|JRE)\s*(?:#\d+)?\s*[-–—]\s*(.+?)(?:\s*\||$)',
        r'#\d+\s*[-–—]\s*(.+?)(?:\s*\||$)',
        r'[-–—]\s*(.+?)(?:\s*\||$)',
    ]

    for pattern in guest_patterns:
        match = re.search(pattern, title)
        if match:
            guest = match.group(1).strip()
            # Clean up common suffixes
            guest = re.sub(r'\s*\(.*?\)\s*$', '', guest)  # Remove parenthetical notes
            guest = guest.strip(' -–—')
            if guest and guest.lower() not in ['joe rogan', 'jre']:
                result["guest"] = guest
                break

    return result


def fetch_all_metadata(srt_dir: Path, api_key: str, cache_file: Path) -> dict[str, dict]:
    """Fetch metadata for all videos, using cache when available.

    Args:
        srt_dir: Directory containing SRT files named by YouTube ID
        api_key: YouTube Data API key
        cache_file: JSON file to cache API responses

    Returns:
        Dict mapping youtube_id -> {episode_number, guest, title, youtube_id}
    """
    # Load existing cache
    cache = {}
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached entries")

    # Get all video IDs from SRT files
    all_ids = []
    for srt_file in srt_dir.glob("*.srt"):
        video_id = srt_file.stem
        all_ids.append(video_id)

    print(f"Found {len(all_ids)} SRT files")

    # Find IDs that need to be fetched
    missing_ids = [vid for vid in all_ids if vid not in cache]
    print(f"Need to fetch metadata for {len(missing_ids)} videos")

    if missing_ids and api_key:
        # Fetch in batches of 50
        batch_size = 50
        for i in range(0, len(missing_ids), batch_size):
            batch = missing_ids[i:i + batch_size]
            print(f"Fetching batch {i // batch_size + 1}/{(len(missing_ids) + batch_size - 1) // batch_size}...")

            results = get_youtube_video_info(batch, api_key)

            for video_id, info in results.items():
                parsed = parse_jre_title(info["title"])
                cache[video_id] = {
                    "episode_number": parsed["episode_number"],
                    "guest": parsed["guest"],
                    "title": info["title"],
                    "youtube_id": video_id,
                    "raw_youtube_data": info,
                }

            # Mark videos that weren't found (private, deleted, etc.)
            for video_id in batch:
                if video_id not in cache:
                    cache[video_id] = {
                        "episode_number": 0,
                        "guest": "Unknown",
                        "title": f"JRE - {video_id}",
                        "youtube_id": video_id,
                        "not_found": True,
                    }

            # Save cache after each batch
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)

            # Rate limit: ~3 requests per second max
            time.sleep(0.5)
    elif missing_ids and not api_key:
        print("WARNING: No YOUTUBE_API_KEY set. Using fallback metadata for missing videos.")
        for video_id in missing_ids:
            cache[video_id] = {
                "episode_number": 0,
                "guest": "Unknown",
                "title": f"JRE - {video_id}",
                "youtube_id": video_id,
                "no_api_key": True,
            }

    # Build final metadata dict
    metadata = {}
    for video_id in all_ids:
        if video_id in cache:
            entry = cache[video_id]
            metadata[video_id] = {
                "episode_number": entry.get("episode_number", 0),
                "guest": entry.get("guest", "Unknown"),
                "title": entry.get("title", f"JRE - {video_id}"),
                "youtube_id": video_id,
            }

    return metadata


def merge_with_readme_metadata(metadata: dict, readme_metadata: dict) -> dict:
    """Merge YouTube API metadata with README metadata, preferring README where available.

    The README metadata from ScribeSalad is more reliable for episode numbers.
    """
    merged = {}

    for video_id, info in metadata.items():
        if video_id in readme_metadata:
            # README has this video - prefer its data
            readme_info = readme_metadata[video_id]
            merged[video_id] = {
                "episode_number": readme_info.get("episode_number", 0) or info.get("episode_number", 0),
                "guest": readme_info.get("guest", "Unknown") if readme_info.get("guest") != "Unknown" else info.get("guest", "Unknown"),
                "title": readme_info.get("title", info.get("title", "")),
                "youtube_id": video_id,
            }
        else:
            merged[video_id] = info

    return merged


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch YouTube metadata for JRE videos")
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
        help="Path to ScribeSalad README.md for existing metadata",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path("data/youtube_metadata_cache.json"),
        help="Cache file for YouTube API responses",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/episode_metadata_full.json"),
        help="Output JSON file with all metadata",
    )
    args = parser.parse_args()

    # Get API key from environment
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        print("WARNING: YOUTUBE_API_KEY environment variable not set.")
        print("Will use cached data and README metadata only.")
        print("\nTo fetch fresh metadata, get an API key from:")
        print("https://console.cloud.google.com/apis/credentials")
        print("Then run: export YOUTUBE_API_KEY='your-key-here'\n")

    # Load README metadata first
    readme_metadata = {}
    if args.readme.exists():
        print(f"Loading metadata from {args.readme}...")
        from parse_metadata import parse_readme
        readme_metadata = parse_readme(args.readme)
        print(f"Found {len(readme_metadata)} entries in README")

    # Fetch YouTube metadata
    print(f"\nFetching metadata for videos in {args.srt_dir}...")
    youtube_metadata = fetch_all_metadata(args.srt_dir, api_key, args.cache)

    # Merge both sources
    print("\nMerging metadata sources...")
    merged = merge_with_readme_metadata(youtube_metadata, readme_metadata)

    # Save final metadata
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    print(f"\nSaved {len(merged)} entries to {args.output}")

    # Stats
    with_episode = sum(1 for m in merged.values() if m["episode_number"] > 0)
    with_guest = sum(1 for m in merged.values() if m["guest"] != "Unknown")
    print(f"\nStats:")
    print(f"  Total videos: {len(merged)}")
    print(f"  With episode number: {with_episode}")
    print(f"  With guest name: {with_guest}")

    # Sample output
    print("\nSample entries:")
    for i, (vid, info) in enumerate(list(merged.items())[:5]):
        print(f"  {vid}: #{info['episode_number']} - {info['guest']}")


if __name__ == "__main__":
    main()
