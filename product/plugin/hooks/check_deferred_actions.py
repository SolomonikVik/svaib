#!/usr/bin/env python3
"""
Stop hook: ловит отложенные действия («в следующий раз сделаю X»).

Каждая сессия начинается с нуля — «следующего раза» не существует.
При срабатывании блокирует остановку: порученное действие доводится до результата,
новое изменение предлагается пользователю. Полномочия задаёт инструкция пространства.

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


def get_last_turn_text(transcript_path: str, turn_id: str | None = None) -> str | None:
    """Хвост (50KB): прежний ход Claude либо последний ответ текущего хода Codex."""
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            # Если граница хода Codex не попала в хвост, fallback пропускает проверку.
            chunk = min(size, 51200)
            f.seek(size - chunk)
            tail = f.read().decode("utf-8", errors="replace")
    except (OSError, ValueError):
        return None

    parts = []
    codex_text = None
    is_codex = isinstance(turn_id, str)
    in_turn = False
    for line in tail.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        entry_type = entry.get("type")
        payload = entry.get("payload")
        if is_codex:
            if not isinstance(payload, dict):
                continue
            if entry_type == "turn_context" or (
                entry_type == "event_msg" and payload.get("type") == "task_started"
            ):
                # Не подтягивать ответ прошлого хода, даже если у нового ещё нет текста.
                codex_text = None
                in_turn = payload.get("turn_id") == turn_id
            elif entry_type == "event_msg" and payload.get("type") == "user_message":
                codex_text = None
            elif (in_turn and entry_type == "response_item"
                  and payload.get("type") == "message"
                  and payload.get("role") == "assistant"
                  and payload.get("phase") != "commentary"):
                content = payload.get("content")
                # Заменяем ответ, а не накапливаем уже исправленные обещания.
                codex_text = "\n".join(
                    block["text"] for block in content
                    if isinstance(block, dict)
                    and block.get("type") in ("output_text", "text")
                    and isinstance(block.get("text"), str)
                ) if isinstance(content, list) else None
            continue
        if entry_type == "user":
            parts = []  # сброс: держим только текст после последнего сообщения пользователя
            continue
        if entry_type != "assistant":
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
                    if isinstance(text, str) and text:
                        parts.append(text)
    if is_codex:
        return codex_text or None
    return "\n".join(parts) if parts else None


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError, UnicodeError):
        sys.exit(0)

    if not isinstance(hook_input, dict):
        sys.exit(0)

    if hook_input.get("stop_hook_active"):
        sys.exit(0)

    # turn_id — штатное расширение события Codex. Claude оставляем на прежней
    # ветке транскрипта, даже если он тоже передал last_assistant_message.
    # У Codex пустая строка авторитетна: не подменяем её старым текстом rollout.
    turn_id = hook_input.get("turn_id")
    text = hook_input.get("last_assistant_message") if isinstance(turn_id, str) else None
    if not isinstance(text, str):
        transcript_path = hook_input.get("transcript_path")
        if not isinstance(transcript_path, str) or not transcript_path:
            sys.exit(0)
        text = get_last_turn_text(transcript_path, turn_id)
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
            "Обещание помнить без записи не сохраняет правило. "
            "Вернись к текущей работе и доведи порученное действие до результата "
            "в пределах разрешения пользователя и правил пространства. "
            "Если предлагаешь новое изменение, покажи, что именно изменится, "
            "и получи согласие, когда его требует инструкция пространства."
        ),
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
