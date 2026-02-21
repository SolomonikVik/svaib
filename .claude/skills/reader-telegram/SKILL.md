---
name: reader-telegram
description: "Fetch Telegram channel post content by URL. Use when the user provides a Telegram URL (t.me, telegram.me) or asks to read a post from a Telegram channel. Also trigger when: (1) user shares a t.me link, (2) user says 'прочитай пост', 'что в этом посте в телеге', 'посмотри в телеграме', (3) a Telegram post needs to be analyzed or summarized. Returns post text with inline links preserved, author, date, views, and reactions."
---

# Telegram Post Reader

Fetch public Telegram channel posts with full text and inline links preserved. Uses embed page parsing — no API keys needed.

## Usage

```bash
# Single post
uv run scripts/fetch_post.py "POST_URL"

# Multiple posts
uv run scripts/fetch_post.py "URL1" "URL2" "URL3"
```

## The Iron Law

**NEVER modify the post text.** Output it exactly as received from the page. Summarize or analyze only AFTER presenting the original text to the user.

## URL Formats Supported

- `https://t.me/channel/post_id`
- `https://telegram.me/channel/post_id`

## Output Example

```
# Anton Vdovitchenko — Ai Agents
**URL:** https://t.me/aiwizards/397
**Date:** 2026-02-17T16:22:30+00:00
**Views:** 810
**Reactions:** ❤ 9 | 💯 8 | 👍 4 | 🔥 1

---

**Software On Demand.** Привет, друзья! ...
Помните историю про [ClawdBot](https://github.com/openclaw/openclaw)...
```

## After Getting Post Content

1. Present the formatted output to the user
2. Then — and only then — analyze, summarize, or process if the user asked for it

## Limitations

- Only public channels (private channels/groups will return errors)
- Media returned as URLs, not downloaded
- Depends on Telegram embed page availability
- No search capability — only fetches by URL

## Related Skills

- **reader-twitter** — tweets and threads from X/Twitter
- **reader-youtube** — video transcript extraction from YouTube
- **reader-jina** — general fallback for JS-heavy web pages
