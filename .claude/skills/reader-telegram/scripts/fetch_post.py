#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.10"
# dependencies = ["beautifulsoup4"]
# ///

"""
Fetch Telegram channel post content by URL.
Extracts text with inline links preserved, metadata, and media URLs.

Usage:
    uv run scripts/fetch_post.py <post_url>
    uv run scripts/fetch_post.py <url1> <url2> ...

Example:
    uv run scripts/fetch_post.py https://t.me/aiwizards/397
"""

import sys
import re
import argparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from bs4 import BeautifulSoup, NavigableString, Tag


def parse_telegram_url(url: str) -> tuple[str, str]:
    """Extract channel and post_id from Telegram URL."""
    pattern = r'https?://(?:t\.me|telegram\.me)/([a-zA-Z][a-zA-Z0-9_]{3,})/(\d+)'
    match = re.match(pattern, url)
    if not match:
        raise ValueError(
            f"Invalid Telegram URL: {url}\n"
            f"Expected format: https://t.me/channel/post_id"
        )
    return match.group(1), match.group(2)


def fetch_embed_html(channel: str, post_id: str) -> str:
    """Fetch post embed page HTML."""
    embed_url = f"https://t.me/{channel}/{post_id}?embed=1&mode=tme"
    req = Request(embed_url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; TelegramReader/1.0)",
    })

    try:
        with urlopen(req, timeout=15) as resp:
            return resp.read().decode()
    except HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Post not found: {channel}/{post_id}")
        raise ValueError(f"HTTP error {e.code}: {e.reason}")
    except URLError as e:
        raise ValueError(f"Network error: {e.reason}")


def html_to_markdown(element) -> str:
    """Convert Telegram's HTML subset to Markdown, preserving links."""
    if isinstance(element, NavigableString):
        return str(element)

    if not isinstance(element, Tag):
        return ""

    tag = element.name
    children = "".join(html_to_markdown(child) for child in element.children)

    if tag == "br":
        return "\n"
    if tag == "b" or tag == "strong":
        return f"**{children}**"
    if tag == "i" or tag == "em":
        return f"*{children}*"
    if tag == "s" or tag == "del":
        return f"~~{children}~~"
    if tag == "u":
        return children  # Markdown has no underline, pass through
    if tag == "code":
        return f"`{children}`"
    if tag == "pre":
        return f"\n```\n{children}\n```\n"
    if tag == "a":
        href = element.get("href", "")
        if href and children.strip():
            return f"[{children}]({href})"
        return children
    if tag == "blockquote":
        lines = children.strip().split("\n")
        return "\n".join(f"> {line}" for line in lines)

    return children


def parse_post(html: str) -> dict:
    """Parse embed HTML and extract post data."""
    soup = BeautifulSoup(html, "html.parser")

    data = {
        "channel": "",
        "date": "",
        "views": "",
        "text": "",
        "reactions": [],
        "images": [],
        "forwarded_from": "",
    }

    # Channel name
    owner = soup.select_one(".tgme_widget_message_owner_name span")
    if owner:
        data["channel"] = owner.get_text(strip=True)

    # Date
    time_el = soup.select_one("time.datetime")
    if time_el:
        data["date"] = time_el.get("datetime", time_el.get_text(strip=True))

    # Views
    views_el = soup.select_one(".tgme_widget_message_views")
    if views_el:
        data["views"] = views_el.get_text(strip=True)

    # Forwarded from
    fwd = soup.select_one(".tgme_widget_message_forwarded_from_name")
    if fwd:
        data["forwarded_from"] = fwd.get_text(strip=True)

    # Post text (HTML → Markdown)
    text_el = soup.select_one(".tgme_widget_message_text")
    if text_el:
        data["text"] = html_to_markdown(text_el).strip()

    # Reactions
    for reaction_el in soup.select(".tgme_widget_message_reactions .tgme_reaction"):
        emoji_el = reaction_el.select_one(".emoji b")
        emoji = emoji_el.get_text(strip=True) if emoji_el else ""
        # Count is the text node after the emoji element
        count_text = reaction_el.get_text(strip=True)
        # Extract just the number from the end
        count_match = re.search(r'(\d+)$', count_text)
        count = count_match.group(1) if count_match else ""
        if emoji and count:
            data["reactions"].append(f"{emoji} {count}")

    # Images
    for photo_el in soup.select(".tgme_widget_message_photo_wrap"):
        style = photo_el.get("style", "")
        url_match = re.search(r"background-image:url\('([^']+)'\)", style)
        if url_match:
            data["images"].append(url_match.group(1))

    return data


def format_post(data: dict, url: str) -> str:
    """Format parsed post data as Markdown."""
    lines = []

    # Header
    channel = data["channel"] or "Unknown Channel"
    lines.append(f"# {channel}")
    lines.append(f"**URL:** {url}")

    if data["date"]:
        lines.append(f"**Date:** {data['date']}")
    if data["views"]:
        lines.append(f"**Views:** {data['views']}")
    if data["reactions"]:
        lines.append(f"**Reactions:** {' | '.join(data['reactions'])}")
    if data["forwarded_from"]:
        lines.append(f"**Forwarded from:** {data['forwarded_from']}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Text
    if data["text"]:
        lines.append(data["text"])
    else:
        lines.append("*[No text content]*")

    # Images
    if data["images"]:
        lines.append("")
        lines.append("**Images:**")
        for i, img_url in enumerate(data["images"], 1):
            lines.append(f"- Image {i}: {img_url}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch Telegram channel post content")
    parser.add_argument("urls", nargs="+", help="Telegram post URL(s)")
    args = parser.parse_args()

    results = []
    errors = []

    for url in args.urls:
        try:
            channel, post_id = parse_telegram_url(url)
            html = fetch_embed_html(channel, post_id)
            data = parse_post(html)
            if not data["channel"] and not data["text"]:
                raise ValueError(f"Post not found or empty: {channel}/{post_id}")
            results.append(format_post(data, url))
        except ValueError as e:
            errors.append(str(e))
            print(f"Error: {e}", file=sys.stderr)

    if results:
        print("\n\n===\n\n".join(results))

    if errors and not results:
        sys.exit(1)


if __name__ == "__main__":
    main()
