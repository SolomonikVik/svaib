---
name: reader-jina
description: "Read any web page as clean Markdown. Use when WebFetch fails on JS-heavy sites, or when the user asks to read a page that requires JavaScript rendering. Trigger when: (1) WebFetch returns empty/broken content, (2) user shares a URL from a JS-heavy site (SPA, dashboards), (3) user says 'прочитай страницу', 'что на этой странице'. Returns page content as Markdown."
---

# Jina Reader

Read any web page as clean Markdown via Jina Reader API (`r.jina.ai`). Fallback for when WebFetch fails on JS-heavy sites.

## Usage

```bash
uv run scripts/fetch_page.py "URL"
uv run scripts/fetch_page.py "URL1" "URL2"
```

## The Iron Law

**Try WebFetch first.** reader-jina is a fallback, not a replacement. Use only when WebFetch returns empty, broken, or incomplete content.

## How It Works

Prepends `https://r.jina.ai/` to the target URL. Jina renders the page (including JavaScript) and returns clean Markdown.

## Limitations

- Free tier: 200 requests per minute (no API key needed)
- Public pages only (no authentication passthrough)
- Timeout: 30 seconds (some heavy pages may fail)
- Content may be summarized for very large pages

## Related Skills

- **reader-twitter** — specialized skill for Twitter/X posts and threads
- **reader-youtube** — transcript extraction from YouTube videos
