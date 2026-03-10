#!/usr/bin/env python3
"""
Stop hook: enforce CLAUDE.md Rule 10.

Rule 10: if assistant message contains a question to user OR substantive
explanation — send ONLY text, no tool calls in the same turn.
Exception: brief status before action ("Делаю X", "Обновляю файл") is OK.

How it works:
1. Fires after each Claude response (Stop event)
2. Reads transcript — finds last assistant message
3. Checks if it has BOTH substantive text AND tool_use blocks
4. If yes — blocks stop, tells Claude to undo and resend text-only

Limitations (verified 2026-03-10):
- Only catches violations where ALL tool calls were auto-allowed (no permission prompt).
  If any tool call triggers a permission prompt (Edit, Write without allow-list),
  the prompt blocks the pipeline and Stop hook fires only AFTER user responds.
- PreToolUse was tried first but doesn't work: transcript doesn't contain
  current user/assistant messages at PreToolUse time (only previous turns).

Zero context pollution: stdout only on violation.
"""

import json
import re
import sys

# Minimum text length to consider "substantive"
MIN_SUBSTANTIVE_LENGTH = 150

# Question mark = always substantive
QUESTION_RE = re.compile(r"\?")

# Brief status patterns that are OK with tool calls
STATUS_PATTERNS = [
    r"^(делаю|обновляю|читаю|проверяю|запускаю|создаю|удаляю|ищу|смотрю|пишу|правлю|добавляю|убираю|меняю|переименовываю)\b",
    r"^(готово|сделано|обновлено|done|updated|fixed)\b",
    r"^(let me|давай|сейчас|ок,?\s)",
    r"^(running|reading|checking|creating|writing|updating|looking|searching)\b",
]
STATUS_RE = re.compile("|".join(STATUS_PATTERNS), re.IGNORECASE)

# Tools that are "meta" — don't count as "action" tool calls
META_TOOLS = {"TodoWrite", "Read", "Glob", "Grep", "ToolSearch"}


def get_last_assistant_message(transcript_path: str) -> list | None:
    """Read transcript, return content blocks of the last assistant message
    after the last user message."""
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            chunk = min(size, 102400)  # last 100KB
            f.seek(size - chunk)
            tail = f.read().decode("utf-8", errors="replace")
    except (OSError, IOError):
        return None

    last_assistant_content = None
    for line in tail.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if entry.get("type") == "user":
            last_assistant_content = None
            continue

        if entry.get("type") != "assistant":
            continue

        message = entry.get("message")
        if not isinstance(message, dict):
            continue

        content = message.get("content")
        if isinstance(content, list):
            last_assistant_content = content

    return last_assistant_content


def analyze_content(content_blocks: list) -> tuple[str, bool]:
    """Analyze content blocks. Returns (text, has_action_tools)."""
    text_parts = []
    has_action_tools = False

    for block in content_blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            t = block.get("text", "").strip()
            if t:
                text_parts.append(t)
        elif block.get("type") == "tool_use":
            tool_name = block.get("name", "")
            if tool_name not in META_TOOLS:
                has_action_tools = True

    return "\n".join(text_parts), has_action_tools


def is_substantive(text: str) -> tuple[bool, str]:
    """Check if text is substantive (not just a brief status).
    Returns (is_substantive, reason)."""
    if not text:
        return False, ""

    if QUESTION_RE.search(text):
        return True, "text contains a question"

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) <= 2 and all(STATUS_RE.match(l) for l in lines):
        return False, "brief status"

    if len(text) >= MIN_SUBSTANTIVE_LENGTH:
        return True, f"text is {len(text)} chars (threshold {MIN_SUBSTANTIVE_LENGTH})"

    return False, "short text without question"


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

    content = get_last_assistant_message(transcript_path)
    if not content:
        sys.exit(0)

    text, has_action_tools = analyze_content(content)

    if not has_action_tools:
        sys.exit(0)

    substantive, reason = is_substantive(text)
    if not substantive:
        sys.exit(0)

    # Violation found — block stop
    result = {
        "decision": "block",
        "reason": (
            f'RULE 10 VIOLATION: You wrote substantive text ({reason}) '
            f'AND called action tools in the same turn. '
            'Rule 10: substantive text = ONLY text, no tool calls. '
            'You MUST: (1) undo/revert any file changes you just made, '
            '(2) send ONLY your text explanation or question, '
            '(3) wait for Viktor to respond before acting.'
        ),
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
