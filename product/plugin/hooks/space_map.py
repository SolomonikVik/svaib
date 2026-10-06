#!/usr/bin/env python3
"""Карта пространства — генератор (поставка клиенту).

Собирает карту из дерева управленческого пространства: корень (юниты с миссиями и
составом менеджмент-кита, файлы корня, покрытие), подкарта узла (файлы с миссиями,
подпапки, датированные группы), персональная подкарта зоны по ответу `whoami`.
Ничего в пространство не пишет: карта печатается в stdout или отдаётся хуку
`inject_space_map.py` (лежит рядом) как модуль — один процесс на вызов.

  ./space_map.py --base <корень> --emit [--focus dev,lab] [--no-model] [--no-skills]
  ./space_map.py --base <корень> --emit-node dev
  ./space_map.py --base <корень> --personalize --whoami-file <json>
  ./space_map.py --base <корень> --print-model          # стабильный блок корневого файла
  ./space_map.py --base <корень> --write-model          # переписать его в AGENTS.md
  ./space_map.py --base <корень> --cache-json           # кэш пользователя этой машины

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
SERVICE_DIRS = {"_templates", "_state", "node_modules", "_map", "__pycache__"}
ROOT_BUDGET_LINES = 60
NODE_BUDGET_LINES = 50

MODEL_BLOCK = """\
**Модель пространства.** Бизнес разложен по папкам так, как им реально управляют.
**Направления** — части бизнеса, которыми управляют отдельно: вся компания, маркетинг,
продажи, продукт, филиал, клиенты. Направление начинается с одного файла, при живой работе
разворачивается в папку и обрастает ракурсами и management kit. Папки направлений лежат
в корне; внутри могут быть вложенные направления поменьше.
**Ракурсы** — стороны, с которых ведут направление: стратегия (`01_strategic/`), команда
(`02_team/`), метрики (`03_metrics/`), а также проекты, процессы, знания. Главные ракурсы
пронумерованы, остальные — нет. В ракурсе ведётся вся содержательная работа по этой стороне.
В пространстве есть также служебные папки.
Management kit объекта: `01_overview` (обзор) · `02_active` (текущее + план) ·
`03_backlog` (будущее) · `04_progress` (хроника) · `05_decisions` (решения).
`README.md` папки — её карта. Встречи и датированные артефакты: `YYYY-MM-DD_*`.

**Куда идти за классом вопроса.**
текущая работа, планы и повестки management unit → его `02_active` · решения → `05_decisions`
своего уровня · метрики → `03_metrics/` своего уровня · люди и профили → `02_team/`
своего уровня · встречи management unit → его `meetings/` · курс, цели и стратегия компании →
`01_company/` · личное руководителя → `00_ceo/` · неразобранное → `_inbox/` ·
правила работы агента на всё пространство, находки о расхождениях с каноном и служебное агента → `.svaib/`;
учёт скиллов → `.svaib/usage/`.
Вопрос уровня компании решается в `01_company/`, вопрос направления — в его папке.

**Как ходить.** Адрес файла бери из карты, README, ссылки или результата ограниченного поиска; не угадывай.
Полный путь от корня указывай в адресе ссылки.
**Факт о содержимом файла — только после чтения этого файла тобой или скаутом.**
Нужен раздел, а не весь файл — сначала получи оглавление файла: поиск строк `^## ` в файле
даёт заголовки с номерами строк; затем прочитай только нужный диапазон. Файл длиннее
~150 строк без оглавления целиком не читай.
Файл выбирай по полному пути и `title` (нет `title` — H1), не открывая. Кандидатов из поиска
или из папки без подкарты сверяй одним поиском `^title:` по папке, затем читай выбранный.
Свежий датированный артефакт выбирай листингом папки, не по памяти.
Отвечая про устройство, опирайся на состав management kit из списка («kit: …»),
а не на догадку. В подкарте пометка «узел» — вложенная папка со своей подкартой;
«unit, kit: …» — техническая метка узла с найденными элементами управления;
их фактический состав перечислен после `kit`. Метка не обещает полного набора файлов.

**Границы карты.** {built}Глубина — management units и их первый
уровень; содержимого в карте нет, только адреса и миссии.{coverage}
Подкарта содержит только часть маршрутов чтения README; правил узла, маршрутов записи
и связанных контекстов она не заменяет. «В карте нет» ≠ «в пространстве нет»:
прежде чем ответить, что чего-то не существует, проверь
листингом. Если карта противоречит дереву — прав диск."""

# Строка, зовущая скаута пространства. Замеры показали, что субагент сам
# почти никогда не запускается (3 прогона из 36), а по прямой просьбе даёт лучшую верность
# и вчетверо меньшее окно координатора; скаут с правилами карты (`agents/svaib-scout.md`)
# читает вчетверо меньше типового. Строка включена по умолчанию и едет
# клиентам со скаутом. Выключить: `SVAIB_MAP_SCOUT=0`.
SCOUT_BLOCK = """\
**Поиск по пространству отдавай скауту.** Если ответа нет в карте и нужен обход файлов,
не ищи сам широким обходом — передай поиск субагенту `svaib-scout`, он приезжает с плагином svaib.
Скаута в этой среде нет — отдай поиск встроенному субагенту: в Codex это коллаборация
субагентов (`multi_agent`); нет и его — ищи сам, но узким запросом по названным адресам.
Скаут не видит карту — передай ему вопрос, известные адреса и границу поиска.
Он читает в своём контексте и возвращает выжимку с адресами; используй её.
Нужна проверка — прочитай соответствующий источник."""

# Один текст для Claude и Codex — инструкция живёт в AGENTS.md,
# CLAUDE.md импортирует её.


# Метка карты — правило доставки хуками (whoami, подкарта при входе); одна для Claude и Codex.
LABEL_BLOCK = """\
**`map_profile` в контексте.** Динамическую карту узнавай по отдельной строке с `map_profile` и значением профиля, поданной хуком; упоминания метки в этой инструкции картой не считаются. Кто пользователь — имя, профиль, зона — бери из неё. `map_profile` нет или он `general` — вызови `whoami` (MCP svaib), подкарта зоны придёт сама; `whoami` недоступен — пользователя не угадывай и имя не подставляй. Подкарта узла приходит сама при первом обращении к его файлам — чтением, поиском или командой; после первого обращения учти пришедшую подкарту до выводов об устройстве и составе узла. Динамической секции нет — для поиска неизвестного адреса ходи по `README.md` папок; известный файл читай сразу."""

# Раздел стабильной модели — в AGENTS.md корня (канон scaffold: инструкция в AGENTS.md,
# CLAUDE.md — импорт `@AGENTS.md`; один текст для обеих платформ)
ROOT_MODEL_TARGETS = (("AGENTS.md", "## Карта пространства"),)


def model_text() -> str:
    """Стабильная часть карты для корневого файла — единственный источник текста."""
    parts = [MODEL_BLOCK.format(
        built="Дата сборки и покрытие — в динамической части (секция с `map_profile`). ", coverage="")]
    if scout_enabled():
        parts.append(SCOUT_BLOCK)
    parts.append(LABEL_BLOCK)
    return "\n\n".join(parts)


def write_model(base: Path) -> list[str]:
    """Переписать раздел стабильной модели в AGENTS.md корня: от заголовка до
    следующего `## `. Файла или заголовка нет — пропуск (раздел не вставляется молча).
    Операция подготовки шаблона и эталона новой, ещё не выпущенной миграции:
    `space_map.py --base <папка-шаблона> --write-model`. Установленный AGENTS.md
    обновляется миграцией из плагина. С `SVAIB_MAP_SCOUT=0` абзац скаута выпадет."""
    report = []
    for name, heading in ROOT_MODEL_TARGETS:
        fp = base / name
        if not fp.is_file():
            report.append(f"{name}: нет файла — пропущен")
            continue
        lines = fp.read_text(encoding="utf-8").split("\n")
        try:
            start = next(i for i, l in enumerate(lines) if l.rstrip() == heading)
        except StopIteration:
            report.append(f"{name}: нет заголовка «{heading}» — пропущен")
            continue
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        new = lines[:start] + [heading, ""] + model_text().split("\n") + [""] + lines[end:]
        if new == lines:
            report.append(f"{name}: без изменений")
            continue
        tmp = fp.with_name(fp.name + ".tmp")
        tmp.write_text("\n".join(new), encoding="utf-8")
        os.replace(tmp, fp)
        report.append(f"{name}: раздел «{heading}» переписан")
    return report


def scout_enabled() -> bool:
    """Строка о скауте в карте: по умолчанию включена, `SVAIB_MAP_SCOUT=0` выключает."""
    return os.environ.get("SVAIB_MAP_SCOUT", "1") != "0"


# Блок «подкарта по требованию» — в emit-режиме юнитовые CLAUDE.md не пишутся,
# подкарту узла вне зоны агент получает вызовом генератора
ON_DEMAND_BLOCK = """\
**Подкарта узла вне зоны** (файлы с миссиями, подпапки, датированные группы) —
по требованию: `python3 "{tool}" --base "{base}" --emit-node <узел>` (Bash, ~0.1 с,
печатает карту, ничего не пишет). Заходя в узел вне зоны по вопросу о его
устройстве или составе — сначала возьми его подкарту, потом читай файлы."""


def coverage_line(base: Path, units, listed_files: int) -> str:
    """Счётчики покрытия для «Границ карты»: полна на уровне юнитов, неполна на
    уровне файлов — и говорит, насколько."""
    total = md_counts(base).get(base.resolve(), 0)
    return (f" Покрытие: management units {len(units)} — все верхнего уровня; файлов с адресом "
            f"в карте {listed_files} из {total} в дереве — карта полна по management units и "
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
    вместо rglob на каждый юнит и на всё дерево (Drive)."""
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


def dated_dirs(d: Path) -> list:
    return [p for p in subdirs(d) if DATED_RE.match(p.name)]


def dated_summary(files, dirs=()) -> str | None:
    """Датированные файлы и папки — одной строкой: встреча с 4.2 — папка, а не файл."""
    df = [f.name for f in files if DATED_RE.match(f.name)]
    dd = [p.name for p in dirs if DATED_RE.match(p.name)]
    dated = sorted(df + dd)
    if len(dated) < 3:
        return None
    kind = "файлов и папок" if df and dd else ("папок" if dd else "файлов")
    return f"{len(dated)} датированных {kind}, {dated[0][:10]} … {dated[-1][:10]} — свежий выбирай листингом"


KIT_ELEMENTS = [
    ("01_overview", "overview"), ("02_active", "active"), ("03_backlog", "backlog"),
    ("03_metrics", "metrics"), ("04_progress", "progress"), ("05_decisions", "decisions"),
    ("02_team", "team"), ("meetings", "meetings"),
]


NODE_MARKER_FILE = "README.md"        # узел = папка с README.md, не с 01_overview.md (тот же предикат в хуке).
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
    kit_part = f" (kit: {kit}; файлов: {n})" if kit else (f" (файлов: {n})" if n else "")
    return f"- `{rel}/` — {mission or d.name}{kit_part}"


# ---------------------------------------------------------------------------
# Маршруты чтения из README узла. В подкарту идёт
# только кастомная логика узла — то, что из дерева не выводится: цепочки из ≥2 целей,
# цели вне узла, указатели на раздел файла, условия, «читать первым», внешние ссылки.
# Строки уровня канона («Войти → 01_overview», «Что в работе → 02_active») и строки с
# одной целью-файлом без оговорок отбрасываются — их несут стабильный блок и миссии
# файлов в подкарте. Каждая цель проверяется по дереву: битые строки выбрасываются,
# счётчик «проверены M из N» — признак честности. По умолчанию
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
    kept = []
    for raw in body.splitlines():
        line = raw.strip()
        if not (line.startswith(("-", "*")) or re.match(r"^\d+[.)]", line)):
            continue
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
    head = "**Маршруты узла** (из README):"
    return "\n".join([head] + kept[:ROUTES_MAX_LINES]
                     + ([f"- … ещё {len(kept) - ROUTES_MAX_LINES} — в README узла"] if len(kept) > ROUTES_MAX_LINES else []))


def node_map(node: Path, base: Path, deep: bool = False) -> str:
    lines = ["## Карта узла", ""]
    mission = mission_of_dir(node)
    rel = node.resolve().relative_to(base.resolve()).as_posix() if base.resolve() in node.resolve().parents else node.name
    if mission:
        lines.append(f"**{rel}/** — {mission}")
        lines.append("")
    files = md_files(node)
    ds = dated_summary(files, dated_dirs(node))
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
    # под нагрузкой стенда стоил 0,6–1,4 с на вызов)
    counts = _MD_COUNTS.get(base.resolve()) or md_counts(node)
    if (node / ".svaib").is_dir():                     # скрытая, но на неё ведут маршруты корня
        lines.append("- `.svaib/` — служебное агента: правила владельца, находки, учёт скиллов, версия пространства")
    for sd in subdirs(node):
        if ds and DATED_RE.match(sd.name):
            continue                                   # датированная папка — в строке сводки выше
        sfiles = md_files(sd)
        sds = dated_summary(sfiles, dated_dirs(sd))
        m = mission_of_dir(sd)
        n = counts.get(sd.resolve(), 0)
        # служебные — не узлы даже с README/китом, вход туда не даёт хук (NOT_NODES)
        is_node = sd.name not in NODE_EXCLUDED and (sd / NODE_MARKER_FILE).is_file()
        kit = kit_of(sd) if is_node else None          # кит показываем только у узла со своей картой
        kit_part = f"unit, kit: {kit}; " if kit else ("узел; " if is_node else "")
        if sd.name == "zz_archive":
            lines.append(f"- `{sd.name}/` — архив (файлов: {n}), только по явной надобности")
        elif sd.name == "_inbox":
            lines.append(f"- `{sd.name}/` — входящее до разбора (файлов: {n})")
        elif sds:
            tag = f" ({kit_part.rstrip('; ')})" if kit_part else ""   # пометка не терялась у датированных групп
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
    lines = ["## Карта пространства", ""]
    if model:
        lines.append(MODEL_BLOCK.format(built=f"Карта собрана из дерева {date}. ", coverage=coverage))
    else:  # стабильный блок живёт в корневом файле пространства и приходит каждый ход — не дублировать
        lines.append(f"Карта собрана из дерева {date}, глубина — management units и их первый уровень.{coverage}")
    lines.append("")
    where = (" (подробные карты — ниже):" if single
             # emit без модели — доставка хуками (Claude Code): подкарта узла придёт при входе;
             # emit с моделью — сред без хуков (Codex/Cursor): подкарта по требованию (ON_DEMAND_BLOCK)
             else " (подкарты зоны — ниже, остальных — при первом обращении к файлам узла):" if emit and not model
             else " (подкарты зоны — ниже, остальных — по требованию: `--emit-node <узел>`):" if emit
             else " (подробная карта — в `CLAUDE.md` management unit):")
    lines.append("**Management units**" + where)
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
    головным считается `X`, вариант помечается."""
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
# Идентичность от платформы, кэш на машине
#
# «Кто» приходит из MCP `whoami` (subject, tenant, profile_path, about). Ответ
# ловит PostToolUse-хук и отдаёт сюда JSON целиком — без интерполяции в shell.
# Генератор по profile_path читает профиль в пространстве, выводит юниты зоны
# и пишет кэш в state-каталог машины — ВНЕ репозитория и Drive. Кэш ключуется
# email аккаунта Claude + корнем пространства (один аккаунт, две базы),
# хранит tenant для сверки, живёт CACHE_TTL_HOURS. Без email кэша нет: каждая
# сессия персонализируется заново через whoami (Cowork).
# ---------------------------------------------------------------------------

CACHE_TTL_HOURS = 24
CACHE_VERSION = 3   # 3 — запись несёт `onboarding` из whoami; старая версия не читается, агент зовёт whoami заново


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
    d["name"] = clean_name(d.get("name"))   # старая запись имени не несёт — пусто, не отказ
    d["preferences"] = clean_block(d.get("preferences"), PREFERENCES_LIMIT)
    d["onboarding"] = d["onboarding"] if isinstance(d.get("onboarding"), dict) else None
    return d


def write_cache(email: str, base: Path, rec: dict) -> Path | None:
    """0600, атомарно (tmp + replace); без email — не пишется. `ts` записи сохраняется, если
    есть: срок кэша отсчитывается от `whoami`, а не от поправки."""
    p = cache_path(email, base)
    if p is None:
        return None
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    rec = dict(rec, v=CACHE_VERSION, email=email, base=str(base.resolve()))
    rec.setdefault("ts", _now().isoformat(timespec="seconds"))
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
    не возвращается: в контекст едут только юниты."""
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


def clean_name(value) -> str:
    """Имя из whoami уходит в контекст агента: одна строка без разметки, не длиннее 120."""
    if not isinstance(value, str):
        return ""
    return re.sub(r"[`*_\[\]<>|\\]", "", " ".join(value.split()))[:120]


def who_line(subject: str, name: str) -> str:
    """Начало заголовка персональной карты: метка и, если известно, имя пользователя."""
    return f"`map_profile: {subject}` — пользователь **{name}**" if name else f"`map_profile: {subject}` — пользователь"


def keyboard_line(name: str) -> str:
    """Метки профиля агенту мало — он идёт за именем по
    умолчанию из корневых файлов. Прямая инструкция, кто за клавиатурой и как обращаться."""
    if not name:
        return ""
    return (f"\n\n**За клавиатурой — {name}.** Обращайся к пользователю «{name}»; имя по умолчанию "
            "из других инструкций к этому пользователю не относится.")


PREFERENCES_LIMIT = 2000
RULES_FILE = ".svaib/rules.md"
RULES_LIMIT = 6000


def clean_block(value, limit: int) -> str:
    """Многострочный текст владельца или пользователя для контекста агента: без заголовков
    markdown (не ломают разделы карты), без пустых серий, не длиннее limit."""
    if not isinstance(value, str):
        return ""
    lines = [re.sub(r"^\s{0,3}#{1,6}\s+", "", l.rstrip()) for l in value.replace("\r", "").split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + " …"


def preferences_line(prefs: str) -> str:
    """Как работать с человеком — поле `preferences` в MCP.
    Там только отличия от умолчаний; поля нет или пусто — строки нет, действует канон."""
    if not prefs:
        return ""
    return ("\n\n**Как работать с пользователем** — его настройки в svaib; старшинство — `AGENTS.md`, "
            "раздел «Что дополняет эту инструкцию»:\n\n" + prefs)


def space_rules(base: Path) -> str:
    """Правила работы агента в этом пространстве — `.svaib/rules.md`,
    пишет владелец. Подаются после карты; файла нет — раздела нет. Заголовки файла снимаются."""
    fp = base / RULES_FILE
    try:   # битая кодировка или нечитаемый файл — раздела нет, карта не должна пропасть из-за него
        text = fp.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    fm = re.match(r"^---\n.*?\n---\n", text, re.S)
    body = text[fm.end():] if fm else text
    body = re.sub(r"^\s*# [^\n]*\n", "", body.lstrip("\n"), count=1)
    body = clean_block(body, RULES_LIMIT)
    if not body:
        return ""
    return (f"## Требования владельца пространства (`{RULES_FILE}`)\n\nСтаршинство — `AGENTS.md`, раздел "
            "«Что дополняет эту инструкцию».\n\n" + body)


def tool_payload(raw):
    """Ответ MCP-ручки, как его отдаёт PostToolUse: строка JSON, content-блоки или объект
    результата (`structuredContent` старше `content`). `structuredContent` берётся и у отказа:
    `onboarding-conflict` несёт в нём текущий объект. Отказ без него (`isError`) — None."""
    data = json.loads(raw) if isinstance(raw, str) else raw
    if isinstance(data, dict) and "structuredContent" in data:
        return data["structuredContent"]
    if isinstance(data, dict) and data.get("isError"):
        return None
    if isinstance(data, dict) and isinstance(data.get("content"), list):
        data = data["content"]
    if isinstance(data, list):  # content-блоки MCP
        for block in data:
            if isinstance(block, dict) and block.get("type") == "text":
                try:
                    return json.loads(block["text"])
                except (ValueError, KeyError, TypeError):
                    continue
        return None
    return data


def parse_whoami(raw) -> dict:
    """Ответ whoami как его отдаёт PostToolUse (строка JSON) или объект."""
    data = tool_payload(raw)
    if not isinstance(data, dict) or not data.get("subject_id"):
        raise ValueError("в ответе whoami нет subject_id")
    ws = data.get("workspace") or {}
    return {"subject": str(data["subject_id"]), "name": clean_name(data.get("display_name")),
            "preferences": clean_block(data.get("preferences"), PREFERENCES_LIMIT),
            "tenant": str(data.get("tenant_id") or ""),
            "role": str(data.get("role") or ""), "about": str(data.get("about") or ""),
            "profile_path": str(ws.get("profile_path") or ""),
            "onboarding": data["onboarding"] if isinstance(data.get("onboarding"), dict) else None}


def apply_update_me(base: Path, raw) -> bool:
    """После `update_me`: пришедшие в ответе `onboarding` и `preferences` — в кэш этой машины
    (пустые `preferences` очищают), срок кэша не продлевается. Отказ `onboarding-conflict` несёт
    текущий `onboarding` — пишется только он. Ни одного из полей или нет кэша — ничего."""
    try:
        data = tool_payload(raw)
    except ValueError:
        return False
    if not isinstance(data, dict):
        return False
    fields = {}
    if isinstance(data.get("onboarding"), dict):
        fields["onboarding"] = data["onboarding"]
    if "preferences" in data and (data["preferences"] is None or isinstance(data["preferences"], str)):
        fields["preferences"] = clean_block(data["preferences"] or "", PREFERENCES_LIMIT)
    email = account_email()
    rec = read_cache(email, base) if fields else None
    if not rec:
        return False
    rec.pop("fresh", None)
    return write_cache(email, base, dict(rec, **fields)) is not None


# ---------------------------------------------------------------------------
# Онбординг пользователя под строкой «За клавиатурой»: «два и два» — два последних
# пройденных и два следующих этапа. План = каталог этапов плагина × личное человека ×
# отметки (dev/it-onboarding/_plan.md, «Архитектура статусов»); тот же расчёт ведёт скилл
# `space-onboarding`. Каталог — производный от таблиц методологии, его кладёт сборка рядом со
# скиллом (как спецификации `space-scaffold` для inject_file_spec.py); без поставки блока нет.
# ---------------------------------------------------------------------------

STAGES_PATH = (Path(os.path.abspath(__file__)).parent.parent / "skills" / "space-onboarding" / "references"
               / "stages.json")
STATE_NOTES = {"waiting": "жду", "deferred": "отложен", "unverified": "не удалось проверить"}


def load_stages() -> list | None:
    try:
        d = json.loads(STAGES_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return d.get("stages") if isinstance(d, dict) and isinstance(d.get("stages"), list) else None


def onboarding_near(stages: list, ob: dict, role: str) -> tuple[list, list]:
    """«Два и два»: ([(этап, id зачёта)] — два последних пройденных по `at`, [этап] — два следующих).
    Применим: `track=user`, `active`, `audiences` пуст или содержит `audience`, этап базовый или
    выбран в `tools`. Пройден: `done` на своём id, а без своей отметки — на предшественнике из
    `replaces` (зачёт — по самому позднему). Следующие — по `order` из применимых непройденных, не `skip`, с пройденными `requires`.
    Незнакомые id отметок не участвуют."""
    marks = ob.get("marks") if isinstance(ob.get("marks"), dict) else {}
    tools = ob.get("tools") if isinstance(ob.get("tools"), list) else []
    audience = ob.get("audience") if isinstance(ob.get("audience"), str) and ob.get("audience") \
        else ("ceo" if role == "owner" else "employee")
    catalog = {s["id"]: s for s in stages if isinstance(s, dict) and isinstance(s.get("id"), str)}

    def done_by(sid: str):
        own = marks.get(sid)
        if isinstance(own, dict):            # явная отметка важнее наследования
            return (own, sid) if own.get("state") == "done" else None
        best = None                          # из пройденных предшественников — самый поздний по `at`
        for r in (catalog.get(sid) or {}).get("replaces") or []:
            m = marks.get(r)
            if isinstance(m, dict) and m.get("state") == "done" \
                    and (best is None or str(m.get("at") or "") > str(best[0].get("at") or "")):
                best = (m, r)
        return best

    def applicable(s: dict) -> bool:
        aud = s.get("audiences") or []
        return (s.get("track") == "user" and s.get("active") is True and (not aud or audience in aud)
                and (s.get("kind") == "base" or s["id"] in tools))

    mine = sorted((s for s in catalog.values() if applicable(s)),
                  key=lambda s: s["order"] if isinstance(s.get("order"), int) else 10 ** 9)
    done, nxt = [], []
    for s in mine:
        hit = done_by(s["id"])
        if hit:
            done.append((str(hit[0].get("at") or ""), s, hit[1]))
        elif not (isinstance(marks.get(s["id"]), dict) and marks[s["id"]].get("state") == "skip") \
                and all(done_by(r) for r in s.get("requires") or []):
            nxt.append(s)
    done.sort(key=lambda d: d[0])
    return [(s, src) for _, s, src in done[-2:]], nxt[:2]


def onboarding_block(rec: dict) -> str:
    """Блок онбординга под строкой «За клавиатурой». Нет `onboarding` в кэше, каталога или этапов
    к показу, любой сбой — пусто: карта приходит и без блока."""
    try:
        ob = rec.get("onboarding")
        stages = load_stages() if isinstance(ob, dict) else None
        if not stages:
            return ""
        done, nxt = onboarding_near(stages, ob, rec.get("role", ""))
        if not done and not nxt:
            return ""
        marks = ob.get("marks") if isinstance(ob.get("marks"), dict) else {}

        def title(s: dict) -> str:
            return f"«{clean_name(s.get('title')) or s['id']}»"

        def todo(s: dict) -> str:
            m = marks.get(s["id"]) if isinstance(marks.get(s["id"]), dict) else {}
            note = STATE_NOTES.get(m.get("state"), "")
            if note and m.get("state") == "waiting" and clean_name(m.get("actor")):
                note += ": " + clean_name(m.get("actor"))
            return title(s) + (f" ({note})" if note else "")

        lines = ["\n\n**Онбординг пользователя:**"]
        if done:
            lines.append("- пройдено: " + ", ".join(
                title(s) + (f" (зачтён по `{src}`)" if src != s["id"] else "") for s, src in done))
        if nxt:
            lines.append("- дальше: " + "; ".join(todo(s) for s in nxt))
        lines.append("- весь путь — скилл `space-onboarding`")
        return "\n".join(lines)
    except Exception:  # noqa: BLE001 — блок онбординга не имеет права уронить карту
        return ""


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
    rec = {"subject": who["subject"], "name": who.get("name", ""), "preferences": who.get("preferences", ""),
           "tenant": who.get("tenant", ""), "role": who.get("role", ""),
           "profile_path": who.get("profile_path", ""), "units": units, "onboarding": who.get("onboarding")}
    email = account_email()
    cp = write_cache(email, base, rec)
    remembered = (f"запомнен на этой машине на {CACHE_TTL_HOURS} ч" if cp
                  else "аккаунт Claude на машине не определён — кэша нет, в следующей сессии снова `whoami`")
    lines = [f"{who_line(who['subject'], who.get('name', ''))}, профиль "
             f"`{who.get('profile_path') or '—'}` — персональная подкарта зоны; {remembered}."
             f"{keyboard_line(who.get('name', ''))}{onboarding_block(rec)}"
             f"{preferences_line(who.get('preferences', ''))}"]
    if units:
        lines.append(f"\n**Management units зоны** ({source}): " + " · ".join(f"`{u}/`" for u in units))
        for u in units:
            lines.append("\n" + node_map(base / u, base))
    else:
        lines.append("\nManagement units зоны не выведены ни из профиля, ни из `about`. Персональной подкарты нет: "
                     "работай по общей карте — подкарта узла приходит при первом обращении к его файлам "
                     f"(папки верхнего уровня: {', '.join(units_all)}). Точный источник зоны — поле "
                     "`units:` в шапке профиля.")
    return "\n".join(lines), rec


def emit_text(base: Path, focus: list[str] | None = None, no_model: bool = False,
              no_skills: bool = False) -> str:
    """Карта как текст, репозиторий не трогается. Корень (+ подкарты зоны) (+ реестр
    скиллов). Рецепт «подкарта по требованию» — только вместе со стабильным блоком:
    при --no-model он уже в корневом AGENTS.md."""
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
    if routes_enabled():   # README корня — вместе с корневой картой
        rr = node_routes(base, base)
        if rr:
            parts.append(rr.replace("**Маршруты узла** (из README", "**Маршруты пространства** (из README корня", 1))
    if not no_model:
        tool = Path(__file__).resolve()
        tool_s = tool.relative_to(base).as_posix() if base in tool.parents else tool.as_posix()
        parts.append(ON_DEMAND_BLOCK.format(tool=tool_s, base=base.as_posix()))
        if scout_enabled():   # тот же флаг, что у --print-model — единый источник
            parts.append(SCOUT_BLOCK)
    if zone_maps:
        zone = " · ".join(f"`{f}/`" for f in focus if f in names)
        parts.append(f"**Зона ответственности пользователя** — {zone}. Подробные карты этих "
                     "management units — ниже; по вопросу из зоны адрес бери отсюда.")
        parts.extend(zone_maps)
    if missing:
        parts.append("Management units зоны, которых нет в дереве (подкарты не собраны): "
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
                    help="напечатать карту в stdout — корень (+ подкарты --focus, реестр "
                         "скиллов); в файлы ничего не пишется, --out не нужен")
    ap.add_argument("--emit-node", default="",
                    help="напечатать подкарту одного узла (путь от корня) и выйти")
    ap.add_argument("--no-skills", action="store_true",
                    help="--emit без реестра скиллов (Claude Code и так показывает скиллы в "
                         "системном промпте; для Codex/Cursor реестр оставлять)")
    ap.add_argument("--no-model", action="store_true",
                    help="--emit без стабильного блока (модель пространства, как ходить): он "
                         "живёт в корневом AGENTS.md и приходит каждый ход")
    ap.add_argument("--cache-json", action="store_true",
                    help="напечатать кэш пользователя этой машины для --base (JSON, {} если нет)")
    ap.add_argument("--print-model", action="store_true",
                    help="напечатать стабильный блок корневого файла (единый источник текста)")
    ap.add_argument("--write-model", action="store_true",
                    help="подготовить раздел карты в AGENTS.md шаблона или новой миграции (--base)")
    ap.add_argument("--personalize", action="store_true",
                    help="после whoami — подкарты зоны по профилю + кэш пользователя на машине")
    ap.add_argument("--whoami-file", default="",
                    help="--personalize: файл с ответом whoami (JSON); `-` — stdin. Не через shell-аргументы")
    ap.add_argument("--subject", default="", help="--personalize без файла: subject_id из whoami")
    ap.add_argument("--profile", default="", help="--personalize без файла: profile_path из whoami")
    ap.add_argument("--units", default="", help="--personalize: юниты зоны через запятую (переопределяет)")


def run_prod(args) -> bool:
    """Выполнить прод-режим, если он запрошен. True — обработано."""
    src = Path(args.base).expanduser()
    focus = [f.strip().rstrip("/") for f in getattr(args, "focus", "").split(",") if f.strip()]
    # --- прод-режимы: ничего не пишут в пространство ---
    try:
        if args.cache_json:
            print(json.dumps(read_cache(account_email(), src) or {}, ensure_ascii=False))
            return True
        if args.print_model:
            # Без HTML-комментария-маркера: наличие блока в CLAUDE.md/AGENTS.md
            # хук узнаёт по заголовку раздела — «## Карта пространства» / «## Space Map» — а не по метке в тексте.
            print(model_text())
            return True
        if args.write_model:
            print("\n".join(write_model(src.resolve())))
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
        ap.error("укажи режим: --emit, --emit-node, --personalize, --print-model, --write-model или --cache-json")


if __name__ == "__main__":
    main()
