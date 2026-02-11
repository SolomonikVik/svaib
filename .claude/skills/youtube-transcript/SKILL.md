---
name: youtube-transcript
description: "Use when the user provides a YouTube URL (youtube.com, youtu.be, shorts, embed) or asks to get a transcript, subtitles, or captions from a YouTube video. Also trigger when: (1) user shares a YouTube link and wants to know what's in it, (2) user says 'посмотри видео', 'что в этом видео', 'достань транскрипт', (3) a YouTube video needs to be analyzed or summarized. Extracts transcript text and video metadata (title, channel)."
---

# YouTube Transcript

Extract transcript and metadata from YouTube videos using `youtube-transcript-api`.

## Usage

```bash
uv run scripts/get_transcript.py "VIDEO_URL_OR_ID"
uv run scripts/get_transcript.py "VIDEO_URL_OR_ID" --timestamps
uv run scripts/get_transcript.py "VIDEO_URL_OR_ID" --lang en,ru
```

## Parameters

| Flag | Default | What it does |
|------|---------|-------------|
| `--timestamps` / `-t` | off | Add `[MM:SS]` before each line |
| `--lang` / `-l` | `ru,en` | Language priority (first available wins) |

## Output

Script prints to stdout: metadata header (title, channel, URL, video ID), separator, then transcript text.

## The Iron Law

**NEVER modify the transcript text.** Output it exactly as received. Reformat into paragraphs (merge short lines into logical blocks) but NEVER change, summarize, or rephrase any words.

## After Getting Transcript

1. Save raw transcript as `{video_id}-transcript.txt` (or user-specified file)
2. Then — and only then — analyze, summarize, or process if the user asked for it

## Limitations

- Requires video to have subtitles (manual or auto-generated). If none — inform user, do not attempt workarounds
- Subject to YouTube rate limiting on heavy use
