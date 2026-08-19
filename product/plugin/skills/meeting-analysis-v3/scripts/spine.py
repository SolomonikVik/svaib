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

Предлагаемые изменения базы ядро не записывает: их применяет LLM-узел по
фактическому состоянию файла (решение Эрика 09.08). Исключение ровно одно и
названо: протокол встречи и архивную копию транскрипта кладёт в базу само ядро
(решение Эрика 13.08) — это не предложение к записи, а артефакт разбора,
подписанный человеком на паузе 1; текст его рендерит код, и файл появляется
сразу после выжимки, а не в конце. Хранение и синхронизация базы — зона
ответственности клиента; откат — версионная история его платформы.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
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
        # mkstemp отдаёт 0600: файл базы не должен отличаться правами от соседей —
        # база живёт в git и в облачных папках, где 0600 читается как аномалия
        mask = os.umask(0)
        os.umask(mask)
        os.chmod(tmp, 0o666 & ~mask)
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
        # протокол в базе идёт за состоянием прогона: его yaml-поле `status`
        # называет этап, на котором разбор стоит. Одна точка вместо вызова из
        # каждой фазы — иначе новая фаза однажды забудет обновить файл, и в базе
        # останется статус, которого прогон давно не имеет
        sync_protocol(self)

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
        """Файл базы текстом — или ничего.

        Нечитаемое (чужая кодировка, исчезнувший файл, путь наружу) означает
        «источника нет», а не падение команды: база пользователя живёт своей
        жизнью, и один файл в cp1251 не повод останавливать разбор.
        """
        try:
            path = self.base_file(rel)
        except SpineError:
            return None
        if not path.is_file():
            return None
        try:
            return read_text(path)
        except (OSError, UnicodeDecodeError):
            return None

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

README_SECTIONS = ("Маршруты записи", "Содержимое папки", "Правила работы",
                   "Контекст перед разбором")
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
#: Журнал решений панели узла. Канон kit (`management-kit.md`, final): «Принятые
#: решения не переписываются; если решение устарело, оно помечается как
#: Superseded со ссылкой на новое». Правка прежней записи там запрещена, и
#: запрет держится кодом, а не прозой промпта — так велит канон формы файла:
#: «Если нужен жёсткий запрет, он фиксируется отдельным validator/procedure, не
#: текстом правила» (`02_file-spec.md`, final).
#:
#: Имя читается по канону панели во всех формах, которые он допускает: цифра —
#: атрибут сортировки, а не часть имени (`decisions.md` = `05_decisions.md`), и
#: любой файл кита вправе развернуться в папку (`decisions/`). Поэтому смотрим
#: каждый сегмент пути, а не только имя файла.
DECISION_LOG = re.compile(r"^(?:\d{2}_)?decisions(?:\.md)?$")


def is_decision_log(rel: str) -> bool:
    """Журнал решений — и файлом, и развернувшейся папкой.

    Канон панели разрешает `05_decisions.md` вырасти в `05_decisions/`: тогда
    журналом становится всё её содержимое, и правило append-only действует там
    же. Смотрим все сегменты пути, а не только имя файла.
    """
    return any(DECISION_LOG.match(part.lower()) for part in rel.split("/") if part)


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
    """Форма выбора карты: названное место существует в базе и не служебное.

    Каталог встреч домом не бывает: канон scaffold зовёт его infrastructure
    folder и говорит прямо — такие каталоги «не являются управляемыми узлами»
    (`01_architecture.md`). Без этой проверки карта вправе назвать юнитом сам
    `product/meetings`, и тогда срез записей встреч обходится с корня: редактор
    получает протоколы как свои файлы (круг ревью 17.08).
    """
    if not unit or unit.startswith("/") or ".." in unit.split("/"):
        return False
    if service_parts(tuple(unit.split("/"))):
        return False
    if is_historic_record(unit) or any(part.lower() == MEETINGS_DIR
                                       for part in unit.split("/")):
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


#: Запись встречи в базе: протокол разбора или архивная копия транскрипта.
#: Это исторический слой — разбор его не читает и не правит, иначе собственная
#: выжимка этого же прогона становится законной уликой дубля, и сущность тихо
#: исчезает из разбора, не дойдя до экрана решений.
MEETING_RECORD = re.compile(r"^\d{4}-\d{2}-\d{2}_.+_(?:summary|transcript)\.md$", re.I)

#: Каталог записей встреч по канону scaffold (`02_folder-spec.md` § `meetings/`):
#: infrastructure folder, который «хранит память встреч узла: протоколы, выжимки,
#: ссылки на сырьё». Подпапка внутри — форма роста, и имена её произвольны
#: (`one-to-one/`, `quarterly/`, `okr-3/`), поэтому исключается всё поддерево.
#:
#: Имя файла протокола каноном не закреплено так же жёстко, как имя каталога:
#: живые базы держат рядом `2026-08-03_product_sync.md`, `..._summary_v1.md` и
#: `README.md` — под `MEETING_RECORD` они не подходят, а протоколами являются.
#: Каталог — надёжный признак, регекс имени остаётся страховкой на запись,
#: положенную руками мимо него.
MEETINGS_DIR = "meetings"


def is_meeting_record(rel: str) -> bool:
    return bool(MEETING_RECORD.match(rel.rsplit("/", 1)[-1]))


def in_meetings_dir(rel: str) -> bool:
    """Путь лежит в каталоге записей встреч — на любом уровне дерева."""
    return any(part.lower() == MEETINGS_DIR for part in rel.split("/")[:-1] if part)


def is_historic_record(rel: str) -> bool:
    """Исторический слой: запись встречи по каталогу либо по имени файла.

    Один предикат на все входы — контекст редактора, улики отсева, подсказки
    адреса, объявленные источники чтения, выбор дома карты. Разъехавшись, они
    дают обход: первый круг ревью 17.08 нашёл ровно это — каталог закрыли в
    одном месте, а через объявление `reading_sources` протокол по-прежнему
    заезжал в разбор.
    """
    return is_meeting_record(rel) or in_meetings_dir(rel)


def unit_files(run: Run, unit: str) -> List[str]:
    """Файлы юнита: дерево каталога без поддеревьев дочерних юнитов карты и без
    записей встреч — протоколы прошлых разборов узлам не показываются.

    Каталог `meetings/` срезается целиком, вместе с подпапками: по канону
    scaffold там живёт вся память встреч узла, включая выжимку ЭТОГО прогона.
    Оставленный, он даёт круговую ссылку — свежий протокол доказывает сам себя,
    и редактор списывает сущность в `already_covered` по собственному разбору
    (живой прогон 14.08, юнит product).
    """
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
                         and name.lower() != MEETINGS_DIR
                         and (f"{rel}/{name}" if rel else name) not in units)
        for name in sorted(files):
            if name.lower().endswith(".md") and not is_meeting_record(name):
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
        "meeting_hint": {name: value for name, value in
                         (("тип встречи", getattr(args, "meeting_kind", None)),
                          ("цель встречи", getattr(args, "meeting_goal", None)))
                         if value},
        "transcript": {"path": str(transcript.resolve()),
                       "sha256": sha256_bytes(body.encode("utf-8"))},
    })
    write_json(workspace / "artifacts" / "base-raw.json", raw)
    inbox = workspace / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    # дефолтный речевой контекст — до карты: без неё область сбора — корень и
    # 01_company, то есть глобальные словари базы. Этого хватает штатному пути
    # extract-first; пустой контекст — сигнал фоллбэка (map первым, по
    # транскрипту: его область добавит юниты и досье)
    run = Run(workspace)
    context = build_reading_context(run)
    declared = declared_reading_lines(run)
    if declared["lines"]:
        context["declared"] = declared
    # отчёт сохраняется: подсказка next_action на ready читает факт контекста,
    # а не пересобирает его на каждый вопрос «что дальше»
    run.store("reading-context.json", context)
    data: Dict[str, Any] = {"directories": len(raw["directories"]),
                            "spine": SPINE_PATH,
                            "run_dir": str(workspace),
                            "inbox": str(inbox),
                            # размер транскрипта решает, читать его одним
                            # проходом или резать: порог узла — в nodes.json
                            "transcript_bytes": len(body.encode("utf-8")),
                            "reading_context": context,
                            "base_raw": str(workspace / "artifacts" / "base-raw.json")}
    # Старта, кроме check, у v3 нет — сравнение версий садится сюда, последним
    # шагом: прогон к этому моменту уже создан, рекомендация его не держит.
    update = skill_update(base)
    if update:
        data["skill_update"] = update
    empty_context = not context.get("sources")
    if empty_context:
        next_text = ("речевой контекст базы пуст — фоллбэк: узел map читает "
                     "транскрипт и строит карту по artifacts/base-raw.json → "
                     "submit map (контекст соберётся по её области)")
    else:
        next_text = ("узел extract читает транскрипт с речевым контекстом "
                     f"({context['file']}) → submit brief; карта строится после, "
                     "по ростеру выжимки")
    return {"state": "ready", "step": "", "run_id": run_id,
            "next": next_text,
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
                  message="разбор дважды не смог оформить это место — "
                          "решение за вами")
    first = violations[0]
    raise SpineError(first.code, first.message, field=first.field, hint=first.hint,
                     issues=[item.as_dict() for item in violations],
                     error_class="question" if escalate else None,
                     data={"phase": phase})


def drop_brief_quote_flags(run: Run) -> None:
    """Флаги цитат прежней выжимки: они сняты с текста, которого больше нет.

    Зеркало `drop_unit_quote_flags` для переподачи brief: зовётся ДО разбора
    новой выжимки. Оставленный флаг держал бы экран в ожидании суда над
    исчезнувшей цитатой, а оставленный вердикт — спорность по фразе, которой
    в новом ростере нет.
    """
    flags = run.load("quote-flags.json")
    if not flags:
        return
    kept = [row for row in flags.get("flags", [])
            if row.get("stage") == "operations"]
    dropped = [row.get("quote") for row in flags.get("flags", [])
               if row not in kept]
    if len(kept) != len(flags.get("flags", [])):
        run.store("quote-flags.json", {"flags": kept})
        run.event("quote_flags_dropped", message="переподача выжимки")
    if not dropped:
        return
    verdicts = run.load("quote-verdicts.json")
    if not verdicts:
        return
    live = [row for row in verdicts.get("quotes", [])
            if row.get("quote") not in dropped]
    if len(live) != len(verdicts.get("quotes", [])):
        run.store("quote-verdicts.json", {"quotes": live})


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


#: Поля lean-ростера — вход карты по штатному пути (extract-first): сущности
#: без цитат и спецификаций. Карте нужен предмет разговора, а не дословность:
#: цитаты удваивают размер и ничего не добавляют вопросу «чей это разговор».
ROSTER_LEAN_ENTITY = ("eid", "type", "thread", "title", "author", "unit_hint",
                      "owner")
ROSTER_LEAN_MEETING = ("gist", "topic", "kind", "participants")


def write_roster_lean(run: Run) -> Path:
    """Ростер выжимки для узла map: транскрипт через LLM проходит один раз."""
    brief = run.load("brief.json") or {}
    meeting = brief.get("meeting") or {}
    lean = {"meeting": {k: meeting.get(k) for k in ROSTER_LEAN_MEETING
                        if meeting.get(k)},
            "roster": [{k: row.get(k) for k in ROSTER_LEAN_ENTITY if row.get(k)}
                       for row in brief.get("roster", []) or []]}
    path = run.artifact("roster-lean.json")
    write_json(path, lean)
    return path


def submit_map(run: Run, payload: Any) -> Dict[str, Any]:
    require_state(run, ("ready", "mapped", "briefed"))
    raise_violations(run, V.validate_map(payload), "map")
    missing = [row["unit"] for row in payload.get("units", [])
               if not unit_exists(run, row.get("unit", ""))]
    if missing:
        raise_violations(run, [V.Violation(
            "unknown_unit", f"места {', '.join(missing)} в базе нет либо оно служебное",
            field="map.units",
            hint="юнит — существующий каталог или md-файл базы; нет подходящего — "
                 "опиши предмет в findings, вопрос доедет до паузы 1")], "map")
    declared_units = {row.get("unit") for row in payload.get("units", [])}
    stray = {str(k): str(v) for k, v in (payload.get("hint_map") or {}).items()
             if str(v) not in declared_units}
    if stray:
        raise_violations(run, [V.Violation(
            "unknown_unit",
            "hint_map ведёт в место вне карты: "
            + "; ".join(f"{k!r} → {v!r}" for k, v in sorted(stray.items())),
            field="map.hint_map",
            hint="значение hint_map — юнит из units этой же карты")], "map")
    run.store("map.json", payload)
    for finding in payload.get("findings", []) or []:
        run.event("map_finding", message=str(finding))
    if run.load("brief.json"):
        # extract-first: выжимка уже сдана, карта пришла по её ростеру. Речевой
        # контекст узлу extract больше не нужен — вместо него строится
        # назначение, а смена состояния кладёт протокол в базу: дом только что
        # стал известен
        questions = rebuild_assignment(run)
        run.set_state("briefed")
        # контракт команды, а не побочный эффект смены состояния: протокол
        # ложится в базу ЗДЕСЬ — дом только что стал известен. set_state выше
        # уже синхронизировал, но фаза не сменилась (briefed → briefed), и
        # полагаться на «sync зовётся и при том же состоянии» нельзя: явный
        # вызов идемпотентен и переживёт любой рефакторинг set_state
        sync_protocol(run)
        pending = pending_quote_flags(run)
        data: Dict[str, Any] = {"units": run.units(),
                                "assignment": len(run.assignment()),
                                "questions": questions}
        if payload.get("reading_sources") or payload.get("counterparties"):
            # молчание здесь читалось бы как «источники учтены» — а выжимка уже
            # сдана, и перечитать контекст ей нельзя: поля работают только в
            # фоллбэке, когда карта идёт до выжимки
            data["note"] = ("reading_sources и counterparties этой карты не "
                            "потребляются: выжимка уже сдана — эти поля "
                            "работают только в фоллбэке (map до выжимки). "
                            "Новые словари важны для чтения этой встречи — "
                            "передай их пути узлу extract напрямую и переподай "
                            "выжимку")
        report = protocol_report(run)
        if report:
            data["protocol"] = report
        return {"state": run.state, "step": run.step,
                "next": ("узел quote-judge судит спорные цитаты → submit quotes"
                         if pending else "render summary → decide --screen summary"),
                "data": data}
    run.set_state("mapped")
    context = build_reading_context(run)
    declared = declared_reading_lines(run)
    if declared["lines"]:
        context["declared"] = declared
    notes: List[str] = []
    if context.get("rejected"):
        # молчание в ответ на «поищи сам» читается как «ищи ещё»: координатор
        # уже нашёл файл, и промах в имени роли обязан быть назван
        notes.append("названные источники не взяты: "
                     + "; ".join(f"{row['file'] or '—'} — {row['why']}"
                                 for row in context["rejected"]))
    if context["bytes"] > READING_CONTEXT_LOUD:
        notes.append(f"речевой контекст велик — {context['bytes'] // 1024} КБ: узел "
                     "прочитает его целиком. Дорого — сузь состав полем "
                     "`reading_sources` карты")
    if context["missing_roles"]:
        # фоллбэк к суждению ровно там, где канон не сработал: файл мог
        # называться иначе или лежать не на месте — это видно глазами, а не
        # правилом, и переподача карты дешевле нового экрана
        notes.append("канон не нашёл в базе: " + ", ".join(context["missing_roles"])
                     + " — поищи эти файлы сам (имя с префиксом, чужая папка, "
                       "другое название) и переподай карту с `reading_sources`; "
                       "не нашёл — так и работаем")
    nudge = "; ".join(notes) + "; " if notes else ""
    return {"state": run.state, "step": run.step, "next": nudge + "submit brief",
            "data": {"units": run.units(), "reading_context": context}}


def submit_brief(run: Run, payload: Any) -> Dict[str, Any]:
    require_state(run, ("ready", "mapped", "briefed"))
    transcript = run.transcript_text()
    violations, flags = V.validate_brief(payload, transcript)
    raise_violations(run, violations, "brief")
    resubmitted = bool(run.load("brief.json"))
    if resubmitted:
        # флаги и вердикты прежней выжимки сняты с текста, которого больше
        # нет, — до сохранения новых, иначе стёрлась бы эта же подача
        drop_brief_quote_flags(run)
    run.store("brief.json", payload)
    lean = write_roster_lean(run)
    added = store_quote_flags(run, flags)
    has_map = bool(run.load("map.json"))
    # без карты назначению не к чему приводить hint'ы — оно строится на
    # `submit map`, когда дома известны (extract-first)
    questions = rebuild_assignment(run) if has_map else []
    # состояние меняется последним: на этой смене ядро кладёт выжимку в базу —
    # уже сейчас, до паузы 1 (в extract-first — на `submit map`, как только
    # прочитан дом протокола). Оборванный дальше разбор оставляет файл встречи
    # на месте, со статусом того этапа, где он встал
    run.set_state("briefed")
    pending = pending_quote_flags(run)
    data: Dict[str, Any] = {"assignment": len(run.assignment()),
                            "questions": questions, "quote_flags": added,
                            "roster_lean": str(lean)}
    if resubmitted and has_map:
        # карта пересчёта не получает: назначение перестроено, но дома и
        # findings остались от прежнего ростера — молчание читалось бы как
        # «карта учла правку»
        data["note"] = ("карта осталась от прежнего ростера — если состав "
                        "сущностей изменился существенно, переподай map по "
                        "artifacts/roster-lean.json")
    report = protocol_report(run)
    if report:
        data["protocol"] = report
    if not has_map:
        if not (run.load("reading-context.json") or {}).get("sources"):
            # выжимка на пустом контексте законна, но молчать о ней нельзя:
            # имена читались без резолверов, и рекомендованный путь был другой
            data["context_note"] = ("речевой контекст базы был пуст — выжимка "
                                    "читала имена без резолверов; штатная "
                                    "рекомендация на такой базе — фоллбэк "
                                    "(map первым, по транскрипту)")
        judge = " · узел quote-judge судит спорные цитаты → submit quotes" \
            if pending else ""
        return {"state": run.state, "step": run.step,
                "next": f"узел map строит карту домов по {lean} → submit map"
                        + judge,
                "data": data}
    return {"state": run.state, "step": run.step,
            "next": ("узел quote-judge судит спорные цитаты → submit quotes"
                     if pending else "render summary → decide --screen summary"),
            "data": data}


def rebuild_assignment(run: Run) -> List[Dict[str, Any]]:
    """Артефакт eid → юнит: hint выжимки приводится к дому карты.

    Правка пользователя (поле `unit` поверх ростера) сильнее hint выжимки.
    Узел называет раздел (`dev/gateway`) чаще, чем юнит; нормализация видна в
    `source`. Место, которого в карте нет, и сущность без места — вопрос
    пользователю, а не молчаливый дефолт.
    """
    units = run.units()
    # перевод свободных hint'ов («инженерия» → dev) даёт карта: extract домов
    # базы не видит и пишет hint человеческим именем, а не путём
    hint_map = {V.normalize_line(str(k)): str(v)
                for k, v in ((run.load("map.json") or {}).get("hint_map") or {}).items()
                if str(v) in units}
    questions: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    default = units[0] if units else ""
    for item in run.roster():
        eid = str(item.get("eid", ""))
        edited = str(item.get("unit") or "")
        hint = edited or str(item.get("unit_hint") or "")
        unit = (hint if hint in units
                else unit_of_file(hint, units)
                or hint_map.get(V.normalize_line(hint))) if hint else None
        source = ("edit" if edited else
                  "hint" if unit == hint else ("normalized" if unit else "default"))
        if unit is None:
            unit = default
            title = str(item.get("title") or "").strip()
            named = f"«{title}»" if title else f"сущность {eid}"
            message = (f"{named}: место {hint!r} в базе не найдено — "
                       f"запись пойдёт в {unit!r}" if hint else
                       f"{named}: место не названо — запись пойдёт в {unit!r}, "
                       f"поправьте, если дом другой")
            questions.append({"kind": "unknown_place", "eid": eid,
                              "title": title or None, "message": message})
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

#: Канонический узел компании: § «Корень scaffold». Держится в коде по той же
#: причине, что имена kit-файлов, — это канон, а не догадка о конкретной базе.
COMPANY_UNIT = "01_company"

#: Холодный архив рядом с протоколом: сюда едет копия транскрипта. Имя то же,
#: что у служебного дерева базы (`SKIP_DIRS`), — сырьё карты его не увидит, и
#: транскрипт не станет фоном следующего разбора.
PROTOCOL_ARCHIVE = "zz_archive"


def meeting_topic(run: Run) -> str:
    """Тема встречи из выжимки — вторая половина имени файла протокола."""
    brief = run.load("brief.json") or {}
    return str((brief.get("meeting") or {}).get("topic") or "").strip()


def rule_dir_of(run: Run, named: str, quote: str) -> Optional[str]:
    """Каталог, который улика правила называет: сам дом или папка над ним.

    База часто называет правилом общий каталог протоколов, а раскладку внутри
    него ведёт «Маршрутами записи» того же README — параметрически («okr-N/»,
    «one-to-one/<фамилия>/»). Дословной строки под конкретную подпапку в базе
    нет и быть не может, а протокол ей всё равно принадлежит: закрытого списка
    имён в коде тем более быть не может — какие подпапки существуют, знает
    README базы, а не продукт.

    Нотариус от этого не слабеет: улика обязана назвать СУЩЕСТВУЮЩИЙ каталог
    целиком, как и раньше, — просто им может оказаться родитель дома. Разница
    между «улика назвала дом» и «улика назвала родителя» не теряется: во втором
    случае дом выбрал узел, и адрес показывается человеку до записи.
    """
    candidate = named
    while candidate:
        if base_dir_exists(run, candidate) and V.mentions_path(quote, candidate):
            return candidate
        if "/" not in candidate:
            return None
        candidate = candidate.rsplit("/", 1)[0]
    return None


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
        "rule_dir": None,
        "inferred": False,
        "source": ("edit" if edited else "map" if named else None),
        "evidence": None if edited else evidence,
        "verified": False,
        "issue": None,
    }
    if not named:
        row["issue"] = ("в базе не нашлось правила о том, где хранить протоколы "
                        "встреч — назовите каталог сами либо запишите правило "
                        "в README базы")
        return row
    if not base_dir_exists(run, named):
        row["issue"] = (f"каталога протоколов {named!r} в базе нет либо он "
                        "служебный — назовите существующий")
        return row
    quote = str((evidence or {}).get("quote") or "").strip()
    source_file = str((evidence or {}).get("file") or "").strip()
    if edited:
        # адрес назвал человек — улики он не требует; но если карта успела
        # подтвердить каталог правила, архив транскрипта остаётся при нём:
        # человек уточняет подпапку, а не переносит архив внутрь неё
        confirmed = None
        if quote and source_file and V.contains_fragment(run.read_base(source_file) or "", quote):
            confirmed = rule_dir_of(run, named, quote)
        row["rule_dir"] = confirmed or named
        row["verified"] = True
        return row
    if not quote or not source_file:
        row["issue"] = (f"каталог протоколов {named!r} назван без опоры: не указан "
                        "файл базы и строка, из которой это правило прочитано")
        return row
    if not V.contains_fragment(run.read_base(source_file) or "", quote):
        row["issue"] = (f"опора не подтвердилась: строки {quote!r} в {source_file} "
                        "нет — подтвердите каталог протоколов сами")
        return row
    confirmed = rule_dir_of(run, named, quote)
    if confirmed is None:
        # улика обязана подтверждать ДОМ, а не собственное существование:
        # настоящая строка правила, названная при чужом каталоге, проходила обе
        # прежние проверки — и протокол уезжал в чужой юнит (круг ревью, Н1)
        row["issue"] = (f"строка {quote!r} из {source_file} говорит о другом месте, "
                        f"не о каталоге {named!r} и не о том, внутри которого он "
                        "лежит — подтвердите каталог протоколов сами")
        return row
    row["rule_dir"] = confirmed
    row["inferred"] = confirmed != named
    row["verified"] = True
    return row


#: Роли канона scaffold, которыми читается РЕЧЬ встречи. Имена не догадка
#: скилла: `speech-aliases.md` заведён каноном ровно ради разбора встреч
#: («чтобы AI правильно разбирал встречи» — миссия файла в шаблоне), `glossary`
#: и `profile` объявлены § «Типовые смысловые файлы», `org-structure` —
#: канонический файл ракурса team. Знать их — то же чтение канона, каким скилл
#: уже знает имена kit-файлов и служебных папок.
#:
#: `full` — файл целиком: у словаря нет другого потребителя, кроме чтения речи.
#: `head` — преамбула до первого `##`: кто это, одной шапкой. Именованные
#: секции кодом не режутся: живая база уже зовёт «Термины» там, где v1 искал
#: «Термины и сокращения», и точечный парсинг тихо даёт пусто.
READING_ROLES: Dict[str, str] = {
    "speech-aliases": "full",
    "glossary": "full",
    "org-structure": "full",
    "profile": "head",
    "company": "head",
}

#: Роли, которых база держит по одной на дом: их отсутствие — повод поискать
#: глазами. Профиль и досье в этот список не входят — они срез узла, а не
#: словарь базы.
BASE_READING_ROLES = {"speech-aliases", "glossary", "org-structure"}

#: Числовой префикс имени роли не меняет: `01_org-structure.md` — та же роль.
ROLE_PREFIX = re.compile(r"^\d+[_-]")

#: Секция README, которой база вправе назвать свои источники чтения речи.
#: Канон README её не требует (пять его блоков — другие), поэтому это opt-in
#: поверх канонического дефолта, а не условие работы.
READING_CONTEXT_SECTION = "Контекст перед разбором"


def role_of_file(name: str) -> Optional[str]:
    stem = ROLE_PREFIX.sub("", name.rsplit("/", 1)[-1])
    stem = stem[:-3] if stem.lower().endswith(".md") else stem
    return stem if stem in READING_ROLES else None


#: Потолок преамбулы. Срез до первого `##` предполагает, что заголовок близко;
#: файл без заголовков вовсе отдал бы себя целиком — а профиль пользователя
#: бывает и на десяток килобайт. Это предохранитель формы, а не фильтр смысла.
HEAD_LIMIT = 4000


def head_slice(body: str) -> str:
    """Преамбула файла: всё до первого `##`, но не длиннее потолка.

    Тот же срез, что v1 делал `awk` руками координатора, — только его делает
    код до вызова модели: глубокие разделы профиля (стиль работы, зоны
    развития, коучинг-лог) не попадают ни в выжимку, ни в контекст координатора.
    """
    out: List[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            break
        out.append(line)
    text = "\n".join(out).strip()
    if len(text) <= HEAD_LIMIT:
        return text
    return text[:HEAD_LIMIT].rstrip() + "\n\n*(шапка длинная — показано начало)*"


#: Порог нормализации словарного файла роли `full`. Раздувает словарь не число
#: записей, а журнал внутри них: даты подтверждений встреч, кейсы, мини-досье
#: в ячейках (живые базы: 160–286 КБ при речевом ядре в единицы КБ; канонный
#: шаблон — строка на человека). Нормализация сохраняет каждую строку-запись и
#: режет только её хвост. Это правило формы, а не имён секций: точечный парсинг
#: заголовков v1 тихо давал пусто, сюда он не возвращается.
ROLE_FULL_LIMIT = 32_000
#: Потолок хвоста записи — ячейки таблицы и прозаической строки. Канон и
#: варианты живут в начале записи; длинный хвост — журнал подтверждений.
#: Замер на живом словаре 280 КБ: масса байтов лежит в записях 100–400
#: символов, потолок выше 120 нормализацию выхолащивает.
CELL_LIMIT = 120
LINE_LIMIT = 120


#: Минимум, ниже которого предложение не считается ядром записи: защита от
#: обрезки по инициалу («Т. Иванов») и по аббревиатуре в самом начале.
TRIM_FLOOR = 40


def _trim_tail(text: str, limit: int) -> str:
    """Запись длиннее потолка режется до ПЕРВОГО предложения: канон словарной
    записи — «кто/что это», первым предложением; дальше идёт журнал."""
    text = text.strip()
    if len(text) <= limit:
        return text
    for sep in (". ", "; "):
        pos = text.find(sep, TRIM_FLOOR, limit)
        if pos != -1:
            return text[:pos + 1].rstrip() + " …"
    return text[:limit].rstrip() + " …"


def normalize_slice(body: str, rel: str) -> str:
    """Словарь больше порога: каждая запись остаётся, хвосты усечены.

    Таблица не теряет ни строки — усечены ячейки; прозаическая строка режется
    до предложения в пределах потолка. Заголовки, разделители и короткие строки
    проходят как есть. Полный файл остаётся в базе и назван в пометке — узел
    видит, что читает срез, а не весь словарь.
    """
    raw = body.strip()
    if raw.startswith("*(словарь нормализован кодом"):
        # вход всегда сырой файл базы; guard делает повторный вызов
        # безвредным (f(f(x)) = f(x)) вместо порчи собственной пометки
        return raw
    raw_bytes = len(raw.encode("utf-8"))
    if raw_bytes <= ROLE_FULL_LIMIT:
        return raw
    out: List[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and not set(stripped) <= {"|", "-", ":", " "}:
            indent = line[:len(line) - len(line.lstrip())]
            cells = stripped.strip("|").split("|")
            out.append(indent + "| "
                       + " | ".join(_trim_tail(c, CELL_LIMIT) for c in cells) + " |")
        elif len(stripped) > LINE_LIMIT and not stripped.startswith("#"):
            indent = line[:len(line) - len(line.lstrip())]
            out.append(indent + _trim_tail(stripped, LINE_LIMIT))
        else:
            out.append(line)
    text = "\n".join(out).strip()
    note = (f"*(словарь нормализован кодом: {raw_bytes // 1024} КБ → "
            f"{len(text.encode('utf-8')) // 1024} КБ; длинные ячейки и абзацы "
            f"усечены, записи сохранены все; полный файл — {rel})*")
    return note + "\n\n" + text


def home_area(run: Run, rel: str) -> str:
    """Каталог дома: у юнита-файла свои соседи живут в его папке.

    Дом бывает и md-файлом (`clients/acme.md`), и папкой. Профиль и досье
    ищутся рядом с домом, поэтому область считается по каталогу — иначе дом-файл
    не получил бы собственной шапки.
    """
    parts = [part for part in str(rel).split("/") if part]
    try:
        if parts and run.base_file(rel).is_file():
            parts = parts[:-1]
    except SpineError:
        return ""
    return "/".join(parts)


def reading_areas(run: Run) -> List[str]:
    """Где ищутся источники чтения речи: корень, компания, дома встречи и их
    предки. Вся остальная база не читается — десять глоссариев несвязанных
    направлений к этой встрече отношения не имеют, а фильтр здесь — карта,
    которая уже сдана."""
    areas: List[str] = ["."]
    if base_dir_exists(run, COMPANY_UNIT):
        areas.append(COMPANY_UNIT)
    named = list(run.units()) + counterparties(run)
    for rel in named:
        parts = [part for part in home_area(run, rel).split("/") if part]
        for depth in range(1, len(parts) + 1):
            areas.append("/".join(parts[:depth]))
    ordered: List[str] = []
    for area in areas:
        if area not in ordered:
            ordered.append(area)
    return ordered


def counterparties(run: Run, rejected: Optional[List[Dict[str, str]]] = None
                   ) -> List[str]:
    """Досье, названные картой ради ЧТЕНИЯ речи.

    Отдельно от `units`, потому что вопросы разные: `units` — чей это разговор
    и куда писать; `counterparties` — чья речь звучит. Внутренний разбор про
    клиента пишет в свои юниты, а имена и язык читает из его досье.
    """
    payload = run.load("map.json") or {}
    out: List[str] = []
    for rel in payload.get("counterparties", []) or []:
        name = str(rel).strip().strip("/")
        if not name:
            continue
        if not unit_exists(run, name):
            if rejected is not None:
                rejected.append({"file": name,
                                 "why": "досье не найдено: такого места в базе нет "
                                        "либо оно служебное"})
            continue
        if name not in out:
            out.append(name)
    return out


def declared_sources(run: Run, rejected: Optional[List[Dict[str, str]]] = None
                     ) -> List[Dict[str, str]]:
    """Источники, названные картой руками: база отклонилась от канона.

    Фоллбэк к суждению там, где дефолт не сработал: файл лежит не в
    каноническом месте, зовётся иначе, живёт в чужой папке. Область здесь не
    проверяется — в том и смысл, — но границы базы, служебные каталоги и записи
    встреч закрыты так же, как везде.
    """
    payload = run.load("map.json") or {}
    out: List[Dict[str, str]] = []
    drop = rejected if rejected is not None else []
    for row in payload.get("reading_sources", []) or []:
        if not isinstance(row, dict):
            drop.append({"file": "", "why": "источник описывается объектом {file, role}"})
            continue
        rel = str(row.get("file") or "").strip()
        role = str(row.get("role") or "").strip() or role_of_file(rel) or "glossary"
        if not rel:
            drop.append({"file": "", "why": "имя файла не названо"})
            continue
        if role not in READING_ROLES:
            drop.append({"file": rel, "why": f"роль {role!r} неизвестна — допустимы "
                                             f"{sorted(READING_ROLES)}"})
            continue
        try:
            path = run.base_file(rel)
        except SpineError:
            drop.append({"file": rel, "why": "путь выходит за пределы базы"})
            continue
        if not path.is_file():
            drop.append({"file": rel, "why": "файла нет по этому пути"})
            continue
        if path.is_symlink():
            drop.append({"file": rel, "why": "символическая ссылка не читается"})
            continue
        if is_historic_record(rel):
            drop.append({"file": rel, "why": "это запись встречи, а не словарь базы"})
            continue
        if service_parts(tuple(rel.split("/"))):
            drop.append({"file": rel, "why": "служебный каталог базы"})
            continue
        out.append({"file": rel, "role": role})
    return out


def area_files(run: Run, area: str) -> List[str]:
    """Md-файлы каталога — с живого диска, а не из снимка старта.

    Снимок `base-raw.json` заморожен на `check`, а между ним и картой проходит
    вызов модели: в длинной сессии и на синхронизируемой папке файл успевает
    появиться. Каталогов здесь единицы, обхода дерева нет — цена нулевая.
    """
    try:
        path = run.base_file(area) if area != "." else run.base
    except SpineError:
        return []
    if not path.is_dir():
        return []
    try:
        return sorted(entry.name for entry in os.scandir(path)
                      if entry.is_file(follow_symlinks=False)
                      and entry.name.lower().endswith(".md"))
    except OSError:
        return []


def collect_reading_sources(run: Run, rejected: Optional[List[Dict[str, str]]] = None
                           ) -> List[Dict[str, str]]:
    """Канонический дефолт плюс названное картой, в порядке близости к встрече."""
    found: List[Dict[str, str]] = []
    seen: Set[str] = set()
    homes = {home_area(run, rel) for rel in list(run.units()) + counterparties(run)}
    # дом, названный md-файлом, — сам себе шапка: соседей по имени у него нет
    for rel in counterparties(run) + list(run.units()):
        try:
            if run.base_file(rel).is_file() and rel not in seen:
                seen.add(rel)
                found.append({"file": rel, "role": "profile", "source": "canon"})
        except SpineError:
            continue
    for area in reading_areas(run):
        # ракурс team живёт подпапкой узла: оргструктура канонически там
        for directory in (area, f"{area}/02_team" if area != "." else "02_team"):
            for name in area_files(run, directory):
                role = role_of_file(name)
                if role is None:
                    continue
                # профиль и досье читаются только у названных домов: чужая
                # шапка к чтению этой речи отношения не имеет
                if READING_ROLES[role] == "head" and area not in homes:
                    continue
                rel = name if directory == "." else f"{directory}/{name}"
                if rel not in seen:
                    seen.add(rel)
                    found.append({"file": rel, "role": role, "source": "canon"})
    for row in declared_sources(run, rejected):
        if row["file"] not in seen:
            seen.add(row["file"])
            found.append({**row, "source": "declared"})
    return found


def build_reading_context(run: Run) -> Dict[str, Any]:
    """Речевой контекст собирает КОД — и кладёт его файлом рядом с прогоном.

    Узел extract читает транскрипт без базы, и это защита: фон, поданный
    содержанием, протекает в выжимку. Но резолв имён, ASR-ошибок и жаргона
    фоном не является — без него выжимка врёт в именах, а ошибка расходится по
    всему конвейеру: владелец, профиль, маршрут.

    Прошлая версия спрашивала базу, что читать, секцией, которой канон README
    не знает: на каждой развёрнутой базе это давало пусто. Здесь состав решает
    канон, область — карта, а суждение остаётся ровно там, где канон молчит:
    база отклонилась — карта называет свои файлы (`reading_sources`).

    Координатор получает ПУТЬ артефакта, а не текст: большой глоссарий в его
    сессии — тот же класс дефекта, что прочитанный им транскрипт.
    """
    rejected: List[Dict[str, str]] = []
    counterparties(run, rejected)
    sources = collect_reading_sources(run, rejected)
    blocks: List[str] = ["# Речевой контекст встречи", "",
                         "Резолверы «кто и что»: имена, роли, термины, варианты "
                         "произношения. Источником содержания выжимки не является.", ""]
    hint = run.manifest.get("meeting_hint") or {}
    if hint:
        blocks += ["## О встрече со слов пользователя", ""]
        blocks += [f"- {name}: {value}" for name, value in hint.items() if value]
        blocks.append("")
    used: List[Dict[str, Any]] = []
    for row in sources:
        body = run.read_base(row["file"])
        if body is None:
            # файл есть, а прочитать нечем: чужая кодировка или права. Молчание
            # здесь означало бы «словаря в базе нет», а он есть и не работает
            rejected.append({"file": row["file"],
                             "why": "файл не читается: не UTF-8 либо нет прав"})
            continue
        if READING_ROLES[row["role"]] == "head":
            text = head_slice(body)
        else:
            text = normalize_slice(body, row["file"])
        if not text:
            continue
        blocks += ["---", "", f"## Источник: {row['file']} · роль: {row['role']}",
                   "", text, ""]
        entry = {**row, "bytes": len(text.encode("utf-8"))}
        raw_bytes = len(body.strip().encode("utf-8"))
        if entry["bytes"] < raw_bytes:
            entry["raw_bytes"] = raw_bytes
        used.append(entry)
    path = run.artifact("reading-context.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(blocks).rstrip() + "\n"
    atomic_write(path, text)
    # спрашивается только то, что база держит для чтения речи как таковой:
    # профиль и досье — срез конкретного узла, их отсутствие означает лишь, что
    # узел не развёрнут, и посылать координатора искать их по базе незачем
    missing = sorted(BASE_READING_ROLES - {row["role"] for row in used})
    report = {"file": str(path), "sources": used, "missing_roles": missing,
              "areas": reading_areas(run), "bytes": len(text.encode("utf-8"))}
    if rejected:
        report["rejected"] = rejected
    return report


#: Порог, после которого о размере контекста говорят вслух. Нормализация выше
#: уже срезала журнальные хвосты словарей; контекст всё ещё велик — значит,
#: велико само число записей, и решение о сужении состава остаётся карте и
#: человеку, а не машинному ножу.
READING_CONTEXT_LOUD = 120_000


def declared_reading_lines(run: Run) -> Dict[str, Any]:
    """Объявление базы, если она его завела: opt-in поверх канона."""
    home = protocol_home(run)
    for directory in (str(home.get("rule_dir") or ""), ""):
        rel = f"{directory}/README.md" if directory else "README.md"
        body = run.read_base(rel)
        if not body:
            continue
        found = readme_sections(body, (READING_CONTEXT_SECTION,))
        if found.get(READING_CONTEXT_SECTION):
            return {"source": rel, "lines": found[READING_CONTEXT_SECTION]}
    return {"source": None, "lines": []}


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
    # Архив сырья висит при каталоге ПРАВИЛА, а не при выбранной подпапке:
    # база держит один архив транскриптов на весь каталог протоколов, и
    # `zz_archive` в каждой тематической подпапке — новая папка в чужой
    # структуре, которой разбор заводить не вправе.
    archive_root = str(home.get("rule_dir") or home["dir"])
    return {"dir": str(home["dir"]),
            "rule_dir": archive_root,
            "summary": f"{home['dir']}/{stem}_summary.md",
            "transcript": f"{archive_root}/{PROTOCOL_ARCHIVE}/{stem}_transcript.md"}


def protocol_absence(run: Run) -> Optional[Dict[str, Any]]:
    """Почему протокола в базе НЕ будет — именованным полем и человеческим текстом.

    Дом не подтверждён — адреса нет, и выжимка в базу не ложится вовсе.
    Молчание тут не видит никто: шаг тихо не случается, и
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
    titles = roster_titles(run)
    for eid in sorted(fabricated_eids(run)):
        title = titles.get(eid, "")
        named = f"«{title}»" if title else f"сущность {eid}"
        out.append({"kind": "quote_fabricated", "eid": eid,
                    "title": title or None,
                    "message": f"{named}: цитата, на которой стоит эта запись, "
                               "не подтвердилась — такой фразы на встрече "
                               "не прозвучало"})
    home = protocol_home(run)
    if home["issue"]:
        out.append({"kind": "protocol_home", "message": home["issue"]})
    elif home.get("inferred"):
        # дом внутри каталога правила выбрал узел, а не улика: человек видит
        # адрес до записи и вправе назвать другой. Без правки подтверждение
        # экрана означает согласие — лишнего цикла это не стоит
        targets = protocol_targets(run)
        where = (targets or {}).get("summary") or f"{home['dir']}/…"
        out.append({"kind": "protocol_home",
                    "message": f"протокол встречи ляжет в {where} — подпапку выбрал "
                               f"разбор по маршрутам записи каталога "
                               f"{home['rule_dir']!r}; подтвердите или назовите "
                               "другой каталог"})
    out.extend(open_escalations(run))
    return out


def open_escalations(run: Run) -> List[Dict[str, Any]]:
    """Эскалации «узел не исправил со второй попытки» доезжают до экранов,
    а не остаются строкой events.jsonl, которую никто не читает."""
    titles = roster_titles(run)
    out: List[Dict[str, Any]] = []
    for event in run.events():
        if event.get("event") != "question":
            continue
        eid = str(event.get("eid") or "")
        title = titles.get(eid, "")
        message = str(event.get("message") or "")
        if title:
            message = f"«{title}»: {message}"
        out.append({"kind": "node_escalation", "eid": eid or None,
                    "title": title or None, "message": message,
                    "code": event.get("code")})
    return out


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
            # метаданные и нарратив — тело протокола: они подписываются вместе
            # с ростером, иначе человек подтверждает не тот файл, который ляжет
            # в базу (тот же закон, что у дома протокола)
            "meeting": brief.get("meeting") or {},
            "protocol": {key: home[key]
                         for key in ("dir", "source", "evidence", "verified")},
            "meeting_questions": groups["meeting_questions"],
            "map_findings": groups["map_findings"],
            "ambiguities": groups["ambiguities"],
            "roster_counts": roster_counts(run),
            "roster": roster}


#: Тяжёлые части метаданных: нарратив на три абзаца и ключевые цитаты — тело
#: файла, а не экран. В коротком показе они превратили бы «короткий экран» в
#: чтение вслух того, что человек и так откроет в базе.
SUMMARY_HEAVY = ("narrative", "key_quotes")


def summary_view(run: Run, full: bool) -> Dict[str, Any]:
    """Показ паузы 1: полный — ровно подписанное состояние, короткий — оно же
    без построчного ростера (его место занимают счётчики) и без тяжёлых частей
    метаданных. Подпись считается от полного состояния в обеих формах."""
    state = summary_state(run)
    if full:
        return state
    short = {k: v for k, v in state.items() if k != "roster"}
    meeting = short.get("meeting")
    if isinstance(meeting, dict):
        short["meeting"] = {k: v for k, v in meeting.items() if k not in SUMMARY_HEAVY}
    return short


def render_summary(run: Run, full: bool) -> Dict[str, Any]:
    require_state(run, ("briefed", "confirmed"))
    if not run.load("map.json"):
        raise SpineError(
            "map_missing",
            "карты ещё нет — пауза 1 без домов, находок и назначения не собирается",
            hint="узел map строит карту по artifacts/roster-lean.json → submit map")
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
    titles = roster_titles(run)
    units = run.units()
    edits: List[Tuple[str, Dict[str, Any]]] = []
    for edit in payload.get("edits", []) or []:
        eid = str(edit.get("eid", ""))
        if eid not in known:
            raise SpineError("bad_usage", f"правка неизвестной записи {eid}", field="edits")
        fields = {k: v for k, v in edit.items()
                  if k in ("title", "type", "modality", "owner", "due", "unit") and v}
        unit_value = str(fields.get("unit") or "")
        if unit_value and unit_value not in units \
                and not unit_of_file(unit_value, units):
            # отказ здесь, а не вопрос после подтверждения: вопрос, рождённый
            # после экрана, никто не увидит (kimi m10)
            named = titles.get(eid) or eid
            raise SpineError("unknown_unit",
                             f"правка «{named}»: места {unit_value!r} в базе нет",
                             field="edits",
                             hint=f"места этой встречи: {units}")
        edits.append((eid, fields))
    removals: List[Tuple[str, str]] = []
    for row in payload.get("withdraw", []) or []:
        eid = str(row.get("eid", ""))
        if eid not in known:
            raise SpineError("bad_usage", f"снятие неизвестной записи {eid}", field="withdraw")
        reason = (row.get("reason") or "").strip()
        if not reason:
            raise SpineError("bad_usage",
                             f"снятие «{titles.get(eid) or eid}» без причины",
                             field="withdraw",
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
    lexicon, lexicon_skipped = check_lexicon(run, payload.get("lexicon") or [], known)
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
    if lexicon:
        stored = (run.load("lexicon.json") or {}).get("entries", [])
        run.store("lexicon.json", {"entries": stored + lexicon})
        for row in lexicon:
            run.journal("user_correction", eid=row.get("eid"), heard=row["heard"],
                        canonical=row["canonical"], kind=row["kind"], file=row["file"])
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
    data: Dict[str, Any] = {
        "units": assigned_units(run),
        "contexts": {unit: str(run.artifact(f"context/{run.unit_key(unit)}.json"))
                     for unit in assigned_units(run)}}
    # человека спросили «разовая правка или так теперь и писать» — он обязан
    # узнать, что стало с его ответом: молчание здесь читается как «принято»
    if lexicon or lexicon_skipped:
        data["lexicon"] = {"accepted": [{"was": row["heard"], "now": row["canonical"],
                                         "file": row["file"]} for row in lexicon],
                           "skipped": lexicon_skipped}
    # выжимка в базе переписана подтверждённой: правки паузы 1 и ответы на
    # «Требует уточнения» доехали до файла, который читают вместо транскрипта
    report = protocol_report(run)
    if report:
        data["protocol"] = report
    return {"state": run.state, "step": run.step,
            "next": "редакторы юнитов → submit operations --unit …; "
                    "затем контролёры → submit verdicts --unit …",
            "data": data}


#: Куда ложится устойчивая поправка пользователя: имя и произношение — в
#: словарь речи, понятие — в глоссарий. Оба файла объявлены каноном scaffold.
LEXICON_ROLES = {"speech_alias": "speech-aliases", "term": "glossary"}


def lexicon_target(run: Run, unit: str, role: str) -> str:
    """Ближайший существующий словарь: юнит → его предки → компания → корень.

    Словаря нет нигде — адресом становится канонический файл в юните: пункт
    экрана покажет его создание, и без принятия человеком файл не появится.
    """
    parts = [part for part in unit.split("/") if part]
    chain = ["/".join(parts[:depth]) for depth in range(len(parts), 0, -1)]
    for area in chain + [COMPANY_UNIT, ""]:
        rel = f"{area}/{role}.md" if area else f"{role}.md"
        try:
            if run.base_file(rel).is_file():
                return rel
        except SpineError:
            continue
    home = home_area(run, unit)
    return f"{home}/{role}.md" if home else f"{role}.md"


def check_lexicon(run: Run, rows: Any, known: Set[str]
                  ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Устойчивая поправка вычитки: «слышится X → писать Y».

    Разовую правку от устойчивой отличает не вопрос и не догадка кода, а сам
    факт подачи: `edits` чинит только эту выжимку, `lexicon` говорит «сохранить
    на будущее». Записью это станет на экране решений, не здесь.
    """
    out: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    if not isinstance(rows, list):
        raise SpineError("bad_usage", "lexicon — список поправок", field="lexicon")
    assignment = run.assignment()
    units = run.units()
    # ключ нормализованный: «Ерик → Эрик» и «ерик → эрик» — одна поправка, и
    # две одинаковые пары в пакете не должны дать двух одинаковых записей
    stored = (run.load("lexicon.json") or {}).get("entries", [])
    seen = {(V.normalize_line(row["heard"]), V.normalize_line(row["canonical"]))
            for row in stored}
    for row in rows:
        if not isinstance(row, dict):
            raise SpineError("bad_usage", "поправка словаря — объект", field="lexicon")
        heard = str(row.get("heard") or "").strip()
        canonical = str(row.get("canonical") or "").strip()
        kind = str(row.get("kind") or "speech_alias")
        eid = str(row.get("eid") or "")
        if not heard or not canonical or heard == canonical:
            raise SpineError("bad_usage",
                             "поправка словаря — пара «как слышится» → «как писать»",
                             field="lexicon",
                             hint='{"heard": "Ерик", "canonical": "Эрик", '
                                  '"kind": "speech_alias"}')
        if kind not in LEXICON_ROLES:
            raise SpineError("bad_usage", f"неизвестный вид поправки {kind!r}",
                             field="lexicon", hint=f"допустимо: {sorted(LEXICON_ROLES)}")
        if eid and eid not in known:
            raise SpineError("bad_usage", f"поправка ссылается на неизвестную сущность {eid}",
                             field="lexicon")
        unit = str(row.get("unit") or "").strip() or assignment.get(eid) or (
            units[0] if units else "")
        if unit and unit not in units and not unit_of_file(unit, units):
            raise SpineError("unknown_unit", f"поправка словаря: юнита {unit!r} нет в карте",
                             field="lexicon", hint=f"юниты карты: {units}")
        target = lexicon_target(run, unit, LEXICON_ROLES[kind])
        body = run.read_base(target) or ""
        if any(V.contains_fragment(line, canonical) and V.contains_fragment(line, heard)
               for line in body.splitlines()):
            # пара уже стоит в словаре одной строкой — предлагать её незачем.
            # Врозь эти слова ничего не значат: «Эрик» автором строки и «Ерик»
            # в чужом пункте — не запись о том, что одно читается как другое
            skipped.append({"heard": heard, "canonical": canonical, "file": target,
                            "why": "пара уже стоит в словаре"})
            continue
        key = (V.normalize_line(heard), V.normalize_line(canonical))
        if key in seen:
            skipped.append({"heard": heard, "canonical": canonical, "file": target,
                            "why": "такая пара уже принята в этом разборе"})
            continue
        seen.add(key)
        out.append({"eid": eid or None, "heard": heard, "canonical": canonical,
                    "kind": kind, "unit": unit, "file": target,
                    "exists": bool(body)})
    return out, skipped


def lexicon_items(run: Run, start: int) -> List[Dict[str, Any]]:
    """Пункты экрана решений из поправок вычитки — их строит код.

    Через редакторов юнитов этот путь не проходит по построению: словарь речи
    обычно лежит вне домов встречи, а операции заперты в своём юните. Iron Law
    соблюдён — запись всё равно делает applier после экрана.
    """
    entries = (run.load("lexicon.json") or {}).get("entries", [])
    items: List[Dict[str, Any]] = []
    for offset, row in enumerate(entries, start=1):
        text = (f"| {row['canonical']} | {row['heard']} |  |" if row["kind"] == "speech_alias"
                else f"- **{row['canonical']}** — в речи: {row['heard']}")
        doubt = ("словарь речи ещё не развёрнут — принятие создаст файл"
                 if not row["exists"] else
                 "поправка вычитки: сохранить на будущее или это разовая правка?")
        items.append({"n": start + offset - 1, "eid": f"LEX{offset:02d}",
                      "about": row.get("eid"),
                      "unit": row["unit"], "op": "new", "file": row["file"],
                      "text": text, "title": f"{row['heard']} → {row['canonical']}",
                      "owner": None, "due": None,
                      "kind": "lexicon", "was": row["heard"], "now": row["canonical"],
                      "section": "doubtful", "doubts": [doubt]})
    return items


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
    # записи встреч сюда не доходят вовсе — `unit_files` их не отдаёт: они
    # исторический слой, и собственная выжимка этого прогона не должна
    # возвращаться редактору уликой дубля
    rest = sorted((rel for rel in files if rel not in set(core)),
                  key=lambda rel: -freshness(rel))
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
    # переподача начинается с гашения флагов прежнего пакета: суд над фразой,
    # которой в новом тексте нет, экран держать не должен
    if run.operations(unit) is not None:
        drop_unit_quote_flags(run, unit)
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
        + check_base_quotes(run, unit, payload) \
        + check_replace_anchors(run, payload)
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
def drop_unit_quote_flags(run: Run, unit: str) -> None:
    """Флаги цитат прежнего пакета юнита: они сняты с текста, которого больше нет.

    Зовётся ДО разбора нового пакета — иначе стёрлись бы флаги этой же подачи.
    Оставленные, старые флаги держат экран в ожидании суда над исчезнувшей
    фразой и делают спорным пункт, переписанный начисто.
    """
    flags = run.load("quote-flags.json")
    dropped = []
    if flags:
        kept = [row for row in flags.get("flags", [])
                if not (row.get("stage") == "operations" and row.get("unit") == unit)]
        dropped = [row.get("quote") for row in flags.get("flags", []) if row not in kept]
        if len(kept) != len(flags.get("flags", [])):
            run.store("quote-flags.json", {"flags": kept})
            run.event("quote_flags_dropped", unit=unit)
    # вердикт судьи снят с фразы прежнего текста: оставленный, он держит пункт
    # спорным по цитате, которой в новом тексте больше нет
    verdicts = run.load("quote-verdicts.json")
    if not verdicts or not dropped:
        return
    live = [row for row in verdicts.get("quotes", [])
            if row.get("quote") not in dropped]
    if len(live) != len(verdicts.get("quotes", [])):
        run.store("quote-verdicts.json", {"quotes": live})
        run.event("quote_verdicts_dropped", unit=unit)


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


def under_dir(rel: str, directory: str) -> bool:
    """Путь лежит в каталоге (или это он сам). Сравниваются сегменты, не строки."""
    if not directory or not rel:
        return False
    directory = directory.rstrip("/")
    return rel == directory or rel.startswith(directory + "/")


def address_violations(run: Run, rel: Optional[str], op_kind: str,
                       field: str, eid: str, anchor: str = "") -> List[V.Violation]:
    """Что нельзя писать по этому адресу — в одном месте на весь пайплайн.

    Адрес приходит тремя путями: `target` операции, её `projections[]` и подмена
    при переезде записи в другой дом. Правило, написанное только для первого,
    обходится двумя остальными — так и случилось с журналом решений, пока
    проверка стояла в цикле операций.
    """
    out: List[V.Violation] = []
    if not rel:
        return out
    # `new` с якорем законен ровно в журнале решений: новая запись называет
    # прежнее решение, которое отменяет, — по нему applier ставит пометку
    # `Superseded`. Везде ещё якорь у `new` означал бы «сотри вот это»
    if op_kind == "new" and anchor and not is_decision_log(rel):
        out.append(V.Violation(
            "schema_invalid", "у операции new стоит якорь записи",
            field=field, eid=eid,
            hint="replaces называет существующую запись; у new он законен только в "
                 "журнале решений, где новая запись помечает прежнюю Superseded"))
    if op_kind in V.ANCHORED_OPS and is_decision_log(rel):
        out.append(V.Violation(
            "decision_log_append_only",
            f"{rel} — журнал решений, правка прежней записи там запрещена каноном панели",
            field=field, eid=eid,
            hint="принятое решение не переписывается и не снимается: пересмотр — "
                 "новая запись (op: new) со ссылкой на прежнюю; пометку Superseded "
                 "к старой записи applier поставит сам как часть новой"))
    # правка существующей записи в файле, которого нет: заменять и снимать там
    # нечего. `new` в новый файл законен — он его и создаёт
    if op_kind in V.ANCHORED_OPS and run.read_base(rel) is None:
        try:
            exists = run.base_file(rel).exists()
        except SpineError:
            exists = False
        if not exists:
            out.append(V.Violation(
                "target_absent",
                f"{rel} в базе нет, а операция {op_kind} правит существующую запись",
                field=field, eid=eid,
                hint="проверь путь по фактическому дереву: файл мог называться иначе. "
                     "Записи там правда ещё нет — это op: new"))
    return out


def base_relative_hits(run: Run, rel: str, units: Sequence[str]) -> List[str]:
    """Полные адреса, которыми этот путь становится, если он отсчитан от юнита.

    Отказ обязан быть исполнимым. Путь `02_active.md` вместо `product/02_active.md`
    ядро отбивало как «файл не принадлежит юниту» и звало в проекцию или переезд —
    то есть чинить не то (живой прогон 14.08: отбились оба больших пакета).
    Догадки здесь нет: адрес называется, только когда он существует в базе,
    действительно лежит в названном юните — и виден узлу.

    Последнее условие не косметика: подсказка утверждает «ровно так этот файл
    стоит в списке `files` твоего контекста», а записи встреч из контекста
    срезаны. Назвав такой адрес, ядро само вернуло бы узел в исторический слой,
    от которого его только что увели (круг ревью 17.08 — сошлись все четыре
    ревьюера). Каталог адресом записи тоже не бывает.
    """
    if not rel or rel.startswith("/") or "\\" in rel or ".." in rel.split("/"):
        return []
    out: List[str] = []
    for unit in units:
        candidate = f"{unit.rstrip('/')}/{rel}"
        if unit_of_file(candidate, run.units()) != unit:
            continue
        if is_historic_record(candidate):
            continue
        try:
            # `base_file` держит границу базы: путь, уводящий наружу симлинком,
            # отказывает здесь же, а не превращается в подсказку
            if run.base_file(candidate).is_file():
                out.append(candidate)
        except SpineError:
            continue
    return out


def check_targets(run: Run, unit: str, payload: Dict[str, Any]) -> List[V.Violation]:
    """Адрес операции: файл своего юнита; нового файла это не запрещает.

    Якорей больше нет — куда именно внутри файла, решает applier по канону
    формы. Код проверяет только принадлежность, что путь не убегает из базы —
    и что он не ведёт в каталог протоколов.

    Последнее — граница исторического слоя. Протоколы прошлых встреч лежат
    внутри юнита и по принадлежности проходят: редактор `01_company` вправе
    адресовать любой из сотен своих файлов, включая протокол трёхмесячной
    давности. Штамп `run_id` туда не достаёт — он стережёт один адрес, который
    ядро пишет само. Разбор дописывает базу, а не правит историю; выжимку этой
    встречи кладёт ядро, и другого законного повода писать в этот каталог
    у операции нет.
    """
    out: List[V.Violation] = []
    home = protocol_home(run)
    protocol_root = str(home.get("rule_dir") or home.get("dir") or "")

    def protocol_violation(rel: str, field: str, eid: str) -> Optional[V.Violation]:
        if not under_dir(rel, protocol_root):
            return None
        return V.Violation("protocol_immutable",
                           f"{rel} лежит в каталоге протоколов {protocol_root} — "
                           "разбор туда не пишет",
                           field=field, eid=eid,
                           hint="выжимку этой встречи кладёт в базу само ядро; "
                                "протоколы прошлых встреч — исторический слой "
                                "базы, он не правится разбором. Запись предназначена "
                                "живому файлу юнита — назови его")

    for idx, op in enumerate(payload.get("operations", []) or []):
        if not isinstance(op, dict):
            continue
        eid = str(op.get("eid", ""))
        rel = (op.get("target") or {}).get("file")
        out += address_violations(run, rel, str(op.get("op") or ""),
                                  f"operations[{idx}].target.file", eid,
                                  V.anchor_text(op))
        if rel:
            try:
                run.base_file(rel)
            except SpineError:
                out.append(V.Violation("path_escapes_base",
                                       f"путь {rel} выходит за пределы базы",
                                       field=f"operations[{idx}].target.file", eid=eid))
            else:
                if unit_of_file(rel, run.units()) != unit:
                    hits = base_relative_hits(run, rel, [unit])
                    out.append(V.Violation("schema_invalid",
                                           f"файл {rel} не принадлежит юниту {unit}",
                                           field=f"operations[{idx}].target.file",
                                           eid=eid,
                                           hint=(f"путь пишется от корня базы: назови "
                                                 f"{hits[0]} — ровно так этот файл стоит "
                                                 "в списке files твоего контекста"
                                                 if hits else
                                                 "запись в чужой дом — проекция "
                                                 "(projections[]) либо вердикт "
                                                 "wrong_file контролёра")))
                breach = protocol_violation(rel, f"operations[{idx}].target.file", eid)
                if breach:
                    out.append(breach)
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
                # тот же класс, что у target: путь отсчитан от каталога, а не от
                # корня базы. Подсказка выдаётся, только если такой файл в базе
                # ровно один — двусмысленный адрес чинит редактор, не ядро
                hits = base_relative_hits(run, pfile, run.units())
                out.append(V.Violation("schema_invalid",
                                       f"проекция в {pfile}: места нет в карте",
                                       field=f"operations[{idx}].projections", eid=eid,
                                       hint=(f"путь пишется от корня базы: назови "
                                             f"{hits[0]}" if len(hits) == 1 else "")))
            # отражение записи — такая же запись: правила адреса на него те же,
            # иначе гарантия обходится проекцией
            out += address_violations(run, pfile, str(op.get("op") or ""),
                                      f"operations[{idx}].projections", eid)
            breach = protocol_violation(pfile, f"operations[{idx}].projections", eid)
            if breach:
                out.append(breach)
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


def check_replace_anchors(run: Run, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Якорь замены проверяется файлом: есть ли строка и одна ли она.

    Якорь необязателен по форме — редактор видит файл срезом; здесь проверяется
    факт названного. Пакет это не отбивает: как и у прочих улик, ненайденный
    якорь едет на экран спорным пунктом — файл мог измениться после того, как
    редактор его читал, и решать это человеку, а не отказом узлу.

    Неоднозначный якорь опаснее ненайденного: applier заменил бы первое
    вхождение и стёр бы чужую запись, отчитавшись `written`.
    """
    notes: List[Dict[str, Any]] = []
    for op in payload.get("operations", []) or []:
        if not isinstance(op, dict):
            continue
        if op.get("op") not in V.ANCHORED_OPS:
            continue
        rel = str((op.get("target") or {}).get("file") or "")
        body = run.read_base(rel)
        if body is None:
            # файла нет — это отказ формы (`check_targets`), а не улика: править
            # существующую запись там негде, и на экран пункт не поедет вовсе
            continue
        text = V.anchor_text(op)
        # у операции, которая ничего не вытесняет, якоря нет по форме — её
        # отбил валидатор, и второй раз шуметь о ней на экране незачем
        if not text:
            continue
        body = body or ""
        hits = sum(1 for line in body.splitlines()
                   if V.normalize_line(line) == V.normalize_line(text))
        if hits == 1:
            continue
        kind = "replace_anchor_missing" if hits == 0 else "replace_anchor_ambiguous"
        notes.append({"eid": str(op.get("eid", "")), "kind": kind,
                      "file": rel, "quote": text, "hits": hits})
        run.event("evidence_invalid", eid=str(op.get("eid", "")), code=kind)
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
    titles = roster_titles(run)
    for row in payload.get("verdicts", []) or []:
        eid = str(row.get("eid", ""))
        title = titles.get(eid) or None
        kind = row.get("verdict")
        evidence = row.get("evidence") or {}
        if kind == "duplicate":
            rel = str(evidence.get("file", ""))
            # запись встречи не доказывает дубля — ни именем файла, ни местом:
            # каталог `meetings/` держит и выжимку ЭТОГО прогона, а имена в нём
            # произвольны. Улика оттуда не отсеивает — пункт едет человеку
            historic = is_historic_record(rel)
            body = "" if historic else (run.read_base(rel) or "")
            if V.contains_fragment(body, str(evidence.get("quote", ""))):
                run.event("filtered", eid=eid, unit=unit, code="duplicate")
                run.journal("filtered", eid=eid, unit=unit, code="duplicate",
                            evidence=evidence)
                out.append({"kind": "filtered", "eid": eid, "title": title,
                            "code": "duplicate"})
            else:
                run.event("evidence_invalid", eid=eid, code="duplicate")
                out.append({"kind": "doubt", "eid": eid, "title": title,
                            "code": "duplicate_unverified"})
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
                out.append({"kind": "filtered", "eid": eid, "title": title,
                            "code": "episode"})
            else:
                run.event("evidence_invalid", eid=eid, code="episode")
                out.append({"kind": "doubt", "eid": eid, "title": title,
                            "code": "episode_unverified"})
        elif kind == "wrong_file":
            path = str(evidence.get("path", ""))
            home = unit_of_file(path, run.units())
            if home and home != unit:
                out.append({"kind": "wrong_file", "eid": eid, "title": title,
                            "path": home})
            else:
                run.event("evidence_invalid", eid=eid, code="wrong_file")
                out.append({"kind": "doubt", "eid": eid, "title": title,
                            "code": "wrong_file_unverified"})
        elif kind == "contradiction":
            body = run.read_base(str(evidence.get("file", ""))) or ""
            verified = V.contains_fragment(body, str(evidence.get("quote", "")))
            if not verified:
                run.event("evidence_invalid", eid=eid, code="contradiction")
            out.append({"kind": "doubt", "eid": eid, "title": title,
                        "code": "contradiction" if verified else "contradiction_unverified"})
        elif kind == "doubt":
            out.append({"kind": "doubt", "eid": eid, "title": title,
                        "code": "doubt"})
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
        # адрес переезда проходит те же ворота, что адрес операции: иначе через
        # смену дома в защищённый файл заезжает то, что туда не пускают прямо
        source_op = next((op for unit in run.units_with_operations()
                          for op in (run.operations(unit) or {}).get("operations", [])
                          if str(op.get("eid", "")) == eid), {})
        raise_violations(run, address_violations(
            run, str(target.get("file", "")), str(source_op.get("op") or ""),
            "relocation.target.file", eid, V.anchor_text(source_op)), "relocation")
        row["target"] = target
        row["to_unit"] = to_unit
        duplicate = payload.get("duplicate")
        if isinstance(duplicate, dict) and duplicate.get("quote"):
            # тот же исторический слой, что и у вердикта контролёра: иначе отсев
            # по протоколу этой же встречи заезжает через переезд — вход, где
            # проверка стояла своя (круг ревью 3, находка Codex)
            rel = str(duplicate.get("file", ""))
            body = "" if is_historic_record(rel) else (run.read_base(rel) or "")
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


def disputed_noop(run: Run, unit: str, op: Dict[str, Any]) -> bool:
    """`noop`, с которым контролёр юнита не согласился.

    Молчаливый `noop` — законный ответ редактора и уходит в журнал отсева. Но
    когда контролёр возразил, а улика его не подтвердилась, сущность исчезала
    между ними двумя: `duplicate_unverified` ядро выносило честно, а до экрана
    пункт не доезжал — `noop` отсекался раньше, чем читались вердикты. Ровно
    так пропали 9 сущностей юнита `product` на прогоне 14.08 (находка Codex,
    круг ревью 17.08).

    Подтверждённая улика сюда не попадает: она уже в `filtered`, и отсев
    засчитан машинно — там спорить не о чем.
    """
    if op.get("op") != "noop":
        return False
    verdict = verdict_for(run, unit, str(op.get("eid", ""))) or {}
    return str(verdict.get("verdict") or "accept") != "accept"


def effective_operations(run: Run) -> List[Tuple[str, Dict[str, Any]]]:
    """Операции, дошедшие до экрана: без молчаливых noop, отсеянных и снятых.

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
            if op.get("journal_only") or eid in withdrawn:
                continue
            if op.get("op") == "noop" and not disputed_noop(run, unit, op):
                continue
            move = relocations.get(eid)
            moved = bool(move and move.get("accepted") and move.get("to_unit"))
            home = move["to_unit"] if moved else unit
            if (unit, eid) in filtered or (home, eid) in filtered:
                continue
            if moved:
                # якорь подтверждали в прежнем файле — в новом доме он ничего не
                # значит и указал бы applier'у на строку, которой там нет
                moved_op = {key: value for key, value in op.items() if key != "replaces"}
                out.append((home, {**moved_op,
                                   "target": move.get("target") or op.get("target"),
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
    titles = roster_titles(run)
    for unit in run.units_with_operations():
        for op in (run.operations(unit) or {}).get("operations", []):
            eid = str(op.get("eid", ""))
            if op.get("op") == "noop" and ("noop", eid) not in logged:
                run.journal("noop", eid=eid, title=titles.get(eid), unit=unit,
                            reason=op.get("noop_reason"))
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
            "pending_quotes": sorted({row["eid"] for row in pending_quote_flags(run)})}


#: Сущности, которые предписывают, а не описывают: принцип действует всегда,
#: договорённость задаёт порядок работы впредь (канон типов — prompts/extract.md).
#: Записать такую — значит поменять правило, по которому база живёт дальше и по
#: которому будут приниматься следующие разборы. Это методологическое решение, и
#: человек принимает его отдельно, а не пакетом «беру всё рекомендованное»:
#: спорным пункт становится всегда, даже когда контролёр к нему не придрался.
#: Признак читается у сущности, а не у файла: файл каноном себя не объявляет —
#: `version:` стоит и на живых 05_decisions, куда разбор пишет штатно.
RULE_TYPES = {"principle", "agreement"}

#: Механика разбора в текст человеку не едет. На экране стоит предмет решения:
#: что записываем, что исчезнет, почему сомнение, — а не имя операции, вердикта
#: или узла (правило Эрика 17.08). Ярлыки живут одним словарём: разойдясь по
#: строкам, техническое слово протекает в первый же новый текст.
VERDICT_LABELS = {
    "doubt": "сомнение проверяющего",
    "contradiction": "противоречие с тем, что уже записано",
    "duplicate": "похоже на уже записанное",
    "episode": "эпизод разговора, а не факт для базы",
    "wrong_file": "спор о месте записи",
}

NOOP_REASON_LABELS = {
    "already_covered": "это уже записано в базе",
    "not_valuable": "записывать нечего",
    "episode": "это эпизод разговора",
}


def roster_titles(run: Run) -> Dict[str, str]:
    """Название каждой сущности по её номеру — один проход по ростеру.

    Номер сущности человеку ничего не говорит: «E48 не подтверждена» и
    «E48 назначена product» — строки, в которых не видно предмета. Название
    едет рядом с номером везде, где о сущности говорят человеку.
    """
    return {str(item.get("eid", "")): str(item.get("title") or "")
            for item in run.roster() if item.get("eid")}


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
            label = VERDICT_LABELS.get(str(verdict.get("verdict")), "сомнение")
            doubts.append(f"{label}: {verdict.get('note') or ''}".strip(": "))
        if verdict.get("verdict") in ("duplicate", "episode") \
                and (source_unit, eid) not in filtered:
            label = VERDICT_LABELS.get(str(verdict.get("verdict")), "сомнение")
            doubts.append(f"{label} — подтверждения в базе не нашлось, "
                          "решение за вами")
        move = relocations.get(eid)
        if verdict.get("verdict") == "wrong_file" and move and not move.get("accepted"):
            doubts.append("хозяин названного места забирать запись не стал: "
                          + (move.get("note") or "без причины"))
        if eid in fabricated:
            doubts.append("цитата не подтвердилась: такой фразы на встрече "
                          "не прозвучало")
        if eid in conflicts:
            doubts.append("запись предложена сразу в двух местах базы: "
                          + ", ".join(conflicts[eid]) + " — выберите одно")
        if op.get("relocated_from"):
            doubts.append(f"запись пришла из другого места базы ({op['relocated_from']}) "
                          "— проверьте адрес")
        for note in evidence_notes.get((source_unit, eid), []):
            # улики якоря считались по файлу прежнего дома: после переезда они
            # говорят о чужом адресе, и место правки applier ищет заново
            if op.get("relocated_from") and str(note.get("kind", "")).startswith("replace_"):
                continue
            if note.get("kind") == "replace_anchor_missing":
                doubts.append(f"прежняя запись не найдена: строки {note.get('quote')!r} "
                              f"в {note.get('file')} нет — замена не выполнится")
            elif note.get("kind") == "replace_anchor_ambiguous":
                doubts.append(f"непонятно, что именно заменяется: строка {note.get('quote')!r} "
                              f"встречается в {note.get('file')} {note.get('hits')} раза")
            elif note.get("kind") == "base_quote_unverified":
                doubts.append(f"цитата из базы не найдена: {note.get('quote')!r} "
                              f"нет в {note.get('file')}")
            else:
                doubts.append("обоснование места не подтвердилось: строки "
                              f"{note.get('quote')!r} в {note.get('file')} нет")
        # замена вслепую: якоря нет — applier будет искать запись сам, и человек
        # принимает необратимую правку, не видя, что исчезнет. Пакет за это не
        # отбивается (редактор видит файл срезом и вправе строки не знать), но
        # молча такой пункт не проходит
        if op.get("op") in V.ANCHORED_OPS and not V.anchor_text(op):
            doubts.append("прежняя запись не названа: место правки определится "
                          "по фактическому состоянию файла, и что именно "
                          "исчезнет — на экране не видно")
        entity = roster.get(eid, {})
        # правило решается отдельно и когда вводится, и когда снимается: тихо
        # убранная норма стоит не меньше тихо заведённой, а формулировка
        # сомнения у этих случаев разная — иначе текст врёт человеку
        if str(entity.get("type") or "") in RULE_TYPES:
            if op.get("op") in ("new", "update"):
                doubts.append("правило работы, а не факт встречи: запись будет действовать "
                              "на следующие решения — прими её отдельно и только если "
                              "правило объявлено на встрече, а не прозвучало рассуждением")
            else:
                doubts.append("снимается правило работы: оно перестанет действовать на "
                              "следующие разборы — подтверди, что на встрече его правда "
                              "отменили")
        # оспоренный отсев: записи за ним нет — ни текста, ни адреса. Пункт
        # спрашивает человека о судьбе сущности, а не предлагает запись, и
        # исходы у него поэтому свои (`decide_decision`)
        if op.get("op") == "noop":
            because = NOOP_REASON_LABELS.get(str(op.get("noop_reason") or ""),
                                             "записывать нечего")
            doubts.insert(0, f"это решили не записывать — {because}, — но "
                             "проверка не согласилась и подтверждения в базе "
                             "не нашла. Готовой записи за этим пунктом нет: "
                             "решите, оставить как есть или считать, что "
                             "предмет записан раньше")
        item = {
            "n": number, "eid": eid, "unit": unit, "op": op.get("op"),
            "file": (op.get("target") or {}).get("file"),
            # у оспоренного отсева записи не существует: подставить сюда
            # название сущности значило бы выдать его за «точный текст записи»,
            # который человек принимает дословно (круг ревью 2, находка Codex)
            "text": "" if op.get("op") == "noop"
                    else (op.get("proposed_text") or entity.get("title") or ""),
            "title": entity.get("title"), "owner": entity.get("owner"),
            "due": entity.get("due"),
            "section": "doubtful" if doubts else "recommended",
            "doubts": doubts,
        }
        if op.get("op") == "noop":
            item["kind"] = "disputed_noop"
        # якорь замены едет вместе с пунктом: applier видит только материал
        # применения, и без якоря в нём замена снова стала бы догадкой. Едет
        # только у операций над существующей записью — у `new` якорь означал бы
        # «сотри вот это», чего операция не просила
        anchor = V.anchor_text(op)
        if anchor and op.get("op") in V.ANCHORED_OPS:
            item["replaces"] = {"text": anchor}
        # проекция — часть пункта: пользователь принимает обе записи разом,
        # и applier получает её из решения, а не из пакета редактора
        projections = [{"file": p.get("file"), "proposed_text": p.get("proposed_text")}
                       for p in op.get("projections") or [] if isinstance(p, dict)]
        if projections:
            item["projections"] = projections
        items.append(item)
    # два пункта об одной записи: применяются они последовательно, и второй
    # либо затрёт правку первого, либо честно упадёт — принятое человеком
    # изменение теряется молча. Ловим здесь, пока решение ещё не принято
    by_anchor: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for item in items:
        anchor = str((item.get("replaces") or {}).get("text") or "")
        if anchor and item.get("file"):
            by_anchor.setdefault((str(item["file"]), V.normalize_line(anchor)),
                                 []).append(item)
    for (path, _), rows in by_anchor.items():
        if len(rows) < 2:
            continue
        for item in rows:
            item["doubts"].append(
                "ту же запись " + path + " правят пункты "
                + ", ".join(str(row["n"]) for row in rows)
                + " — примите один, иначе второй затрёт первый")
            item["section"] = "doubtful"
    items += lexicon_items(run, number + 1)
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
        # оспоренный отсев записи не несёт: применять нечего, и текст записи,
        # придуманный на экране, был бы записью, которой не формулировал никто
        if items[n].get("kind") == "disputed_noop" \
                and outcome not in ("reject", "already"):
            named = items[n].get("title") or f"пункт {n}"
            raise SpineError("bad_usage",
                             f"«{named}»: готовой записи за этим пунктом нет, "
                             "применять нечего",
                             field="decisions",
                             hint="здесь два решения: оставить как есть либо "
                                  "считать, что предмет записан раньше. Нужна "
                                  "запись — верните сущность в разбор этого "
                                  "места и переподайте его пакет")
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
            run.journal("already", eid=item["eid"], title=item.get("title"),
                        unit=item["unit"])
        if outcome == "reject":
            run.journal("rejected", eid=item["eid"], title=item.get("title"),
                        unit=item["unit"], reason=row.get("reason"))
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


#: Секции протокола: тип сущности → заголовок. Порядок — канон v1 (Решения,
#: Задачи, Цели, Запросы, Идеи, Инсайты, Факты, Принципы, Метрики, Открытые
#: вопросы, Риски); типы, которых v1 не знал, стоят рядом по смыслу. Тип вне
#: словаря не теряется — он уходит в «Прочее» последней секцией.
PROTOCOL_SECTIONS = (
    ("decision", "Решения"),
    ("agreement", "Договорённости"),
    ("task", "Задачи"),
    ("goal", "Цели"),
    ("request", "Запросы"),
    ("idea", "Идеи"),
    ("insight", "Инсайты"),
    ("fact", "Факты"),
    ("principle", "Принципы"),
    ("metric", "Метрики"),
    ("question", "Открытые вопросы"),
    ("risk", "Риски"),
    ("people-observation", "Наблюдения о людях"),
    ("glossary-term", "Термины"),
)

PROTOCOL_SECTION_OTHER = "Прочее"

#: Модальность по-русски: протокол читает человек, а не машина.
MODALITY_LABELS = {
    "committed": "обязательство",
    "intention": "намерение",
    "deprioritized": "отложено",
    "cancelled": "отменено на встрече",
    "done_in_meeting": "сделано на встрече",
}

#: Этап разбора человеческим языком. Печатается в протоколе, только пока разбор
#: не дошёл до конца: файл со `status: briefed` в базе обязан сам объяснить, что
#: правки по этой встрече ещё не применялись.
STATE_LABELS = {
    "ready": "разбор только начат — выжимки ещё нет",
    "mapped": "карта базы построена, выжимки ещё нет",
    "briefed": "выжимка сдана, человек её ещё не подтвердил",
    "confirmed": "выжимка подтверждена, предложения по базе готовятся",
    "review": "предложения по базе проходят контроль",
    "decided": "решения приняты, записи в базу ещё не сделаны",
    "writing": "записи в базу применяются",
    "applied": "записи в базу применены, сводка участникам не отправлена",
}


def protocol_line(row: Dict[str, Any], task: bool = False) -> List[str]:
    """Строка сущности в протоколе: заголовок, факты, дом, опора.

    Задача печатается чекбоксом и живёт под именем владельца — форма v1;
    сделанное в кадре отмечается сразу закрытым, потому что оно и правда
    закрыто. Спецификация идёт вложенным списком: сжатая в заголовок, она
    перестаёт быть спецификацией.
    """
    title = str(row.get("title") or row.get("eid") or "").strip()
    done = row.get("modality") == "done_in_meeting"
    head = f"- [{'x' if done else ' '}] {title}" if task else f"- {title}"
    facts: List[str] = []
    if row.get("due"):
        # срок печатается у любой сущности: горизонт цели или запроса теряется
        # ровно так же, как срок задачи, — а ищут по протоколу и его тоже
        facts.append(f"срок: {row['due']}")
    if not task and row.get("owner"):
        facts.append(f"отв. {row['owner']}")
    if row.get("author"):
        facts.append(str(row["author"]))
    label = MODALITY_LABELS.get(str(row.get("modality") or ""))
    if label:
        facts.append(f"*({label})*")
    if row.get("next_meeting"):
        facts.append("[→след.встреча]")
    if facts:
        head += " — " + " · ".join(facts)
    # тема в строке не печатается: она задаёт порядок записей (`by_thread`), а
    # тегом у каждой строки только шумит — читателю она видна тем, что записи
    # одной темы стоят подряд
    tail = [f"{name}: {row[key]}" for key, name in (("unit", "дом"),)
            if row.get(key)]
    if tail:
        head += ". " + " · ".join(tail)
    quote = str(row.get("quote") or "").strip()
    if quote:
        head += f'. Опора: "{quote}"'
    lines = [head]
    spec = row.get("spec")
    lines += [f"  - {item}" for item in (spec if isinstance(spec, list) else [])
              if str(item).strip()]
    return lines


def by_thread(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Записи одной темы — подряд: тема в строке не печатается, но задаёт
    порядок, и разговор об одном предмете читается вместе, а не вразбивку.

    Темы идут в порядке первого появления в подписанном ростере (правки паузы 1
    его порядок могли изменить — «порядок встречи» не обещаем); внутри темы
    порядок ростера сохранён, сортировка стабильна. Записи без темы собираются
    одной группой на месте первой такой записи.
    """
    order: Dict[str, int] = {}
    for row in rows:
        order.setdefault(str(row.get("thread") or ""), len(order))
    return sorted(rows, key=lambda row: order[str(row.get("thread") or "")])


def protocol_tasks(rows: Sequence[Dict[str, Any]]) -> List[str]:
    """Блок задач: по владельцу, безымянные — последними; внутри — по темам."""
    by_owner: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        owner = str(row.get("owner") or "").strip() or "Не назначен"
        by_owner.setdefault(owner, []).append(row)
    lines: List[str] = []
    for owner in sorted(by_owner, key=lambda name: (name == "Не назначен", name)):
        lines.append(f"{owner}:")
        for row in by_thread(by_owner[owner]):
            lines += protocol_line(row, task=True)
        lines.append("")
    return lines


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
    meeting = state.get("meeting") or {}
    date = run.manifest["meeting_date"]
    topic = str(state.get("topic") or "")
    lines = ["---", f'title: "Протокол встречи {date} — {topic}"', "type: meeting",
             f"date: {date}", f"topic: {topic}", f"status: {run.state}",
             f"run_id: {run.manifest['run_id']}", "---", "",
             f"# Встреча {date}", "", "## Метаданные", f"Дата: {date}"]
    people = [str(person.get("name") or "").strip()
              + (f" ({person['role']})" if person.get("role") else "")
              for person in meeting.get("participants") or []
              if isinstance(person, dict) and str(person.get("name") or "").strip()]
    lines.append("Участники: " + (", ".join(people) if people else "не названы"))
    if meeting.get("duration"):
        lines.append(f"Длительность: {meeting['duration']}")
    lines.append(f"Тип встречи: {meeting.get('kind') or 'неизвестно'}")
    lines += ["", "## Содержание встречи", "",
              str(meeting.get("narrative") or state.get("gist") or "—"), ""]
    live = [row for row in state["roster"] if not row.get("withdrawn")]
    # отдельной секции тем в протоколе нет: список тем повторял оглавление того,
    # что и так стоит ниже строками. Тема осталась порядком записей внутри секций
    known = {name for name, _ in PROTOCOL_SECTIONS}
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for row in live:
        kind = str(row.get("type") or "")
        buckets.setdefault(kind if kind in known else PROTOCOL_SECTION_OTHER, []).append(row)
    if live:
        lines += ["## Извлечённые сущности", ""]
    for kind, heading in PROTOCOL_SECTIONS + ((PROTOCOL_SECTION_OTHER,
                                               PROTOCOL_SECTION_OTHER),):
        rows = buckets.get(kind)
        if not rows:
            continue
        lines += [f"### {heading}", ""]
        if kind == "task":
            lines += protocol_tasks(rows)
        else:
            for row in by_thread(rows):
                lines += protocol_line(row)
            lines.append("")
    quotes = [row for row in (meeting.get("key_quotes") or [])
              if isinstance(row, dict) and str(row.get("quote") or "").strip()]
    if quotes:
        lines += ["## Ключевые цитаты", ""]
        for row in quotes:
            note = " — ".join(str(row[key]).strip() for key in ("speaker", "context")
                              if str(row.get(key) or "").strip())
            lines.append(f'- "{str(row["quote"]).strip()}"' + (f" — {note}" if note else ""))
        lines.append("")
    # Вопрос, на который человек ответил, в файле не висит: ответ на паузе 1 —
    # это правка или снятие сущности, о которой спрашивали. Неоднозначности
    # разбора (дефолтный дом, дом протокола) закрывает само подтверждение —
    # после него они не «требуют уточнения», а приняты
    answered = set(run.load("roster-overrides.json") or {})
    answered |= {row["eid"] for row in state["roster"] if row.get("withdrawn")}
    open_questions = [row for row in state["meeting_questions"]
                      if str(row.get("eid") or "") not in answered]
    if run.state == "briefed":
        open_questions += state["ambiguities"]
    if open_questions:
        lines += ["## Требует уточнения", ""]
        lines += [f"- {row.get('message')}" for row in open_questions]
        lines.append("")
    withdrawn = [row for row in state["roster"] if row.get("withdrawn")]
    if withdrawn:
        lines += ["## Снято на подтверждении", ""]
        lines += [f"- {row.get('title') or row.get('eid')} — {row['withdrawn']}"
                  for row in withdrawn]
        lines.append("")
    # разбор, оборванный на середине, обязан сказать это сам: файл живёт в базе
    # дольше сессии, и через месяц отличить «так и было» от «не доехало» нечем
    if run.state != "done":
        lines += ["---", "",
                  f"*Разбор на этом файле остановился: {STATE_LABELS.get(run.state, run.state)}.*"]
    return "\n".join(lines).rstrip() + "\n"


#: По этим строкам шапки протокол узнаёт своего хозяина и его состояние: файл,
#: написанный ЭТИМ прогоном, он вправе переписать; чужой — только если тот
#: прогон разбор бросил.
RUN_STAMP = re.compile(r"^run_id:\s*(\S+)\s*$", re.MULTILINE)
STATUS_STAMP = re.compile(r"^status:\s*(\S+)\s*$", re.MULTILINE)


def protocol_stamp(path: Path) -> Dict[str, Optional[str]]:
    """Штамп файла по адресу протокола: чей прогон и на чём он встал.

    Читается только шапка. Файл нечитаемый или не в UTF-8 (протокол, набранный
    руками в другой кодировке, — бытовой случай русскоязычной базы) — штампа
    нет, и файл считается чужим: молчаливая перезапись здесь необратима.
    """
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:1000]
    except OSError:
        return {"run_id": None, "status": None}
    run_match = RUN_STAMP.search(head)
    status_match = STATUS_STAMP.search(head)
    return {"run_id": run_match.group(1) if run_match else None,
            "status": status_match.group(1) if status_match else None}


def drop_orphan_protocol(run: Run, part: str, keep: str) -> Optional[str]:
    """Прежний файл, оставшийся не по адресу, убирается своим прогоном.

    Адрес меняется по двум законным поводам: человек назвал другой каталог
    протоколов на паузе 1, узел переподал выжимку с другой темой. Оставленный
    файл застывает со `status: briefed` и врёт ровно тем способом, который весь
    этот механизм и чинит; оставленная копия транскрипта просто задваивает
    сотни килобайт. Работает для обеих частей: выжимка узнаётся по штампу
    `run_id`, архив — по совпадению с исходником прогона побайтово.
    """
    previous = ((run.load("protocol-status.json") or {}).get(part) or {}).get("file")
    if not previous or previous == keep:
        return None
    try:
        stale = run.base_file(str(previous))
    except SpineError:
        return None
    if not stale.is_file():
        return None
    if part == "summary":
        if protocol_stamp(stale)["run_id"] != run.manifest["run_id"]:
            return None
    else:
        try:
            source = Path(run.manifest["transcript"]["path"]).read_bytes()
            if sha256_bytes(stale.read_bytes()) != sha256_bytes(source):
                return None
        except OSError:
            return None
    try:
        stale.unlink()
    except OSError:
        return None
    run.journal("protocol_moved", part=part, was=previous, now=keep)
    return str(previous)


def write_protocol(run: Run) -> Dict[str, Any]:
    """Выжимку встречи и архивную копию транскрипта в базу кладёт ЯДРО.

    Причина исключения: это не предложение к записи, а артефакт разбора —
    выжимка, которую человек видит и правит на паузе 1. Через applier она шла
    в самом конце, и оборванный разбор не оставлял в базе ничего: встречу
    разобрали, а найти её через месяц нечем. Теперь файл появляется сразу после
    выжимки и переписывается на каждой смене фазы — его `status` называет этап,
    на котором разбор стоит.

    Чужой файл по адресу: доведённый до конца (`status: done`) и файл без штампа
    (написан руками) не трогаются никогда — правило v1. Брошенный на середине
    прогон — другое дело: перезапуск разбора после обрыва штатен, и вечно
    лежащий огрызок чужого прогона хуже свежей выжимки. Перезапись называется
    вслух в отчёте.

    Транскрипт копируется, а не переносится: он приходит произвольным путём,
    часто вне базы, и удалять исходник пользователя скилл не вправе.
    """
    targets = protocol_targets(run)
    if targets is None:
        absence = protocol_absence(run) or {}
        return {"written": False, **absence}
    report: Dict[str, Any] = {"written": True}
    summary_rel = targets["summary"]
    path = run.base_file(summary_rel)
    stamp = protocol_stamp(path) if path.is_file() else {"run_id": None, "status": None}
    mine = stamp["run_id"] == run.manifest["run_id"]
    abandoned = bool(stamp["run_id"]) and not mine and stamp["status"] not in (None, "done")
    if path.is_file() and not mine and not abandoned:
        report["summary"] = {
            "status": "skipped", "file": summary_rel,
            "note": "выжимка этой встречи в базе уже есть, и писал её не этот "
                    "разбор — существующий протокол не перезаписывается"}
        report["written"] = False
    else:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(path, protocol_text(run))
            report["summary"] = {"status": "written", "file": summary_rel}
            if abandoned:
                report["summary"]["note"] = (
                    "поверх выжимки брошенного разбора "
                    f"({stamp['run_id']}, остановился на этапе {stamp['status']})")
                run.journal("protocol_replaced", file=summary_rel,
                            was_run=stamp["run_id"], was_status=stamp["status"])
            moved = drop_orphan_protocol(run, "summary", summary_rel)
            if moved:
                report["summary"]["note"] = f"адрес изменился, прежний файл убран: {moved}"
        except OSError as error:
            report["summary"] = {"status": "failed", "file": summary_rel,
                                 "note": f"запись не удалась: {error}"}
            report["written"] = False
    transcript_rel = targets["transcript"]
    archive = run.base_file(transcript_rel)
    copied = ((run.load("protocol-status.json") or {}).get("transcript") or {})
    moved_archive = drop_orphan_protocol(run, "transcript", transcript_rel)
    if archive.is_file():
        # копия делается один раз; статус честный — «положил этот прогон», а не
        # «уже лежала», иначе финальный отчёт врёт о собственной работе
        report["transcript"] = {
            "status": "written" if copied.get("file") == transcript_rel
            and copied.get("status") == "written" else "skipped",
            "file": transcript_rel,
            "note": None if copied.get("status") == "written"
            else "копия транскрипта уже лежала в архиве до этого разбора"}
    else:
        try:
            archive.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(run.manifest["transcript"]["path"], archive)
            report["transcript"] = {"status": "written", "file": transcript_rel}
            if moved_archive:
                report["transcript"]["note"] = (
                    f"адрес изменился, прежняя копия убрана: {moved_archive}")
        except OSError as error:
            report["transcript"] = {"status": "failed", "file": transcript_rel,
                                    "note": f"копия не удалась: {error}"}
    return report


def sync_protocol(run: Run) -> None:
    """Держит выжимку в базе синхронной состоянию прогона.

    Зовётся из `set_state` — единственной точки, через которую проходит любая
    смена фазы. Провал записи прогон не валит и не исчезает: он ложится в отчёт,
    который координатор называет пользователю, и в события прогона. Ловится
    ЛЮБОЕ исключение, не только файловое: смена состояния уже записана в
    манифест, и падение отсюда оставило бы прогон в фазе, из которой нет выхода
    ни вперёд, ни назад — команда падала бы на том же месте снова и снова.
    """
    if not run.load("brief.json"):
        return
    try:
        report = write_protocol(run)
    except SpineError as error:
        report = {"written": False, "reason": error.message,
                  "say": "выжимка этой встречи в базу не легла: " + error.message}
    except Exception as error:  # noqa: BLE001 — см. докстринг: фаза уже сменилась
        reason = f"{type(error).__name__}: {error}"
        report = {"written": False, "reason": reason,
                  "say": "выжимка этой встречи в базу не легла из-за сбоя записи: "
                         + reason}
    previous = run.load("protocol-status.json") or {}
    run.store("protocol-status.json", report)
    if report.get("reason") and previous.get("reason") != report.get("reason"):
        run.event("protocol_status", code="absent", message=report["reason"])
    for part in ("summary", "transcript"):
        row = report.get(part)
        if not isinstance(row, dict) or row.get("status") == "written":
            continue
        # событие пишется на смену положения дел, а не на каждую фазу: иначе
        # журнал забивается повтором одного и того же факта
        if (previous.get(part) or {}).get("status") == row.get("status"):
            continue
        run.event("protocol_status", code=row.get("status"),
                  message=f"{part}: {row.get('note')}")


def protocol_report(run: Run) -> Optional[Dict[str, Any]]:
    """Что ядро сделало с протоколом на последней смене фазы."""
    report = run.load("protocol-status.json")
    return report if isinstance(report, dict) else None


def render_apply(run: Run) -> Dict[str, Any]:
    """Замок 1 пройден по построению: `decided` не наступает без исходов по всем
    пунктам. Материал applier — узкий вход: принятые пункты, целевые файлы,
    канон формы. Правило узла: перечитай файл перед правкой.

    Протокол встречи сюда не входит: он лежит в базе с момента выжимки, его
    пишет и обновляет ядро (`write_protocol`). Прогон без единого `take` больше
    не означает «встречу разобрали, в базе пусто» — файл встречи там уже есть.
    """
    require_state(run, ("decided", "writing"))
    items = accepted_items(run)
    if not items:
        run.set_state("applied", "completed")
        data: Dict[str, Any] = {"items": [],
                                "message": "принятых записей нет — писать нечего"}
        absent = protocol_absence(run)
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
        if row.get("replaces"):
            # якорь замены: строка, которую узел найдёт в файле и заменит целой
            # записью. Без него `update` — догадка о том, что вытеснять
            entry["replaces"] = row["replaces"]
        if row.get("kind"):
            # словарная пара пишется в форму СВОЕГО файла, а не строкой active:
            # без этой пометки узел догадывается о жанре по имени файла
            entry["kind"] = row["kind"]
            entry["title"] = row.get("title")
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
    absent = protocol_absence(run)
    if absent:
        # пропуск выжимки обязан быть громким в обеих ветках: материал с
        # принятыми пунктами читают внимательнее пустого
        payload["protocol_absent"] = absent
    digest = V.digest(payload)
    run.store("apply-material.json", {"payload": payload, "digest": digest})
    run.set_state("writing")
    return {"state": run.state, "step": run.step,
            "next": "узел applier применяет и отчитывается → submit applied",
            "data": payload, "digest": digest}


def submit_applied(run: Run, payload: Any) -> Dict[str, Any]:
    """Замок 2: статус записи по каждому принятому пункту — до этого сводки нет.

    Протокол встречи в этот отчёт не входит: его пишет ядро, и статус по нему
    ядро знает само (`protocol_report`) — спрашивать узел о работе, которой он
    не делал, значит получить выдумку.

    Отчёт один, applier'ов может быть несколько: большой write-set координатор
    делит на непересекающиеся группы файлов и склеивает строки в один `results`.
    """
    require_state(run, ("writing",))
    expected = [row["eid"] for row in accepted_items(run)]
    violations = V.validate_applied(payload, expected)
    violations.extend(check_applied_files(run, payload))
    raise_violations(run, violations, "applied")
    run.store("applied.json", payload)
    for row in payload.get("results", []):
        run.journal("apply_status", eid=row.get("eid"), file=row.get("file"),
                    status=row.get("status"), note=row.get("note"),
                    applier_id=row.get("applier_id"))
    statuses = {row.get("status") for row in payload.get("results", [])}
    run.set_state("applied", "completed")
    titles = roster_titles(run)
    data: Dict[str, Any] = {"written": sum(1 for r in payload["results"]
                                           if r.get("status") == "written"),
                            "unwritten": [{**r, "title": titles.get(str(r.get("eid")))}
                                          for r in payload["results"]
                                          if r.get("status") != "written"],
                            "statuses": sorted(s for s in statuses if s)}
    report = protocol_report(run)
    if report:
        # статус протокола ядро называет там же, где статусы записи: пользователь
        # видит судьбу всех файлов встречи одним взглядом
        data["protocol"] = report
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


#: Обёртка строки базы: маркер списка и чекбокс. Строка файла — не фраза для
#: участника встречи, и разметка в мессенджере читается мусором.
LIST_MARK = re.compile(r"^[ \t]*(?:[-*+][ \t]+(?:\[[ xX]\][ \t]+)?|\d+[.)][ \t]+)")


def plain_item(text: Optional[str]) -> Optional[str]:
    if not isinstance(text, str):
        return text
    return LIST_MARK.sub("", text).strip() or None


def delivery_material(run: Run) -> Dict[str, Any]:
    """Содержание сводки — от отражения в базе, а не от полного нарратива:
    в базу записывается важное, и сводка не вправе выдавать обсуждённое за
    зафиксированное (дефект прогона 07.08). Отражение — written ∪ already ∪
    duplicate: неважно, новая это дельта или предмет уже был записан ранее
    (решение пользователя 10.08).

    Шапка сводки (кто был, какая встреча, когда) и тип каждого пункта едут
    отсюда же: без них узел не соберёт формат v1 — заголовок, задачи по
    исполнителям, решения отдельно от задач.
    """
    results = applied_results(run)
    written = {str(r.get("eid")) for r in results if r.get("status") == "written"}
    decision_items = (run.load("decision.json") or {}).get("items", [])
    brief = run.load("brief.json") or {}
    meeting = brief.get("meeting") or {}
    roster = {str(item.get("eid")): item for item in run.roster()}
    reflected: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    # заголовок, доехавший до сводки, — один и тот же в обоих блоках: пункт,
    # отредактированный человеком, не может уехать участникам в двух редакциях
    titles: Dict[str, str] = {}
    for row in decision_items:
        eid = str(row.get("eid"))
        if row.get("kind") == "lexicon":
            # поправка словаря — внутренняя работа базы, не итог встречи
            continue
        if row.get("outcome") in ("take", "closed") and eid in written:
            kind = "written"
        elif row.get("outcome") == "already":
            kind = "already"
        else:
            # непринятое и незаписанное (в том числе failed/skipped applier'а)
            # отражением не является — тема уходит в фон
            continue
        entity = roster.get(eid) or {}
        # правка человека на экране решений сильнее исходной формулировки:
        # заголовок, поехавший в сводку мимо неё, — дефект прогона 12.08.
        # Обёртка строки базы (маркер списка, чекбокс) при этом снимается:
        # участнику встречи едет смысл пункта, а не разметка файла
        title = (plain_item(row.get("text")) if row.get("edited")
                 else (row.get("title") or plain_item(row.get("text"))))
        reflected.append({"title": title,
                          "text": row.get("text"), "owner": row.get("owner"),
                          "due": row.get("due"), "op": row.get("op"),
                          "type": entity.get("type"),
                          "modality": entity.get("modality"),
                          "outcome": row.get("outcome"),
                          "next_meeting": bool(entity.get("next_meeting")),
                          "reflection": kind})
        titles[eid] = str(title or "")
        seen.add(eid)
    duplicates = {eid for _, eid in filtered_eids(run, code="duplicate")}
    for eid in sorted(duplicates - seen):
        entity = roster.get(eid) or {}
        reflected.append({"title": entity.get("title"), "text": None,
                          "owner": entity.get("owner"), "due": entity.get("due"),
                          "op": None, "outcome": None, "type": entity.get("type"),
                          "modality": entity.get("modality"),
                          "next_meeting": bool(entity.get("next_meeting")),
                          "reflection": "duplicate"})
    # «к следующей встрече» — ожидания, прозвучавшие явно; они живут отдельным
    # блоком формата и потому собираются от ростера, а не от отражения: снятое
    # человеком не в счёт, остальное участник обязан увидеть
    withdrawn = run.withdrawn()
    next_meeting = [{"title": titles.get(str(item.get("eid"))) or item.get("title"),
                     "owner": item.get("owner"), "due": item.get("due"),
                     "reflection": "written" if str(item.get("eid")) in written else None}
                    for item in run.roster()
                    if item.get("next_meeting") and str(item.get("eid")) not in withdrawn]
    return {
        "intent": "delivery_material",
        "meeting": {"date": run.manifest["meeting_date"],
                    "kind": meeting.get("kind"),
                    "duration": meeting.get("duration"),
                    "participants": meeting.get("participants") or []},
        "gist": meeting.get("gist") or brief.get("gist"),
        "reflected": reflected,
        "next_meeting": next_meeting,
        "limit_chars": 4000,
    }


def submit_delivery(run: Run, payload: Any) -> Dict[str, Any]:
    require_written(run)
    raise_violations(run, V.validate_delivery(payload), "delivery")
    # границы проверяются по всему, что поедет наружу: разрезанная сводка —
    # тот же текст, и кухня, просочившаяся во вторую часть, ничем не лучше
    parts = [part for part in payload.get("messages") or [] if isinstance(part, str)]
    leaks = leaked_technique(run, "\n".join([payload.get("text") or ""] + parts))
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
        # подсказка идёт за фактом контекста, тем же сигналом, что и `check`
        sources = (run.load("reading-context.json") or {}).get("sources")
        if not sources:
            return ("речевой контекст базы пуст — фоллбэк: узел map по "
                    "транскрипту → submit map")
        return "узел extract → submit brief; карта после, по ростеру"
    if state == "mapped":
        return "узел extract → submit brief"
    if state == "briefed":
        needs_map = not run.load("map.json")
        pending = bool(pending_quote_flags(run))
        if needs_map:
            return ("узел map строит карту по artifacts/roster-lean.json → "
                    "submit map" + (" · узел quote-judge → submit quotes"
                                    if pending else ""))
        if pending:
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
        report = protocol_report(run)
        if report:
            data["protocol"] = report
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
    # тип и цель встречи со слов пользователя: v1 их спрашивал и подавал
    # экстрактору как фокус чтения. База их не выводит, код не угадывает —
    # не названы, поля нет
    check.add_argument("--meeting-kind", default=None)
    check.add_argument("--meeting-goal", default=None)
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
    except InjectedFault:
        raise
    except Exception as error:  # noqa: BLE001
        # координатор разговаривает с ядром только через JSON: трассировка в
        # stdout означает для него тишину — ни кода, ни подсказки, ни шага
        print(json.dumps({"error": {
            "code": "internal_error",
            "message": f"{type(error).__name__}: {error}",
            "hint": "это дефект ядра, а не входа: скажи пользователю и приложи "
                    "команду; разбор придётся перезапустить",
            "error_class": V.BLOCKER, "next": "", "issues": [], "data": {},
        }}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
