---
name: reader-twitter
description: "Fetch Twitter/X post content by URL. Use when the user provides a Twitter/X URL (x.com, twitter.com) or asks to read a tweet, post, or thread. Also trigger when: (1) user shares an x.com or twitter.com link, (2) user says 'прочитай твит', 'что в этом посте', 'посмотри в X', (3) a Twitter/X post needs to be analyzed or summarized. Returns author, text, engagement metrics, and media descriptions."
---

# Twitter Reader

Fetch Twitter/X post content without needing authentication or API keys. Single tweets via FXTwitter API, threads via Thread Reader App + Jina Reader.

## Usage

```bash
# Single tweet
uv run scripts/fetch_tweet.py "TWEET_URL"

# Multiple tweets
uv run scripts/fetch_tweet.py "URL1" "URL2" "URL3"

# Full thread
uv run scripts/fetch_tweet.py --thread "TWEET_URL"
```

## The Iron Law

**NEVER modify the tweet text.** Output it exactly as received from the API. Summarize or analyze only AFTER presenting the original text to the user.

## When to Use `--thread`

Use `--thread` when the user mentions: "тред", "thread", "весь тред", "all posts", or when the tweet is clearly part of a thread (multiple connected posts by the same author). The script will hint if a tweet has many replies.

## URL Formats Supported

- `https://x.com/USER/status/ID`
- `https://twitter.com/USER/status/ID`

## Output Example (single tweet)

```
# Boris Cherny (@bcherny)
**URL:** https://x.com/bcherny/status/2021699851499798911
**Date:** Wed Feb 11 21:36:20 +0000 2026
**Likes:** 4,267 | **Retweets:** 362 | **Replies:** 155 | **Views:** 505,623

---

Reflecting on what engineers love about Claude Code, one thing that jumps out is its customizability...
```

Includes: author name and handle, original URL, date, engagement stats, full tweet text, media URLs if present, quoted tweet if present.

## After Getting Tweet Content

1. Present the formatted output to the user
2. Then — and only then — analyze, summarize, or process if the user asked for it

## Limitations

- Only public tweets (protected accounts will return errors)
- Depends on FXTwitter and Thread Reader App service availability
- No search capability — only fetches by URL
- Thread mode is slower (~30 sec) due to Thread Reader App + Jina processing

## Related Skills

- **reader-youtube** — аналогичный скилл для извлечения контента из YouTube видео по URL
- **reader-jina** — general fallback для чтения любых JS-heavy страниц
