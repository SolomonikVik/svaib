#!/usr/bin/env python3
"""Реестр адресатов канала send-telegram: alias → ИМЯ ключа окружения.

ЧЕГО ЗДЕСЬ НЕТ: значений. Резолвер переводит алиас в `chat_id_ref` и на этом
останавливается — сам номер подставляет bash, у которого уже есть резолв
`.env` (env → ./.env → git-root/.env). Иначе логика поиска кредов раздвоилась
бы на python и shell и разошлась бы, как уже разошёлся приоритет окружения
между plain и rich.

Отсюда же следует, что резолвер НИКОГДА не читает `.env` и не печатает chat_id.

Разрешение атомарно: неизвестный алиас, пустой элемент списка или дефект формы
дают пустой stdout и ненулевой код. Частично разрешённый список не возвращается
никогда — отправить «кому получилось» хуже, чем не отправить: ошибка адресации
здесь означает чужие глаза на содержимом встречи.

Коды возврата: 0 — успех, 1 — нарушения контракта, 2 — ошибка вызова или ввода-вывода.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "recipients.schema.json"

ALIAS_RE = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
# Строже, чем SECRET_REF_RE в dev/infra/runner/registry.py: там универсальный
# ^[A-Z][A-Z0-9_]{1,62}$, при котором «SOME_KEY» проходит как chat_id_ref.
# Здесь префикс обязателен — он единственное, что отличает адрес от любого
# другого ключа окружения при беглом чтении реестра.
CHAT_REF_RE = re.compile(r"^TG_CHAT_[A-Z0-9_]+$")
BOT_ID_RE = re.compile(r"^[0-9]{5,20}$")

ENV_REGISTRY = "SVAIB_RECIPIENTS"
REGISTRY_NAME = "recipients.yaml"


# --- Поиск файла ------------------------------------------------------------


def find_registry(explicit: Optional[str] = None) -> Tuple[Optional[Path], Optional[str]]:
    """Возвращает (путь, ошибка). Порядок повторяет резолв кредов в скриптах.

    Явно указанный путь (аргументом или SVAIB_RECIPIENTS), которого нет на
    диске, — жёсткий отказ, а не переход к следующему кандидату: молчаливый
    переход подсунул бы другой реестр и сменил адресатов.
    """
    for source, value in (("--registry", explicit), (ENV_REGISTRY, os.environ.get(ENV_REGISTRY))):
        if value:
            path = Path(value).expanduser()
            if not path.is_file():
                return None, "{0}: файл не найден — {1}".format(source, path)
            return path, None

    candidates = [Path.cwd() / REGISTRY_NAME]
    git_root = _git_root()
    if git_root:
        candidates.append(git_root / REGISTRY_NAME)
    candidates.append(Path.home() / ".config" / "svaib" / REGISTRY_NAME)

    for path in candidates:
        if path.is_file():
            return path, None
    return None, "реестр не найден (искал: {0})".format(", ".join(str(c) for c in candidates))


def _git_root() -> Optional[Path]:
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    root = out.stdout.strip()
    return Path(root) if out.returncode == 0 and root else None


def load(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        import yaml
    except ImportError:
        return None, ("нужен PyYAML: python3 -m pip install pyyaml "
                      "(без него реестр не читается, доставка по --to недоступна)")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, "не читается {0}: {1}".format(path, exc)
    except Exception as exc:  # yaml.YAMLError и наследники
        return None, "битый YAML в {0}: {1}".format(path, exc)
    if not isinstance(data, dict):
        return None, "{0}: ожидается объект верхнего уровня".format(path)
    return data, None


# --- Проверки ---------------------------------------------------------------


def check_schema(data: Any) -> List[str]:
    """Форма — файлом схемы; уникальность и целостность ссылок — семантикой ниже."""
    try:
        import jsonschema
    except ImportError:
        return []  # структурные дефекты доберёт семантика
    if not SCHEMA_FILE.is_file():
        return []
    try:
        schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    validator = jsonschema.Draft7Validator(schema)
    out = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in error.path) or "реестр"
        out.append("{0}: {1}".format(where, error.message))
    return out


TOP_KEYS = {"version", "bot", "people", "groups"}
BOT_KEYS = {"id", "username"}
PERSON_KEYS = {"alias", "chat_id_ref", "person_ref"}
GROUP_KEYS = {"alias", "chat_id_ref", "purpose", "members"}


def _unknown(where: str, item: Dict[str, Any], allowed: set) -> List[str]:
    """Неизвестные поля ловятся семантикой, а не только схемой.

    check_schema молча возвращает пустой список, если jsonschema не установлен
    или файл схемы не приехал, — значит опечатка в имени поля проглатывалась бы
    ровно там, где реестр собирают руками.
    """
    extra = sorted(set(item) - allowed)
    if not extra:
        return []
    return ["{0}: неизвестные поля {1} (опечатка?), разрешены: {2}".format(
        where, ", ".join(extra), ", ".join(sorted(allowed)))]


def validate(data: Dict[str, Any], base: Optional[Path] = None, strict: bool = False) -> List[str]:
    problems = check_schema(data)
    problems.extend(_unknown("реестр", data, TOP_KEYS))

    if data.get("version") != 1:
        problems.append("version: ожидается 1")

    bot = data.get("bot")
    if not isinstance(bot, dict):
        problems.append("bot: обязателен — реестр действителен только для своего бота")
    else:
        problems.extend(_unknown("bot", bot, BOT_KEYS))
        bot_id = bot.get("id")
        if not isinstance(bot_id, str) or not BOT_ID_RE.match(bot_id):
            problems.append("bot.id: ожидается строка цифр (префикс токена до двоеточия)")

    entries = _entries(data, problems)
    if not entries:
        problems.append("people/groups: нужен хотя бы один адресат")
        return problems

    seen_alias: Dict[str, str] = {}
    seen_ref: Dict[str, str] = {}
    for kind, idx, item in entries:
        where = "{0}[{1}]".format(kind, idx)
        if not isinstance(item, dict):
            problems.append("{0}: не объект".format(where))
            continue
        problems.extend(_unknown(where, item, PERSON_KEYS if kind == "people" else GROUP_KEYS))

        alias = item.get("alias")
        if not isinstance(alias, str) or not ALIAS_RE.match(alias):
            problems.append("{0}.alias: ожидается [a-z0-9-], 2–32 символа, без запятых".format(where))
        elif alias in seen_alias:
            problems.append(
                "{0}.alias: дубль «{1}» (уже в {2}) — --to {1} стал бы двусмысленным".format(
                    where, alias, seen_alias[alias]))
        else:
            seen_alias[alias] = where
            where = "{0}.{1}".format(kind, alias)

        ref = item.get("chat_id_ref")
        if isinstance(ref, (int, float)) and not isinstance(ref, bool):
            # YAML разбирает -1001234567890 как число, поэтому проверка на
            # «положили значение вместо имени» обязана ловить и нестроковый тип:
            # иначе диагностика говорит про тип и умалчивает о сути ошибки.
            problems.append("{0}.chat_id_ref: похоже на сам chat_id — реестр несёт только имена".format(where))
        elif not isinstance(ref, str):
            problems.append("{0}.chat_id_ref: обязателен (ИМЯ ключа окружения, не значение)".format(where))
        elif ref.lstrip("-").isdigit():
            problems.append("{0}.chat_id_ref: похоже на сам chat_id — реестр несёт только имена".format(where))
        elif not CHAT_REF_RE.match(ref):
            problems.append("{0}.chat_id_ref: ожидается имя вида TG_CHAT_X".format(where))
        elif ref in seen_ref:
            problems.append(
                "{0}.chat_id_ref: «{1}» уже назначен {2} — два алиаса на один чат дают "
                "двойную доставку при валидном файле".format(where, ref, seen_ref[ref]))
        else:
            seen_ref[ref] = where

        person_ref = item.get("person_ref")
        if person_ref is not None:
            problems.extend(_check_person_ref(person_ref, where, base, strict))

    problems.extend(_check_members(data))
    return problems


def _entries(data: Dict[str, Any], problems: List[str]) -> List[Tuple[str, int, Any]]:
    out: List[Tuple[str, int, Any]] = []
    for kind in ("people", "groups"):
        value = data.get(kind)
        if value is None:
            continue
        if not isinstance(value, list):
            problems.append("{0}: ожидается список".format(kind))
            continue
        for idx, item in enumerate(value):
            out.append((kind, idx, item))
    return out


def _check_person_ref(value: Any, where: str, base: Optional[Path], strict: bool) -> List[str]:
    """Путь резолвится от корня базы, а не от cwd и не от каталога реестра.

    Реестр может лежать в ~/.config/svaib/, где никакой базы рядом нет; при
    резолве от cwd один и тот же файл был бы валиден в одном каталоге и
    невалиден в другом.
    """
    if not isinstance(value, str) or not value.strip():
        return ["{0}.person_ref: ожидается непустая строка".format(where)]
    path = Path(value)
    if path.is_absolute():
        return ["{0}.person_ref: путь обязан быть относительным".format(where)]
    if ".." in path.parts:
        return ["{0}.person_ref: «..» запрещён — профиль лежит внутри базы".format(where)]
    if strict:
        root = base or _git_root() or Path.cwd()
        if not (root / path).is_file():
            return ["{0}.person_ref: файл не найден: {1}".format(where, root / path)]
    return []


def _check_members(data: Dict[str, Any]) -> List[str]:
    out = []
    people_aliases = {
        item.get("alias")
        for item in (data.get("people") or [])
        if isinstance(item, dict)
    }
    for idx, group in enumerate(data.get("groups") or []):
        if not isinstance(group, dict):
            continue
        members = group.get("members")
        if members is None:
            continue
        if not isinstance(members, list):
            out.append("groups[{0}].members: ожидается список".format(idx))
            continue
        where = group.get("alias") or "groups[{0}]".format(idx)
        for member in members:
            if member not in people_aliases:
                out.append("groups.{0}.members: «{1}» нет среди people".format(where, member))
    return out


# --- Разрешение -------------------------------------------------------------


def resolve(data: Dict[str, Any], raw: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    """alias[,alias...] → [(alias, chat_id_ref)]. Всё или ничего.

    Дубли схлопываются с сохранением порядка первого вхождения. Пересечение
    человека и группы, где он состоит, дублем НЕ считается: это два разных
    чата и две осознанные доставки.
    """
    index: Dict[str, str] = {}
    for kind in ("people", "groups"):
        for item in (data.get(kind) or []):
            if isinstance(item, dict) and isinstance(item.get("alias"), str):
                index[item["alias"]] = item.get("chat_id_ref")

    out: List[Tuple[str, str]] = []
    problems: List[str] = []
    seen = set()
    parts = raw.split(",")
    for part in parts:
        alias = part.strip()
        if not alias:
            problems.append("пустой элемент в списке адресатов: «{0}»".format(raw))
            continue
        if alias not in index:
            known = ", ".join(sorted(index)) or "реестр пуст"
            problems.append("неизвестный адресат «{0}» (есть: {1})".format(alias, known))
            continue
        ref = index[alias]
        if not isinstance(ref, str) or not ref:
            problems.append("у адресата «{0}» не задан chat_id_ref".format(alias))
            continue
        if alias in seen:
            continue
        seen.add(alias)
        out.append((alias, ref))

    if problems:
        return [], problems
    if not out:
        return [], ["список адресатов пуст"]
    return out, []


def check_bot(data: Dict[str, Any], bot_id: str) -> List[str]:
    """Сверка реестра с ботом, от чьего имени пойдёт отправка.

    Пока у каждого свой бот, реестр коллеги резолвит алиасы в номера, которые
    для нашего бота означают другие чаты или не существуют вовсе.
    """
    bot = data.get("bot")
    declared = bot.get("id") if isinstance(bot, dict) else None
    if not isinstance(declared, str):
        return ["реестр не объявляет bot.id — сверить не с чем"]
    if declared != bot_id:
        return [
            "реестр собран для бота {0}, а отправка идёт от {1} — "
            "chat_id зависит от бота, адресаты не совпадут".format(declared, bot_id)
        ]
    return []


# --- CLI --------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Реестр адресатов send-telegram: alias → имя ключа окружения.")
    parser.add_argument("--registry", help="путь к реестру (по умолчанию — поиск)")
    parser.add_argument("--base", help="корень базы для проверки person_ref")
    parser.add_argument("--bot-id", help="id бота для сверки (префикс токена до двоеточия)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--resolve", metavar="ALIAS[,ALIAS...]", help="печатает alias<TAB>chat_id_ref")
    group.add_argument("--list", action="store_true", help="все адресаты реестра")
    group.add_argument("--validate", action="store_true", help="проверить контракт")
    parser.add_argument("--strict", action="store_true",
                        help="с --validate: проверять существование person_ref на диске")
    args = parser.parse_args(argv)

    path, err = find_registry(args.registry)
    if err:
        print("ERROR: {0}".format(err), file=sys.stderr)
        return 2
    data, err = load(path)
    if err:
        print("ERROR: {0}".format(err), file=sys.stderr)
        return 2

    problems = validate(data, base=Path(args.base) if args.base else None, strict=args.strict)
    if args.bot_id:
        problems.extend(check_bot(data, args.bot_id))
    if problems:
        print("Реестр {0} — нарушения:".format(path), file=sys.stderr)
        for p in problems:
            print("  - {0}".format(p), file=sys.stderr)
        return 1

    if args.validate:
        print("Реестр {0} — контракт соблюдён.".format(path))
        return 0

    if args.list:
        for kind, label in (("people", "person"), ("groups", "group")):
            for item in (data.get(kind) or []):
                print("{0}\t{1}\t{2}".format(item.get("alias"), label, item.get("chat_id_ref")))
        return 0

    pairs, problems = resolve(data, args.resolve)
    if problems:
        for p in problems:
            print("ERROR: {0}".format(p), file=sys.stderr)
        return 1
    for alias, ref in pairs:
        print("{0}\t{1}".format(alias, ref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
