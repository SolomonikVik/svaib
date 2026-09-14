#!/usr/bin/env python3
"""Карта пространства — генератор (поставка клиенту, трек space-map).

Собирает карту из дерева управленческого пространства: корень (юниты с миссиями и
составом менеджмент-кита, файлы корня, покрытие), подкарта узла (файлы с миссиями,
подпапки, датированные группы), персональная подкарта зоны по ответу `whoami`.
Ничего в пространство не пишет: карта печатается в stdout или отдаётся хуку
`inject_space_map.py` (лежит рядом) как модуль — один процесс на вызов.

  ./space_map.py --base <корень> --emit [--focus dev,lab] [--no-model] [--no-skills]
  ./space_map.py --base <корень> --emit-node dev
  ./space_map.py --base <корень> --personalize --whoami-file <json>
  ./space_map.py --base <корень> --print-model          # стабильный блок для CLAUDE.md/AGENTS.md
  ./space_map.py --base <корень> --cache-json           # кэш пользователя этой машины

Оснастка замера (режимы --replace/--single/--focus-lazy/--k1..k3, запись копий
снимка) живёт в репозитории svaib — dev/space-map/engine/tools/build_map.py — и
импортирует этот файл: один источник генерации, в поставку едет только он.
Python 3.9+, stdlib.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

MARK_BEGIN = "<!-- SPACE-MAP:BEGIN generated -->"
MARK_END = "<!-- SPACE-MAP:END -->"
DATED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
SERVICE_DIRS = {"_templates", "_state", "node_modules", "_map"}
ROOT_BUDGET_LINES = 60
NODE_BUDGET_LINES = 50

MODEL_BLOCK = """\
**Модель пространства.** Папка = объект управления (компания, направление, команда).
Менеджмент-кит объекта: `01_overview` (обзор) · `02_active` (текущее + план) ·
`03_backlog` (будущее) · `04_progress` (хроника) · `05_decisions` (решения).
`README.md` папки — её карта. Встречи и датированные артефакты: `YYYY-MM-DD_*`.

**Куда идти за классом вопроса.** Сущность живёт там, где ею управляют:
текущая работа, планы и повестки юнита → его `02_active` · решения → `05_decisions`
своего уровня · метрики → `03_metrics/` своего уровня · люди и профили → `02_team/`
своего уровня · встречи юнита → его `meetings/` · курс, цели и стратегия компании →
`01_company/` · личное руководителя → `00_ceo/` · неразобранное → `_inbox/`.
Вопрос уровня компании решается в `01_company/`, вопрос направления — в его папке.

**Как ходить.** Адрес файла бери из карты и подкарт юнитов, не угадывай.
**Адрес в ответе называй полным путём от корня; факт о содержимом файла — только
после чтения этого файла.**
Когда нужен раздел, а не весь файл: сначала карточка — `Grep '^## ' <файл>` даст
оглавление с номерами строк, затем `Read` только нужного диапазона. Файл длиннее
~150 строк без карточки целиком не читай.
Свежий датированный артефакт выбирай листингом папки (Glob), не по памяти.
У каждого юнита в списке показан состав его менеджмент-кита («кит: …») — отвечая
про устройство, опирайся на него, а не на догадку.

**Границы карты.** {built}Глубина — юниты и их первый
уровень; содержимого в ней нет, только адреса и миссии.{coverage} «В карте нет» ≠ «в
пространстве нет»: прежде чем ответить, что чего-то не существует, проверь
Glob/листингом. Если карта противоречит дереву — прав диск."""

# R1 (12.09): строка, зовущая скаута пространства. Замеры показали, что субагент сам
# почти никогда не запускается (3 прогона из 36), а по прямой просьбе даёт лучшую верность
# и вчетверо меньшее окно координатора; скаут с правилами карты (`agents/svaib-scout.md`)
# читает вчетверо меньше типового. ❗️ В прод-форму строка пока не включена: она меняет
# измеренный стабильный блок, поэтому живёт за флагом `SVAIB_MAP_SCOUT=1` до своей серии.
SCOUT_BLOCK = """\
**Поиск по пространству отдавай скауту.** Если ответа нет в карте и нужен обход файлов —
вызови субагента `svaib-scout` (инструмент Agent) вместо самостоятельного поиска: он знает
канон пространства, возвращает выжимку с адресами и не расходует твой контекст. Сам читай
только то, что он назвал."""


def scout_enabled() -> bool:
    """Строка о скауте в карте — за флагом до своей серии замеров (R1, 12.09)."""
    return os.environ.get("SVAIB_MAP_SCOUT", "0") == "1"


# N2: блок «подкарта по требованию» — в emit-режиме юнитовые CLAUDE.md не пишутся,
# подкарту узла вне зоны агент получает вызовом генератора (шаг к модулю-навигатору)
ON_DEMAND_BLOCK = """\
**Подкарта узла вне зоны** (файлы с миссиями, подпапки, датированные группы) —
по требованию: `python3 "{tool}" --base "{base}" --emit-node <узел>` (Bash, ~0.1 с,
печатает карту, ничего не пишет). Заходя в узел вне зоны по вопросу о его
устройстве или составе — сначала возьми его подкарту, потом читай файлы."""


def coverage_line(base: Path, units, listed_files: int) -> str:
    """Счётчики покрытия для «Границ карты»: полна на уровне юнитов, неполна на
    уровне файлов — и говорит, насколько (форма признака неполноты, 10.09)."""
    total = md_counts(base).get(base.resolve(), 0)
    return (f" Покрытие: юнитов {len(units)} — все верхнего уровня; файлов с адресом "
            f"в карте {listed_files} из {total} в дереве — карта полна по юнитам и "
            f"НЕполна по файлам.")


def read_head(path: Path, limit: int = 40):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return [next(f, "") for _ in range(limit)]
    except OSError:
        return []


def mission_of_file(path: Path, with_desc: bool = False) -> str | None:
    """title из YAML, иначе H1; при with_desc — плюс description, если несёт новое."""
    lines = read_head(path)
    title = desc = None
    if lines and lines[0].strip() == "---":
        for l in lines[1:]:
            if l.strip() == "---":
                break
            m = re.match(r'^title:\s*"?(.+?)"?\s*$', l)
            if m:
                title = m.group(1).strip()
            m = re.match(r'^description:\s*"?(.+?)"?\s*$', l)
            if m:
                desc = m.group(1).strip()
    if not title:
        title = next((l[2:].strip() for l in lines if l.startswith("# ")), None)
    if with_desc and desc and title and desc[:40] != title[:40]:
        return f"{title} · {desc[:110]}"
    return title or (desc if with_desc else None)


CANON_DIR_MISSIONS = {
    "02_team": "команда: оргструктура и профили",
    "03_metrics": "метрики",
    "meetings": "память встреч",
    "clients": "клиентские досье",
    "projects": "проекты",
    "05_decisions": "решения",
}


def mission_of_dir(d: Path) -> str | None:
    for cand in ("README.md", "01_overview.md"):
        p = d / cand
        if p.exists():
            m = mission_of_file(p)
            if m:
                return m
    return CANON_DIR_MISSIONS.get(d.name)


def md_files(d: Path):
    return sorted(p for p in d.iterdir() if p.is_file() and p.suffix == ".md")


_MD_COUNTS: dict = {}


def md_counts(base: Path) -> dict:
    """Число .md в каждом каталоге дерева (рекурсивно), один os.walk на базу —
    вместо rglob на каждый юнит и на всё дерево (ревью 10.09: Drive)."""
    base = base.resolve()
    if base in _MD_COUNTS:
        return _MD_COUNTS[base]
    counts: dict = {}
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SERVICE_DIRS]
        n = sum(1 for f in files if f.endswith(".md"))
        p = Path(root)
        counts[p] = counts.get(p, 0) + n
        for anc in p.parents:
            counts[anc] = counts.get(anc, 0) + n
            if anc == base:
                break
    _MD_COUNTS[base] = counts
    return counts


def subdirs(d: Path):
    return sorted(
        p for p in d.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in SERVICE_DIRS
    )


def dated_summary(files) -> str | None:
    dated = sorted(f.name for f in files if DATED_RE.match(f.name))
    if len(dated) < 3:
        return None
    return f"{len(dated)} датированных файлов, {dated[0][:10]} … {dated[-1][:10]} — свежий выбирай листингом"


KIT_ELEMENTS = [
    ("01_overview", "overview"), ("02_active", "active"), ("03_backlog", "backlog"),
    ("03_metrics", "metrics"), ("04_progress", "progress"), ("05_decisions", "decisions"),
    ("02_team", "team"), ("meetings", "meetings"),
]


NODE_MARKER_FILE = "README.md"        # узел = папка с README.md, не с 01_overview.md (уточнение Эрика 14.09; тот же предикат в хуке).
                                       # Узел — любая управляемая папка со своей картой (канон scaffold); юнит —
                                       # узел с менеджмент-китом, полноценный объект управления (не путать: NODE_MARKER_FILE
                                       # задаёт границу узла, а не юнита).
NODE_EXCLUDED = {"zz_archive", "_inbox"}  # служебные — карта их узлами не считает (тот же NOT_NODES, что в хуке)


def kit_of(d: Path) -> str | None:
    """Фактический состав менеджмент-кита папки — из дерева, не из канона."""
    found = []
    for stem, label in KIT_ELEMENTS:
        if (d / f"{stem}.md").exists() or (d / stem).is_dir():
            found.append(label)
    return "·".join(found) if found else None


def describe_dir_line(d: Path, base: Path) -> str:
    rel = d.relative_to(base)
    mission = mission_of_dir(d)
    n = md_counts(base).get(d.resolve(), 0)
    if d.name == "zz_archive":
        return f"- `{rel}/` — архив, только по явной надобности (файлов: {n})"
    if d.name == "_inbox":
        return f"- `{rel}/` — входящее до разбора (файлов: {n})"
    kit = kit_of(d)
    kit_part = f" (кит: {kit}; файлов: {n})" if kit else (f" (файлов: {n})" if n else "")
    return f"- `{rel}/` — {mission or d.name}{kit_part}"


# ---------------------------------------------------------------------------
# Маршруты чтения из README узла (эксперимент 11.09, решение Эрика). В подкарту идёт
# только кастомная логика узла — то, что из дерева не выводится: цепочки из ≥2 целей,
# цели вне узла, указатели на раздел файла, условия, «читать первым», внешние ссылки.
# Строки уровня канона («Войти → 01_overview», «Что в работе → 02_active») и строки с
# одной целью-файлом без оговорок отбрасываются — их несут стабильный блок и миссии
# файлов в подкарте. Каждая цель проверяется по дереву: битые строки выбрасываются,
# счётчик «проверены M из N» — признак честности. Прод-форма с 11.09 (решение Эрика):
# включено; SVAIB_MAP_ROUTES=0 выключает (стенд, откат). Маршруты README корня — с корневой картой.
# ---------------------------------------------------------------------------

ROUTES_HEAD_RE = re.compile(r"^##+\s*(?:.*маршрут.*чтен.*|.*чтен.*маршрут.*|reading routes?.*)$", re.I | re.M)
ROUTE_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)|`([^`]+)`")
ROUTE_COND_RE = re.compile(r"(?<!\w)(если|когда|кроме|не из|затем|сначала|потом|перед|после|первым|только|по умолчанию|обязательно|раздел|секци|глава)(?!\w)", re.I)
KIT_NAMES = {"README.md", "01_overview.md", "02_active.md", "03_backlog.md", "04_progress.md", "05_decisions.md",
             "03_metrics", "02_team", "meetings", "_inbox", "zz_archive", "_templates"}
ROUTES_MAX_LINES = 8


def routes_enabled() -> bool:
    return os.environ.get("SVAIB_MAP_ROUTES", "1").strip().lower() not in ("0", "false", "off")


def _looks_like_path(t: str) -> bool:
    return " " not in t and ("/" in t or t.endswith(".md"))   # `Grep '^## ' x.md` — команда, не путь


def _route_targets(line: str) -> list[str]:
    """Цели строки: markdown-ссылки и backtick-пути (backtick без «/» и «.md» — не путь, а имя: не цель)."""
    out = []
    for a, b in ROUTE_LINK_RE.findall(line):
        t = (a or b or "").strip()
        if not t or t.startswith("#"):
            continue
        if b and not a and not _looks_like_path(t) and not t.startswith("http"):
            continue
        out.append(t)
    return out


def _route_is_custom(line: str, targets: list[str]) -> bool:
    """Кастомная логика юнита, а не дубль канона/структуры."""
    if ROUTE_COND_RE.search(line):
        return True
    local = [t for t in targets if not t.startswith("http")]
    if any(t.startswith("http") for t in targets):
        return True
    if len(local) >= 2 or "../" in line:
        return True
    if not local:
        return False
    t = local[0].split("#")[0].rstrip("/")
    if "{" in t:                              # `{project}/01_overview.md` — шаблон канона
        return False
    name = t.split("/")[-1]
    if name in KIT_NAMES or t.endswith("/README.md"):
        return False                          # один китовый адрес — канон / структура
    return "/" in t                           # один файл своей папки — миссию несёт подкарта; путь вглубь — берём


def node_routes(node: Path, base: Path) -> str | None:
    """Раздел «Маршруты чтения» README узла после фильтра и проверки целей по дереву."""
    readme = node / "README.md"
    if not readme.is_file():
        return None
    text = readme.read_text(encoding="utf-8", errors="replace")
    m = ROUTES_HEAD_RE.search(text)
    if not m:
        return None
    body = text[m.end():]
    nxt = re.search(r"^#{1,6}\s", body, re.M)   # любой заголовок закрывает секцию (### тоже)
    body = body[:nxt.start()] if nxt else body
    kept, total, broken = [], 0, 0
    for raw in body.splitlines():
        line = raw.strip()
        if not (line.startswith(("-", "*")) or re.match(r"^\d+[.)]", line)):
            continue
        total += 1
        targets = _route_targets(line)
        if not _route_is_custom(line, targets):
            continue
        def _rel(t: str) -> str | None:
            """Путь цели от корня пространства; None — цели нет в дереве или она вне пространства."""
            p = (node / t.split("#")[0]).resolve()
            try:
                rel = p.relative_to(base.resolve()).as_posix()
            except ValueError:
                return None                       # ../ за пределы пространства — битая цель
            return rel if p.exists() else None
        ok = all(t.startswith("http") or "{" in t or _rel(t) is not None for t in targets)
        if not ok:
            broken += 1
            continue
        # адреса — от корня пространства: ссылки и backtick-пути README относительны папке узла
        def _abs(mm):
            t = (mm.group(1) or mm.group(2) or "").strip()
            if not t or t.startswith(("http", "#")) or "{" in t or (mm.group(2) and not _looks_like_path(t)):
                return mm.group(0)
            rel = _rel(t)
            if rel is None:
                return mm.group(0)
            frag = "#" + t.split("#", 1)[1] if "#" in t else ""
            return f"`{rel}{frag}`"
        line = ROUTE_LINK_RE.sub(_abs, line)
        kept.append("- " + line.lstrip("-* ").strip())
    if not kept:
        return None
    head = (f"**Маршруты узла** (из README, только логика узла; строк {len(kept)} из {total}, "
            f"с целями не в дереве отброшено: {broken}):")
    return "\n".join([head] + kept[:ROUTES_MAX_LINES]
                     + ([f"- … ещё {len(kept) - ROUTES_MAX_LINES} — в README узла"] if len(kept) > ROUTES_MAX_LINES else []))


def node_map(node: Path, base: Path, deep: bool = False) -> str:
    lines = [f"## Карта узла (сгенерирована из дерева)", ""]
    mission = mission_of_dir(node)
    rel = node.resolve().relative_to(base.resolve()).as_posix() if base.resolve() in node.resolve().parents else node.name
    if mission:
        lines.append(f"**{rel}/** — {mission}")
        lines.append("")
    files = md_files(node)
    ds = dated_summary(files)
    plain = [f for f in files if not (DATED_RE.match(f.name) and ds)
             and f.name not in ("CLAUDE.md", "AGENTS.md")]
    for f in plain[:15]:
        m = mission_of_file(f, with_desc=True)
        lines.append(f"- `{f.name}` — {m}" if m else f"- `{f.name}`")
    if len(plain) > 15:
        lines.append(f"- … ещё файлов: {len(plain) - 15} — смотри листингом")
    if ds:
        lines.append(f"- {ds}")
    # счётчики: если дерево базы уже обойдено (корневая карта) — берём его; иначе обходим
    # только узел (хук node-enter: отдельный процесс на каждый вход, полный обход svaib
    # под нагрузкой стенда стоил 0,6–1,4 с на вызов — замер 10.09 вечер)
    counts = _MD_COUNTS.get(base.resolve()) or md_counts(node)
    for sd in subdirs(node):
        sfiles = md_files(sd)
        sds = dated_summary(sfiles)
        m = mission_of_dir(sd)
        n = counts.get(sd.resolve(), 0)
        # служебные — не узлы даже с README/китом, вход туда не даёт хук (NOT_NODES; ревью 14.09)
        is_node = sd.name not in NODE_EXCLUDED and (sd / NODE_MARKER_FILE).is_file()
        kit = kit_of(sd) if is_node else None          # кит показываем только у узла со своей картой
        kit_part = f"юнит, кит: {kit}; " if kit else ("узел; " if is_node else "")
        if sd.name == "zz_archive":
            lines.append(f"- `{sd.name}/` — архив (файлов: {n}), только по явной надобности")
        elif sd.name == "_inbox":
            lines.append(f"- `{sd.name}/` — входящее до разбора (файлов: {n})")
        elif sds:
            tag = f" ({kit_part.rstrip('; ')})" if kit_part else ""   # пометка не терялась у датированных групп (ревью 14.09)
            lines.append(f"- `{sd.name}/` — {m or sd.name}: {sds}{tag}")
        else:
            lines.append(f"- `{sd.name}/` — {m or sd.name} ({kit_part}файлов: {n})")
        if deep and not sds and sd.name != "zz_archive":
            for f in sfiles[:8]:
                fm = mission_of_file(f)
                lines.append(f"  - `{sd.name}/{f.name}`" + (f" — {fm}" if fm else ""))
    budget = NODE_BUDGET_LINES * (2 if deep else 1)
    if len(lines) > budget:
        lines = lines[:budget] + ["- … подкарта обрезана бюджетом строк — остальное листингом"]
    if routes_enabled():   # маршруты — сверх бюджета дерева, у них свой потолок ROUTES_MAX_LINES
        rt = node_routes(node, base)
        if rt:
            lines.append("")
            lines.extend(rt.split("\n"))
    lines.append("")
    lines.append("Карта не полна: содержимое глубже — листингом. «В карте нет» ≠ «нет».")
    return "\n".join(lines)


ADDR_RE = re.compile(r"^\s*- `[^`]+\.md`", re.M)


def count_addresses(text: str) -> int:
    return len(ADDR_RE.findall(text))


def root_map(base: Path, date: str, single: bool = False, coverage: str = "",
             emit: bool = False, model: bool = True) -> str:
    lines = ["## Карта пространства (сгенерирована из дерева)", ""]
    if model:
        lines.append(MODEL_BLOCK.format(built=f"Карта собрана из дерева {date}. ", coverage=coverage))
    else:  # стабильный блок живёт в корневом файле пространства и приходит каждый ход — не дублировать
        lines.append(f"Правила чтения карты — в корневом файле пространства (`CLAUDE.md`/`AGENTS.md`, "
                     f"раздел «Карта пространства» / «Space Map»). Карта собрана "
                     f"из дерева {date}, глубина — юниты и их первый уровень.{coverage}")
    lines.append("")
    where = (" (подробные карты — ниже):" if single
             # emit без модели — доставка хуками (Claude Code): подкарта узла придёт при входе;
             # emit с моделью — сред без хуков (Codex/Cursor): подкарта по требованию (ON_DEMAND_BLOCK)
             else " (подкарты зоны — ниже, остальных — при первом обращении к файлам узла):" if emit and not model
             else " (подкарты зоны — ниже, остальных — по требованию: `--emit-node <узел>`):" if emit
             else " (подробная карта — в `CLAUDE.md` юнита):")
    lines.append("**Юниты**" + where)
    lines.append("")
    for d in subdirs(base):
        lines.append(describe_dir_line(d, base))
    root_files = md_files(base)
    named = [f for f in root_files if f.name not in ("CLAUDE.md", "AGENTS.md")]
    if named:
        lines.append("")
        lines.append("**Файлы корня:**")
        for f in named[:8]:
            m = mission_of_file(f)
            lines.append(f"- `{f.name}` — {m}" if m else f"- `{f.name}`")
    budget = ROOT_BUDGET_LINES + 20
    if len(lines) > budget:
        lines = lines[:budget] + ["- … карта обрезана бюджетом строк — остальное листингом"]
    return "\n".join(lines)


def first_sentence(text: str, cap: int = 160) -> str:
    text = " ".join(text.split())
    for sep in (". ", "! "):
        i = text.find(sep)
        if 0 < i < cap:
            return text[: i + 1]
    if len(text) <= cap:
        return text
    return text[:cap].rsplit(" ", 1)[0] + "…"


def skill_description(head: str) -> str:
    m = re.search(r"^description:\s*(.+)$", head, re.M)
    if not m:
        return ""
    val = m.group(1).strip().strip('"')
    if val in (">", ">-", "|", "|-"):  # multiline YAML — берём первую строку блока
        after = head[m.end():]
        for l in after.split("\n"):
            if l.strip():
                return l.strip()
        return ""
    return val


VARIANT_SUFFIXES = ("-beta", "-v2", "-v3", "-new", "-old", "-legacy", "-experimental")


def skills_registry(base: Path) -> str | None:
    """Реестр инструментов из .claude/skills/*/SKILL.md — выводится из дерева.

    Курация вариантов — тоже из дерева: если рядом с `X` лежит `X-beta`/`X-v2`,
    головным считается `X`, вариант помечается (ловушка T7/S13)."""
    items = {}
    for sk in sorted(base.glob(".claude/skills/*/SKILL.md")):
        head = "".join(read_head(sk, 30))
        name = re.search(r"^name:\s*(.+)$", head, re.M)
        label = (name.group(1) if name else sk.parent.name).strip().strip('"')
        items[label] = first_sentence(skill_description(head))
    if not items:
        return None
    rows = []
    for label, desc in items.items():
        mark = ""
        for suf in VARIANT_SUFFIXES:
            if label.endswith(suf) and label[: -len(suf)] in items:
                mark = f" ❗️вариант; головной — `{label[: -len(suf)]}`"
                break
        rows.append(f"- `{label}` — {desc}{mark}")
    return "**Инструменты (скиллы `.claude/skills/`):**\n\n" + "\n".join(rows)


# ---------------------------------------------------------------------------
# N2 · идентичность от платформы, кэш на машине (решение Эрика 10.09; ревью 10.09)
#
# «Кто» приходит из MCP `whoami` (subject, tenant, profile_path, about). Ответ
# ловит PostToolUse-хук и отдаёт сюда JSON целиком — без интерполяции в shell.
# Генератор по profile_path читает профиль в пространстве, выводит юниты зоны
# и пишет кэш в state-каталог машины — ВНЕ репозитория и Drive. Кэш ключуется
# email аккаунта Claude + корнем пространства (ревью: один аккаунт, две базы),
# хранит tenant для сверки, живёт CACHE_TTL_HOURS. Без email кэша нет: каждая
# сессия персонализируется заново через whoami (Cowork).
# ---------------------------------------------------------------------------

CACHE_TTL_HOURS = 24
CACHE_VERSION = 2


def state_dir() -> Path:
    override = os.environ.get("SVAIB_STATE_DIR")  # стенд замера: свой каталог на прогон
    if override:
        return Path(override)
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "svaib"
    return Path.home() / ".local" / "state" / "svaib"


def account_email() -> str:
    """Email аккаунта Claude Code с этой машины; пусто — если файла нет (Cowork)."""
    try:
        d = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
        return ((d.get("oauthAccount") or {}).get("emailAddress") or "").strip().lower()
    except (OSError, ValueError, AttributeError):
        return ""


def cache_path(email: str, base: Path) -> Path | None:
    if not email:
        return None
    key = hashlib.sha256(f"{email}\n{base.resolve()}".encode("utf-8")).hexdigest()[:20]
    return state_dir() / "identity" / f"{key}.json"


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def read_cache(email: str, base: Path) -> dict | None:
    """Свежая запись этого аккаунта для этого корня, иначе None. Поле `fresh`
    отдельно: протухшая запись возвращается с fresh=False (subject известен)."""
    p = cache_path(email, base)
    if p is None:
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or d.get("v") != CACHE_VERSION:
        return None
    if d.get("email") != email or d.get("base") != str(base.resolve()):
        return None
    if not isinstance(d.get("subject"), str) or not isinstance(d.get("units"), list):
        return None
    try:
        age = _now() - datetime.datetime.fromisoformat(d["ts"])
    except (KeyError, TypeError, ValueError):
        return None
    d["fresh"] = datetime.timedelta(0) <= age < datetime.timedelta(hours=CACHE_TTL_HOURS)
    d["units"] = [u for u in d["units"] if isinstance(u, str)]
    return d


def write_cache(email: str, base: Path, rec: dict) -> Path | None:
    """0600, атомарно (tmp + replace); без email — не пишется."""
    p = cache_path(email, base)
    if p is None:
        return None
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    rec = dict(rec, v=CACHE_VERSION, email=email, base=str(base.resolve()),
               ts=_now().isoformat(timespec="seconds"))
    fd, tmp = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=str(p.parent))   # свой tmp на процесс
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    return p


ZONE_HEADINGS = ("зона", "роль", "responsib", "role")
UNIT_RE = r"(?<![\w/]){unit}(?![\w-])"


def _frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end > 0 else ""


def units_from_frontmatter(fm: str) -> list[str]:
    """`units: dev, lab` · `units: [dev, lab]` · блок `units:\\n  - dev`."""
    m = re.search(r"^units:[ \t]*(.*)$", fm, re.M)  # не \s: съедает перевод строки и первый «- элемент»
    if not m:
        return []
    inline = m.group(1).strip().strip("[]")
    if inline:
        return [u.strip().strip("`\"' /") for u in inline.split(",") if u.strip()]
    items = []
    for line in fm[m.end():].split("\n")[1:]:  # [0] — хвост строки `units:`
        mm = re.match(r"^\s+-\s*(.+?)\s*$", line)
        if not mm:
            break
        items.append(mm.group(1).strip().strip("`\"' /"))
    return items


def units_in_text(text: str, units_all: list[str]) -> list[str]:
    low = text.lower()
    return [u for u in units_all if re.search(UNIT_RE.format(unit=re.escape(u.lower())), low)]


def profile_units(base: Path, profile_path: str, units_all: list[str]) -> list[str]:
    """Юниты зоны из профиля: frontmatter `units:` (канон) → имена юнитов в тексте
    секции «Роль/зона» (или первой секции — профиль не по канону). Проза наружу
    не возвращается: в контекст едут только юниты (ревью 10.09)."""
    if not profile_path:
        return []
    p = (base / profile_path).resolve()
    if base not in p.parents:
        raise ValueError(f"профиль {profile_path!r} вне пространства {base}")
    if not p.is_file():
        return []
    text = p.read_text(encoding="utf-8", errors="replace")
    found = [u for u in units_from_frontmatter(_frontmatter(text)) if u in units_all]
    if found:
        return found
    sections = re.split(r"^## ", text, flags=re.M)[1:]
    zone_text = ""
    for sec in sections:
        head, _, body = sec.partition("\n")
        if any(k in head.lower() for k in ZONE_HEADINGS):
            zone_text = body
            break
    if not zone_text and sections:
        zone_text = sections[0].partition("\n")[2]
    return units_in_text(zone_text, units_all)


def parse_whoami(raw) -> dict:
    """Ответ whoami как его отдаёт PostToolUse (строка JSON) или объект."""
    data = raw
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, list):  # content-блоки MCP
        for block in data:
            if isinstance(block, dict) and block.get("type") == "text":
                try:
                    data = json.loads(block["text"])
                    break
                except (ValueError, KeyError):
                    continue
    if isinstance(data, dict) and "structuredContent" in data:
        data = data["structuredContent"]
    if not isinstance(data, dict) or not data.get("subject_id"):
        raise ValueError("в ответе whoami нет subject_id")
    ws = data.get("workspace") or {}
    return {"subject": str(data["subject_id"]), "tenant": str(data.get("tenant_id") or ""),
            "role": str(data.get("role") or ""), "about": str(data.get("about") or ""),
            "profile_path": str(ws.get("profile_path") or "")}


def personalize(base: Path, who: dict, units_override: list[str] | None = None) -> tuple[str, dict]:
    """После whoami: юниты зоны (профиль → about → override), подкарты зоны, кэш.
    Возвращает (текст для контекста, запись кэша)."""
    base = base.resolve()
    units_all = [u.name for u in subdirs(base) if u.name not in ("zz_archive", "_inbox")]
    units = profile_units(base, who.get("profile_path", ""), units_all)
    source = "профиль"
    if not units and who.get("about"):
        units = units_in_text(who["about"], units_all)
        source = "about"
    if units_override:
        units = [u.strip().strip("/") for u in units_override if u.strip()]
        source = "указаны"
    units = [u for u in units if u in units_all]
    rec = {"subject": who["subject"], "tenant": who.get("tenant", ""), "role": who.get("role", ""),
           "profile_path": who.get("profile_path", ""), "units": units}
    email = account_email()
    cp = write_cache(email, base, rec)
    remembered = (f"пользователь запомнен на этой машине на {CACHE_TTL_HOURS} ч" if cp
                  else "аккаунт Claude на машине не определён — кэша нет, в следующей сессии снова `whoami`")
    lines = [f"`map_profile: {who['subject']}` — персональная подкарта зоны; профиль "
             f"`{who.get('profile_path') or '—'}`; {remembered}."]
    if units:
        lines.append(f"\n**Юниты зоны** ({source}): " + " · ".join(f"`{u}/`" for u in units))
        for u in units:
            lines.append("\n" + node_map(base / u, base))
    else:
        lines.append("\nЮниты зоны не выведены ни из профиля, ни из `about`. Персональной подкарты нет: "
                     "работай по общей карте — подкарта узла приходит при первом обращении к его файлам "
                     f"(папки верхнего уровня: {', '.join(units_all)}). Точный источник зоны — поле "
                     "`units:` в шапке профиля.")
    return "\n".join(lines), rec


def emit_text(base: Path, focus: list[str] | None = None, no_model: bool = False,
              no_skills: bool = False) -> str:
    """N2: карта как текст, репозиторий не трогается. Корень (+ подкарты зоны) (+ реестр
    скиллов). Рецепт «подкарта по требованию» — только вместе со стабильным блоком:
    при --no-model он уже в CLAUDE.md."""
    base = base.resolve()
    date = datetime.date.today().isoformat()
    units = [u for u in subdirs(base) if u.name not in ("zz_archive", "_inbox")]
    names = {u.name for u in units}
    focus = [f for f in (focus or []) if f]
    zone_maps = [node_map(u, base) for u in units if u.name in focus]
    missing = [f for f in focus if f not in names]
    root_named = [f for f in md_files(base) if f.name not in ("CLAUDE.md", "AGENTS.md")][:8]
    listed = len(root_named) + sum(count_addresses(z) for z in zone_maps)
    parts = [root_map(base, date, coverage=coverage_line(base, units, listed), emit=True,
                      model=not no_model)]
    if routes_enabled():   # README корня — вместе с корневой картой (решение Эрика 11.09)
        rr = node_routes(base, base)
        if rr:
            parts.append(rr.replace("**Маршруты узла** (из README", "**Маршруты пространства** (из README корня", 1))
    if not no_model:
        tool = Path(__file__).resolve()
        tool_s = tool.relative_to(base).as_posix() if base in tool.parents else tool.as_posix()
        parts.append(ON_DEMAND_BLOCK.format(tool=tool_s, base=base.as_posix()))
        if scout_enabled():   # тот же флаг, что у --print-model — единый источник (ревью 14.09)
            parts.append(SCOUT_BLOCK)
    if zone_maps:
        zone = " · ".join(f"`{f}/`" for f in focus if f in names)
        parts.append(f"**Зона ответственности пользователя** — {zone}. Подробные карты этих "
                     "юнитов — ниже; по вопросу из зоны адрес бери отсюда.")
        parts.extend(zone_maps)
    if missing:
        parts.append("Юниты зоны, которых нет в дереве (подкарты не собраны): "
                     + ", ".join(f"`{m}/`" for m in missing))
    reg = None if no_skills else skills_registry(base)
    if reg:
        parts.append(reg)
    return "\n\n".join(parts)


def emit_node_text(base: Path, node: str) -> str:
    base = base.resolve()
    u = (base / node.strip().strip("/")).resolve()
    if base not in u.parents or not u.is_dir():
        raise ValueError(f"узел {node!r} не найден в {base}")
    return node_map(u, base)



# ---------------------------------------------------------------------------- CLI (прод-режимы)

def add_prod_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--base", required=True)
    ap.add_argument("--emit", action="store_true",
                    help="N2/прод: напечатать карту в stdout — корень (+ подкарты --focus, реестр "
                         "скиллов); в файлы ничего не пишется, --out не нужен")
    ap.add_argument("--emit-node", default="",
                    help="N2/прод: напечатать подкарту одного узла (путь от корня) и выйти")
    ap.add_argument("--no-skills", action="store_true",
                    help="--emit без реестра скиллов (Claude Code и так показывает скиллы в "
                         "системном промпте; для Codex/Cursor реестр оставлять)")
    ap.add_argument("--no-model", action="store_true",
                    help="--emit без стабильного блока (модель пространства, как ходить): он "
                         "живёт в CLAUDE.md корня и приходит каждый ход")
    ap.add_argument("--cache-json", action="store_true",
                    help="напечатать кэш пользователя этой машины для --base (JSON, {} если нет)")
    ap.add_argument("--print-model", action="store_true",
                    help="напечатать стабильный блок для CLAUDE.md корня (единый источник текста)")
    ap.add_argument("--personalize", action="store_true",
                    help="N2: после whoami — подкарты зоны по профилю + кэш пользователя на машине")
    ap.add_argument("--whoami-file", default="",
                    help="--personalize: файл с ответом whoami (JSON); `-` — stdin. Не через shell-аргументы")
    ap.add_argument("--subject", default="", help="--personalize без файла: subject_id из whoami")
    ap.add_argument("--profile", default="", help="--personalize без файла: profile_path из whoami")
    ap.add_argument("--units", default="", help="--personalize: юниты зоны через запятую (переопределяет)")


def run_prod(args) -> bool:
    """Выполнить прод-режим, если он запрошен. True — обработано."""
    src = Path(args.base).expanduser()
    focus = [f.strip().rstrip("/") for f in getattr(args, "focus", "").split(",") if f.strip()]
    # --- прод-режимы (N2): ничего не пишут в пространство ---
    try:
        if args.cache_json:
            print(json.dumps(read_cache(account_email(), src) or {}, ensure_ascii=False))
            return True
        if args.print_model:
            # Без HTML-комментария-маркера (снят 14.09, решение Эрика): наличие блока в CLAUDE.md/AGENTS.md
            # хук узнаёт по заголовку раздела — «## Карта пространства» / «## Space Map» — а не по метке в тексте.
            print(MODEL_BLOCK.format(built="Дата сборки и покрытие — в динамической части (секция с `map_profile`). ", coverage=""))
            if scout_enabled():
                print("\n" + SCOUT_BLOCK)
            return True
        if args.personalize:
            if args.whoami_file:
                raw = sys.stdin.read() if args.whoami_file == "-" else Path(args.whoami_file).read_text(encoding="utf-8")
                who = parse_whoami(raw)
            elif args.subject:
                who = {"subject": args.subject, "profile_path": args.profile, "tenant": "", "role": "", "about": ""}
            else:
                raise SystemExit("space_map: " + "--personalize требует --whoami-file (JSON ответа whoami) или --subject/--profile")
            units = [u for u in args.units.split(",") if u.strip()] or None
            text, _ = personalize(src, who, units)
            print(text)
            return True
        if args.emit_node:
            print(emit_node_text(src, args.emit_node))
            return True
        if args.emit:
            print(emit_text(src, focus, no_model=args.no_model, no_skills=args.no_skills))
            return True
    except (ValueError, OSError) as e:
        print(f"space_map: {e}", file=sys.stderr)
        sys.exit(2)

    return False


def main():
    ap = argparse.ArgumentParser()
    add_prod_args(ap)
    ap.add_argument("--focus", default="", help="--emit: юниты зоны через запятую — их подкарты инлайн")
    args = ap.parse_args()
    if not run_prod(args):
        ap.error("укажи режим: --emit, --emit-node, --personalize, --print-model или --cache-json")


if __name__ == "__main__":
    main()
