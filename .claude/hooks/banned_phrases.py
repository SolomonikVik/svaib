#!/usr/bin/env python3
"""
Stop hook: block banned phrases in assistant responses.

Expandable list of phrases Claude must never say to Viktor.
Each ban has its own patterns and explanation (reason).
If "user_initiated" is true, the ban only fires when Claude says it unprompted —
if Viktor himself used similar words in his last message, Claude may echo them.

To add a new ban: append a dict to BANS list with "patterns" and "reason".

Zero context pollution: stdout only on violation.
"""

import json
import re
import sys

BANS = [
    {
        "patterns": [
            r"закрываем сессию",
            r"закрываем\?",
            r"заканчиваем\?",
            r"закрываемся\?",
            r"завершаем сессию",
            r"завершаем\?",
            r"оставляем как задачу\?",
            r"закроем сессию",
            r"shall we (wrap up|end|close)",
            r"let'?s (wrap up|end|close) the session",
            r"should we (stop|end|wrap)",
        ],
        "reason": (
            "BANNED PHRASE: Do not suggest ending/closing the session. "
            "Viktor perceives this as laziness and nagging — he will say when to stop. "
            "If you have an objective reason to flag (context overload, loss of coherence), "
            "state the FACT ('context is 80% full'), do NOT propose to close."
        ),
        "user_initiated": True,  # OK to echo if Viktor said it first
    },
]

# Patterns to detect user initiating session close (checked against user message)
USER_CLOSE_PATTERNS = re.compile(
    r"закрыва|заканчива|завершаем|завершай|закрой|close.?session|wrap.?up|всё на сегодня|финал",
    re.IGNORECASE,
)

# Compile all bans into (compiled_regex, reason, user_initiated) tuples
COMPILED_BANS = []
for ban in BANS:
    combined = "|".join(ban["patterns"])
    COMPILED_BANS.append((
        re.compile(combined, re.IGNORECASE),
        ban["reason"],
        ban.get("user_initiated", False),
    ))


def get_last_turn(transcript_path: str) -> tuple[str | None, str | None]:
    """Read last 50KB of transcript.
    Returns (assistant_text, user_text) for the last turn."""
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            chunk = min(size, 51200)
            f.seek(size - chunk)
            tail = f.read().decode("utf-8", errors="replace")
    except (OSError, IOError):
        return None, None

    assistant_parts = []
    last_user_text = None
    for line in tail.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if entry.get("type") == "user":
            assistant_parts = []
            # Extract user text
            message = entry.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                user_parts = []
                if isinstance(content, str):
                    user_parts.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            t = block.get("text", "")
                            if t:
                                user_parts.append(t)
                last_user_text = "\n".join(user_parts) if user_parts else None
            continue

        if entry.get("type") != "assistant":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            assistant_parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        assistant_parts.append(text)

    assistant_text = "\n".join(assistant_parts) if assistant_parts else None
    return assistant_text, last_user_text


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

    assistant_text, user_text = get_last_turn(transcript_path)
    if not assistant_text:
        sys.exit(0)

    # Check if user initiated session close
    user_initiated_close = bool(
        user_text and USER_CLOSE_PATTERNS.search(user_text)
    )

    for compiled_re, reason, is_user_initiated in COMPILED_BANS:
        match = compiled_re.search(assistant_text)
        if match:
            # Skip if user said it first and this ban allows echoing
            if is_user_initiated and user_initiated_close:
                continue
            result = {
                "decision": "block",
                "reason": reason,
            }
            print(json.dumps(result, ensure_ascii=False))
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
