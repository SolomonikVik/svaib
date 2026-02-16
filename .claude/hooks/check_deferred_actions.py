#!/usr/bin/env python3
"""
Stop hook: catch deferred-action phrases.

Claude says "next time I'll do X" instead of acting NOW.
Each session starts from scratch — "next time" never happens.

When triggered: blocks stop, tells Claude to PROPOSE a fix to the user
(not fix it himself). User decides whether to apply.

Zero context pollution: stdout only on failure.
"""

import json
import re
import sys

DEFERRED_PATTERNS = [
    # Russian
    r"в следующий раз",
    r"в следующем чате",
    r"в следующей сессии",
    r"в будущих сессиях",
    r"в следующих сессиях",
    r"буду иметь в виду",
    r"буду помнить",
    r"запомню на будущее",
    r"в будущем буду",
    r"в будущем постараюсь",
    r"учту на будущее",
    r"учту это на будущее",
    r"в следующий раз буду",
    r"в следующий раз постараюсь",
    # English
    r"next time i'?ll",
    r"i'?ll remember (this |that )?(for )?(next|future)",
    r"i will remember (this |that )?(for )?(next|future)",
    r"note for future",
    r"for future reference",
    r"in future sessions",
    r"next session i'?ll",
]

DEFERRED_RE = re.compile("|".join(DEFERRED_PATTERNS), re.IGNORECASE)


def get_last_turn_text(transcript_path: str) -> str | None:
    """Read last 50KB of transcript, extract assistant text."""
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            chunk = min(size, 51200)
            f.seek(size - chunk)
            tail = f.read().decode("utf-8", errors="replace")
    except (OSError, IOError):
        return None

    parts = []
    for line in tail.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("type") == "user":
            parts = []  # reset: only keep text after last user message
            continue
        if entry.get("type") != "assistant":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        parts.append(text)
    return "\n".join(parts) if parts else None


def main():
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, IOError):
        sys.exit(0)

    if hook_input.get("stop_hook_active"):
        sys.exit(0)

    transcript_path = hook_input.get("transcript_path")
    if not transcript_path:
        sys.exit(0)

    text = get_last_turn_text(transcript_path)
    if not text:
        sys.exit(0)

    match = DEFERRED_RE.search(text)
    if not match:
        sys.exit(0)

    matched_phrase = match.group(0)
    result = {
        "decision": "block",
        "reason": (
            f'HOOK: Deferred action detected: "{matched_phrase}". '
            "Next session does not exist — each starts from scratch. "
            "Instead of deferring, PROPOSE to the user a specific change: "
            "which file to edit (CLAUDE.md, skill, hook, command, or prompt) "
            "and what exactly to change. User decides whether to apply. "
            "Do NOT edit files yourself."
        ),
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
