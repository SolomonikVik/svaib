#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Fetch Twitter/X post content using FXTwitter API.
For threads, uses Thread Reader App via Jina Reader.

Usage:
    uv run scripts/fetch_tweet.py <tweet_url>
    uv run scripts/fetch_tweet.py <tweet_url1> <tweet_url2> ...
    uv run scripts/fetch_tweet.py --thread <tweet_url>

Example:
    uv run scripts/fetch_tweet.py https://x.com/bcherny/status/2021699851499798911
    uv run scripts/fetch_tweet.py --thread https://x.com/bcherny/status/2021699851499798911
"""

import sys
import re
import json
import argparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


def parse_tweet_url(url: str) -> tuple[str, str]:
    """Extract username and tweet_id from Twitter/X URL."""
    pattern = r'https?://(?:x\.com|twitter\.com)/(\w+)/status/(\d+)'
    match = re.match(pattern, url)
    if not match:
        raise ValueError(f"Invalid Twitter/X URL: {url}\nExpected format: https://x.com/USER/status/ID")
    return match.group(1), match.group(2)


def fetch_tweet(username: str, tweet_id: str) -> dict:
    """Fetch tweet data from FXTwitter API."""
    api_url = f"https://api.fxtwitter.com/{username}/status/{tweet_id}"
    req = Request(api_url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Tweet not found: {username}/status/{tweet_id}")
        raise ValueError(f"API error {e.code}: {e.reason}")
    except URLError as e:
        raise ValueError(f"Network error: {e.reason}")

    if data.get("code") != 200 or not data.get("tweet"):
        raise ValueError(f"Tweet not found or unavailable: {username}/status/{tweet_id}")

    return data["tweet"]


def fetch_thread(tweet_id: str) -> str:
    """Fetch full thread via Thread Reader App + Jina Reader."""
    api_url = f"https://r.jina.ai/https://threadreaderapp.com/thread/{tweet_id}.html"
    req = Request(api_url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/markdown",
    })

    try:
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode()
    except HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Thread not found: {tweet_id}. Make sure it's a thread, not a single tweet.")
        raise ValueError(f"Thread Reader error {e.code}: {e.reason}")
    except URLError as e:
        raise ValueError(f"Network error fetching thread: {e.reason}")


def format_tweet(tweet: dict) -> str:
    """Format tweet data as Markdown."""
    author = tweet.get("author", {})
    name = author.get("name", "Unknown")
    screen_name = author.get("screen_name", "unknown")
    text = tweet.get("text", "")
    created = tweet.get("created_at", "")
    url = tweet.get("url", "")

    likes = tweet.get("likes", 0)
    retweets = tweet.get("retweets", 0)
    replies = tweet.get("replies", 0)
    views = tweet.get("views")

    lines = [
        f"# {name} (@{screen_name})",
        f"**URL:** {url}",
        f"**Date:** {created}",
    ]

    stats = f"**Likes:** {likes:,} | **Retweets:** {retweets:,} | **Replies:** {replies:,}"
    if views:
        stats += f" | **Views:** {views:,}"
    lines.append(stats)

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(text)

    # Media
    media = tweet.get("media") or {}
    photos = media.get("photos") or []
    videos = media.get("videos") or []

    if photos or videos:
        lines.append("")
        lines.append("**Media:**")
        for i, photo in enumerate(photos, 1):
            lines.append(f"- Image {i}: {photo.get('url', 'N/A')}")
        for i, video in enumerate(videos, 1):
            lines.append(f"- Video {i}: {video.get('url', 'N/A')}")

    # Quote tweet
    quote = tweet.get("quote")
    if quote:
        q_author = quote.get("author", {})
        lines.append("")
        lines.append(f"> **Quoted @{q_author.get('screen_name', '?')}:** {quote.get('text', '')}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch Twitter/X post content")
    parser.add_argument("urls", nargs="+", help="Twitter/X post URL(s)")
    parser.add_argument("--thread", action="store_true", help="Fetch full thread via Thread Reader App")
    args = parser.parse_args()

    results = []
    errors = []

    for url in args.urls:
        try:
            username, tweet_id = parse_tweet_url(url)

            if args.thread:
                results.append(fetch_thread(tweet_id))
            else:
                tweet = fetch_tweet(username, tweet_id)
                results.append(format_tweet(tweet))
                # Hint: suggest --thread if tweet has many replies
                replies = tweet.get("replies", 0)
                if replies > 5:
                    print(f"Hint: This tweet has {replies} replies. If it's a thread, re-run with --thread", file=sys.stderr)
        except ValueError as e:
            errors.append(str(e))
            print(f"Error: {e}", file=sys.stderr)

    if results:
        print("\n\n===\n\n".join(results))

    if errors and not results:
        sys.exit(1)


if __name__ == "__main__":
    main()
