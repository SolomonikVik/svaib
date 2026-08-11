#!/usr/bin/env python3
"""collect_sources.py — чек-лист источников под объект встречи.

Строит manifest: какие канон-пути прочитаны, каких нет, какие недоступны. Пункт
повестки, не опирающийся на источник из этого перечня, не проходит валидатор:
пропущенный источник деградирует повестку молча — агент не знает, чего не увидел.

Здесь же строится кросс-серийный индекс — строка «объект + дата + тема» на
каждый протокол всех `meetings/` базы, БЕЗ чтения тел. Без него бюджет серии
молча обнулил бы две проверки каталога из десяти.

Правило полноты индекса (design.md, «Бюджет чтения»): если доля протоколов без
шапки выше порога, кросс-серийные проверки уходят в checks_skipped и права
формулировать отрицательное утверждение не имеют. Иначе протокол, у которого
тема есть только в теле, даст вывод «тема не обсуждалась» — R2-класс: отсутствие
в неполном представлении выдано за отсутствие в базе.

Коды возврата: 0 — manifest построен; 1 — обязательный источник недоступен;
2 — usage/IO.

Stdlib-only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Шапка протокола: читаем только её. Тела протоколов в индекс не читаются
# никогда, транскрипты — тем более.
HEADER_MAX_LINES = 15
# Формат шапки задаёт meeting-analysis, повестка его ЧИТАЕТ. Фактический
# шаблон узла выжимки пишет метаданные без markdown-жира (`Дата: …`), поэтому
# обе формы принимаются: требовать `**Дата:**` значило бы не разобрать ни один
# реальный протокол и молча остаться без индекса.
OBJECT_LINE = re.compile(r"^\*{0,2}Объект:\*{0,2}\s*(.+?)\s*$", re.M)
DATE_LINE = re.compile(r"^\*{0,2}Дата:\*{0,2}\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.M)
TYPE_LINE = re.compile(r"^\*{0,2}Тип встречи:\*{0,2}\s*(.+?)\s*$", re.M)
TOPIC_LINE = re.compile(r"^#\s+(.+?)\s*$", re.M)
DATE_IN_NAME = re.compile(r"(20[0-9]{2}-[0-9]{2}-[0-9]{2})")

# Доля протоколов без строки `**Объект:**`, выше которой кросс-серийным
# проверкам доверять нельзя. Число калибруемое: правка соседа только вводится,
# и на старых базах шапок не будет вовсе.
HEADER_COVERAGE_MIN = 0.5

CROSS_SERIES_CHECKS = ("attention-skew", "blind-spot")

# Роли источников под профиль объекта. Пути не зашиты списком: ищем по канону
# ракурсов, потому что scaffold composable — ракурс бывает файлом и папкой,
# meetings/ бывают централизованными и распределёнными.
#: Роль источника → чем она представлена в базе. Ракурсы (стратегия, метрики,
#: команда) — это ПАПКИ, а файлы внутри называются как угодно: цель живёт в
#: `01_strategic/goal.md`, паспорт метрик — в `03_metrics/business-metrics.md`.
#:
#: Прежние маски искали файл со словом в ИМЕНИ и потому давали два дефекта разом,
#: оба наблюдались на живых базах: цель не находилась никогда («не смогли найти
#: объект целей» — повестка приходила без верхнего блока), а `*metrics*` и
#: `*team*` цепляли протоколы встреч вида `2026-07-07_khoreva_support_metrics.md`
#: и выдавали их за паспорт метрик и за состав команды.
#: Третий элемент — искать ли рекурсивно. Панели объекта (`02_active`,
#: `05_decisions`, `04_progress`) лежат в самом узле, и рекурсия по поддереву
#: подтягивает ЧУЖИЕ: у компании активкой становилась активка сотрудника из
#: `02_team/<кто-то>/02_active.md`. Ракурсы искать рекурсивно нужно —
#: у направления они бывают и в дочерних узлах.
ROLE_PATTERNS: Tuple[Tuple[str, Tuple[str, ...], bool], ...] = (
    ("strategic", ("*strategic*/*.md", "goal.md"), True),
    # Ракурс метрик номерной (`03_metrics/`), а не любая папка со словом
    # «metrics»: у базы, где рядом лежит сам продукт, маска `*metrics*`
    # затягивала его шаблоны и служебные файлы скилла и выдавала их за паспорта
    # клиента.
    ("metrics", ("03_metrics/*-metrics.md",), True),
    ("active", ("02_active.md",), True),
    ("decisions", ("05_decisions.md",), True),
    ("progress", ("04_progress.md", "04_progress/*.md"), True),
    # Состав команды, а не все её профили: досье конкретного человека нужно
    # встрече С НИМ (объект-person), а на планёрке компании двадцать профилей
    # вытесняют из чек-листа то, ради чего он собирается.
    ("team", ("*team*/org-structure.md", "*team*/README.md"), True),
)

#: Служебные деревья, которых в повестке быть не должно: архив, входящее,
#: шаблоны и техническая обвязка. Без этого фильтра планёрка компании получала
#: «паспорт метрик» из шаблона scaffold и «решения» из архива позапрошлого года.
SKIP_PARTS = frozenset({
    "zz_archive", "_inbox", "_templates", "template", "templates",
    ".claude", ".git", "node_modules", "__pycache__", "_private",
})

#: Насколько глубоко от объекта собираются панели узлов (`02_active` и прочие).
#: Планёрка компании смотрит направления и их подразделения — это два уровня;
#: глубже начинается проектная мелочь, которая вытесняет главное.
MAX_NODE_DEPTH = 3

#: Сколько панелей одной роли попадает в чек-лист. У компании с десятком
#: направлений активок и хроник столько же, и все они в повестку не помещаются
#: — не по объёму файла, а по вниманию читателя.
#:
#: Отбор — по свежести правки: панель, которую не трогали полгода, к сегодняшней
#: планёрке отношения почти не имеет, а недавняя правка означает живую работу.
#: Прокси неидеальный (правка бывает косметической), поэтому срезанное не
#: исчезает молча: их число попадает в ответ и доезжает до человека.
PANEL_BUDGET = 8
BUDGETED_ROLES = frozenset({"active", "decisions", "progress"})


class CollectError(Exception):
    def __init__(self, code: str, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


def read_header(path: Path) -> Tuple[str, Dict[str, Optional[str]]]:
    """Возвращает текст шапки и разобранные поля. Тело файла не читается."""
    lines: List[str] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                # Обрыва на первом `##` нет намеренно: у протокола метаданные
                # лежат ВНУТРИ секции `## Метаданные`, и прежний обрыв отбрасывал
                # ровно то, ради чего шапка читается, — объект, дату и тип.
                # Даты подхватывались из имён файлов, и дефект был незаметен.
                if i >= HEADER_MAX_LINES:
                    break
                lines.append(line.rstrip("\n"))
    except OSError:
        return "", {"object": None, "date": None, "topic": None, "type": None}
    head = "\n".join(lines)
    obj = OBJECT_LINE.search(head)
    date = DATE_LINE.search(head)
    topic = TOPIC_LINE.search(head)
    mtype = TYPE_LINE.search(head)
    return head, {
        "object": obj.group(1) if obj else None,
        "date": date.group(1) if date else None,
        "topic": topic.group(1) if topic else None,
        "type": mtype.group(1) if mtype else None,
    }


def is_service_path(path: Path, root: Path) -> bool:
    """Путь ведёт в служебное дерево: шаблон, архив, входящее, техобвязка.

    Единственный владелец правила «это не база» — на него опираются и чек-лист
    источников, и ворота метрик, и карта объектов. Свои укороченные списки уже
    успели разойтись: в карте объектов не было шаблонов, и планёрка компании
    получала «паспорт метрик» из scaffold.

    Отсчёт — от `root`, а не от корня файловой системы: служебной должна быть
    часть ПУТИ ВНУТРИ базы, иначе база, развёрнутая в каталоге со скрытым
    предком, отсеивается целиком.

    Стороны приводятся к абсолютным без обращения к диску: у вызывающих база
    бывает относительной, а найденный путь абсолютным, и «не потомок» здесь
    означает отказ — паспорт исчез бы из повестки молча.
    """
    try:
        parts = Path(os.path.abspath(path)).relative_to(os.path.abspath(root)).parts
    except ValueError:
        return True
    return any(part in SKIP_PARTS or part.startswith(".") for part in parts)


def meeting_files(base: Path) -> List[Path]:
    out: List[Path] = []
    for meetings_dir in base.rglob("meetings"):
        if meetings_dir.is_dir() and not is_service_path(meetings_dir, base):
            out.extend(sorted(p for p in meetings_dir.rglob("*.md")
                              if p.is_file() and not is_service_path(p, base)))
    return out


def build_index(base: Path) -> Dict[str, Any]:
    """Дешёвый индекс встреч базы: строка на протокол, тела не читаются."""
    rows: List[Dict[str, Any]] = []
    for path in meeting_files(base):
        _, fields = read_header(path)
        name_date = DATE_IN_NAME.search(path.name)
        rows.append({
            "path": str(path.relative_to(base)),
            "date": fields["date"] or (name_date.group(1) if name_date else None),
            "object": fields["object"],
            "type": fields["type"],
            "topic": fields["topic"] or path.stem,
            "has_header": bool(fields["object"]),
        })
    with_header = sum(1 for r in rows if r["has_header"])
    coverage = (with_header / len(rows)) if rows else 0.0
    return {"rows": rows, "coverage": round(coverage, 3), "total": len(rows), "with_header": with_header}


def series_of(index: Dict[str, Any], object_ref: str, meeting_type: Optional[str]) -> Dict[str, Any]:
    """Серия встреч объекта: даты прошлых протоколов и ключ серии.

    Распределённая конфигурация — протоколы контейнера объекта с совпадающим
    типом; централизованная — протоколы, чей `**Объект:**` совпадает с объектом
    сборки. Ключа нет → серия не определена, работает fallback свежести, и это
    попадает во флаги, а не молчит.
    """
    distributed = [r for r in index["rows"] if r["path"].startswith(object_ref.rstrip("/") + "/")]
    centralized = [r for r in index["rows"] if r["object"] and r["object"].strip() == object_ref.strip()]
    rows = distributed or centralized

    # Серия = протоколы контейнера С СОВПАДАЮЩИМ ТИПОМ ВСТРЕЧИ. Без фильтра
    # квартальный разбор в том же `meetings/` попадает в серию недельной
    # планёрки: ритм ломается, а пункты ложно объявляются протухшими — «после
    # даты пункта прошла встреча серии», которой на самом деле не было.
    if meeting_type:
        typed = [r for r in rows if r.get("type") and r["type"].strip().lower() == meeting_type.strip().lower()]
        untyped = [r for r in rows if not r.get("type")]
        # Протоколы без указанного типа не выбрасываем: до миграции шапок их
        # большинство, и отбросить их значило бы обнулить серию целиком. А вот
        # ЧУЖОЙ тип в серию не попадает никогда: прежний откат «нет своих —
        # берём все» возвращал квартальный разбор в ответ на запрос серии
        # планёрки, то есть ровно ту ошибку, ради которой фильтр и вводился.
        rows = typed + untyped

    dates = sorted({r["date"] for r in rows if r["date"]})
    if not rows:
        return {"series_key": None, "series_dates": [], "series_rows": 0, "typed_rows": 0}
    typed_count = sum(1 for r in rows if r.get("type"))
    key = "{0}::{1}".format(object_ref, meeting_type or "any")
    return {"series_key": key, "series_dates": dates, "series_rows": len(rows), "typed_rows": typed_count}


def _in_agenda_scope(path: Path, scope: Path) -> bool:
    """Файл принадлежит управленческому контуру объекта, а не служебному дереву.

    Два отсева, оба наблюдались на живых базах: служебные каталоги (архив,
    входящее, шаблоны) и глубина. Планёрка компании смотрит направления и их
    подразделения; всё, что глубже, — проектная мелочь, вытесняющая главное.
    """
    if is_service_path(path, scope):
        return False
    try:
        parts = path.relative_to(scope).parts
    except ValueError:  # pragma: no cover — вызывается только для потомков scope
        return False
    return len(parts) <= MAX_NODE_DEPTH


def collect(base: Path, object_ref: str, object_kind: str, meeting_type: Optional[str]) -> Dict[str, Any]:
    target = (base / object_ref)
    if not target.exists():
        raise CollectError("object_missing", "объекта нет в базе: {0}".format(object_ref))

    scope = target if target.is_dir() else target.parent
    sources: List[Dict[str, Any]] = []
    seen: set = set()
    trimmed: Dict[str, int] = {}
    for role, patterns, recursive in ROLE_PATTERNS:
        search = scope.rglob if recursive else scope.glob
        found = [p for pattern in patterns for p in search(pattern)
                 if p.is_file() and _in_agenda_scope(p, scope)]
        if not found:
            sources.append({"path": "{0}/{1}".format(object_ref, patterns[0]),
                            "role": role, "status": "missing"})
            continue
        if role in BUDGETED_ROLES and len(found) > PANEL_BUDGET:
            # Свежие — вперёд; счёт срезанных отдаётся наружу, чтобы «этого нет
            # в базе» и «это не влезло в повестку» не выглядели одинаково.
            found = sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)
            trimmed[role] = len(found) - PANEL_BUDGET
            found = found[:PANEL_BUDGET]
        for path in sorted(found):
            rel = str(path.relative_to(base))
            if rel in seen:
                continue
            seen.add(rel)
            try:
                path.read_text(encoding="utf-8")
                status = "read"
            except OSError:
                status = "unreadable"
            sources.append({"path": rel, "role": role, "status": status})

    if object_kind in ("goal", "person") and target.is_file():
        rel = str(target.relative_to(base))
        if rel not in seen:
            sources.append({"path": rel, "role": object_kind, "status": "read"})

    index = build_index(base)
    series = series_of(index, object_ref, meeting_type)

    checks_skipped: List[Dict[str, str]] = []
    if not index["total"]:
        # Пустой индекс — не «всё в порядке», а отсутствие данных: заявить
        # «направление не появлялось на встречах» тут нельзя тем более.
        reason = "в базе не найдено ни одного протокола — сравнивать не с чем"
        checks_skipped = [{"check_id": cid, "reason": reason} for cid in CROSS_SERIES_CHECKS]
    elif index["coverage"] < HEADER_COVERAGE_MIN:
        reason = "покрытие шапками {0:.0%} из {1} протоколов — отрицательный вывод об отсутствии темы недостоверен".format(
            index["coverage"], index["total"])
        checks_skipped = [{"check_id": cid, "reason": reason} for cid in CROSS_SERIES_CHECKS]

    missing = [{"path": s["path"], "status": "missing" if s["status"] == "missing" else "unreadable", "role": s["role"]}
               for s in sources if s["status"] != "read"]

    return {
        "object_ref": object_ref,
        "object_kind": object_kind,
        "sources": sources,
        "missing": missing,
        "index": index,
        "series_key": series["series_key"],
        "series_dates": series["series_dates"],
        "checks_skipped": checks_skipped,
        "trimmed": trimmed,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Чек-лист источников и индекс встреч.")
    parser.add_argument("--base", required=True)
    parser.add_argument("--object", required=True)
    parser.add_argument("--kind", required=True, choices=["node", "goal", "person"])
    parser.add_argument("--type", dest="meeting_type", default=None, help="тип встречи для ключа серии")
    parser.add_argument("--out", help="куда записать manifest")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        manifest = collect(Path(args.base).resolve(), args.object, args.kind, args.meeting_type)
    except CollectError as exc:
        print(json.dumps({"ok": False, "error": exc.code, "message": exc.message}, ensure_ascii=False, indent=2))
        return exc.exit_code
    except OSError as exc:
        print(json.dumps({"ok": False, "error": "io_error", "message": str(exc)}, ensure_ascii=False))
        return 2

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = {
        "ok": True,
        "sources": len(manifest["sources"]),
        "missing": len(manifest["missing"]),
        "meetings_indexed": manifest["index"]["total"],
        "header_coverage": manifest["index"]["coverage"],
        "series_key": manifest["series_key"],
        "checks_skipped": [c["check_id"] for c in manifest["checks_skipped"]],
        "out": args.out,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Источников: {0} (нет или недоступны: {1})".format(payload["sources"], payload["missing"]))
        print("Встреч в индексе: {0}, покрытие шапками {1:.0%}".format(
            payload["meetings_indexed"], payload["header_coverage"]))
        print("Серия: {0}".format(payload["series_key"] or "не определена — свежесть по fallback"))
        if payload["checks_skipped"]:
            print("Кросс-серийные проверки пропущены: {0}".format(", ".join(payload["checks_skipped"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
