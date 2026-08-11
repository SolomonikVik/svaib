#!/usr/bin/env python3
"""resolve_object.py — карта мест базы, кандидаты объекта встречи, валидация выбора.

Разделение ролей (canon-first, решение продукта): КОД строит карту мест, LLM
выбирает по карте, КОД валидирует выбор. Зашитый список путей запрещён —
scaffold composable: ракурс бывает файлом и папкой, `meetings/` бывают
централизованными и распределёнными, а цель — файл внутри ракурса strategic,
а не узел. Зашитые пути объявили бы валидный централизованный протокол
отсутствующим.

Наличие заполненных метрик — ПРИЗНАК ГОТОВНОСТИ ДАННЫХ, показываемый рядом с
кандидатом, а не критерий отбора. Как hard-фильтр он заставил бы скилл выбирать
не ближайшую встречу, а самую измеряемую.

Команды:
    map      — карта мест базы (узлы, цели, профили, контейнеры встреч)
    rank     — кандидаты по ритму и свежести, когда объект не назван
    validate — проверка выбранного узла

Коды возврата: 0 — ок; 1 — выбор невалиден; 2 — usage/IO.

Stdlib-only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import collect_sources as sources_lib  # noqa: E402  — владелец чтения шапок и индекса

# Служебные деревья карта не показывает: правило одно на весь скилл и живёт в
# `collect_sources.is_service_path`. Свой укороченный список здесь уже успел
# разойтись — в нём не было шаблонов, и карта предлагала встречу по узлу из
# `scaffold/template/01_company`, да ещё с пометкой «метрики есть».
STRATEGIC_HINT = re.compile(r"strategic", re.I)
TEAM_HINT = re.compile(r"team|people", re.I)
GOAL_HINT = re.compile(r"goal|okr|цел", re.I)
RANK_WINDOW = 4


def is_node(path: Path, base: Optional[Path] = None) -> bool:
    """Узел базы — каталог с признаками собственного контура: README, активная
    работа или встречи.

    Наличие внутри metrics-файла узлом НЕ делает: иначе ракурс `03_metrics/`
    сам объявляется узлом и попадает в карту наравне со своим владельцем —
    LLM получает выбор между направлением и его же папкой метрик.
    """
    if not path.is_dir():
        return False
    if sources_lib.is_service_path(path, base if base is not None else path.parent):
        return False
    names = {p.name.lower() for p in path.iterdir()}
    return bool(names & {"readme.md", "02_active.md", "meetings"})


def walk_nodes(base: Path) -> List[Path]:
    out: List[Path] = []
    stack = [base]
    while stack:
        current = stack.pop()
        for child in sorted(p for p in current.iterdir() if p.is_dir()):
            if sources_lib.is_service_path(child, base):
                continue
            if is_node(child, base):
                out.append(child)
            stack.append(child)
    return out


def build_map(base: Path) -> Dict[str, Any]:
    """Карта мест: то, из чего LLM выбирает объект встречи."""
    nodes: List[Dict[str, Any]] = []
    goals: List[Dict[str, Any]] = []
    people: List[Dict[str, Any]] = []

    for node in walk_nodes(base):
        rel = str(node.relative_to(base))
        has_metrics = any(p for p in node.rglob("*metrics*.md")
                          if not sources_lib.is_service_path(p, base))
        has_meetings = (node / "meetings").is_dir()
        nodes.append({"ref": rel, "kind": "node", "has_metrics": has_metrics, "has_meetings": has_meetings})

        for path in node.rglob("*.md"):
            # Отсчёт служебности — от базы: прежняя проверка смотрела части
            # АБСОЛЮТНОГО пути, и база, развёрнутая в каталоге со служебным
            # именем выше корня, отсеивалась бы целиком.
            if sources_lib.is_service_path(path, base):
                continue
            parent_chain = "/".join(path.relative_to(base).parts[:-1]).lower()
            if STRATEGIC_HINT.search(parent_chain) and GOAL_HINT.search(path.stem.lower()):
                goals.append({"ref": str(path.relative_to(base)), "kind": "goal", "owner_node": rel})
            elif TEAM_HINT.search(parent_chain):
                people.append({"ref": str(path.relative_to(base)), "kind": "person", "owner_node": rel})

    index = sources_lib.build_index(base)
    return {
        "nodes": nodes,
        "goals": _dedup(goals),
        "people": _dedup(people),
        "meetings_index": {"total": index["total"], "header_coverage": index["coverage"]},
    }


def _dedup(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for item in items:
        if item["ref"] in seen:
            continue
        seen.add(item["ref"])
        out.append(item)
    return out


def rank_candidates(base: Path, today: Optional[str] = None) -> List[Dict[str, Any]]:
    """Кандидаты, когда объект не назван: по свежести и ритму серии.

    Метрики в ранжировании НЕ участвуют — только показываются рядом.
    """
    index = sources_lib.build_index(base)
    base_date = date.fromisoformat(today) if today else date.today()
    by_object: Dict[str, List[str]] = {}
    for row in index["rows"]:
        if not row["date"]:
            continue
        # Ключ сразу нормализуется до узла: иначе протокол без шапки даёт
        # группу по каталогу `…/meetings`, и после срезки контейнера в списке
        # оказываются два кандидата с одним ref и разными датами — LLM получает
        # противоречивые строки об одном и том же узле.
        key = strip_meetings_container(row["object"] or str(Path(row["path"]).parent), base)
        by_object.setdefault(key, []).append(row["date"])

    out: List[Dict[str, Any]] = []
    for key, dates in by_object.items():
        ordered = sorted(set(dates))
        last = date.fromisoformat(ordered[-1])
        window = ordered[-RANK_WINDOW:]
        gaps = [(date.fromisoformat(b) - date.fromisoformat(a)).days for a, b in zip(window, window[1:])]
        rhythm = statistics.median(gaps) if gaps else None
        ref = key  # уже нормализован до узла при группировке
        candidate_path = base / ref
        out.append({
            "ref": ref,
            "last_meeting": ordered[-1],
            "days_since": (base_date - last).days,
            "meetings": len(ordered),
            "rhythm_days": rhythm,
            # Регулярной серии место в календаре предсказуемо: следующая
            # встреча ожидается через ритм после последней. Разовая встреча
            # такого ожидания не даёт, и ставить её впереди наступившей
            # регулярки — ровно та ошибка, ради которой ритм и считался.
            "due_in_days": (last - base_date).days + int(rhythm) if rhythm else None,
            # Признак готовности данных, не критерий отбора.
            "has_metrics": (any(p for p in candidate_path.rglob("*metrics*.md")
                                if not sources_lib.is_service_path(p, base))
                            if candidate_path.is_dir() else False),
        })

    def sort_key(c: Dict[str, Any]) -> tuple:
        # Сначала серии, чья следующая встреча ближе (в том числе уже
        # наступившая), затем разовые — по свежести.
        if c["due_in_days"] is None:
            return (1, c["days_since"], -c["meetings"])
        return (0, abs(c["due_in_days"]), -c["meetings"])

    out.sort(key=sort_key)
    return out


def strip_meetings_container(ref: str, base: Optional[Path] = None) -> str:
    """Приводит путь протокола к узлу, вокруг которого собирают повестку.

    Мало срезать сам `meetings`: вложенный протокол `sales/meetings/archive/…`
    дал бы кандидат `sales/archive`, которого как узла не существует. Поэтому
    после срезки поднимаемся до ближайшего предка, который узлом является.
    """
    parts = [p for p in Path(ref).parts if p != "meetings"]
    if not parts:
        return ref
    candidate = Path(*parts)
    if base is None:
        return str(candidate)
    while parts:
        current = Path(*parts)
        if is_node(base / current, base):
            return str(current)
        parts = parts[:-1]
    return str(candidate)


def validate_choice(base: Path, object_ref: str, object_kind: str) -> List[str]:
    """Проверка выбора LLM. Пустой список = выбор валиден."""
    problems: List[str] = []
    target = base / object_ref
    if not target.exists():
        problems.append("в базе нет такого места: {0}".format(object_ref))
        return problems
    # Место существует, но управленческим контуром не является. Проверка нужна
    # именно здесь: дальше всё считается ОТ объекта, и внутри шаблона его
    # содержимое снова выглядит обычными источниками и паспортами.
    if sources_lib.is_service_path(target, base):
        problems.append("это служебное дерево, а не место встречи: {0}".format(object_ref))
        return problems
    if object_kind == "node" and not target.is_dir():
        problems.append("объект объявлен узлом, но это файл: {0}".format(object_ref))
    if object_kind in ("goal", "person") and not target.is_file():
        problems.append("объект объявлен {0}, но это каталог: {1}".format(object_kind, object_ref))
    if object_kind == "goal":
        chain = "/".join(Path(object_ref).parts[:-1]).lower()
        if not STRATEGIC_HINT.search(chain):
            problems.append("цель обязана лежать в ракурсе strategic, а лежит в: {0}".format(chain or "корне"))
    if object_kind == "person":
        chain = "/".join(Path(object_ref).parts[:-1]).lower()
        if not TEAM_HINT.search(chain):
            problems.append("профиль человека обязан лежать в ракурсе team, а лежит в: {0}".format(chain or "корне"))
    return problems


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Карта мест и резолвер объекта встречи.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_map = sub.add_parser("map", help="карта мест базы")
    p_map.add_argument("--base", required=True)
    p_map.add_argument("--out")

    p_rank = sub.add_parser("rank", help="кандидаты объекта, когда он не назван")
    p_rank.add_argument("--base", required=True)
    p_rank.add_argument("--today", default=None, help="дата отсчёта (детерминизм тестов)")
    p_rank.add_argument("--limit", type=int, default=3)

    p_val = sub.add_parser("validate", help="проверка выбранного объекта")
    p_val.add_argument("--base", required=True)
    p_val.add_argument("--object", required=True)
    p_val.add_argument("--kind", required=True, choices=["node", "goal", "person"])

    for p in (p_map, p_rank, p_val):
        p.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    base = Path(args.base).resolve()

    try:
        if args.command == "map":
            payload = build_map(base)
            if getattr(args, "out", None):
                Path(args.out).parent.mkdir(parents=True, exist_ok=True)
                Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json or not args.out
                  else "Узлов: {0} · целей: {1} · профилей: {2}".format(
                      len(payload["nodes"]), len(payload["goals"]), len(payload["people"])))
            return 0

        if args.command == "rank":
            candidates = rank_candidates(base, args.today)[: args.limit]
            if args.json:
                print(json.dumps({"ok": True, "candidates": candidates}, ensure_ascii=False, indent=2))
            else:
                for c in candidates:
                    print("· {0} — последняя {1} ({2} дн. назад), встреч {3}, ритм {4}, метрики: {5}".format(
                        c["ref"], c["last_meeting"], c["days_since"], c["meetings"],
                        c["rhythm_days"] or "?", "есть" if c["has_metrics"] else "нет"))
            return 0

        problems = validate_choice(base, args.object, args.kind)
        payload = {"ok": not problems, "problems": problems}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("Выбор валиден." if not problems else "\n".join("❌ " + p for p in problems))
        return 1 if problems else 0
    except OSError as exc:
        print(json.dumps({"ok": False, "error": "io_error", "message": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
