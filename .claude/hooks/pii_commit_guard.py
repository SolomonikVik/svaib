#!/usr/bin/env python3
"""
pii_commit_guard.py — PreToolUse hook (matcher: Bash)

Блокирует `git commit` от Claude и инжектит в stderr инструкцию: просмотреть
staged-дифф на персональные данные перед коммитом. Хук — тупой триггер;
reasoning (что считать PII) — на Claude.

Чтобы не зациклиться: после проверки Claude повторяет коммит с env-префиксом
`PII_REVIEWED=1 git commit ...`. Префикс — честное подтверждение «дифф
просмотрен глазами», не криптозамок.

Принцип: хук создаёт checkpoint, умный обязан подумать в нужный момент.
Ловит только коммиты Claude — ручные коммиты в терминале вне зоны.
"""

import json
import re
import shlex
import sys

# env-опции git, забирающие следующий токен как аргумент
GIT_OPTS_WITH_ARG = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace",
    "--exec-path", "--config-env",
}


def split_env_prefixes(tokens: list[str]) -> tuple[dict[str, str], list[str]]:
    """Отделяет env-префиксы (VAR=value ...) от остальной команды."""
    env = {}
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if "=" in tok and not tok.startswith("-"):
            key, _, val = tok.partition("=")
            if key:
                env[key] = val
                idx += 1
                continue
        break
    return env, tokens[idx:]


def is_git_commit(tokens: list[str]) -> bool:
    """True если tokens — это `git ... commit ...` (не --dry-run)."""
    if not tokens or tokens[0] != "git":
        return False

    # пропускаем глобальные опции git до сабкоманды
    idx = 1
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in GIT_OPTS_WITH_ARG:
            idx += 2
        elif tok.startswith("-"):
            idx += 1
        else:
            break

    if idx >= len(tokens) or tokens[idx] != "commit":
        return False

    # `git commit --dry-run` не создаёт коммит — пропускаем
    commit_args = tokens[idx + 1:]
    if any(a in ("--dry-run", "-n") for a in commit_args):
        return False

    return True


def needs_block(command: str) -> bool:
    """True если в команде есть `git commit` без подтверждения PII_REVIEWED.

    Каждую под-команду (разделители ; && || |) парсим отдельно через shlex —
    не ловим false-positive на `echo "git commit"` и подобное.
    """
    for sub in re.split(r"[;&|]+", command):
        try:
            tokens = shlex.split(sub)
        except ValueError:
            continue
        if not tokens:
            continue

        env, rest = split_env_prefixes(tokens)
        if not is_git_commit(rest):
            continue

        # подтверждение проверки — env-префикс PII_REVIEWED с непустым значением
        approved = env.get("PII_REVIEWED", "").strip().lower() not in ("", "0", "false")
        if not approved:
            return True

    return False


def build_message() -> str:
    return (
        "🛑 git commit заблокирован — проверка на персональные данные.\n\n"
        "Репо публичное. Персональные данные, попавшие в git-историю,\n"
        "остаются в ней навсегда.\n\n"
        "Прежде чем коммитить:\n"
        "  1. Запусти `git diff --cached` — просмотри весь дифф.\n"
        "  2. Проверь на: имена и фамилии людей, ФИО сотрудников,\n"
        "     названия компаний-клиентов, email, телефоны — любые\n"
        "     персональные данные.\n"
        "  3. Нашёл — НЕ коммить. Покажи Виктору, замени на инициал\n"
        "     или обобщение.\n"
        "  4. Чисто — повтори коммит с префиксом:\n"
        "       PII_REVIEWED=1 git commit ...\n\n"
        "Префикс PII_REVIEWED=1 — твоё подтверждение, что дифф\n"
        "просмотрен глазами. Не добавляй его не глядя: хук тупой,\n"
        "проверка — на тебе.\n\n"
        "Правило: svaib/CLAUDE.md → Правила → п.4 «Конфиденциальность»."
    )


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
    if not needs_block(command):
        sys.exit(0)

    print(build_message(), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Хук не должен ломать workflow при своей внутренней ошибке
        sys.exit(0)
