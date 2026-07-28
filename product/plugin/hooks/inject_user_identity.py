#!/usr/bin/env python3
"""
SessionStart hook: сообщает агенту, кто сейчас за клавиатурой.

Источник — `.agents/identity.local` в корне рабочей папки (per-machine, вне git).
Формат файла:
    user: Иван
    profile: 01_company/02_team/ivan.md

Клиентская версия (plugin/hooks). Имя владельца по умолчанию подставляется
сборщиком из vars.conf профиля ({{DEFAULT_USER}}); переопределяется переменной
окружения SVAIB_DEFAULT_USER.

Формат вывода выбирается аргументом:
    inject_user_identity.py claude   # Claude Code hookSpecificOutput JSON
    inject_user_identity.py plain    # голый текст в stdout

Хук НЕ пишет в источник — только читает.
"""

import json
import os
import re
import sys

IDENTITY_FILE = os.path.join(".agents", "identity.local")
USER_RE = re.compile(r"^\s*user:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
PROFILE_RE = re.compile(r"^\s*profile:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)

DEFAULT_USER = os.environ.get("SVAIB_DEFAULT_USER") or "{{DEFAULT_USER}}"


def find_identity_file(start: str) -> str | None:
    """Подняться вверх от start, ища .agents/identity.local (корень рабочей папки)."""
    cur = os.path.abspath(start)
    while True:
        candidate = os.path.join(cur, IDENTITY_FILE)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def detect_identity(path: str) -> tuple[str | None, str | None]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except (OSError, IOError):
        return None, None
    u = USER_RE.search(text)
    p = PROFILE_RE.search(text)
    user = u.group(1).strip() if u else None
    profile = p.group(1).strip() if p else None
    return (user or None), (profile or None)


def build_context(user: str | None, profile: str | None) -> str:
    if user:
        profile_line = (
            f" Профиль: `{profile}` — прочитай при необходимости." if profile else ""
        )
        # Предупреждение о дефолте имеет смысл, только когда за клавиатурой не владелец.
        owner_line = (
            ""
            if user == DEFAULT_USER
            else (
                f" НЕ подставляй «{DEFAULT_USER}» по умолчанию: «{DEFAULT_USER}» — "
                f"владелец рабочей папки, но не обязательно человек за клавиатурой."
            )
        )
        return (
            "## Текущий пользователь за клавиатурой\n\n"
            f"За этой машиной сейчас работает **{user}** — это указано в "
            f"`.agents/identity.local`. Обращайся по имени.{profile_line}{owner_line}"
        )
    return (
        "## Текущий пользователь за клавиатурой\n\n"
        f"В `.agents/identity.local` нет записи о пользователе — используй обращение "
        f"по умолчанию: **{DEFAULT_USER}** (владелец рабочей папки). Если пользователь "
        f"представляется другим человеком — предложи записать его в "
        f"`.agents/identity.local` (строки `user:` и `profile:`), чтобы со следующей "
        f"сессии хук узнавал его сам."
    )


def emit(context: str, fmt: str) -> None:
    if fmt == "plain":
        print(context)
        return
    result = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    print(json.dumps(result, ensure_ascii=False))


def main():
    fmt = sys.argv[1].lower() if len(sys.argv) > 1 else "claude"

    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, IOError):
        hook_input = {}

    start = hook_input.get("cwd") or os.getcwd()
    path = find_identity_file(start)
    user, profile = detect_identity(path) if path else (None, None)

    emit(build_context(user, profile), fmt)
    sys.exit(0)


if __name__ == "__main__":
    main()
