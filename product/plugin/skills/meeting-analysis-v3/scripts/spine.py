#!/usr/bin/env python3
"""Safety-ядро meeting-analysis v3 — нативная пересборка (пакет 4).

Пять обязанностей ядра (спека 2026-08-09):
1. конвейер фаз с двумя паузами и двумя замками: применение — только после
   решений по всем пунктам, сводка — только после статуса записи по каждому;
2. сырьё карты базы и ограничение контекста узлов — карту домов строит LLM;
3. O(1)-проверки: формы артефактов, цитаты (ярус 1), улики вердиктов,
   полнота вердиктов, детектор межъюнитных пересечений;
4. журнал: отсевы с уликами, принятый набор целиком, статусы записи;
5. границы сводки участникам.

Записью в базу ядро не занимается: применяет LLM-узел по фактическому
состоянию файла (решение Эрика 09.08). Хранение и синхронизация базы — зона
ответственности клиента; откат — версионная история его платформы.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validators as V  # noqa: E402

FAULT = "MA_FAULT"

#: Абсолютный путь отработавшего ядра: координатор зовёт его этой строкой, а след
#: прогона фиксирует, какая копия скилла работала. Факт о себе за O(1), без обхода
#: диска: рабочая директория между вызовами не сохраняется, поэтому путь к ядру
#: подбирать нечем — его называет само ядро.
SPINE_PATH = str(Path(__file__).resolve())

#: Каталог установленного скилла: `scripts/` лежит внутри него. Тот же приём,
#: что у SPINE_PATH, — факт о себе за O(1), без обхода диска.
SKILL_ROOT = Path(__file__).resolve().parent.parent

#: Версия этой сборки. `dev` — запуск из дерева разработки: версия не
#: проштампована, рукопожатие молчит. Строка обязана начинаться с начала строки
#: и выглядеть ровно так: по ней бьёт sed сборщика (`build-plugin.sh`, 7.8),
#: и это единственная точка штампа — имя файла в правило штампа не входит.
SKILL_VERSION = "dev"

#: Маркер версии, который сборщик кладёт в базу рядом с установкой скилла:
#: `<base>/.claude/skills/<имя установки>/.skill-version.json`. Имя установки
#: константой нигде не зашито — его называет собственный frontmatter.
SKILL_MARKER_NAME = ".skill-version.json"


class SpineError(Exception):
    def __init__(self, code: str, message: str, *, field: str = "", hint: str = "",
                 issues: Optional[List[Dict[str, Any]]] = None,
                 data: Optional[Dict[str, Any]] = None,
                 error_class: Optional[str] = None, next_command: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.hint = hint
        self.issues = issues or []
        self.data = data or {}
        self.error_class = error_class or V.error_class(code)
        self.next_command = next_command or V.transition(code)


class InjectedFault(Exception):
    """Тестовый шов: детерминированный обрыв в заданной точке."""


def maybe_fault(tag: str) -> None:
    if os.environ.get(FAULT) == tag:
        raise InjectedFault(tag)


# --- файловая мелочь ----------------------------------------------------


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def read_text(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as stream:
        return stream.read()


def atomic_write(path: Path, text: str) -> None:
    handle, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-ma-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


#: Путь лежит в дереве root; сам корень считается своим. Единственный владелец
#: правила «внутри дерева» — оно нужно и границе базы, и границе прогона.
def under(root: Path, path: Path) -> bool:
    return path == root or root in path.parents


def state_root() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))


def runs_root() -> Path:
    return state_root() / "svaib" / "ma" / "runs"


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# --- прогон -------------------------------------------------------------

#: Состояния конвейера. Порядок держит код (урок 27.07: порядок текстом не
#: держится); замков ровно два — на материале применения и на материале сводки.
STATES = ("ready", "mapped", "briefed", "confirmed", "review",
          "decided", "writing", "applied", "done")


class Run:
    """Артефакты текущего прогона. Персистентности поперёк сессий нет."""

    def __init__(self, run_dir: Path):
        self.dir = run_dir
        self.manifest_path = run_dir / "run.json"
        if not self.manifest_path.is_file():
            raise SpineError("run_not_initialized", "прогон не начат — сначала `check`")
        self.manifest: Dict[str, Any] = read_json(self.manifest_path)
        self.base = Path(self.manifest["base_realpath"])
        self.artifacts = run_dir / "artifacts"

    @property
    def state(self) -> str:
        return self.manifest.get("state", "ready")

    @property
    def step(self) -> str:
        return self.manifest.get("step", "")

    def set_state(self, state: str, step: str = "") -> None:
        self.manifest["state"] = state
        self.manifest["step"] = step
        write_json(self.manifest_path, self.manifest)

    def base_dir(self) -> Path:
        return state_root() / "svaib" / "ma" / "bases" / self.manifest["base_id"]

    def journal_path(self) -> Path:
        return self.base_dir() / "journal.jsonl"

    def event(self, event: str, **fields: Any) -> None:
        payload = {"entry_id": new_id("ev"), "event": event,
                   "run_id": self.manifest["run_id"], "phase": self.state}
        payload.update({k: v for k, v in fields.items() if v is not None})
        append_jsonl(self.dir / "events.jsonl", payload)

    def journal(self, event: str, **fields: Any) -> None:
        payload = {"entry_id": new_id("jr"), "event": event,
                   "run_id": self.manifest["run_id"],
                   "base_id": self.manifest["base_id"],
                   "meeting_date": self.manifest["meeting_date"]}
        payload.update({k: v for k, v in fields.items() if v is not None})
        append_jsonl(self.journal_path(), payload)

    def events(self) -> List[Dict[str, Any]]:
        return read_jsonl(self.dir / "events.jsonl")

    # --- база -----------------------------------------------------------

    def base_file(self, rel: str) -> Path:
        path = self.base / rel
        resolved = path.resolve()
        root = self.base.resolve()
        if not under(root, resolved):
            raise SpineError("path_escapes_base", f"путь {rel} выходит за пределы базы",
                             field="target.file")
        return path

    def read_base(self, rel: str) -> Optional[str]:
        try:
            path = self.base_file(rel)
        except SpineError:
            return None
        if not path.is_file():
            return None
        return read_text(path)

    def transcript_text(self) -> str:
        path = Path(self.manifest["transcript"]["path"])
        if not path.is_file():
            raise SpineError("missing_input", "транскрипт исчез", field="--transcript")
        body = path.read_text(encoding="utf-8")
        if sha256_bytes(body.encode("utf-8")) != self.manifest["transcript"]["sha256"]:
            raise SpineError("transcript_changed", "транскрипт изменился после старта прогона",
                             field="--transcript")
        return body

    # --- артефакты ------------------------------------------------------

    def artifact(self, name: str) -> Path:
        return self.artifacts / name

    def load(self, name: str) -> Optional[Any]:
        path = self.artifact(name)
        return read_json(path) if path.is_file() else None

    def store(self, name: str, payload: Any) -> None:
        write_json(self.artifact(name), payload)

    @staticmethod
    def unit_key(unit: str) -> str:
        return unit.replace("/", "__")

    def units(self) -> List[str]:
        payload = self.load("map.json") or {}
        return [row.get("unit") for row in payload.get("units", []) if row.get("unit")]

    def roster(self) -> List[Dict[str, Any]]:
        payload = self.load("brief.json") or {}
        roster = list(payload.get("roster", []))
        overrides = self.load("roster-overrides.json") or {}
        merged = []
        for item in roster:
            eid = str(item.get("eid", ""))
            if eid in overrides:
                merged.append({**item, **overrides[eid]})
            else:
                merged.append(item)
        return merged

    def withdrawn(self) -> Dict[str, str]:
        payload = self.load("withdrawn.json") or {}
        return {str(k): str(v) for k, v in payload.items()}

    def assignment(self) -> Dict[str, str]:
        payload = self.load("assignment.json") or {}
        return {row["eid"]: row["unit"] for row in payload.get("assignment", [])}

    def operations(self, unit: str) -> Optional[Dict[str, Any]]:
        path = self.artifacts / "operations" / f"{self.unit_key(unit)}.json"
        return read_json(path) if path.is_file() else None

    def verdicts(self, unit: str) -> Optional[Dict[str, Any]]:
        path = self.artifacts / "verdicts" / f"{self.unit_key(unit)}.json"
        return read_json(path) if path.is_file() else None

    def units_with_operations(self) -> List[str]:
        directory = self.artifacts / "operations"
        if not directory.is_dir():
            return []
        return sorted(path.stem.replace("__", "/") for path in directory.glob("*.json"))

    def relocations(self) -> List[Dict[str, Any]]:
        return (self.load("relocations.json") or {}).get("relocations", [])

    def quote_verdicts(self) -> Dict[Tuple[str, str], str]:
        payload = self.load("quote-verdicts.json") or {}
        return {(row["eid"], row["quote"]): row["verdict"]
                for row in payload.get("quotes", [])}

    def quote_flags(self) -> List[Dict[str, Any]]:
        return (self.load("quote-flags.json") or {}).get("flags", [])


def resolve_run_dir(args: argparse.Namespace) -> Path:
    """Рабочий каталог прогона: названный именем либо последний по времени.

    Названный каталог привязан к корню прогонов конструкцией: он обязан быть
    ПРЯМЫМ РЕБЁНКОМ `runs_root()`. Склейка `runs_root() / run_id` этого не
    держит — абсолютное имя отбрасывает корень целиком (`Path("/a/b") / "/x"`
    даёт `/x`), а `..` из корня выходит. Дальше `Run` требует только наличия
    `run.json`, и подложенный каталог внутри базы пользователя становится
    рабочим: служебные файлы туда пишет само ядро (`Run.store`, `Run.event`).
    Guard `--file` и `workspace_in_base` этот вход не закрывают — они стерегут
    штатно созданный workspace, а не имя, которым его подменили.

    Привязка к корню сильнее и дешевле проверки «не внутри базы»: базу ядро в
    этой точке ещё не знает (её называет манифест, который лежит в самом
    каталоге), а корень прогонов известен всегда. Одно сравнение, без обхода
    диска, закрывает разом абсолютное имя, `..` и любой соседний каталог.

    Дверей две — `--run-id` и `MA_RUN`, — но точка входа одна, поэтому и
    проверка одна: разъехаться двум спискам правил здесь нечему.
    """
    named = getattr(args, "run_id", None)
    run_id = named or os.environ.get("MA_RUN")
    if run_id:
        root = runs_root().resolve()
        chosen = (runs_root() / run_id).resolve()
        if chosen.parent != root:
            raise SpineError("run_id_invalid",
                             f"каталог прогона {chosen} лежит не в корне прогонов",
                             field="--run-id" if named else "MA_RUN",
                             hint=f"прогон называется именем каталога внутри {root}; "
                                  "абсолютный путь и `..` увели бы рабочий каталог "
                                  "ядра за пределы корня прогонов",
                             data={"runs_root": str(root)})
        return chosen
    root = runs_root()
    candidates = sorted((p for p in root.glob("run-*") if (p / "run.json").is_file()),
                        key=lambda p: (p / "run.json").stat().st_mtime) if root.is_dir() else []
    if not candidates:
        raise SpineError("run_not_initialized", "прогон не начат — сначала `check`")
    return candidates[-1]


# --- сырьё карты базы ---------------------------------------------------

README_SECTIONS = ("Маршруты записи", "Содержимое папки", "Правила работы")
#: Служебные деревья: холодный архив, входящее, приватное, шаблоны каркаса и
#: техническая обвязка. Единственный владелец правила «это не база».
SKIP_DIRS = {"node_modules", "__pycache__", "zz_archive", "_private", "clients-scaffold",
             "venv", "site-packages", "dist", "build", "_inbox", "_templates"}
#: `template`/`templates` — обычное слово клиентского пространства; служебным
#: оно становится только на канонической позиции внутри `scaffold/`.
TEMPLATE_NAMES = {"template", "templates"}
#: Пять канонических kit-имён в обеих формах — файл и развернувшаяся папка.
#: Ядро классов не выводит: панель читается как факт сырья, решает LLM-узел.
KIT_NAME = re.compile(r"^\d{2}_(?:overview|active|backlog|progress|decisions)(?:\.md)?$")


def service_parts(parts: Sequence[str]) -> bool:
    for index, part in enumerate(parts):
        low = part.lower()
        if low in SKIP_DIRS or part.startswith("."):
            return True
        if low in TEMPLATE_NAMES and any(p.lower() == "scaffold" for p in parts[:index]):
            return True
    return False


def readme_sections(text: str, wanted: Sequence[str] = README_SECTIONS) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for line in text.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            title = heading.group(2).lstrip("🔵🔹🔧✅⚡❗️ ")
            current = title if (len(heading.group(1)) in (2, 3)
                                and any(title.startswith(name) for name in wanted)) else None
            if current:
                sections[current] = []
            continue
        if current and line.strip():
            sections[current].append(line.rstrip())
    return sections


def readme_headings(text: str) -> List[str]:
    return [match.group(2).strip() for match in
            re.finditer(r"^(#{1,3})\s+(.+?)\s*$", text, re.M)]


def open_active_items(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines()
            if re.match(r"^\s*[-*+]\s+\[ \]\s+", line)]


def kit_panel(directory: Path) -> List[str]:
    try:
        entries = sorted(directory.iterdir(), key=lambda item: item.name)
    except OSError:
        return []
    return [entry.name for entry in entries
            if KIT_NAME.match(entry.name.lower()) and not entry.is_symlink()]


def read_readme(directory: Path) -> Optional[str]:
    try:
        readme = directory / "README.md"
        if not readme.is_file() or readme.is_symlink():
            return None
        return read_text(readme)
    except (OSError, UnicodeDecodeError):
        return ""


def build_base_raw(base: Path) -> Dict[str, Any]:
    """Сырьё карты: факты диска без классификации «кто дом».

    Код собирает и режет, LLM-узел решает (§4.1 спеки): по каждому каталогу —
    дети, md-файлы, панель, канонические секции README и заголовки остальных.
    Полный текст едет только у корневого README: карта строится от него вниз,
    и это единственный текст, который узлу нужен целиком.
    """
    directories: List[Dict[str, Any]] = []
    for root, dirs, files in os.walk(base, followlinks=False):
        rel_parts = Path(root).parts[len(base.parts):]
        dirs[:] = sorted(name for name in dirs
                         if not service_parts(rel_parts + (name,)))
        rel = "/".join(rel_parts)
        md_files = sorted(name for name in files if name.lower().endswith(".md"))
        if not md_files and not dirs:
            continue
        readme = read_readme(Path(root))
        row: Dict[str, Any] = {
            "path": rel or ".",
            "dirs": list(dirs),
            "md_files": md_files,
            "panel": kit_panel(Path(root)),
        }
        if readme is None:
            row["readme"] = "missing"
        elif readme == "":
            row["readme"] = "unreadable"
        else:
            row["readme"] = "present"
            row["readme_sections"] = readme_sections(readme)
            row["readme_headings"] = readme_headings(readme)
        directories.append(row)
    root_readme = read_readme(base)
    return {
        "schema": "base-raw/1",
        "root_readme": root_readme or "",
        "directories": directories,
    }


def unit_exists(run: Run, unit: str) -> bool:
    """Форма выбора карты: названное место существует в базе и не служебное."""
    if not unit or unit.startswith("/") or ".." in unit.split("/"):
        return False
    if service_parts(tuple(unit.split("/"))):
        return False
    try:
        path = run.base_file(unit)
    except SpineError:
        return False
    return path.is_dir() or (path.is_file() and unit.lower().endswith(".md"))


def base_dir_exists(run: Run, rel: str) -> bool:
    """Названный каталог базы существует и не служебный — факт за O(1).

    Тот же вопрос, что у `unit_exists`, но без md-файла: домом протокола бывает
    только каталог. Разводить их нельзя было бы, если бы совпадал предмет; здесь
    предметы разные, а правило «это не база» у обоих одно — `service_parts`.
    """
    if not rel or rel.startswith("/") or ".." in rel.split("/"):
        return False
    if service_parts(tuple(rel.split("/"))):
        return False
    try:
        return run.base_file(rel).is_dir()
    except SpineError:
        return False


def unit_files(run: Run, unit: str) -> List[str]:
    """Файлы юнита: дерево каталога без поддеревьев дочерних юнитов карты."""
    units = set(run.units())
    path = run.base_file(unit)
    if path.is_file():
        return [unit]
    out: List[str] = []
    for root, dirs, files in os.walk(path, followlinks=False):
        rel_parts = Path(root).parts[len(run.base.parts):]
        rel = "/".join(rel_parts)
        dirs[:] = sorted(name for name in dirs
                         if not service_parts(rel_parts + (name,))
                         and (f"{rel}/{name}" if rel else name) not in units)
        for name in sorted(files):
            if name.lower().endswith(".md"):
                out.append(f"{rel}/{name}" if rel else name)
    return out


def unit_of_file(rel: str, units: Sequence[str]) -> Optional[str]:
    best = None
    for unit in units:
        if rel == unit or rel.startswith(unit.rstrip("/") + "/"):
            if best is None or len(unit) > len(best):
                best = unit
    return best


# --- версия установки ---------------------------------------------------


def installed_skill_name() -> Optional[str]:
    """Имя, под которым установлен этот скилл, — из собственного frontmatter.

    Каталог распаковки архива выбирает хост, и нам он не подконтролен; `name:`
    едет внутри архива и приведён сборщиком к имени каталога установки — значит
    источник имени один, собственный SKILL.md рядом с `scripts/`. Ничего, кроме
    имени, отсюда не следует: не прочиталось — считаем, что имени нет.
    """
    try:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    except (OSError, ValueError):
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^name:\s*(\S+)\s*$", line)
        if not match:
            continue
        name = match.group(1).strip("'\"")
        if not name or "/" in name or name.startswith("."):
            return None
        return name
    return None


def skill_update(base: Path) -> Optional[Dict[str, str]]:
    """Рекомендация обновить установку: в базе лежит сборка другой версии.

    ❗️Отказа по версии в v3 нет. Поле `fail_closed` маркера читается как факт
    и намеренно игнорируется: устаревшая установка разбор не блокирует, старт
    идёт на той версии, которая стоит (решение 11 плана preview). Ни одной
    ветки `raise` — рукопожатие либо возвращает факт с готовой фразой, либо
    молчит. Пометить релиз «несовместимым» этим механизмом нельзя.

    Молчит: сборка из дерева разработки (`dev` — версия не проштампована),
    имя установки не читается, маркера нет, маркер битый, версия совпадает.
    Сравнение — на неравенство: версия это контент-hash состава, порядка у
    него нет, «новее» ядро не знает и не выдумывает.
    """
    if SKILL_VERSION == "dev":
        return None
    name = installed_skill_name()
    if not name:
        return None
    marker_path = base / ".claude" / "skills" / name / SKILL_MARKER_NAME
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(marker, dict):
        return None
    version = marker.get("version")
    if not isinstance(version, str) or not version or version == SKILL_VERSION:
        return None
    artifact = marker.get("artifact")
    if not isinstance(artifact, str) or not artifact:
        artifact = f".claude/skill-archives/{name}.skill"
    return {"installed": SKILL_VERSION, "available": version, "artifact": artifact,
            "say": f"В базе лежит новая версия навыка разбора встреч — установите файл "
                   f"{artifact} (Settings → Skills) и начните новую сессию. Обновление "
                   f"рекомендательное: текущий разбор идёт на установленной версии."}


# --- check --------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> Dict[str, Any]:
    base = Path(args.base).expanduser()
    if not base.is_dir():
        raise SpineError("missing_input", f"базы нет по пути {args.base}", field="--base")
    base = base.resolve()
    transcript = Path(args.transcript).expanduser()
    if not transcript.is_file():
        raise SpineError("missing_input", f"транскрипта нет по пути {args.transcript}",
                         field="--transcript")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.meeting_date or ""):
        raise SpineError("missing_input", "дата встречи задаётся как YYYY-MM-DD",
                         field="--meeting-date")
    body = transcript.read_text(encoding="utf-8")
    run_id = new_id("run")
    workspace = runs_root() / run_id
    if under(base, workspace.resolve()):
        raise SpineError("workspace_in_base",
                         "рабочий каталог прогона попал бы внутрь базы",
                         field="XDG_STATE_HOME",
                         hint=f"каталог прогонов {runs_root()} лежит в базе {base}; "
                              "задай XDG_STATE_HOME вне базы")
    raw = build_base_raw(base)
    write_json(workspace / "run.json", {
        "run_id": run_id,
        "schema": V.SCHEMA_VERSION,
        "spine": SPINE_PATH,
        "state": "ready",
        "step": "",
        "base_realpath": str(base),
        "base_id": sha256_bytes(str(base).encode("utf-8"))[:12],
        "meeting_date": args.meeting_date,
        "transcript": {"path": str(transcript.resolve()),
                       "sha256": sha256_bytes(body.encode("utf-8"))},
    })
    write_json(workspace / "artifacts" / "base-raw.json", raw)
    inbox = workspace / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    data: Dict[str, Any] = {"directories": len(raw["directories"]),
                            "spine": SPINE_PATH,
                            "run_dir": str(workspace),
                            "inbox": str(inbox),
                            "base_raw": str(workspace / "artifacts" / "base-raw.json")}
    # Старта, кроме check, у v3 нет — сравнение версий садится сюда, последним
    # шагом: прогон к этому моменту уже создан, рекомендация его не держит.
    update = skill_update(base)
    if update:
        data["skill_update"] = update
    return {"state": "ready", "step": "", "run_id": run_id,
            "next": "узел map строит карту домов по artifacts/base-raw.json → "
                    f"ответ узла сохрани в {inbox}/map.json → submit map",
            "data": data}


# --- submit -------------------------------------------------------------


def require_state(run: Run, allowed: Sequence[str]) -> None:
    """Ярлык поданной команды сюда не приходит — и назван быть не может.

    Иначе на позднем шаге подсказка звала бы повторить только что отбитое:
    координатор чинит прогон по `hint` и уходил бы на второй круг того же
    отказа. Шаг называет конвейер: `next_action` знает, что идёт следом за
    текущим состоянием, — и это же едет в `next`.
    """
    if run.state not in allowed:
        step = next_action(run)
        raise SpineError("phase_order",
                         f"шаг подан не в свою очередь (состояние {run.state})",
                         hint=f"дальше: {step}", next_command=step)


def raise_violations(run: Run, violations: List[V.Violation], phase: str) -> None:
    if not violations:
        return
    codes = {item.code for item in violations}
    prior = {(event.get("code"), event.get("eid")) for event in run.events()
             if event.get("event") == "refused" and event.get("code") in codes}
    for item in violations:
        run.event("refused", code=item.code, eid=item.eid or None, field=item.field or None)
    escalate = any((item.code, item.eid or None) in prior for item in violations)
    if escalate:
        run.event("question", code=sorted(codes)[0], eid=violations[0].eid or None,
                  message="узел не исправил замечание со второй попытки — решает человек")
    first = violations[0]
    raise SpineError(first.code, first.message, field=first.field, hint=first.hint,
                     issues=[item.as_dict() for item in violations],
                     error_class="question" if escalate else None,
                     data={"phase": phase})


def store_quote_flags(run: Run, new_flags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not new_flags:
        return []
    payload = run.load("quote-flags.json") or {"flags": []}
    known = {(row.get("eid"), row.get("quote")) for row in payload["flags"]}
    added = [row for row in new_flags if (row.get("eid"), row.get("quote")) not in known]
    payload["flags"].extend(added)
    run.store("quote-flags.json", payload)
    return added


def pending_quote_flags(run: Run) -> List[Dict[str, Any]]:
    verdicts = run.quote_verdicts()
    return [row for row in run.quote_flags()
            if (row.get("eid"), row.get("quote")) not in verdicts]


def submit_map(run: Run, payload: Any) -> Dict[str, Any]:
    require_state(run, ("ready", "mapped"))
    raise_violations(run, V.validate_map(payload), "map")
    missing = [row["unit"] for row in payload.get("units", [])
               if not unit_exists(run, row.get("unit", ""))]
    if missing:
        raise_violations(run, [V.Violation(
            "unknown_unit", f"места {', '.join(missing)} в базе нет либо оно служебное",
            field="map.units",
            hint="юнит — существующий каталог или md-файл базы; нет подходящего — "
                 "опиши предмет в findings, вопрос доедет до паузы 1")], "map")
    run.store("map.json", payload)
    for finding in payload.get("findings", []) or []:
        run.event("map_finding", message=str(finding))
    run.set_state("mapped")
    return {"state": run.state, "step": run.step, "next": "submit brief",
            "data": {"units": run.units()}}


def submit_brief(run: Run, payload: Any) -> Dict[str, Any]:
    require_state(run, ("mapped", "briefed"))
    transcript = run.transcript_text()
    violations, flags = V.validate_brief(payload, transcript)
    raise_violations(run, violations, "brief")
    run.store("brief.json", payload)
    added = store_quote_flags(run, flags)
    questions = rebuild_assignment(run)
    run.set_state("briefed")
    pending = pending_quote_flags(run)
    return {"state": run.state, "step": run.step,
            "next": ("узел quote-judge судит спорные цитаты → submit quotes"
                     if pending else "render summary → decide --screen summary"),
            "data": {"assignment": len(run.assignment()), "questions": questions,
                     "quote_flags": added}}


def rebuild_assignment(run: Run) -> List[Dict[str, Any]]:
    """Артефакт eid → юнит: hint выжимки приводится к дому карты.

    Правка пользователя (поле `unit` поверх ростера) сильнее hint выжимки.
    Узел называет раздел (`dev/gateway`) чаще, чем юнит; нормализация видна в
    `source`. Место, которого в карте нет, и сущность без места — вопрос
    пользователю, а не молчаливый дефолт.
    """
    units = run.units()
    questions: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    default = units[0] if units else ""
    for item in run.roster():
        eid = str(item.get("eid", ""))
        edited = str(item.get("unit") or "")
        hint = edited or str(item.get("unit_hint") or "")
        unit = hint if hint in units else unit_of_file(hint, units) if hint else None
        source = ("edit" if edited else
                  "hint" if unit == hint else ("normalized" if unit else "default"))
        if unit is None:
            unit = default
            message = (f"выжимка называет место {hint!r}, которого нет "
                       f"в карте — сущность назначена {unit!r}" if hint else
                       f"выжимка не назвала место — сущность назначена {unit!r}, "
                       f"поправь юнит, если дом другой")
            questions.append({"kind": "unknown_place", "eid": eid, "message": message})
        rows.append({"eid": eid, "unit": unit, "source": source, "hint": hint or None})
    run.store("assignment.json", {"assignment": rows, "questions": questions})
    return questions


def submit_quotes(run: Run, payload: Any) -> Dict[str, Any]:
    require_state(run, ("briefed", "review", "confirmed"))
    raise_violations(run, V.validate_quotes(payload), "quotes")
    pending = {(row["eid"], row["quote"]) for row in pending_quote_flags(run)}
    unknown = [row for row in payload.get("quotes", [])
               if (row["eid"], row["quote"]) not in pending]
    if unknown:
        # судья отвечает ровно по спорным фразам, как они пришли во флаге: ответ
        # по искажённой строке оставил бы флаг висеть pending бесконечно
        raise SpineError("bad_usage",
                         "вердикт по фразе, которой нет среди спорных: "
                         + "; ".join(f"{row['eid']}: {row['quote'][:40]}"
                                     for row in unknown[:3]),
                         field="quotes", data={"pending": sorted(pending)})
    stored = run.load("quote-verdicts.json") or {"quotes": []}
    known = {(row["eid"], row["quote"]) for row in stored["quotes"]}
    softened: List[str] = []
    for row in payload.get("quotes", []):
        key = (row["eid"], row["quote"])
        if key in known:
            continue
        stored["quotes"].append({"eid": row["eid"], "quote": row["quote"],
                                 "verdict": row["verdict"], "note": row.get("note")})
        if row["verdict"] == "fabricated":
            run.event("quote_fabricated", eid=row["eid"], message=row.get("note"))
        if row["verdict"] == "paraphrase":
            # парафраз не выдаётся за дословность: кавычки вокруг фразы снимает
            # код — это микроправка текста записи, не перезапуск узла
            softened.extend(soften_paraphrase(run, row["eid"], row["quote"]))
    run.store("quote-verdicts.json", stored)
    pending = pending_quote_flags(run)
    return {"state": run.state, "step": run.step,
            "next": ("узел quote-judge судит оставшиеся цитаты → submit quotes"
                     if pending else next_action(run)),
            "data": {"pending": pending, "softened": softened}}


def soften_paraphrase(run: Run, eid: str, quote: str) -> List[str]:
    touched: List[str] = []
    directory = run.artifacts / "operations"
    if not directory.is_dir():
        return touched
    for path in sorted(directory.glob("*.json")):
        package = read_json(path)
        changed = False
        for op in package.get("operations", []):
            if str(op.get("eid")) != eid:
                continue
            text = op.get("proposed_text") or ""
            stripped = strip_quotes_around(text, quote)
            if stripped != text:
                op["proposed_text"] = stripped
                changed = True
                touched.append(eid)
                run.journal("quote_softened", eid=eid, before=text, after=stripped)
        if changed:
            write_json(path, package)
    return touched


def strip_quotes_around(text: str, quote: str) -> str:
    """Снятие кавычек — тем же детектором, что их нашёл: `V.strip_quote_marks`.

    Свой список знаков здесь жил бы отдельной жизнью от `_QUOTE_SPAN` и при
    первой правке пар оставил бы часть отсуженных парафразов в кавычках.
    """
    return V.strip_quote_marks(text, quote)


def fabricated_eids(run: Run) -> Set[str]:
    return {eid for (eid, _), verdict in run.quote_verdicts().items()
            if verdict == "fabricated"}


# --- каноническое тело сущности -----------------------------------------

#: Провенанс дома: hint выжимки и правка пользователя. В тело сущности они не
#: входят — дом уже решён и объявлен отдельно: полем `unit` строки ростера на
#: экране паузы 1 и полем `unit` самого файла контекста редактора.
ENTITY_HOME_FIELDS = ("unit", "unit_hint")


def entity_body(item: Dict[str, Any]) -> Dict[str, Any]:
    """Тело сущности — единственный владелец правила «из чего она состоит».

    Кормит обе стороны разом: подпись паузы 1 (`summary_state`) и вход редактора
    (`build_context`). Это и есть гарантия конструкцией: множество, которое
    подписывает человек, и множество, которое уезжает LLM-узлу, строятся одним
    кодом и разъехаться не могут.

    До круга ревью списка было два. Подпись перечисляла девятку полей руками,
    вход редактора отдавал тело целиком минус провенанс дома. Всё, что вне
    девятки, — объявленный схемой `frame`, любое поле, добавленное узлом
    extract, — в подпись не входило, но до редактора доезжало: переподанная
    после показа выжимка проходила решение с прежним дайджестом и подкладывала
    редактору текст, которого человек не видел. Закрыть это списком разрешённых
    имён нельзя — список та же дисциплина, он отстанет от схемы ростера при
    первом же её расширении.
    """
    return {key: value for key, value in item.items() if key not in ENTITY_HOME_FIELDS}


# --- дом протокола встречи ----------------------------------------------

#: Холодный архив рядом с протоколом: сюда едет копия транскрипта. Имя то же,
#: что у служебного дерева базы (`SKIP_DIRS`), — сырьё карты его не увидит, и
#: транскрипт не станет фоном следующего разбора.
PROTOCOL_ARCHIVE = "zz_archive"


def meeting_topic(run: Run) -> str:
    """Тема встречи из выжимки — вторая половина имени файла протокола."""
    brief = run.load("brief.json") or {}
    return str((brief.get("meeting") or {}).get("topic") or "").strip()


def protocol_home(run: Run) -> Dict[str, Any]:
    """Где у ЭТОЙ базы живут протоколы встреч — по правилу самой базы.

    Правило пишет клиент в своём README (блок «Правила работы», иногда неявно —
    в «Маршрутах записи»); прочитать его может только тот, кому README доехал
    целиком, а это узел `map`. Он называет каталог и прикладывает типизированную
    улику — файл и дословную строку, из которой правило прочитано, — той же
    формы, что у опоры размещения операций.

    Ядро здесь нотариус: каталог назван · существует · не служебный · цитата
    улики стоит в названном файле · эта строка называет ИМЕННО ЭТОТ каталог.
    Пять фактов за O(1), ни одного суждения. Последний факт связывает улику с
    домом: без него подтверждалось существование строки где-то в базе, и узел,
    заявивший чужой каталог с настоящей строкой правила, уводил протокол в
    чужой юнит. Как правило записано — не наше дело: формулировку человека
    ядро не судит, оно проверяет связь «названный каталог упомянут в названной
    строке». Имени каталога в коде нет и быть не может: `01_company/meetings` —
    правда одной базы и догадка о любой другой. Факт не подтвердился — это
    вопрос пользователю на паузе 1, а не отказ и не молчаливый дефолт.

    Правка пользователя сильнее карты и улики не требует: человек и есть
    источник правила. Форму его правки проверяет `decide_summary` отказом —
    вопрос, рождённый после экрана, никто не увидит.
    """
    declared = (run.load("map.json") or {}).get("protocol_home")
    declared = declared if isinstance(declared, dict) else {}
    evidence = declared.get("evidence")
    evidence = evidence if isinstance(evidence, dict) else None
    edited = str((run.load("protocol-override.json") or {}).get("dir") or "").strip()
    named = edited or str(declared.get("dir") or "").strip()
    row: Dict[str, Any] = {
        "dir": named or None,
        "source": ("edit" if edited else "map" if named else None),
        "evidence": None if edited else evidence,
        "verified": False,
        "issue": None,
    }
    if not named:
        row["issue"] = ("правило базы о месте протоколов встреч не прочитано: "
                        "узел карты его не назвал — назови каталог протоколов сам "
                        "либо зафиксируй правило в README базы")
        return row
    if not base_dir_exists(run, named):
        row["issue"] = (f"каталог протоколов {named!r} в базе не существует "
                        "либо он служебный — назови существующий")
        return row
    if edited:
        row["verified"] = True
        return row
    quote = str((evidence or {}).get("quote") or "").strip()
    source_file = str((evidence or {}).get("file") or "").strip()
    if not quote or not source_file:
        row["issue"] = (f"каталог протоколов {named!r} назван без улики правила: "
                        "нужен файл и дословная строка, из которой правило прочитано")
        return row
    if not V.contains_fragment(run.read_base(source_file) or "", quote):
        row["issue"] = (f"улика правила не подтвердилась: строки {quote!r} нет "
                        f"в {source_file} — подтверди каталог протоколов сам")
        return row
    if not V.mentions_path(quote, named):
        # улика обязана подтверждать ДОМ, а не собственное существование:
        # настоящая строка правила, названная при чужом каталоге, проходила обе
        # прежние проверки — и протокол уезжал в чужой юнит (круг ревью, Н1)
        row["issue"] = (f"улика правила не называет каталог {named!r}: строка "
                        f"{quote!r} из {source_file} говорит о другом месте — "
                        "подтверди каталог протоколов сам")
        return row
    row["verified"] = True
    return row


def protocol_targets(run: Run) -> Optional[Dict[str, str]]:
    """Адреса протокола и архивной копии транскрипта внутри базы.

    Имя — правило v1: дата ВСТРЕЧИ (не обработки) из манифеста прогона плюс
    короткая тема выжимки. Дом не подтверждён или темы нет — адреса не бывает,
    и выдумывать его нечем.
    """
    home = protocol_home(run)
    topic = meeting_topic(run)
    if not home["verified"] or not topic:
        return None
    stem = f"{run.manifest['meeting_date']}_{topic}"
    return {"dir": str(home["dir"]),
            "summary": f"{home['dir']}/{stem}_summary.md",
            "transcript": f"{home['dir']}/{PROTOCOL_ARCHIVE}/{stem}_transcript.md"}


def protocol_absence(run: Run) -> Optional[Dict[str, Any]]:
    """Почему протокола в базе НЕ будет — именованным полем и человеческим текстом.

    Дом не подтверждён — адреса нет, раздел `protocol` из материала применения
    просто исчезает. Исчезнувшее поле не видит никто: шаг тихо не случается, и
    замечают это через недели по обрыву дат в базе — ровно тот класс дефекта,
    который чинит весь этот пакет. Поэтому отсутствие называется там же, где
    стояло бы присутствие: в материале применения и в состоянии прогона.

    Третьим замком это не становится и стать не может: ядро ничего не запирает
    и ничего не требует — оно называет факт и отдаёт координатору готовую фразу
    пользователю. Причина берётся ровно та, что стояла вопросом на паузе 1:
    человеческий текст, а не код отказа.
    """
    if protocol_targets(run) is not None:
        return None
    cause = protocol_home(run)["issue"] or (
        "тема встречи в выжимке не названа — имя файла протокола строить не из чего")
    return {"written": False,
            "reason": cause,
            "say": "протокол этой встречи и копия транскрипта в базу не лягут: "
                   + cause}


# --- пауза 1 ------------------------------------------------------------

#: Куда едет вопрос на экране паузы 1. Маршрут берётся из `kind`, который
#: проставил производитель вопроса, — не из разбора текста. Незнакомый вид
#: попадает в `ambiguities` (значение по умолчанию), а не пропадает молча.
QUESTION_GROUPS = {
    "map_finding": "map_findings",
    "node_question": "meeting_questions",
    "unknown_place": "ambiguities",
    "quote_fabricated": "ambiguities",
    "node_escalation": "ambiguities",
    "protocol_home": "ambiguities",
}

#: Группа для вида вопроса, которого в таблице нет.
QUESTION_GROUP_DEFAULT = "ambiguities"


def summary_questions(run: Run) -> List[Dict[str, Any]]:
    brief = run.load("brief.json") or {}
    assignment = run.load("assignment.json") or {}
    out: List[Dict[str, Any]] = []
    # находки карты обещаны пользователю и текстами, и hint'ом unknown_unit:
    # событие в events.jsonl никто не читает, доезд до паузы 1 — только отсюда
    for finding in (run.load("map.json") or {}).get("findings", []) or []:
        out.append({"kind": "map_finding", "message": str(finding)})
    for question in brief.get("questions", []) or []:
        if isinstance(question, dict):
            out.append({"kind": "node_question", **question})
        else:
            out.append({"kind": "node_question", "message": str(question)})
    out.extend(assignment.get("questions", []))
    for eid in sorted(fabricated_eids(run)):
        out.append({"kind": "quote_fabricated", "eid": eid,
                    "message": f"цитата-опора сущности {eid} не подтверждена: "
                               f"судья не нашёл её смысла в транскрипте"})
    home = protocol_home(run)
    if home["issue"]:
        out.append({"kind": "protocol_home", "message": home["issue"]})
    out.extend(open_escalations(run))
    return out


def open_escalations(run: Run) -> List[Dict[str, Any]]:
    """Эскалации «узел не исправил со второй попытки» доезжают до экранов,
    а не остаются строкой events.jsonl, которую никто не читает."""
    return [{"kind": "node_escalation", "eid": event.get("eid"),
             "message": event.get("message"), "code": event.get("code")}
            for event in run.events() if event.get("event") == "question"]


def summary_groups(run: Run) -> Dict[str, List[Dict[str, Any]]]:
    """Раскладка плоского списка вопросов по группам показа.

    Долг scaffold (находки карты) и содержательный вопрос встречи — разные
    разговоры и разные адресаты; неоднозначности этого разбора — третий.
    Порядок внутри группы сохраняется тот, в котором вопрос родился.
    """
    groups: Dict[str, List[Dict[str, Any]]] = {
        "meeting_questions": [], "map_findings": [], "ambiguities": []}
    for question in summary_questions(run):
        name = QUESTION_GROUPS.get(str(question.get("kind", "")), QUESTION_GROUP_DEFAULT)
        groups.setdefault(name, []).append(question)
    return groups


def roster_counts(run: Run) -> Dict[str, Any]:
    """Ростер, свёрнутый в цифры для короткого показа.

    `by_unit` считается тем же `assigned_eids`, что кормит редакторов: иначе
    пользователь подтвердит цифру, которой не будет в работе.
    """
    eids = [str(item.get("eid", "")) for item in run.roster()]
    withdrawn = run.withdrawn()
    return {"total": len(eids),
            "withdrawn": sum(1 for eid in eids if eid in withdrawn),
            "by_unit": {unit: len(assigned_eids(run, unit))
                        for unit in assigned_units(run)}}


def summary_state(run: Run) -> Dict[str, Any]:
    """Полное каноническое состояние паузы 1 — то, что подписывает digest.

    Состояние ничего не скрывает: строка ростера несёт тело сущности целиком —
    ровно то, что построит `entity_body` редактору, — плюс решённый дом и
    причину снятия. Собирается из артефактов прогона, а не из того, что
    показали, — поэтому подмена данных после показа видна подписи целиком,
    включая поля, которых в коротком экране нет и которых нет в схеме ростера.

    Дом протокола стоит здесь по той же причине, по какой здесь стоит тело
    сущности: из него строится адрес файла в базе. Поле, из которого строится
    путь, но не вошедшее в подпись, — дефект P20 слово в слово.
    """
    brief = run.load("brief.json") or {}
    assignment = run.assignment()
    withdrawn = run.withdrawn()
    roster = []
    for item in run.roster():
        eid = str(item.get("eid", ""))
        row = {**entity_body(item), "eid": eid, "unit": assignment.get(eid)}
        if eid in withdrawn:
            row["withdrawn"] = withdrawn[eid]
        roster.append(row)
    groups = summary_groups(run)
    home = protocol_home(run)
    return {"intent": "confirm_summary",
            "gist": (brief.get("meeting") or {}).get("gist") or brief.get("gist"),
            "topic": meeting_topic(run) or None,
            "protocol": {key: home[key]
                         for key in ("dir", "source", "evidence", "verified")},
            "meeting_questions": groups["meeting_questions"],
            "map_findings": groups["map_findings"],
            "ambiguities": groups["ambiguities"],
            "roster_counts": roster_counts(run),
            "roster": roster}


def summary_view(run: Run, full: bool) -> Dict[str, Any]:
    """Показ паузы 1: полный — ровно подписанное состояние, короткий — оно же
    без построчного ростера (его место занимают счётчики). Других различий
    между формами нет."""
    state = summary_state(run)
    return state if full else {k: v for k, v in state.items() if k != "roster"}


def render_summary(run: Run, full: bool) -> Dict[str, Any]:
    require_state(run, ("briefed", "confirmed"))
    pending = pending_quote_flags(run)
    if pending:
        raise SpineError("phase_order",
                         "спорные цитаты ещё не отсужены — экран показал бы недопроверенное",
                         hint="узел quote-judge → submit quotes",
                         next_command="submit quotes")
    payload = summary_view(run, full)
    # digest — отпечаток полного состояния, а не показанной формы: `--full`
    # отдаёт ровно его, короткая форма — оно же без ростера. Поэтому подпись
    # одна на обе формы, а правка поля, невидимого в коротком экране (цитата,
    # тема), гасит решение отказом digest_mismatch, а не проходит молча
    digest = V.digest(summary_state(run))
    run.store("screen-summary.json", {"payload": payload, "digest": digest})
    return {"state": run.state, "step": run.step,
            "next": "decide --screen summary --digest <digest>",
            "data": payload, "digest": digest}


def decide_summary(run: Run, payload: Dict[str, Any], digest: str) -> Dict[str, Any]:
    require_state(run, ("briefed",))
    if pending_quote_flags(run):
        raise SpineError("phase_order",
                         "после показа появились спорные цитаты — сначала суд, потом решение",
                         next_command="submit quotes")
    # сверка не со снимком показа, а с текущим состоянием артефактов: переподача
    # brief после render меняла бы ростер, и решение подтверждало бы непоказанное
    if V.digest(summary_state(run)) != digest:
        raise SpineError("digest_mismatch",
                         "экран устарел: артефакты изменились после показа",
                         next_command="render summary")
    # два прохода: сначала весь пакет валидируется, потом применяется и
    # журналируется — отказ по любому элементу не оставляет в журнале строк
    # о правках, которых нет в артефактах (круг 3: Sonnet P0-1, kimi m1)
    known = {str(item.get("eid")) for item in run.roster()}
    units = run.units()
    edits: List[Tuple[str, Dict[str, Any]]] = []
    for edit in payload.get("edits", []) or []:
        eid = str(edit.get("eid", ""))
        if eid not in known:
            raise SpineError("bad_usage", f"правка неизвестной сущности {eid}", field="edits")
        fields = {k: v for k, v in edit.items()
                  if k in ("title", "type", "modality", "owner", "due", "unit") and v}
        unit_value = str(fields.get("unit") or "")
        if unit_value and unit_value not in units \
                and not unit_of_file(unit_value, units):
            # отказ здесь, а не вопрос после подтверждения: вопрос, рождённый
            # после экрана, никто не увидит (kimi m10)
            raise SpineError("unknown_unit",
                             f"правка {eid}: юнита {unit_value!r} нет в карте",
                             field="edits", hint=f"юниты карты: {units}")
        edits.append((eid, fields))
    removals: List[Tuple[str, str]] = []
    for row in payload.get("withdraw", []) or []:
        eid = str(row.get("eid", ""))
        if eid not in known:
            raise SpineError("bad_usage", f"снятие неизвестной сущности {eid}", field="withdraw")
        reason = (row.get("reason") or "").strip()
        if not reason:
            raise SpineError("bad_usage", f"снятие {eid} без причины", field="withdraw",
                             hint="причина уходит в журнал: снятое не исчезает молча")
        removals.append((eid, reason))
    # дом протокола пользователь правит тем же механизмом, что и ростер, и по
    # тем же правилам: проверка в первом проходе, применение во втором. Отказ
    # здесь, а не вопрос после подтверждения — вопрос, рождённый после экрана,
    # никто не увидит (тот же урок, что у правки юнита)
    protocol_dir = ""
    home_edit = payload.get("protocol_home")
    if home_edit is not None:
        if isinstance(home_edit, str):
            protocol_dir = home_edit.strip()
        elif isinstance(home_edit, dict):
            protocol_dir = str(home_edit.get("dir") or "").strip()
        else:
            raise SpineError("bad_usage", "дом протокола называется каталогом базы",
                             field="protocol_home",
                             hint='{"protocol_home": {"dir": "01_company/meetings"}}')
        if not protocol_dir:
            raise SpineError("bad_usage", "дом протокола назван пустым",
                             field="protocol_home")
        if not base_dir_exists(run, protocol_dir):
            raise SpineError("unknown_unit",
                             f"каталога протоколов {protocol_dir!r} в базе нет "
                             "либо он служебный",
                             field="protocol_home",
                             hint="назови существующий каталог базы — путь "
                                  "от её корня")
    overrides = run.load("roster-overrides.json") or {}
    for eid, fields in edits:
        overrides[eid] = {**overrides.get(eid, {}), **fields}
        run.journal("roster_edited", eid=eid, fields=sorted(fields))
    run.store("roster-overrides.json", overrides)
    withdrawn = run.load("withdrawn.json") or {}
    for eid, reason in removals:
        withdrawn[eid] = reason
        run.journal("withdrawn", eid=eid, reason=reason)
    run.store("withdrawn.json", withdrawn)
    if protocol_dir:
        run.store("protocol-override.json", {"dir": protocol_dir})
        run.journal("protocol_home_edited", dir=protocol_dir)
    # назначение пересчитывается и без подтверждения: повторный render summary
    # обязан показывать юнит с учётом правок (круг 3: Sonnet P1-1)
    rebuild_assignment(run)
    # дом протокола, названный в этом же вызове, человеку не показывали ни разу:
    # адрес файла назвал координатор одновременно с подтверждением экрана. Тот
    # же класс, что P20 (поле, из которого строится путь, обязано быть в
    # подписи), и лечится тем же: правка дома требует НОВОГО показа. Сверка
    # именно подписью, а не фактом правки: назвал тот же дом, что стоял на
    # экране, — состояние не изменилось, показывать нечего (круг ревью, Н4)
    if protocol_dir and payload.get("confirmed") \
            and V.digest(summary_state(run)) != digest:
        raise SpineError("digest_mismatch",
                         f"каталог протоколов {protocol_dir!r} назван этим же "
                         "вызовом — экран его не показывал; правка принята, "
                         "подтверждение нет",
                         field="protocol_home",
                         hint="покажи экран заново и подтверди против свежей "
                              "подписи: адрес файла протокола человек обязан "
                              "увидеть до подтверждения",
                         next_command="render summary")
    if not payload.get("confirmed"):
        return {"state": run.state, "step": run.step,
                "next": "render summary (правки учтены, подтверждение не дано)",
                "data": {"edited": len(edits), "withdrawn": len(withdrawn)}}
    # подписанное состояние закрепляется снимком в момент подписи: дальше оно
    # ещё меняется (возврат из журнала законен в `confirmed` и `review` и
    # снимает пометку снятия), а текст протокола обязан остаться тем, который
    # человек подписал, а не тем, что сложилось к `render apply` (круг ревью, Н5)
    run.store("summary-confirmed.json", {"state": summary_state(run),
                                         "digest": digest})
    for unit in sorted(set(run.assignment().values())):
        build_context(run, unit)
    run.set_state("confirmed")
    # путь входа редактора называет ядро: правило склейки имени файла (`unit_key`)
    # внутреннее, и координатор, воспроизводящий его руками, рано или поздно
    # соберёт редактору второй вход другой свежести
    return {"state": run.state, "step": run.step,
            "next": "редакторы юнитов → submit operations --unit …; "
                    "затем контролёры → submit verdicts --unit …",
            "data": {"units": assigned_units(run),
                     "contexts": {unit: str(run.artifact(f"context/{run.unit_key(unit)}.json"))
                                  for unit in assigned_units(run)}}}


def assigned_units(run: Run) -> List[str]:
    withdrawn = run.withdrawn()
    return sorted({unit for eid, unit in run.assignment().items() if eid not in withdrawn})


# --- контекст юнита -----------------------------------------------------

#: Сколько файлов юнита приезжают редактору головами: адреса дёшевы и едут все,
#: дорога только голова. Срез назван числом `omitted_heads` — узел видит неполноту.
CONTEXT_HEADS = 60


def build_context(run: Run, unit: str) -> None:
    """Единственный вход редактора юнита: назначенное ему и его файлы.

    Тела сущностей едут разрешёнными — ростер уже с правками паузы 1, снятое
    вычтено тем же `assigned_eids`, что кормит проверку покрытия: редактору
    нечего склеивать из brief, assignment и overrides, и он не увидит того, за
    что ядро с него операции не спросит. Тело строит `entity_body` — тот же
    код, что кормит подпись паузы 1: сюда не попадёт ни одно поле, которого
    человек не подписал. Провенанс дома (`unit`/`unit_hint`) из тела убран:
    дом решён и объявлен полем `unit` самого файла, а оставшийся hint выжимки —
    приглашение усомниться в решении пользователя.
    """
    files = unit_files(run, unit)
    path = run.base_file(unit)
    panel = set(kit_panel(path)) if path.is_dir() else set()
    readme = read_readme(path) if path.is_dir() else None

    def is_core(rel: str) -> bool:
        tail = rel[len(unit) + 1:] if rel.startswith(unit + "/") else rel
        return tail.split("/")[0] in panel or tail == "README.md"

    def freshness(rel: str) -> float:
        try:
            return (run.base / rel).stat().st_mtime
        except OSError:
            return 0.0

    core = [rel for rel in files if is_core(rel)]
    rest = sorted((rel for rel in files if rel not in set(core)), key=freshness, reverse=True)
    chosen = set(core) | set(rest[:max(0, CONTEXT_HEADS - len(core))])
    slices = []
    for rel in files:
        if rel not in chosen:
            continue
        body = run.read_base(rel)
        if body is None:
            continue
        slices.append({"file": rel, "head": "\n".join(body.splitlines()[:40])})
    open_active = []
    for rel in files:
        tail = rel.rsplit("/", 1)[-1].lower()
        if "active" in tail:
            open_active.extend(open_active_items(run.read_base(rel) or ""))
    brief = run.load("brief.json") or {}
    roster = {str(item.get("eid", "")): item for item in run.roster()}
    entities = [entity_body(roster[eid])
                for eid in assigned_eids(run, unit) if eid in roster]
    run.store(f"context/{run.unit_key(unit)}.json", {
        "unit": unit,
        "gist": (brief.get("meeting") or {}).get("gist") or brief.get("gist"),
        "entities": entities,
        "readme_sections": readme_sections(readme) if readme else {},
        "panel": sorted(panel),
        "open_active": open_active,
        "files": files,
        "slices": slices,
        "omitted_heads": max(0, len(files) - len(slices)),
    })


# --- узлы юнитов --------------------------------------------------------


def assigned_eids(run: Run, unit: str) -> List[str]:
    withdrawn = run.withdrawn()
    return sorted(eid for eid, home in run.assignment().items()
                  if home == unit and eid not in withdrawn)


def require_known_unit(run: Run, unit: Optional[str]) -> str:
    if not unit:
        raise SpineError("bad_usage", "нужен --unit", field="--unit")
    if unit not in run.units():
        raise SpineError("unknown_unit", f"юнита {unit} нет в карте",
                         hint=f"юниты карты: {run.units()}")
    return unit


def submit_operations(run: Run, payload: Any, unit: Optional[str]) -> Dict[str, Any]:
    require_state(run, ("confirmed", "review"))
    unit = require_known_unit(run, unit)
    known = [str(item.get("eid", "")) for item in run.roster()]
    violations, flags = V.validate_operations(payload, unit, assigned_eids(run, unit),
                                              known)
    violations.extend(check_targets(run, unit, payload))
    raise_violations(run, violations, "operations")
    soften_known_paraphrases(run, payload)
    # корпус цитат встречи для редактора — выжимка: транскрипта ему не выдают,
    # и совпадение с транскриптом — совпадение, а не подтверждение
    brief_text = json.dumps(run.load("brief.json") or {}, ensure_ascii=False)
    judged = run.quote_verdicts()
    fresh = [row for row in flags
             if (row["eid"], row["quote"]) not in judged
             and not V.quote_in_text(row["quote"], brief_text)]
    added = store_quote_flags(run, fresh)
    # порядок слагаемых значим: ноты размещения первыми — так их читает экран
    evidence_notes = check_placement_evidence(run, unit, payload) \
        + check_base_quotes(run, unit, payload)
    # файл пишется всегда, в том числе пустым: иначе переподанный чистый пакет
    # оставил бы на экране залипшие ноты прежней версии
    run.store(f"evidence-notes/{run.unit_key(unit)}.json", {"notes": evidence_notes})
    drop_unit_derivatives(run, unit)
    write_json(run.artifacts / "operations" / f"{run.unit_key(unit)}.json", payload)
    run.set_state("review")
    return {"state": run.state, "step": run.step,
            "next": ("узел quote-judge судит спорные цитаты → submit quotes; "
                     if added else "") + f"контролёр юнита → submit verdicts --unit {unit}",
            "data": {"operations": len(payload.get("operations", [])),
                     "quote_flags": added, "evidence_notes": evidence_notes}}


def drop_unit_derivatives(run: Run, unit: str) -> None:
    """Переподача пакета гасит его производные: вердикты и отсевы прежней версии.

    Вердикт, вынесенный на прежний текст, к новому пакету не относится; отсев,
    сделанный по прежней улике, возвращается в разбор явным `returned` — иначе
    рассинхрон файла вердиктов и журнала не виден нигде.
    """
    verdicts_path = run.artifacts / "verdicts" / f"{run.unit_key(unit)}.json"
    if verdicts_path.is_file():
        verdicts_path.unlink()
        run.event("verdicts_dropped", unit=unit)
    for pair_unit, eid in sorted(filtered_eids(run)):
        if pair_unit == unit:
            run.event("returned", eid=eid, unit=unit)
            run.journal("returned", eid=eid,
                        reason=f"пакет юнита {unit} переподан — прежний отсев не аргумент")
    stored = run.load("relocations.json")
    if stored:
        prior = {str(op.get("eid")) for op in (run.operations(unit) or {})
                 .get("operations", [])}
        kept = [row for row in stored.get("relocations", [])
                if str(row.get("eid")) not in prior]
        if len(kept) != len(stored.get("relocations", [])):
            run.store("relocations.json", {"relocations": kept})


def soften_known_paraphrases(run: Run, payload: Dict[str, Any]) -> None:
    """Парафразы, уже отсуженные на стадии выжимки, не остаются кавычками в тексте
    записи: кавычки снимаются на входе пакета, а не ждут второго суда."""
    paraphrases = {(eid, quote) for (eid, quote), verdict in run.quote_verdicts().items()
                   if verdict == "paraphrase"}
    if not paraphrases:
        return
    for op in payload.get("operations", []) or []:
        if not isinstance(op, dict):
            continue
        eid = str(op.get("eid", ""))
        text = op.get("proposed_text") or ""
        for (flag_eid, quote) in paraphrases:
            # «есть ли фраза в тексте» отдельным правилом здесь не решается:
            # это вопрос детектора, и его ответ — `stripped != text` ниже
            if flag_eid != eid:
                continue
            stripped = strip_quotes_around(text, quote)
            if stripped != text:
                op["proposed_text"] = stripped
                run.journal("quote_softened", eid=eid, before=text, after=stripped)
                text = stripped


def check_targets(run: Run, unit: str, payload: Dict[str, Any]) -> List[V.Violation]:
    """Адрес операции: файл своего юнита; нового файла это не запрещает.

    Якорей больше нет — куда именно внутри файла, решает applier по канону
    формы. Код проверяет только принадлежность и что путь не убегает из базы.
    """
    out: List[V.Violation] = []
    for idx, op in enumerate(payload.get("operations", []) or []):
        if not isinstance(op, dict):
            continue
        eid = str(op.get("eid", ""))
        rel = (op.get("target") or {}).get("file")
        if rel:
            try:
                run.base_file(rel)
            except SpineError:
                out.append(V.Violation("path_escapes_base",
                                       f"путь {rel} выходит за пределы базы",
                                       field=f"operations[{idx}].target.file", eid=eid))
            else:
                if unit_of_file(rel, run.units()) != unit:
                    out.append(V.Violation("schema_invalid",
                                           f"файл {rel} не принадлежит юниту {unit}",
                                           field=f"operations[{idx}].target.file",
                                           eid=eid,
                                           hint="запись в чужой дом — проекция "
                                                "(projections[]) либо вердикт "
                                                "wrong_file контролёра"))
        # проекции проверяются независимо от target: у noop/journal_only
        # операций target нет, а мусор в projections не должен жить и там
        for projection in op.get("projections") or []:
            if not isinstance(projection, dict):
                out.append(V.Violation("schema_invalid", "проекция должна быть объектом",
                                       field=f"operations[{idx}].projections", eid=eid))
                continue
            pfile = projection.get("file", "")
            if not pfile:
                out.append(V.Violation("schema_invalid", "проекция без целевого файла",
                                       field=f"operations[{idx}].projections", eid=eid))
                continue
            try:
                run.base_file(pfile)
            except SpineError:
                out.append(V.Violation("path_escapes_base",
                                       f"путь {pfile} выходит за пределы базы",
                                       field=f"operations[{idx}].projections", eid=eid))
                continue
            if unit_of_file(pfile, run.units()) is None:
                out.append(V.Violation("schema_invalid",
                                       f"проекция в {pfile}: места нет в карте",
                                       field=f"operations[{idx}].projections", eid=eid))
    return out


def check_placement_evidence(run: Run, unit: str,
                             payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Опора размещения проверяется фактом, но не отбивает пакет: невалидная
    опора — пометка, она доезжает до `doubts` пункта на экране решений."""
    notes: List[Dict[str, Any]] = []
    for op in payload.get("operations", []) or []:
        if not isinstance(op, dict):
            continue
        evidence = op.get("placement_evidence")
        if not isinstance(evidence, dict) or not evidence.get("quote"):
            continue
        body = run.read_base(str(evidence.get("file", ""))) or ""
        if not V.contains_fragment(body, str(evidence["quote"])):
            notes.append({"eid": str(op.get("eid", "")), "kind": "placement_unverified",
                          "file": evidence.get("file"), "quote": evidence.get("quote")})
            run.event("evidence_invalid", eid=str(op.get("eid", "")),
                      code="placement_unverified")
    return notes


def check_base_quotes(run: Run, unit: str,
                      payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Цитата, объявленная строкой базы, проверяется файлом, а не судьёй смысла.

    Названный файл здесь улика, а не адрес записи: путь вне базы `read_base`
    глотает, и это та же пометка. Ненайденная строка пакет не отбивает — пункт
    едет на экран решений спорным.
    """
    notes: List[Dict[str, Any]] = []
    for claim in V.base_quote_claims(payload):
        body = run.read_base(claim["source_file"]) or ""
        if V.contains_fragment(body, claim["quote"]):
            continue
        notes.append({"eid": claim["eid"], "kind": "base_quote_unverified",
                      "file": claim["source_file"], "quote": claim["quote"]})
        run.event("evidence_invalid", eid=claim["eid"], code="base_quote_unverified")
    return notes


def placement_notes(run: Run) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    out: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    directory = run.artifacts / "evidence-notes"
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.json")):
        unit = path.stem.replace("__", "/")
        for note in read_json(path).get("notes", []):
            out.setdefault((unit, str(note.get("eid", ""))), []).append(note)
    return out


def submit_verdicts(run: Run, payload: Any, unit: Optional[str]) -> Dict[str, Any]:
    require_state(run, ("review",))
    unit = require_known_unit(run, unit)
    package = run.operations(unit)
    if not package:
        raise SpineError("phase_order", f"у юнита {unit} ещё нет пакета операций",
                         hint=f"сначала submit operations --unit {unit}")
    if not isinstance(payload, dict):
        raise SpineError("schema_invalid", "пакет вердиктов должен быть объектом")
    if payload.get("unit") not in (None, "", unit):
        raise SpineError("schema_invalid",
                         f"пакет назван для юнита {payload.get('unit')!r}, подан за {unit!r}",
                         field="verdicts.unit")
    if payload.get("controller_id") and \
            payload.get("controller_id") == package.get("editor_id"):
        raise SpineError("schema_invalid",
                         "контролёр юнита не может быть его же редактором",
                         field="verdicts.controller_id",
                         hint="независимость контроля гарантируется процедурой запуска узлов")
    eids = [str(op.get("eid", "")) for op in package.get("operations", [])]
    raise_violations(run, V.validate_verdicts(payload, unit, eids), "verdicts")
    results = judge_evidence(run, unit, payload)
    write_json(run.artifacts / "verdicts" / f"{run.unit_key(unit)}.json", payload)
    reroutes = [row for row in results if row["kind"] == "wrong_file"]
    next_cmd = ""
    if reroutes:
        targets = sorted({row["path"] for row in reroutes})
        next_cmd = ("переезд: один вызов редактора юнита-адресата "
                    f"({', '.join(targets)}) → submit relocation; ")
    return {"state": run.state, "step": run.step,
            "next": next_cmd + next_action(run),
            "data": {"filtered": [row for row in results if row["kind"] == "filtered"],
                     "doubts": [row for row in results if row["kind"] == "doubt"],
                     "reroutes": reroutes}}


def judge_evidence(run: Run, unit: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Улики вердиктов: код подтверждает факт — отсев без факта спорит, а не режет.

    `duplicate`/`episode` с подтверждённой уликой — журнал отсева (машинный
    фильтр виден человеку свёрнуто). Неподтверждённая улика деградирует в
    `doubt`: пункт едет на экран, цикла доводки нет.
    """
    out: List[Dict[str, Any]] = []
    brief_text = json.dumps(run.load("brief.json") or {}, ensure_ascii=False)
    for row in payload.get("verdicts", []) or []:
        eid = str(row.get("eid", ""))
        kind = row.get("verdict")
        evidence = row.get("evidence") or {}
        if kind == "duplicate":
            body = run.read_base(str(evidence.get("file", ""))) or ""
            if V.contains_fragment(body, str(evidence.get("quote", ""))):
                run.event("filtered", eid=eid, unit=unit, code="duplicate")
                run.journal("filtered", eid=eid, unit=unit, code="duplicate",
                            evidence=evidence)
                out.append({"kind": "filtered", "eid": eid, "code": "duplicate"})
            else:
                run.event("evidence_invalid", eid=eid, code="duplicate")
                out.append({"kind": "doubt", "eid": eid, "code": "duplicate_unverified"})
        elif kind == "episode":
            quote = str(evidence.get("quote", ""))
            # улика эпизода живёт в выжимке либо в транскрипте: цитата встречи,
            # не вошедшая в brief, — не повод спорить с контролёром
            if (V.quote_in_text(quote, brief_text)
                    or V.quote_in_text(quote, run.transcript_text())) and \
                    evidence.get("class") in V.EPISODE_CLASSES:
                run.event("filtered", eid=eid, unit=unit, code="episode")
                run.journal("filtered", eid=eid, unit=unit, code="episode",
                            evidence=evidence)
                out.append({"kind": "filtered", "eid": eid, "code": "episode"})
            else:
                run.event("evidence_invalid", eid=eid, code="episode")
                out.append({"kind": "doubt", "eid": eid, "code": "episode_unverified"})
        elif kind == "wrong_file":
            path = str(evidence.get("path", ""))
            home = unit_of_file(path, run.units())
            if home and home != unit:
                out.append({"kind": "wrong_file", "eid": eid, "path": home})
            else:
                run.event("evidence_invalid", eid=eid, code="wrong_file")
                out.append({"kind": "doubt", "eid": eid, "code": "wrong_file_unverified"})
        elif kind == "contradiction":
            body = run.read_base(str(evidence.get("file", ""))) or ""
            verified = V.contains_fragment(body, str(evidence.get("quote", "")))
            if not verified:
                run.event("evidence_invalid", eid=eid, code="contradiction")
            out.append({"kind": "doubt", "eid": eid,
                        "code": "contradiction" if verified else "contradiction_unverified"})
        elif kind == "doubt":
            out.append({"kind": "doubt", "eid": eid, "code": "doubt"})
    return out


def submit_relocation(run: Run, payload: Any) -> Dict[str, Any]:
    """Переезд — один вызов владельца нового дома, без ревизий и переконтроля."""
    require_state(run, ("review",))
    if not isinstance(payload, dict):
        raise SpineError("schema_invalid", "ответ о переезде должен быть объектом")
    raise_violations(run, V.validate_relocation(payload), "relocation")
    eid = str(payload.get("eid"))
    requested = set()
    for unit in run.units_with_operations():
        for row in (run.verdicts(unit) or {}).get("verdicts", []):
            if row.get("verdict") == "wrong_file":
                requested.add(str(row.get("eid", "")))
    if eid not in requested:
        # переезд без вердикта wrong_file — непрошеная заявка: посторонний вызов
        # не вправе переносить принятую операцию в другой файл
        raise SpineError("bad_usage",
                         f"по сущности {eid} нет вердикта wrong_file — переезд не запрошен",
                         field="eid")
    stored = run.load("relocations.json") or {"relocations": []}
    row: Dict[str, Any] = {"eid": eid, "editor_id": payload.get("editor_id"),
                           "accepted": bool(payload.get("accepted")),
                           "note": payload.get("note")}
    if payload.get("accepted"):
        target = payload.get("target") or {}
        to_unit = unit_of_file(str(target.get("file", "")), run.units())
        if to_unit is None:
            raise SpineError("unknown_unit",
                             f"файл {target.get('file')} не принадлежит ни одному юниту карты",
                             field="relocation.target.file")
        row["target"] = target
        row["to_unit"] = to_unit
        duplicate = payload.get("duplicate")
        if isinstance(duplicate, dict) and duplicate.get("quote"):
            body = run.read_base(str(duplicate.get("file", ""))) or ""
            if V.contains_fragment(body, str(duplicate["quote"])):
                run.event("filtered", eid=eid, unit=to_unit, code="duplicate")
                run.journal("filtered", eid=eid, unit=to_unit, code="duplicate",
                            evidence=duplicate)
                row["filtered_as_duplicate"] = True
    stored["relocations"] = [r for r in stored["relocations"] if r.get("eid") != eid]
    stored["relocations"].append(row)
    run.store("relocations.json", stored)
    run.journal("relocation", eid=eid, accepted=row["accepted"],
                to_unit=row.get("to_unit"))
    return {"state": run.state, "step": run.step, "next": next_action(run),
            "data": row}


# --- сведение к экрану решений ------------------------------------------


def filtered_eids(run: Run, code: Optional[str] = None) -> Set[Tuple[str, str]]:
    """Отсеянное: пары (юнит, сущность); `code` сужает до одного вида отсева.

    Ключ парный: вердикт контролёра относится к операции его юнита, и голый
    eid стирал бы с экрана принятую операцию соседнего юнита (Sonnet, блокер 2).
    `returned` без юнита — возврат человеком, он снимает отсев везде.
    """
    out: Set[Tuple[str, str]] = set()
    for event in run.events():
        eid = str(event.get("eid") or "")
        if not eid:
            continue
        if event.get("event") == "filtered" \
                and (code is None or event.get("code") == code):
            out.add((str(event.get("unit") or ""), eid))
        elif event.get("event") == "returned":
            unit = event.get("unit")
            if unit:
                out.discard((str(unit), eid))
            else:
                out = {pair for pair in out if pair[1] != eid}
    return out


def relocation_map(run: Run) -> Dict[str, Dict[str, Any]]:
    return {str(row.get("eid")): row for row in run.relocations()}


def effective_operations(run: Run) -> List[Tuple[str, Dict[str, Any]]]:
    """Операции, дошедшие до экрана: без noop, отсеянных и снятых человеком.

    Принятый переезд подменяет юнит и адрес операции здесь — в одном месте,
    которое читают и экран, и материал применения.
    """
    filtered = filtered_eids(run)
    withdrawn = run.withdrawn()
    relocations = relocation_map(run)
    out: List[Tuple[str, Dict[str, Any]]] = []
    for unit in run.units_with_operations():
        package = run.operations(unit) or {}
        for op in package.get("operations", []):
            eid = str(op.get("eid", ""))
            if op.get("op") == "noop" or op.get("journal_only") or eid in withdrawn:
                continue
            move = relocations.get(eid)
            moved = bool(move and move.get("accepted") and move.get("to_unit"))
            home = move["to_unit"] if moved else unit
            if (unit, eid) in filtered or (home, eid) in filtered:
                continue
            if moved:
                out.append((home, {**op, "target": move.get("target") or op.get("target"),
                                   "relocated_from": unit}))
            else:
                out.append((unit, op))
    return out


def journal_fates(run: Run) -> None:
    """Журнальные судьбы — `noop` и `journal_only` — видны в журнале базы.

    Пишется явным шагом рендера, а не побочным эффектом чтения: `render state`
    не должен менять журнал. Дедуп — по уже записанным строкам этого прогона.
    """
    logged = {(row.get("event"), row.get("eid"))
              for row in read_jsonl(run.journal_path())
              if row.get("run_id") == run.manifest["run_id"]}
    for unit in run.units_with_operations():
        for op in (run.operations(unit) or {}).get("operations", []):
            eid = str(op.get("eid", ""))
            if op.get("op") == "noop" and ("noop", eid) not in logged:
                run.journal("noop", eid=eid, unit=unit, reason=op.get("noop_reason"))
                logged.add(("noop", eid))
            elif op.get("journal_only") and ("journal_fate", eid) not in logged:
                run.journal("journal_fate", eid=eid, unit=unit, op=op.get("op"),
                            cancel_quote=op.get("cancel_quote"))
                logged.add(("journal_fate", eid))


def verdict_for(run: Run, unit: str, eid: str) -> Optional[Dict[str, Any]]:
    package = run.verdicts(unit) or {}
    for row in package.get("verdicts", []):
        if str(row.get("eid")) == eid:
            return row
    return None


def cross_conflicts(run: Run) -> Dict[str, List[str]]:
    """Детектор пересечений вместо арбитра: одна сущность в двух юнитах —
    спорный пункт с обоими предложениями, решает человек.

    Считается по пакетам как поданы, до подмены переезда: принятый переезд
    схлопнул бы два дома в один и спрятал бы конфликт с экрана.
    """
    filtered = filtered_eids(run)
    withdrawn = run.withdrawn()
    homes: Dict[str, List[str]] = {}
    for unit in run.units_with_operations():
        for op in (run.operations(unit) or {}).get("operations", []):
            eid = str(op.get("eid", ""))
            if op.get("op") == "noop" or op.get("journal_only") \
                    or (unit, eid) in filtered or eid in withdrawn:
                continue
            homes.setdefault(eid, []).append(unit)
    return {eid: units for eid, units in homes.items() if len(set(units)) > 1}


def review_debts(run: Run) -> Dict[str, List[str]]:
    units = assigned_units(run)
    no_operations = [unit for unit in units if run.operations(unit) is None]
    stale_packages = []
    for unit in units:
        package = run.operations(unit)
        if package is None:
            continue
        covered = {str(op.get("eid", "")) for op in package.get("operations", [])}
        if not set(assigned_eids(run, unit)) <= covered:
            # возврат сущности из журнала после сдачи пакета: покрытие устарело,
            # юнит обязан переподать пакет — долг виден, а не молчит
            stale_packages.append(unit)
    no_verdicts = []
    for unit in units:
        package = run.operations(unit)
        if package is None:
            continue
        verdicts = run.verdicts(unit)
        if verdicts is None:
            no_verdicts.append(unit)
            continue
        judged = {str(row.get("eid", "")) for row in verdicts.get("verdicts", [])}
        if not {str(op.get("eid", "")) for op in package.get("operations", [])} <= judged:
            no_verdicts.append(unit)
    relocations = relocation_map(run)
    open_reroutes: List[str] = []
    for unit in run.units_with_operations():
        package = run.verdicts(unit) or {}
        for row in package.get("verdicts", []):
            if row.get("verdict") == "wrong_file":
                eid = str(row.get("eid", ""))
                home = unit_of_file(str((row.get("evidence") or {}).get("path", "")),
                                    run.units())
                if home and home != unit and eid not in relocations:
                    open_reroutes.append(eid)
    return {"no_operations": no_operations, "stale_packages": stale_packages,
            "no_verdicts": no_verdicts,
            "open_relocations": sorted(set(open_reroutes)),
            "pending_quotes": [row["eid"] for row in pending_quote_flags(run)]}


def build_decision(run: Run) -> Dict[str, Any]:
    debts = review_debts(run)
    missing = {k: v for k, v in debts.items() if v}
    if missing:
        raise SpineError("phase_order", "ревью не закончено: " + json.dumps(
            missing, ensure_ascii=False),
            hint="waiting_on в render state называет долг поимённо",
            next_command="render state")
    roster = {str(item.get("eid")): item for item in run.roster()}
    fabricated = fabricated_eids(run)
    conflicts = cross_conflicts(run)
    filtered = filtered_eids(run)
    relocations = relocation_map(run)
    evidence_notes = placement_notes(run)
    items: List[Dict[str, Any]] = []
    number = 0
    for unit, op in effective_operations(run):
        eid = str(op.get("eid", ""))
        source_unit = op.get("relocated_from") or unit
        number += 1
        verdict = verdict_for(run, source_unit, eid) or {}
        doubts: List[str] = []
        if verdict.get("verdict") in ("doubt", "contradiction"):
            doubts.append(f"{verdict['verdict']}: {verdict.get('note') or ''}".strip(": "))
        if verdict.get("verdict") in ("duplicate", "episode") \
                and (source_unit, eid) not in filtered:
            doubts.append(f"{verdict['verdict']} — улика не подтвердилась, решает человек")
        move = relocations.get(eid)
        if verdict.get("verdict") == "wrong_file" and move and not move.get("accepted"):
            doubts.append("переезд отклонён редактором адресата: "
                          + (move.get("note") or "без причины"))
        if eid in fabricated:
            doubts.append("цитата не подтверждена судьёй цитат")
        if eid in conflicts:
            doubts.append(f"сущность предложена в юнитах: {', '.join(conflicts[eid])}")
        if op.get("relocated_from"):
            doubts.append(f"переезд из {op['relocated_from']} — проверь путь")
        for note in evidence_notes.get((source_unit, eid), []):
            if note.get("kind") == "base_quote_unverified":
                doubts.append(f"цитата из базы не найдена: {note.get('quote')!r} "
                              f"нет в {note.get('file')}")
            else:
                doubts.append("опора размещения не подтвердилась: "
                              f"{note.get('quote')!r} нет в {note.get('file')}")
        entity = roster.get(eid, {})
        item = {
            "n": number, "eid": eid, "unit": unit, "op": op.get("op"),
            "file": (op.get("target") or {}).get("file"),
            "text": op.get("proposed_text") or entity.get("title") or "",
            "title": entity.get("title"), "owner": entity.get("owner"),
            "due": entity.get("due"),
            "section": "doubtful" if doubts else "recommended",
            "doubts": doubts,
        }
        # проекция — часть пункта: пользователь принимает обе записи разом,
        # и applier получает её из решения, а не из пакета редактора
        projections = [{"file": p.get("file"), "proposed_text": p.get("proposed_text")}
                       for p in op.get("projections") or [] if isinstance(p, dict)]
        if projections:
            item["projections"] = projections
        items.append(item)
    payload = {"intent": "decision", "items": items,
               "journal": {"filtered": len(filtered_eids(run)),
                           "withdrawn": len(run.withdrawn())}}
    return payload


def render_decision(run: Run) -> Dict[str, Any]:
    require_state(run, ("review", "decided"))
    journal_fates(run)
    payload = build_decision(run)
    digest = V.digest(payload)
    run.store("screen-decision.json", {"payload": payload, "digest": digest})
    return {"state": run.state, "step": run.step,
            "next": "decide --screen decision --digest <digest>",
            "data": payload, "digest": digest}


def decide_decision(run: Run, payload: Dict[str, Any], digest: str) -> Dict[str, Any]:
    require_state(run, ("review",))
    # экран пересобирается от текущих артефактов: переподача пакета или суд цитат
    # после показа меняют дайджест, и решение против устаревшего показа не пройдёт
    current = build_decision(run)
    if V.digest(current) != digest:
        raise SpineError("digest_mismatch",
                         "экран устарел: артефакты изменились после показа",
                         next_command="render decision")
    items = {row["n"]: row for row in current["items"]}
    decisions = payload.get("decisions") or []
    seen: Dict[int, Dict[str, Any]] = {}
    for row in decisions:
        if not isinstance(row, dict):
            raise SpineError("bad_usage", "решение должно быть объектом", field="decisions")
        n = row.get("n")
        if n in seen:
            raise SpineError("bad_usage", f"пункт {n} получил два исхода", field="decisions")
        if n not in items:
            raise SpineError("bad_usage", f"пункта {n} нет на экране", field="decisions",
                             data={"known": sorted(items)})
        outcome = row.get("outcome")
        if outcome not in V.OUTCOMES:
            raise SpineError("bad_usage", f"неизвестный исход {outcome!r} у пункта {n}",
                             field="decisions", hint=f"допустимо: {sorted(V.OUTCOMES)}")
        if outcome == "edit" and not (row.get("text") or "").strip():
            raise SpineError("bad_usage", f"исход edit пункта {n} без текста",
                             field="decisions")
        seen[n] = row
    missing = sorted(set(items) - set(seen))
    if missing:
        raise SpineError("decision_incomplete",
                         f"без исхода остались пункты: {missing}",
                         hint="каждый пункт экрана получает исход — "
                              "take · reject · closed · already · edit")
    accepted_homes: Dict[str, List[int]] = {}
    for n, row in seen.items():
        if row["outcome"] in ("take", "closed", "edit"):
            accepted_homes.setdefault(items[n]["eid"], []).append(n)
    doubled = {eid: ns for eid, ns in accepted_homes.items() if len(ns) > 1}
    if doubled:
        raise SpineError("decision_conflict",
                         "одна сущность принята в нескольких пунктах: "
                         + ", ".join(f"{eid} (пункты {sorted(ns)})"
                                     for eid, ns in sorted(doubled.items())),
                         hint="у сущности один дом: оставьте один take, второй — reject")
    resolved = []
    for n, item in sorted(items.items()):
        row = seen[n]
        outcome = row["outcome"]
        text = row.get("text") if outcome == "edit" else item["text"]
        if outcome == "edit":
            run.journal("edited", eid=item["eid"], before=item["text"], after=text)
        resolved.append({**item, "outcome": "take" if outcome == "edit" else outcome,
                         "text": text, "edited": outcome == "edit"})
        if outcome == "already":
            run.journal("already", eid=item["eid"], unit=item["unit"])
        if outcome == "reject":
            run.journal("rejected", eid=item["eid"], unit=item["unit"],
                        reason=row.get("reason"))
    run.store("decision.json", {"items": resolved, "digest": digest})
    # принятый набор целиком — в журнал базы: расследование и калибровка
    # невозможны по памяти о том, что предлагалось
    run.journal("decision_set", items=[
        {"eid": row["eid"], "unit": row["unit"], "op": row["op"],
         "outcome": row["outcome"], "file": row["file"], "text": row["text"]}
        for row in resolved])
    run.set_state("decided")
    return {"state": run.state, "step": run.step, "next": "render apply",
            "data": {"taken": sum(1 for r in resolved if r["outcome"] in ("take", "closed")),
                     "rejected": sum(1 for r in resolved if r["outcome"] == "reject"),
                     "already": sum(1 for r in resolved if r["outcome"] == "already")}}


# --- применение ---------------------------------------------------------


def accepted_items(run: Run) -> List[Dict[str, Any]]:
    decision = run.load("decision.json") or {}
    return [row for row in decision.get("items", [])
            if row.get("outcome") in ("take", "closed")]


def check_applied_files(run: Run, payload: Any) -> List[V.Violation]:
    """Адрес строки отчёта — адрес её пункта.

    Этой сверкой держится граница ручного разбиения большого пакета: строка не
    может отчитаться о записи по чужому адресу. Пустой адрес и незнакомый eid
    закрывает `validate_applied` — здесь только сопоставление с материалом.
    """
    if not isinstance(payload, dict):
        return []
    items = {str(row.get("eid")): row for row in accepted_items(run)}
    out: List[V.Violation] = []
    for idx, row in enumerate(payload.get("results", []) or []):
        if not isinstance(row, dict):
            continue
        eid = str(row.get("eid", ""))
        rel = str(row.get("file") or "").strip()
        item = items.get(eid)
        if not rel or item is None or rel == item.get("file"):
            continue
        out.append(V.Violation("schema_invalid",
                               f"статус по пункту {eid} назван файлом {rel}, "
                               f"адрес пункта — {item.get('file')}",
                               field=f"results[{idx}].file", eid=eid,
                               hint="строка отчёта называет адрес своего пункта; "
                                    "парная половина, хроника и проекция называются "
                                    "в note. Чужой адрес — знак, что applier вышел "
                                    "за свою группу"))
    return out


def protocol_line(row: Dict[str, Any]) -> str:
    """Строка сущности в протоколе: заголовок, факты, реплика-опора."""
    facts = [str(row[key]) for key in ("type", "modality") if row.get(key)]
    if row.get("owner"):
        facts.append(f"отв. {row['owner']}")
    if row.get("due"):
        facts.append(f"срок: {row['due']}")
    if row.get("unit"):
        facts.append(f"дом: {row['unit']}")
    line = f"- **{row.get('title') or row.get('eid')}**"
    if facts:
        line += " — " + " · ".join(facts)
    quote = str(row.get("quote") or "").strip()
    if quote:
        line += f"\n  > {quote}"
    return line


def confirmed_state(run: Run) -> Dict[str, Any]:
    """Состояние паузы 1 таким, каким его ПОДПИСАЛИ, — снимок, а не пересчёт.

    После подтверждения состояние ещё меняется: `decide --screen journal`
    законен в `confirmed` и `review`, и возврат снятой сущности стирает пометку
    снятия. Пересчёт на момент `render apply` дал бы протокол, которого человек
    не видел. Снимка нет (прогон до подтверждения) — считаем живьём: врать о
    подписи нечем.
    """
    stored = (run.load("summary-confirmed.json") or {}).get("state")
    return stored if isinstance(stored, dict) else summary_state(run)


def protocol_text(run: Run) -> str:
    """Текст протокола рендерит КОД — из состояния, подписанного человеком.

    Это форматирование, а не суждение: gist, темы, владельцы, сроки и модальность
    уже прошли паузу 1, и узлу тут делать нечего. Модель на этом месте означала
    бы второй пересказ встречи — расходящийся с тем, что человек подтвердил.
    Источник ровно один: снимок `summary_state`, снятый в момент подписи.
    """
    state = confirmed_state(run)
    date = run.manifest["meeting_date"]
    topic = str(state.get("topic") or "")
    lines = ["---", f'title: "Протокол встречи {date} — {topic}"', "type: meeting",
             f"date: {date}", f"topic: {topic}", "---", "",
             f"# Встреча {date}", "", "## О чём была встреча", "",
             str(state.get("gist") or "—"), ""]
    threads: Dict[str, List[Dict[str, Any]]] = {}
    for row in state["roster"]:
        if row.get("withdrawn"):
            continue
        threads.setdefault(str(row.get("thread") or "—"), []).append(row)
    if threads:
        lines += ["## Разобрано", ""]
        for thread in sorted(threads):
            lines += [f"### {thread}", ""]
            lines += [protocol_line(row) for row in threads[thread]]
            lines.append("")
    withdrawn = [row for row in state["roster"] if row.get("withdrawn")]
    if withdrawn:
        lines += ["## Снято на подтверждении", ""]
        lines += [f"- {row.get('title') or row.get('eid')} — {row['withdrawn']}"
                  for row in withdrawn]
        lines.append("")
    if state["meeting_questions"]:
        lines += ["## Открытые вопросы", ""]
        lines += [f"- {row.get('message')}" for row in state["meeting_questions"]]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def protocol_material(run: Run) -> Optional[Dict[str, Any]]:
    """Протокол и транскрипт для applier — ПУТЯМИ, а не текстами.

    Выжимка рендерится в рабочий каталог прогона: ядро в базу не пишет ничего и
    после этой правки. В базу оба файла кладёт applier копированием — транскрипт
    живой встречи весит сотни килобайт, и прогон его через модель означал бы
    усечение и выдумку вместо архива. Транскрипт именно КОПИРУЕТСЯ: он приходит
    произвольным путём, часто вне базы, и удалять исходник пользователя скилл
    не вправе.

    Существующий протокол за ту же дату не перезаписывается никогда — правило
    v1: ядро называет факт `exists`, а переписать или пропустить решает не оно.
    """
    targets = protocol_targets(run)
    if targets is None:
        return None
    rendered = run.artifact("protocol") / Path(targets["summary"]).name
    rendered.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(rendered, protocol_text(run))
    return {
        "action": "copy",
        "rule": "оба файла кладутся в базу копированием файла, не пересказом: "
                "содержимое через модель не проходит. Файл на месте (exists) — "
                "статус skipped с причиной: существующий протокол не "
                "перезаписывается никогда",
        "summary": {"source": str(rendered), "target": targets["summary"],
                    "exists": run.base_file(targets["summary"]).is_file()},
        "transcript": {"source": run.manifest["transcript"]["path"],
                       "target": targets["transcript"],
                       "exists": run.base_file(targets["transcript"]).is_file(),
                       "note": "копируется, а не переносится: исходник "
                               "пользователя остаётся на месте"},
    }


def protocol_declared(run: Run) -> Dict[str, Dict[str, Any]]:
    """Раздел протокола ВЫДАННОГО материала: адреса и снимок занятости.

    Спрашивается ровно то, что было обещано: материал читается из артефакта, а
    не пересчитывается, иначе отчёт отвечал бы на другой вопрос, чем задавали.
    Один владелец на оба вопроса — «по каким частям ждём статус» и «против чего
    его сверять»: два источника разъехались бы при первой правке материала.
    """
    material = (run.load("apply-material.json") or {}).get("payload") or {}
    protocol = material.get("protocol")
    protocol = protocol if isinstance(protocol, dict) else {}
    out: Dict[str, Dict[str, Any]] = {}
    for part in ("summary", "transcript"):
        row = protocol.get(part)
        if isinstance(row, dict):
            out[part] = row
    return out


def protocol_parts(run: Run) -> Tuple[str, ...]:
    """Части протокола, по которым ядро ждёт статус, — по выданному материалу."""
    return tuple(protocol_declared(run))


def prepared_sha(row: Dict[str, Any]) -> Optional[str]:
    """Отпечаток файла, приготовленного ядром к копированию, — или ничего.

    `source` обеих частей называет само ядро: у выжимки это отрендеренный
    протокол в каталоге прогона, у транскрипта — исходник прогона. Файл не
    читается — судить не о чем, и ядро молчит вместо догадки.
    """
    try:
        return sha256_bytes(Path(str(row.get("source") or "")).read_bytes())
    except OSError:
        return None


def check_protocol_report(run: Run, payload: Any) -> List[V.Violation]:
    """Статус по файлу протокола: свой адрес и никакой записи поверх чужого файла.

    Две гарантии, обе фактом, обе за один взгляд на диск.

    1. Адрес статуса — адрес из материала. Симметрично строкам пунктов
       (`check_applied_files`): статус, названный чужим файлом, отчитывается не
       о том файле, который выдало ядро.
    2. `written` не принимается, пока по адресу стоит ЧУЖОЙ файл. Чужой — это
       любой файл в снимке материала (приготовленного ядром там ещё нет) и файл
       с не тем содержимым в момент отчёта: оба файла кладутся копированием,
       значит побайтово совпадают с приготовленным. «Существующий протокол не
       перезаписывается никогда» держится этой проверкой, а не послушанием узла.

    Окно между материалом и записью ядро не наблюдает: точки вызова между ними
    нет, а перезапись уничтожает улику. Поэтому снимок берётся не заранее, а в
    `render apply` — непосредственно перед вызовом applier, и всё, что успело
    появиться и уцелеть, ловится вторым взглядом здесь.
    """
    if not isinstance(payload, dict):
        return []
    report = payload.get("protocol")
    report = report if isinstance(report, dict) else {}
    out: List[V.Violation] = []
    for part, declared in protocol_declared(run).items():
        row = report.get(part)
        if not isinstance(row, dict):
            continue
        where = f"applied.protocol.{part}"
        target = str(declared.get("target") or "")
        named = str(row.get("file") or "").strip()
        if named and target and named != target:
            out.append(V.Violation(
                "schema_invalid",
                f"статус по файлу протокола ({part}) назван файлом {named}, "
                f"адрес материала — {target}",
                field=f"{where}.file",
                hint="строка статуса называет адрес, который выдало ядро: "
                     "запись по другому адресу — не этот файл"))
        if row.get("status") != "written":
            continue
        if declared.get("exists"):
            out.append(V.Violation(
                "protocol_overwrite",
                f"файл протокола ({part}) по адресу {target} существовал до "
                "записи — статус written утверждает запись поверх него",
                field=f"{where}.status",
                hint="существующий протокол не перезаписывается никогда: "
                     "верни по нему skipped с причиной"))
            continue
        prepared = prepared_sha(declared)
        standing = run.base_file(target) if target else None
        if prepared and standing is not None and standing.is_file() \
                and sha256_bytes(standing.read_bytes()) != prepared:
            out.append(V.Violation(
                "protocol_overwrite",
                f"по адресу {target} лежит не тот файл, который приготовило "
                f"ядро, — статус written по файлу протокола ({part}) не принят",
                field=f"{where}.status",
                hint="файл появился по адресу помимо этого разбора: оба файла "
                     "кладутся копированием и совпадают с приготовленным "
                     "побайтово; чужой протокол не перезаписывается"))
    return out


def render_apply(run: Run) -> Dict[str, Any]:
    """Замок 1 пройден по построению: `decided` не наступает без исходов по всем
    пунктам. Материал applier — узкий вход: принятые пункты, целевые файлы,
    протокол встречи путями, канон формы. Правило узла: перечитай файл перед
    правкой.

    Ранняя ветка закрывает фазу, только когда писать нечего ВООБЩЕ. Пока она
    считала одни принятые пункты, прогон без единого take означал «встречу
    разобрали, в базе пусто» — ровно ту дыру, которую чинит протокол.

    Протокола не будет — это стоит в материале названным полем `protocol_absent`,
    обеими ветками. Мимо этой команды к сводке дороги нет: `applied` наступает
    только отсюда, — значит, факт нельзя пройти ни разу его не увидев.
    """
    require_state(run, ("decided", "writing"))
    items = accepted_items(run)
    protocol = protocol_material(run)
    absent = protocol_absence(run) if not protocol else None
    if not items and not protocol:
        run.set_state("applied", "completed")
        data: Dict[str, Any] = {"items": [],
                                "message": "принятых записей нет — писать нечего"}
        if absent:
            data["protocol_absent"] = absent
        return {"state": run.state, "step": run.step, "next": next_action(run),
                "data": data}
    files = sorted({row["file"] for row in items if row.get("file")}
                   | {p.get("file") for row in items
                      for p in row.get("projections") or [] if p.get("file")})
    rows = []
    for row in items:
        entry = {"n": row["n"], "eid": row["eid"], "unit": row["unit"],
                 "op": row["op"], "outcome": row["outcome"], "file": row["file"],
                 "text": row["text"], "owner": row.get("owner"), "due": row.get("due")}
        if row.get("projections"):
            entry["projections"] = row["projections"]
        rows.append(entry)
    payload = {
        "intent": "apply",
        "meeting_date": run.manifest["meeting_date"],
        "formats_reference": "references/formats.md",
        "rule": "пиши по фактическому состоянию файла: перечитай каждый файл "
                "непосредственно перед правкой, а не по содержимому из разбора",
        "items": rows,
        "files": files,
    }
    if protocol:
        # отдельным разделом, не строкой `files`: группы файлов координатор режет
        # по юнитам принятых пунктов, а протокол — не пункт и юниту не принадлежит
        payload["protocol"] = protocol
    elif absent:
        # присутствие названо разделом, отсутствие — полем: пропуск протокола
        # обязан быть громким. Статуса ядро по нему не спрашивает — писать нечего
        payload["protocol_absent"] = absent
    digest = V.digest(payload)
    run.store("apply-material.json", {"payload": payload, "digest": digest})
    run.set_state("writing")
    return {"state": run.state, "step": run.step,
            "next": "узел applier применяет и отчитывается → submit applied",
            "data": payload, "digest": digest}


def submit_applied(run: Run, payload: Any) -> Dict[str, Any]:
    """Замок 2: статус записи по каждому принятому пункту — до этого сводки нет.

    Протокол встречи и архивная копия транскрипта — отдельная часть отчёта, и
    спрашиваются они так же строго: материал их нёс — статус обязателен. Иначе
    «встречу разобрали» означало бы неизвестно что. Статус этой части сверяется
    с фактом файла (`check_protocol_report`): свой адрес, и никакого `written`
    поверх файла, которого ядро не готовило.

    Отчёт один, applier'ов может быть несколько: большой write-set координатор
    делит на непересекающиеся группы файлов и склеивает строки в один `results`.
    """
    require_state(run, ("writing",))
    expected = [row["eid"] for row in accepted_items(run)]
    violations = V.validate_applied(payload, expected, protocol_parts(run))
    violations.extend(check_applied_files(run, payload))
    violations.extend(check_protocol_report(run, payload))
    raise_violations(run, violations, "applied")
    run.store("applied.json", payload)
    for row in payload.get("results", []):
        run.journal("apply_status", eid=row.get("eid"), file=row.get("file"),
                    status=row.get("status"), note=row.get("note"),
                    applier_id=row.get("applier_id"))
    protocol = payload.get("protocol") if isinstance(payload.get("protocol"), dict) else {}
    for part in protocol_parts(run):
        row = protocol.get(part) or {}
        run.journal("protocol_status", part=part, status=row.get("status"),
                    file=row.get("file"), note=row.get("note"),
                    applier_id=row.get("applier_id"))
    statuses = {row.get("status") for row in payload.get("results", [])}
    run.set_state("applied", "completed")
    data: Dict[str, Any] = {"written": sum(1 for r in payload["results"]
                                           if r.get("status") == "written"),
                            "unwritten": [r for r in payload["results"]
                                          if r.get("status") != "written"],
                            "statuses": sorted(s for s in statuses if s)}
    if protocol_parts(run):
        data["protocol"] = {part: protocol.get(part) for part in protocol_parts(run)}
    return {"state": run.state, "step": run.step, "next": next_action(run),
            "data": data}


def applied_results(run: Run) -> List[Dict[str, Any]]:
    return (run.load("applied.json") or {}).get("results", [])


def require_written(run: Run) -> None:
    # `done` исключён: после сдачи сводки повторная сдача не имеет предмета —
    # подмена текста после показа пользователю была бы дефектом
    require_state(run, ("applied",))
    if run.step != "completed":
        raise SpineError("apply_status_missing",
                         "статусы записи не сданы — сводка описывала бы неизвестное")


# --- доставка -----------------------------------------------------------

#: Кандидат в адрес: токен со слэшем. Адресом он становится не формой, а тем,
#: что указывает на реально существующее место базы.
PATH_TOKEN = re.compile(r"(?<![\w/:.])[\w.-][\w./-]*/[\w./-]*")


def points_into_base(run: Run, token: str) -> bool:
    candidate = token.strip("/.,;:!?»«\"'()").strip()
    if not candidate or ".." in candidate.split("/"):
        return False
    try:
        base = run.base.resolve()
        target = (base / candidate).resolve()
        if base != target and base not in target.parents:
            return False
        return target.exists()
    except OSError:
        return False


def leaked_technique(run: Run, text: str) -> List[Dict[str, Any]]:
    """След кухни разбора в тексте участникам: адрес, существующий в базе,
    идентификатор этого прогона, имя файла, куда этот разбор писал."""
    found: List[Dict[str, Any]] = []
    for match in PATH_TOKEN.finditer(text):
        if points_into_base(run, match.group(0)):
            found.append({"kind": "file_path", "sample": match.group(0)})
    for eid in sorted({str(item.get("eid")) for item in run.roster() if item.get("eid")}):
        if re.search(rf"(?<!\w){re.escape(eid)}(?!\w)", text):
            found.append({"kind": "entity_id", "sample": eid})
    touched = {str(row.get("file") or "") for row in applied_results(run)}
    # файлы проекций в отчёте applier'а не значатся — статус один на пункт
    touched |= {str(p.get("file") or "") for row in accepted_items(run)
                for p in row.get("projections") or []}
    # протокол и архив транскрипта — такие же тронутые адреса, как целевые файлы
    # пунктов, и берутся они из адресов, а не из факта записи: applier вернул
    # skipped или failed — файла в базе нет, и проверка «путь существует» имя
    # пропустит, а участники получат кухню разбора
    targets = protocol_targets(run)
    if targets:
        touched |= {targets["summary"], targets["transcript"]}
    for name in sorted({path.rsplit("/", 1)[-1] for path in touched}):
        if name and re.search(rf"(?<![\w/]){re.escape(name)}(?!\w)", text):
            found.append({"kind": "file_path", "sample": name})
    return found


def render_delivery(run: Run) -> Dict[str, Any]:
    require_written(run)
    material = delivery_material(run)
    return {"state": run.state, "step": run.step,
            "next": "узел deliver пишет сводку → submit delivery",
            "data": material}


def delivery_material(run: Run) -> Dict[str, Any]:
    """Содержание сводки — от отражения в базе, а не от полного нарратива:
    в базу записывается важное, и сводка не вправе выдавать обсуждённое за
    зафиксированное (дефект прогона 07.08). Отражение — written ∪ already ∪
    duplicate: неважно, новая это дельта или предмет уже был записан ранее
    (решение пользователя 10.08)."""
    results = applied_results(run)
    written = {str(r.get("eid")) for r in results if r.get("status") == "written"}
    decision_items = (run.load("decision.json") or {}).get("items", [])
    brief = run.load("brief.json") or {}
    roster = {str(item.get("eid")): item for item in run.roster()}
    reflected: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for row in decision_items:
        eid = str(row.get("eid"))
        if row.get("outcome") in ("take", "closed") and eid in written:
            kind = "written"
        elif row.get("outcome") == "already":
            kind = "already"
        else:
            # непринятое и незаписанное (в том числе failed/skipped applier'а)
            # отражением не является — тема уходит в фон
            continue
        entity = roster.get(eid) or {}
        reflected.append({"title": row.get("title") or row.get("text"),
                          "text": row.get("text"), "owner": row.get("owner"),
                          "due": row.get("due"), "op": row.get("op"),
                          "modality": entity.get("modality"),
                          "reflection": kind})
        seen.add(eid)
    duplicates = {eid for _, eid in filtered_eids(run, code="duplicate")}
    for eid in sorted(duplicates - seen):
        entity = roster.get(eid) or {}
        reflected.append({"title": entity.get("title"), "text": None,
                          "owner": entity.get("owner"), "due": entity.get("due"),
                          "op": None, "modality": entity.get("modality"),
                          "reflection": "duplicate"})
    # открытые вопросы встречи — сущности типа question из ростера; снятые,
    # уже отражённые и машинно отсеянные открытыми не считаются;
    # brief.questions — вопросы узла к пользователю, они закрыты паузой 1
    withdrawn = run.withdrawn()
    closed_eids = seen | {eid for _, eid in filtered_eids(run)}
    open_questions = [{"title": item.get("title"), "owner": item.get("owner")}
                      for item in run.roster()
                      if item.get("type") == "question"
                      and str(item.get("eid")) not in withdrawn
                      and str(item.get("eid")) not in closed_eids]
    return {
        "intent": "delivery_material",
        "gist": (brief.get("meeting") or {}).get("gist") or brief.get("gist"),
        "reflected": reflected,
        "open_questions": open_questions,
    }


def submit_delivery(run: Run, payload: Any) -> Dict[str, Any]:
    require_written(run)
    raise_violations(run, V.validate_delivery(payload), "delivery")
    leaks = leaked_technique(run, payload.get("text") or "")
    if leaks:
        raise SpineError("context_leak",
                         "в сводке участникам осталась кухня разбора: "
                         + ", ".join(sorted({row["sample"] for row in leaks})),
                         field="text", data={"leaks": leaks},
                         error_class="rework",
                         next_command="submit delivery (перепишите сводку)")
    run.store("delivery.json", payload)
    run.journal("delivery_submitted", chars=len(payload.get("text") or ""))
    run.set_state("done", "completed")
    return {"state": run.state, "step": run.step,
            "next": "покажи сводку пользователю и спроси, кому отправить — "
                    "отправка за координатором, не за ядром",
            "data": {"chars": len(payload.get("text") or "")}}


# --- render state / journal ---------------------------------------------


def next_action(run: Run) -> str:
    state = run.state
    if state == "ready":
        return "узел map → submit map"
    if state == "mapped":
        return "узел extract → submit brief"
    if state == "briefed":
        if pending_quote_flags(run):
            return "узел quote-judge → submit quotes"
        return "render summary → decide --screen summary"
    if state == "confirmed":
        return "редакторы юнитов → submit operations --unit …"
    if state == "review":
        debts = review_debts(run)
        if debts["no_operations"]:
            return f"submit operations --unit {debts['no_operations'][0]}"
        if debts["pending_quotes"]:
            return "узел quote-judge → submit quotes"
        if debts["no_verdicts"]:
            return f"submit verdicts --unit {debts['no_verdicts'][0]}"
        if debts["open_relocations"]:
            return "редактор юнита-адресата → submit relocation"
        return "render decision → decide --screen decision"
    if state == "decided":
        return "render apply → узел applier → submit applied"
    if state == "writing":
        return "узел applier применяет → submit applied"
    if state == "applied":
        return "render delivery → узел deliver → submit delivery"
    return "—"


def render_state(run: Run, full: bool) -> Dict[str, Any]:
    data: Dict[str, Any] = {"state": run.state, "step": run.step,
                            "run_dir": str(run.dir),
                            "inbox": str(run.dir / "inbox"),
                            "units": run.units(),
                            "assigned_units": assigned_units(run) if run.load(
                                "assignment.json") else []}
    if run.state in ("confirmed", "review"):
        data["waiting_on"] = review_debts(run)
    if run.state == "review":
        conflicts = cross_conflicts(run)
        if conflicts:
            data["cross_unit"] = conflicts
    uncovered = [item.get("eid") for item in run.roster()
                 if str(item.get("eid")) not in run.assignment()
                 and str(item.get("eid")) not in run.withdrawn()]
    if uncovered:
        data["uncovered"] = uncovered
    escalations = open_escalations(run)
    if escalations:
        data["escalations"] = escalations
    # состояние прогона называет и то, чего в нём не будет: до выжимки темы нет
    # и вопрос был бы преждевременным, после неё молчание означало бы, что
    # координатор узнаёт о пропущенном протоколе от пользователя через месяц
    if run.load("brief.json"):
        absent = protocol_absence(run)
        if absent:
            data["protocol_absent"] = absent
    if full:
        data["transitions"] = V.TRANSITIONS
    return {"state": run.state, "step": run.step, "next": next_action(run), "data": data}


def render_journal(run: Run) -> Dict[str, Any]:
    rows = [row for row in read_jsonl(run.journal_path())
            if row.get("run_id") == run.manifest["run_id"]]
    return {"state": run.state, "step": run.step, "next": next_action(run),
            "data": {"entries": rows}}


def decide_journal(run: Run, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Возврат пункта из журнала отсева — легальное действие человека.

    Но только пока разбор не решён: после экрана решений «возврат» ничего бы не
    изменил и отвечал бы ложным успехом. Возврат после сдачи пакета юнита делает
    пакет устаревшим — долг `stale_packages` виден в `render state` и запирает
    экран решений до переподачи.
    """
    require_state(run, ("briefed", "confirmed", "review"))
    eid = str(payload.get("eid", ""))
    if not eid:
        raise SpineError("bad_usage", "нужен eid возвращаемого пункта", field="eid")
    filtered = {pair[1] for pair in filtered_eids(run)}
    withdrawn = run.withdrawn()
    if eid not in filtered and eid not in withdrawn:
        raise SpineError("bad_usage", f"пункт {eid} не отсеян и не снят", field="eid")
    run.event("returned", eid=eid)
    run.journal("returned", eid=eid, reason=payload.get("reason"))
    data: Dict[str, Any] = {"returned": eid}
    if eid in withdrawn:
        stored = run.load("withdrawn.json") or {}
        stored.pop(eid, None)
        run.store("withdrawn.json", stored)
        # состав назначенного изменился после подтверждения: вход редактора
        # перестраивается здесь же, иначе он обязан дать судьбу сущности,
        # которой не видит, — покрытие ядро с него уже спросит
        home = run.assignment().get(eid)
        if home and run.state in ("confirmed", "review"):
            build_context(run, home)
            data["context"] = str(run.artifact(f"context/{run.unit_key(home)}.json"))
    debts = review_debts(run) if run.state in ("confirmed", "review") else {}
    data["stale_packages"] = debts.get("stale_packages", [])
    return {"state": run.state, "step": run.step, "next": next_action(run),
            "data": data}


# --- CLI ----------------------------------------------------------------


def load_artifact(run: Run, raw: str) -> Any:
    """Читает технический JSON прогона, поданный `--file`.

    Единственная дверь для артефактов узлов и ответов на экраны. Файл из базы
    не принимается: база — территория работы applier, всё остальное живёт в
    рабочем каталоге прогона. `--transcript` и `--base` правило не касается.

    Файла нет — отказ называется, а не падает трассировкой: путь в сообщении
    абсолютен (координатор видит, где ядро искало), а `next` возвращает в ту же
    точку конвейера, а не на перезапуск разбора, как советует реестр переходов.
    """
    path = Path(raw).expanduser().resolve()
    if under(run.base.resolve(), path):
        raise SpineError("artifact_in_base", f"артефакт {path} лежит внутри базы",
                         field="--file",
                         hint="перенеси файл в inbox прогона и подай оттуда",
                         data={"inbox": str(run.dir / "inbox")})
    if not path.is_file():
        raise SpineError("missing_input", f"файла нет по пути {path}",
                         field="--file",
                         hint="путь называется абсолютно: рабочая директория "
                              "между вызовами не сохраняется",
                         next_command=next_action(run),
                         data={"inbox": str(run.dir / "inbox")})
    return read_json(path)


def cmd_submit(args: argparse.Namespace) -> Dict[str, Any]:
    run = Run(resolve_run_dir(args))
    payload = load_artifact(run, args.file)
    kind = args.kind
    if kind == "map":
        return submit_map(run, payload)
    if kind == "brief":
        return submit_brief(run, payload)
    if kind == "quotes":
        return submit_quotes(run, payload)
    if kind == "operations":
        return submit_operations(run, payload, args.unit)
    if kind == "verdicts":
        return submit_verdicts(run, payload, args.unit)
    if kind == "relocation":
        return submit_relocation(run, payload)
    if kind == "applied":
        return submit_applied(run, payload)
    if kind == "delivery":
        return submit_delivery(run, payload)
    raise SpineError("bad_usage", f"неизвестный артефакт {kind}", field="KIND")


def cmd_render(args: argparse.Namespace) -> Dict[str, Any]:
    run = Run(resolve_run_dir(args))
    what = args.what
    if what == "state":
        return render_state(run, args.full)
    if what == "summary":
        return render_summary(run, args.full)
    if what == "decision":
        return render_decision(run)
    if what == "apply":
        return render_apply(run)
    if what == "delivery":
        return render_delivery(run)
    if what == "journal":
        return render_journal(run)
    raise SpineError("bad_usage", f"неизвестный экран {what}", field="WHAT")


def cmd_decide(args: argparse.Namespace) -> Dict[str, Any]:
    run = Run(resolve_run_dir(args))
    payload = load_artifact(run, args.file) if args.file else {}
    if not isinstance(payload, dict):
        raise SpineError("bad_usage", "payload решения должен быть объектом", field="--file")
    screen = args.screen
    if screen == "summary":
        return decide_summary(run, payload, args.digest or "")
    if screen == "decision":
        return decide_decision(run, payload, args.digest or "")
    if screen == "journal":
        return decide_journal(run, payload)
    raise SpineError("bad_usage", f"неизвестный экран {screen}", field="--screen")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="spine.py",
                                     description="Safety-ядро meeting-analysis v3")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="старт прогона: среда, сырьё карты")
    check.add_argument("--base", required=True)
    check.add_argument("--transcript", required=True)
    check.add_argument("--meeting-date", required=True)
    check.set_defaults(func=cmd_check)

    submit = sub.add_parser("submit", help="приём артефакта узла")
    submit.add_argument("kind", choices=["map", "brief", "quotes", "operations",
                                         "verdicts", "relocation", "applied", "delivery"])
    submit.add_argument("--file", "-f", required=True)
    submit.add_argument("--unit")
    submit.add_argument("--run-id")
    submit.set_defaults(func=cmd_submit)

    render = sub.add_parser("render", help="payload экрана или состояния")
    render.add_argument("what", choices=["state", "summary", "decision", "apply",
                                         "delivery", "journal"])
    render.add_argument("--full", action="store_true")
    render.add_argument("--run-id")
    render.set_defaults(func=cmd_render)

    decide = sub.add_parser("decide", help="решение человека против показа")
    decide.add_argument("--screen", required=True,
                        choices=["summary", "decision", "journal"])
    decide.add_argument("--file", "-f")
    decide.add_argument("--digest")
    decide.add_argument("--run-id")
    decide.set_defaults(func=cmd_decide)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except SpineError as error:
        print(json.dumps({"error": {
            "code": error.code, "message": error.message, "field": error.field,
            "hint": error.hint, "error_class": error.error_class,
            "next": error.next_command, "issues": error.issues, "data": error.data,
        }}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
