#!/usr/bin/env python3
"""
SubagentStart hook (matcher: rescue): inject session transcript context.

Reads the parent session transcript and extracts the last ~20 conversation
turns (user + assistant text). Returns them via additionalContext so that
the rescue agent starts with full context of what went wrong.

Zero overhead for other subagents — matcher ensures this only runs for rescue.
"""

import json
import sys

MAX_TURNS = 20
TAIL_BYTES = 102400  # 100KB — covers ~20-30 turns comfortably


def extract_conversation(transcript_path: str) -> str | None:
    """Extract last N user/assistant turns from JSONL transcript."""
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            chunk = min(size, TAIL_BYTES)
            f.seek(size - chunk)
            tail = f.read().decode("utf-8", errors="replace")
    except (OSError, IOError):
        return None

    turns = []
    for line in tail.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        entry_type = entry.get("type")
        if entry_type not in ("user", "assistant"):
            continue

        # Extract text content
        text_parts = []
        message = entry.get("message", entry)
        content = message.get("content") if isinstance(message, dict) else None

        if isinstance(content, str):
            text_parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        text_parts.append(text)

        if text_parts:
            role = "ВИКТОР" if entry_type == "user" else "КООРДИНАТОР"
            # Truncate very long turns to save context
            combined = "\n".join(text_parts)
            if len(combined) > 2000:
                combined = combined[:2000] + "\n[...обрезано]"
            turns.append(f"### {role}:\n{combined}")

    if not turns:
        return None

    # Keep last N turns
    recent = turns[-MAX_TURNS:]
    return "\n\n".join(recent)


def main():
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, IOError):
        sys.exit(0)

    transcript_path = hook_input.get("transcript_path")
    if not transcript_path:
        sys.exit(0)

    conversation = extract_conversation(transcript_path)
    if not conversation:
        sys.exit(0)

    result = {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": (
                "## Контекст сессии (автоматически извлечён из транскрипта)\n\n"
                f"{conversation}\n\n"
                "---\n"
                "Выше — последние реплики сессии. Найди где произошёл сбой."
            ),
        }
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
