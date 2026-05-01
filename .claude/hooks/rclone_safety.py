#!/usr/bin/env python3
"""
rclone_safety.py — PreToolUse hook (matcher: Bash)

Блокирует `rclone sync` к/из `gdrive:` без `--dry-run`.
При блокировке — выгружает в stderr секцию «Протокол безопасной синхронизации»
из setup_workspace.md, чтобы агент видел правила прямо в момент блокировки,
а не «должен был сходить прочитать».

Принцип: ландшафт важнее инструкции — блокируем неправильный путь, не учим правильному.
"""

import json
import re
import shlex
import sys
from pathlib import Path

PROTOCOL_FILE = "clients/playbook/delivery/operations/setup_workspace.md"
PROTOCOL_SECTION = "### Протокол безопасной синхронизации"


def extract_section(file_path: Path, section_header: str) -> str | None:
    """Достаёт секцию от header до следующего заголовка того же уровня или выше."""
    if not file_path.exists():
        return None
    text = file_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    start_idx = None
    for i, line in enumerate(lines):
        if line.strip() == section_header:
            start_idx = i
            break
    if start_idx is None:
        return None

    section_level = len(section_header) - len(section_header.lstrip("#"))
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= section_level:
                end_idx = i
                break

    return "\n".join(lines[start_idx:end_idx]).strip()


def is_dangerous_rclone(command: str) -> bool:
    """True если команда содержит `rclone sync ... gdrive:...` без `--dry-run`.

    Парсит каждую под-команду (разделители ; && || |) отдельно через shlex.
    Не ловит false-positive на `echo "rclone sync ..."` и подобное.
    """
    sub_commands = re.split(r"[;&|]+", command)
    for sub in sub_commands:
        try:
            tokens = shlex.split(sub)
        except ValueError:
            continue
        if not tokens:
            continue

        # Пропускаем env-префиксы (FOO=bar rclone ...)
        idx = 0
        while idx < len(tokens) and "=" in tokens[idx] and not tokens[idx].startswith("-"):
            idx += 1
        if idx >= len(tokens) or tokens[idx] != "rclone":
            continue

        rest = tokens[idx + 1:]
        if not rest or rest[0] != "sync":
            continue

        args = rest[1:]
        if any(arg in ("--dry-run", "--dry_run", "-n") for arg in args):
            continue
        if any("gdrive:" in arg for arg in args):
            return True

    return False


def build_message(cwd: str) -> str:
    msg = "🚫 rclone sync к/из gdrive: без --dry-run заблокирован.\n\n"
    msg += "Может удалить файлы:\n"
    msg += "  • на Drive клиента — при push (sync local → gdrive:)\n"
    msg += "  • локально, особенно .env и dot-папки — при pull (sync gdrive: → local)\n\n"
    msg += "Безопасные альтернативы:\n"
    msg += "  • Точечно: rclone copy / rclone deletefile\n"
    msg += "  • Проверка состояния: rclone ls / rclone lsf / rclone check\n"
    msg += "  • Если нужен sync — добавь --dry-run, посмотри что произойдёт\n\n"

    protocol_path = Path(cwd) / PROTOCOL_FILE
    protocol_text = extract_section(protocol_path, PROTOCOL_SECTION)

    if protocol_text:
        msg += "─" * 60 + "\n"
        msg += f"ПОЛНЫЙ ПРОТОКОЛ из {PROTOCOL_FILE}:\n"
        msg += "─" * 60 + "\n"
        msg += protocol_text + "\n"
    else:
        msg += f"Протокол: {PROTOCOL_FILE} → «Протокол безопасной синхронизации»\n"

    return msg


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if data.get("hook_event_name") != "PreToolUse":
        sys.exit(0)
    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command = data.get("tool_input", {}).get("command", "")
    if not is_dangerous_rclone(command):
        sys.exit(0)

    cwd = data.get("cwd", ".")
    print(build_message(cwd), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Хук не должен ломать workflow при своей внутренней ошибке
        sys.exit(0)
