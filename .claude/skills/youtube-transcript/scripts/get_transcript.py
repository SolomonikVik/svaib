#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.10"
# dependencies = ["youtube-transcript-api>=1.0.0"]
# ///

"""
Extract transcript and metadata from a YouTube video.

Usage:
    uv run scripts/get_transcript.py <video_url_or_id>
    uv run scripts/get_transcript.py <video_url_or_id> --timestamps
    uv run scripts/get_transcript.py <video_url_or_id> --lang ru,en
    uv run scripts/get_transcript.py <video_url_or_id> --timestamps --lang en,ru
"""

import sys
import re
import json
import argparse
from urllib.request import urlopen, Request
from urllib.error import URLError
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from: {url_or_id}")


def get_metadata(video_id: str) -> dict:
    """Fetch video metadata via YouTube oEmbed API (no API key needed)."""
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return {
                "title": data.get("title", ""),
                "author": data.get("author_name", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
    except (URLError, json.JSONDecodeError, KeyError):
        return {
            "title": "",
            "author": "",
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def get_transcript(video_id: str, languages: list[str], with_timestamps: bool = False) -> str:
    """Fetch and format transcript for a YouTube video."""
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id, languages=languages)

    if with_timestamps:
        lines = [f"[{format_timestamp(s.start)}] {s.text}" for s in transcript.snippets]
    else:
        lines = [s.text for s in transcript.snippets]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Get YouTube video transcript")
    parser.add_argument("video", help="YouTube video URL or video ID")
    parser.add_argument("--timestamps", "-t", action="store_true", help="Include timestamps")
    parser.add_argument("--lang", "-l", default="ru,en", help="Language priority, comma-separated (default: ru,en)")
    args = parser.parse_args()

    languages = [lang.strip() for lang in args.lang.split(",")]

    try:
        video_id = extract_video_id(args.video)
        meta = get_metadata(video_id)
        transcript = get_transcript(video_id, languages, with_timestamps=args.timestamps)

        # Print metadata header
        if meta["title"]:
            print(f"# {meta['title']}")
        if meta["author"]:
            print(f"**Channel:** {meta['author']}")
        print(f"**URL:** {meta['url']}")
        print(f"**Video ID:** {video_id}")
        print(f"**Languages requested:** {', '.join(languages)}")
        print()
        print("---")
        print()
        print(transcript)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
