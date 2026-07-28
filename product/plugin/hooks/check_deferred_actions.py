#!/usr/bin/env python3
"""
Stop hook: ловит отложенные действия («в следующий раз сделаю X»).

Каждая сессия начинается с нуля — «следующего раза» не существует.
При срабатывании: блокирует остановку и требует ПРЕДЛОЖИТЬ пользователю
конкретную правку (файл + что изменить). Решение применять — за пользователем.

Клиентская версия (plugin/hooks). Переносима: не зависит от структуры репо.
Ноль загрязнения контекста: stdout только при срабатывании.
"""

import json
import re
import sys

DEFERRED_PATTERNS = [
    # Русский — отложено «на следующий раз»
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
    # Русский — фальшивое «принял», без записи в файл
    r"зафиксирую для себя",
    r"запомню для себя",
    r"возьму на заметку",
    r"приму к сведению",
    r"буду учитывать",
    # English — deferred to "next time"
    r"next time i'?ll",
    r"i'?ll remember (this |that )?(for )?(next|future)",
    r"i will remember (this |that )?(for )?(next|future)",
    r"note for future",
    r"for future reference",
    r"in future sessions",
    r"next session i'?ll",
    # English — fake "noted" without writing to file
    r"i'?ll keep (this |that )?in mind",
    r"noted for myself",
    r"i'?ll take note",
]

DEFERRED_RE = re.compile("|".join(DEFERRED_PATTERNS), re.IGNORECASE)


def get_last_turn_text(transcript_path: str) -> str | None:
    """Прочитать хвост транскрипта (50KB), собрать текст последнего хода агента."""
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
            parts = []  # сброс: держим только текст после последнего сообщения пользователя
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
            f'HOOK: обнаружено отложенное действие: "{matched_phrase}". '
            "Следующей сессии не существует — каждая начинается с нуля. "
            "Вместо откладывания ПРЕДЛОЖИ пользователю конкретную правку: "
            "какой файл изменить (CLAUDE.md, скилл, хук, промпт) и что именно. "
            "Решение применять — за пользователем. Не правь файлы сам."
        ),
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
