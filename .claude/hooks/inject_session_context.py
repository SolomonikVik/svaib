#!/usr/bin/env python3
"""
SubagentStart hook (all subagents): inject parent session context + rules.

Two things injected into every subagent via additionalContext:
1. Last ~5 conversation turns from the parent session
2. Critical subagent rules (SUBAGENT_RULES below)

Source of truth for rules: lab/subagent-rules.md (⚡-marked rules).
When updating rules there — update SUBAGENT_RULES here too, and vice versa.

Replaces inject_rescue_context.py (was rescue-only, 20 turns).
Pattern: Context-Free Delegation fix (rescue-log 2026-03-10).
"""

import json
import sys

MAX_TURNS = 5
TAIL_BYTES = 25600  # 25KB — covers ~5-8 turns comfortably

# ⚡ Critical subagent rules — synced with lab/subagent-rules.md
# If you change these, update the source file too (and vice versa).
SUBAGENT_RULES = """\
## Обязательные правила для субагентов

1. **Bash: только простые команды.** Одна команда за вызов. Без &&, ||, |, ; и редиректов.
2. **Запись: только в указанный путь внутри _inbox/subagents/.** Если путь не дан — не придумывай его сам.
3. **Работай только в пределах порученного куска.** Если не хватает границ задачи или пути записи — вернись к координатору с блокером.

Источник: lab/subagent-rules.md\
"""


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
            combined = "\n".join(text_parts)
            if len(combined) > 1200:
                combined = combined[:1200] + "\n[...обрезано]"
            turns.append(f"### {role}:\n{combined}")

    if not turns:
        return None

    recent = turns[-MAX_TURNS:]
    return "\n\n".join(recent)


def main():
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, IOError):
        sys.exit(0)

    transcript_path = hook_input.get("transcript_path")
    conversation = extract_conversation(transcript_path) if transcript_path else None

    parts = [SUBAGENT_RULES]

    if conversation:
        parts.append(
            "## Контекст родительской сессии\n\n"
            f"{conversation}\n\n"
            "---\n"
            "Используй этот контекст чтобы понять задачу. "
            "Если запрос координатора неполный — опирайся на слова Виктора."
        )

    result = {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": "\n\n".join(parts),
        }
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
