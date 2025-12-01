#!/usr/bin/env python3
"""Parse the ScribeSalad README.md to extract JRE episode metadata.

Creates a lookup table mapping YouTube video IDs to episode info.
"""

import json
import re
from pathlib import Path


def parse_readme(readme_path: Path) -> dict[str, dict]:
    """Parse README.md and extract episode metadata.

    Returns:
        Dict mapping youtube_id -> {episode_number, title, guest}
    """
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    metadata = {}

    # Pattern to match table rows like:
    # | Joe Rogan Experience #1220 - Joey Diaz | [txt](./txt/ll4E3-kP_54.txt) | ...
    # Also handles titles without episode numbers
    pattern = r'\|\s*(.+?)\s*\|\s*\[txt\]\(\./txt/([^)]+)\.txt\)'

    for match in re.finditer(pattern, content):
        title_full = match.group(1).strip()
        youtube_id = match.group(2).strip()

        # Extract episode number from title
        ep_match = re.search(r'#(\d+)', title_full)
        episode_number = int(ep_match.group(1)) if ep_match else 0

        # Extract guest name (after the dash)
        guest = "Unknown"
        if ' - ' in title_full:
            parts = title_full.split(' - ', 1)
            if len(parts) > 1:
                guest = parts[1].strip()

        # Clean up title
        title = title_full

        metadata[youtube_id] = {
            "episode_number": episode_number,
            "title": title,
            "guest": guest,
            "youtube_id": youtube_id,
        }

    return metadata


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Parse ScribeSalad README for metadata")
    parser.add_argument(
        "--readme",
        type=Path,
        default=Path("data/scribesalad/transcripts/en/Joe_Rogan_Experience/README.md"),
        help="Path to README.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/episode_metadata.json"),
        help="Output JSON file",
    )
    args = parser.parse_args()

    print(f"Parsing {args.readme}...")
    metadata = parse_readme(args.readme)

    print(f"Found {len(metadata)} episodes")

    # Save to JSON
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved to {args.output}")

    # Show some examples
    print("\nSample entries:")
    for i, (yt_id, info) in enumerate(list(metadata.items())[:5]):
        print(f"  {yt_id}: #{info['episode_number']} - {info['guest']}")


if __name__ == "__main__":
    main()
