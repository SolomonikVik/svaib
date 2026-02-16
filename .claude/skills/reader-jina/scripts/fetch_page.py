#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Read any web page as clean Markdown via Jina Reader API.
Useful for JS-heavy sites where WebFetch fails.

Usage:
    uv run scripts/fetch_page.py <url>
    uv run scripts/fetch_page.py <url1> <url2> ...

Example:
    uv run scripts/fetch_page.py https://example.com/some-page
"""

import sys
import argparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


def fetch_page(url: str) -> str:
    """Fetch page content as Markdown via Jina Reader."""
    jina_url = f"https://r.jina.ai/{url}"
    req = Request(jina_url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/markdown",
    })

    try:
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode()
    except HTTPError as e:
        raise ValueError(f"Jina Reader error {e.code} for {url}: {e.reason}")
    except URLError as e:
        raise ValueError(f"Network error for {url}: {e.reason}")


def main():
    parser = argparse.ArgumentParser(description="Read web page as Markdown via Jina Reader")
    parser.add_argument("urls", nargs="+", help="URL(s) to read")
    args = parser.parse_args()

    results = []
    errors = []

    for url in args.urls:
        try:
            results.append(fetch_page(url))
        except ValueError as e:
            errors.append(str(e))
            print(f"Error: {e}", file=sys.stderr)

    if results:
        print("\n\n===\n\n".join(results))

    if errors and not results:
        sys.exit(1)


if __name__ == "__main__":
    main()
