#!/usr/bin/env python3
"""Spine пайплайна meeting-analysis: state machine, диспетчер, гейты, write-path.

Фазы: start → locate → l1 → confirm → deltas → canon → review → compose ⇄ accept
→ apply → postcheck → [deliver] → finalize → done.

Коды возврата: 0 — ок · 1 — ожидаемое нарушение (precondition/валидация) ·
2 — bad usage либо внутренняя ошибка.

Stdlib-only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import stat
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_canon as canon_check  # noqa: E402  — лежит рядом, путь добавлен выше
import validate_deltas as delta_rules  # noqa: E402  — библиотека инвариантов пакета

NODES_FILE = SKILL_ROOT / "schema" / "nodes.json"
STATE_SCHEMA_FILE = SKILL_ROOT / "schema" / "run-state.schema.json"
DELTA_SCHEMA_FILE = SKILL_ROOT / "schema" / "delta.schema.json"
QUESTIONS_SCHEMA_FILE = SKILL_ROOT / "schema" / "questions.schema.json"

# Версию штампует builder при сборке поставки (`dev` — запуск из дерева
# репозитория: гейт обновления молчит). Пакет 0 волны G: обновление скилла у
# Cowork-клиента — ручной шаг руководителя, канала принудительной доставки нет;
# единственный контролируемый канал — сама база (маркер + свежий .skill).
SKILL_VERSION = "dev"
SKILL_VERSION_MARKER = ".claude/skills/meeting-analysis/.skill-version.json"

RUNS_ENV = "SVAIB_RUNS_DIR"
# Тестовый шов fault-injection: значение вида "apply:after_fileop:d002" рвёт
# процесс сразу после файловой операции — до журнальной записи `done`;
# "apply:after_intent:d002" — сразу после write-ahead intent, ДО файловой
# операции (проверка честного разрешения intent при resume);
# "apply:move_between_steps:d002" — строго между подоперациями move
# (текст уже в target, якорь ещё в source).
FAULT_ENV = "SVAIB_SPINE_FAULT"
LOCK_NAME = "active.lock"
STATE_NAME = "state.json"
ARTIFACTS_DIRNAME = "artifacts"
STATE_SCHEMA_VERSION = 2

# lock без state.json = падение start между созданием lock и записью состояния.
STALE_LOCK_SECONDS = 900
TERMINAL_STATUSES = ("done", "abandoned")
ARCHIVE_DIRNAME = "zz_archive"

# Артефакты фаз L2 внутри run-каталога.
ART_DELTAS_NORM = "artifacts/deltas.normalized.json"
ART_CANON_NORM = "artifacts/canon.normalized.json"
ART_CANON_AUTO = "artifacts/canon.auto.json"
ART_PACKAGES_DIR = "artifacts/review/packages"
ART_VERDICTS_DIR = "artifacts/review/verdicts"
ART_LEDGER = "artifacts/ledger.json"
ART_POST_VALIDATION = "artifacts/post_review_validation.json"
ART_QUESTIONS = "artifacts/questions.json"
ART_COMPOSE = "artifacts/compose.md"
ART_COMPOSE_HASH = "artifacts/compose.hash"
ART_COMPOSE_MAP = "artifacts/compose-map.json"
ART_ACCEPT = "artifacts/accept.json"
ART_SNAPSHOT = "artifacts/base-snapshot.json"
ART_JOURNAL = "artifacts/apply-journal.json"
ART_POSTCHECK = "artifacts/postcheck.json"
# Вход deliver-узла: решения пользователя по дельтам (Telegram = план работы,
# не пересказ встречи — решение Эрика 30.07). Собирается постчеком.
ART_DELIVER_INPUT = "artifacts/deliver-input.json"
# Карта мест хранения встреч базы: детерминированный шаг start, вход узла locate.
ART_MEETINGS_MAP = "artifacts/meetings-map.json"

# Каталог-контур протоколов: protocol_dir обязан лежать в нём (возможна подпапка-тип).
MEETINGS_DIRNAME = "meetings"

# Стратегический контур базы — терминально закрыт для записи (норма S13 карты
# миграции): скилл `01_company/01_strategic/` не обновляет.
STRATEGIC_PARTS = ("01_company", "01_strategic")

# Известные строковые поля `l1_context` (волна D, D-C п.9). Ограничений длины в
# схеме нет: `maxLength` считает символы, а контракт размера — в байтах и кодом.
L1_CONTEXT_FIELDS: Tuple[str, ...] = ("meeting_purpose", "background", "people", "glossary")

# Минимальная schema context-manifest (артефакт узла locate-context).
CONTEXT_MANIFEST_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["meeting_type", "contours", "date", "topic", "protocol_dir"],
    "properties": {
        "meeting_type": {"type": "string", "minLength": 1},
        "contours": {"type": "array", "minItems": 1},
        "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "topic": {"type": "string", "pattern": r"^[a-z0-9]+(_[a-z0-9]+)*$"},
        "protocol_dir": {"type": "string", "minLength": 1},
        "protocol_dir_new": {"type": "boolean"},
        "protocol_required": {"type": "boolean"},
        "deliver_required": {"type": "boolean"},
        # Тела контекста, которые узел locate-context кладёт в манифест. Поле
        # optional: манифест старого прогона без `l1_context` принимается.
        # Неизвестные ключи внутри — отказ кодовой проверкой рядом с гейтом
        # размера (`additionalProperties` мини-валидатор не реализует).
        "l1_context": {
            "type": "object",
            "properties": {name: {"type": "string"} for name in L1_CONTEXT_FIELDS},
        },
    },
}

# Гейт размера артефакта locate (волна D, D-C п.8): 128 КиБ в байтах UTF-8.
CONTEXT_MAX_BYTES = 131072

VERDICT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    # package_id/package_hash в файле НЕ обязательны: их проставляет spine на
    # приёме (submit review знает пакет из --package, hash — из манифеста).
    # Механическое копирование hash ревьюером порождало полные re-review пакета
    # из-за описки формы; привязка вердикта к пакету держится на покрытии
    # delta_id — пакеты разбиты по файлам и составы не пересекаются.
    "required": ["verdicts"],
    "properties": {
        "package_id": {"type": "string", "minLength": 1},
        "package_hash": {"type": "string", "minLength": 1},
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["delta_id", "verdict"],
                "properties": {
                    "delta_id": {"type": "string", "minLength": 1},
                    # Enum — опечатка в вердикте должна падать на submit, а не
                    # молча деградировать дельту в doubtful (ревью 30.07, Low).
                    "verdict": {"type": "string", "enum": [
                        "accept", "revise", "reject",
                        "escalate_insufficient_evidence", "escalate_spec_gap"]},
                    # attack — поле аудита для пользователя: машина не проверяет.
                    "attack": {"type": ["string", "null"]},
                    "dispute_class": {"type": ["string", "null"]},
                    "revised_text": {"type": ["string", "null"]},
                    "reason": {"type": ["string", "null"]},
                },
            },
        },
    },
}

META_WHITELIST: Dict[str, Tuple[str, ...]] = {
    # `allow_large_context` — обход гейта размера манифеста (D-C п.8). Подаёт
    # координатор и только после явного слова пользователя: recovery-текст
    # отказа обход не называет, поле с таким именем ВНУТРИ артефакта его не
    # включает — meta приходит только с CLI.
    "locate": ("allow_duplicate", "allow_large_context"),
    "l1": (),
    "confirm": (),
    "deltas": (),
    "canon": (),
    "review": (),
    "questions": (),
    "deliver": (),
    "accept": ("ack_unresolved",),
}

# Вердикты ревью → раскладка (prompts/review.md, детерминированный маппинг).
REVIEW_ACCEPTING = ("accept", "revise")
DISPUTE_CLASSES = ("fact", "node", "home_antipattern", "home_choice")

# --------------------------------------------------------------------------- #
# Бизнес-слой: этапы разбора и готовые тексты экранов (hitl-ux-spec, волна C)
# --------------------------------------------------------------------------- #

# Пользователь видит 4 рабочие реплики и 3 экрана; 13 фаз spine — внутренность.
# Тон — первое лицо (решение Эрика 30.07). Порядок кортежа = порядок пайплайна.
BUSINESS_STAGES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Изучаю базу и разбираю транскрипт", ("locate", "l1")),
    ("Экран 1: выжимка — подтверждение", ("confirm",)),
    ("Готовлю изменения базы и прогоняю независимую проверку",
     ("deltas", "canon", "review", "questions", "compose")),
    ("Экран 2: решения по изменениям", ("accept",)),
    ("Вношу принятое и сверяю базу", ("apply", "postcheck")),
    ("Экран 3: сводка в Telegram", ("deliver",)),
    ("Закрываю разбор", ("finalize",)),
)

BUSINESS_SCREENS: Dict[str, str] = {
    "confirm": "Выжимка встречи готова — посмотрите. Если всё верно и ничего не потеряно, "
               "скажите «подтверждаю». Если есть поправки — назовите их, я внесу и покажу снова.",
    "accept": "Вот что предлагаю изменить в базе. Нужны ответы на все вопросы списка; по "
              "советуемым достаточно одной фразы — «берём всё советуемое» или назовите "
              "исключения. Текст пункта можно поправить — скажите, какой и как: я внесу "
              "правку и покажу обновлённый список перед записью.",
    "deliver": "Сводка встречи для Telegram готова — отправляем?",
}

# Экраны, чей текст выдаётся на каждый `next` паузы. deliver сюда не входит: на
# его `next` текста сводки ещё нет, экран 3 живёт в ответе `show deliver`.
BUSINESS_PAUSE_SCREENS = ("confirm", "accept")


# --------------------------------------------------------------------------- #
# Ошибки и вывод
# --------------------------------------------------------------------------- #

class SpineError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        exit_code: int = 1,
        violations: Optional[List[Dict[str, Any]]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code
        self.violations = violations or []
        self.payload = payload or {}


def violation(code: str, message: str, **extra: Any) -> Dict[str, Any]:
    item = {"code": code, "message": message}
    item.update(extra)
    return item


def emit(args: argparse.Namespace, payload: Dict[str, Any], lines: List[str]) -> None:
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for line in lines:
            print(line)


def emit_error(args: argparse.Namespace, exc: SpineError) -> int:
    payload: Dict[str, Any] = {"ok": False, "error": exc.code, "message": exc.message}
    if exc.violations:
        payload["violations"] = exc.violations
    payload.update(exc.payload)
    # status_payload в exc.payload (fail_run) несёт ok: True — исход ошибочный.
    payload["ok"] = False
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        # Реплика пользователю обязана прозвучать и на ошибочном исходе (resume
        # с расхождениями): контракт «resume говорит всегда» не различает исходы.
        business = (exc.payload or {}).get("business") or {}
        if business.get("say"):
            print("Пользователю: {}".format(business["say"]))
        print("Ошибка [{}]: {}".format(exc.code, exc.message), file=sys.stderr)
        for item in exc.violations:
            print("  - [{}] {}".format(item.get("code"), item.get("message") or item.get("msg")),
                  file=sys.stderr)
    return exc.exit_code


# Глубина симуляции (pre-apply dry-run, волна D): та же `perform_operation`
# исполняется на копии базы. Тестовый шов обрыва принадлежит РЕАЛЬНОЙ записи —
# в песочнице он обязан молчать, иначе fault-инъекция рвала бы процесс на копии
# и обрыв реального write-path не воспроизводился бы вовсе.
_SIMULATION_DEPTH = 0


def maybe_fault(tag: str) -> None:
    """Тестовый обрыв процесса в заданной точке (fault-injection suite)."""
    if _SIMULATION_DEPTH:
        return
    if os.environ.get(FAULT_ENV) == tag:
        os._exit(137)


# --------------------------------------------------------------------------- #
# Утилиты: время, hash, атомарная запись
# --------------------------------------------------------------------------- #

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def delta_fingerprint(delta: Dict[str, Any]) -> str:
    """Семантический отпечаток дельты для журнала apply.

    Журнальная запись обязана быть связана с содержанием операции, а не только
    с id: после restart-from canonize может выдать под тем же id другую дельту
    (иной anchor/текст/адрес/операция), и сверки «по наблюдаемому состоянию
    базы» её не различат — delete вообще не оставляет текста (Codex re-check
    30.07, High×2). Сравнение отпечатков ловит любое расхождение полей симметрично.
    """
    return sha256_bytes(canonical_json_bytes({
        "operation": delta.get("operation"),
        "target_file": delta.get("target_file"),
        "source_file": delta.get("source_file"),
        "anchor": delta.get("anchor"),
        "proposed_text": delta.get("proposed_text"),
    }))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_artifact(path: Path) -> Tuple[Any, str]:
    """JSON хешируется канонично (sorted keys, utf-8, compact), md — байтами."""
    raw = path.read_bytes()
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SpineError("artifact_not_json", "артефакт не разобран как JSON: {}".format(exc))
    return obj, sha256_bytes(canonical_json_bytes(obj))


def artifact_hash(path: Path) -> str:
    if path.suffix == ".json":
        return read_json_artifact(path)[1]
    return sha256_file(path)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """tmp + os.replace: недописанный файл никогда не виден под целевым именем."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / ".tmp-{}-{}".format(path.name, uuid.uuid4().hex[:8])
    fd = os.open(str(tmp), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp), str(path))
    finally:
        if tmp.exists():
            tmp.unlink()
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def write_json_artifact(path: Path, obj: Any) -> str:
    """Пишет JSON-артефакт и возвращает канонический hash его содержимого."""
    atomic_write_bytes(path, (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return sha256_bytes(canonical_json_bytes(obj))


def load_json_file(path: Path, code: str = "artifact_not_json") -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpineError(code, "файл не прочитан как JSON: {}".format(exc), exit_code=2)


# --------------------------------------------------------------------------- #
# Пути и path confinement
# --------------------------------------------------------------------------- #

def default_runs_root() -> Path:
    """Платформенный runs-root (решение B№6, 30.07): state-каталог CLI-инструмента.

    Windows native — %LOCALAPPDATA%\\svaib\\runs (без env — ~/AppData/Local/svaib/runs,
    то же место при стандартной конфигурации); Linux, macOS и WSL —
    ${XDG_STATE_HOME:-~/.local/state}/svaib/runs. XDG-значение не-абсолютным быть
    не может (basedir-spec: такое игнорируется). Дубль — check_canon.default_runs_root.
    """
    if os.name == "nt":
        # Симметрично XDG: относительный LOCALAPPDATA дал бы runs-root от cwd —
        # при запуске из базы служебные файлы легли бы внутрь неё.
        local = os.environ.get("LOCALAPPDATA")
        if local and Path(local).expanduser().is_absolute():
            return Path(local).expanduser() / "svaib" / "runs"
        return Path.home() / "AppData" / "Local" / "svaib" / "runs"
    state = os.environ.get("XDG_STATE_HOME")
    if state:
        path = Path(state).expanduser()
        if path.is_absolute():
            return path / "svaib" / "runs"
    return Path.home() / ".local" / "state" / "svaib" / "runs"


def runs_root() -> Path:
    raw = os.environ.get(RUNS_ENV)
    if raw:
        return Path(raw).expanduser()
    return default_runs_root()


def compute_base_id(base: Path) -> str:
    return sha256_bytes(str(base).encode("utf-8"))[:12]


def resolve_base(raw: Optional[str]) -> Path:
    base = Path(raw).expanduser() if raw else Path.cwd()
    base = base.resolve()
    if not base.is_dir():
        raise SpineError("base_missing", "корень базы не существует: {}".format(base), exit_code=2)
    return base


def base_runs_dir(base: Path) -> Path:
    return runs_root() / compute_base_id(base)


def resolve_within(raw: str, root: Path, label: str, root_label: str, exit_code: int = 2) -> Path:
    """Все принимаемые пути нормализуются resolve(); выход за root — отказ."""
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if path.is_symlink():
        raise SpineError(
            "path_confinement",
            "нарушен precondition path_confinement: {} — symlink запрещён".format(label),
            exit_code=exit_code,
        )
    resolved = path.resolve()
    root_resolved = root.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise SpineError(
            "path_confinement",
            "нарушен precondition path_confinement: {} вне {}".format(label, root_label),
            exit_code=exit_code,
            payload={"path": str(resolved), "root": str(root_resolved)},
        )
    return resolved


def resolve_base_relative(raw: str, base: Path, label: str) -> Path:
    """Путь из содержимого артефакта (target_file и пр.) — только внутри базы, exit 1."""
    if not raw or not str(raw).strip():
        raise SpineError("path_confinement", "нарушен precondition path_confinement: {} пуст".format(label))
    path = Path(str(raw))
    if path.is_absolute():
        raise SpineError(
            "path_confinement",
            "нарушен precondition path_confinement: {} должен быть путём относительно базы".format(label),
        )
    if ".." in path.parts:
        raise SpineError(
            "path_confinement",
            "нарушен precondition path_confinement: {} содержит `..`".format(label),
        )
    candidate = base / path
    if candidate.is_symlink():
        raise SpineError(
            "path_confinement",
            "нарушен precondition path_confinement: {} — symlink запрещён".format(label),
        )
    resolved = candidate.resolve()
    base_resolved = base.resolve()
    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise SpineError(
            "path_confinement",
            "нарушен precondition path_confinement: {} вне корня базы".format(label),
        )
    return resolved


def ensure_inside_base(path: Path, base: Path, label: str) -> Path:
    """Повторный confinement непосредственно перед записью в базу.

    Валидация `submit locate` живёт задолго до `apply`/`finalize`: между ними
    каталог могли подменить symlink'ом наружу. Поэтому перед КАЖДОЙ записью вне
    apply-дельт путь проверяется заново — ни один его компонент внутри базы не
    symlink, резолвнутый путь лежит внутри базы.
    """
    base_resolved = base.resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = base_resolved / candidate
    candidate = Path(os.path.normpath(str(candidate)))
    try:
        rel = candidate.relative_to(base_resolved)
    except ValueError:
        raise SpineError(
            "path_confinement",
            "нарушен precondition path_confinement: {} вне корня базы".format(label),
            payload={"path": str(candidate), "root": str(base_resolved)},
        )
    walk = base_resolved
    for part in rel.parts:
        walk = walk / part
        if walk.is_symlink():
            raise SpineError(
                "path_confinement",
                "нарушен precondition path_confinement: {} — symlink на пути запрещён".format(label),
                payload={"path": str(walk)},
            )
    resolved = candidate.resolve()
    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise SpineError(
            "path_confinement",
            "нарушен precondition path_confinement: {} вне корня базы".format(label),
            payload={"path": str(resolved), "root": str(base_resolved)},
        )
    return resolved


def mkdir_inside_base(path: Path, base: Path, label: str) -> Path:
    """Создаёт каталог внутри базы покомпонентно, не следуя symlink'ам.

    `mkdir(parents=True)` прошёл бы через подменённый родительский каталог молча;
    здесь каждый уровень проверяется перед созданием, а файл на месте каталога —
    отказ, а не падение записи ниже по стеку.
    """
    target = ensure_inside_base(path, base, label)
    base_resolved = base.resolve()
    walk = base_resolved
    for part in target.relative_to(base_resolved).parts:
        walk = walk / part
        if walk.is_symlink():
            raise SpineError(
                "path_confinement",
                "нарушен precondition path_confinement: {} — symlink на пути запрещён".format(label),
                payload={"path": str(walk)},
            )
        if not walk.exists():
            try:
                os.mkdir(str(walk), 0o755)
            except FileExistsError:
                pass
        if not walk.is_dir():
            raise SpineError(
                "protocol_dir_not_a_directory",
                "по пути {} лежит не каталог — запись отменена".format(label),
                payload={"path": str(walk)},
            )
    return target


def ensure_not_strategic(path: Path, base: Path, label: str, delta_ids: Tuple[str, ...] = ()) -> Path:
    """Терминальный запрет записи в стратегический контур базы (норма S13).

    Скилл не обновляет `01_company/01_strategic/` — это зона руководителя.
    Валидатор помечает такую дельту (`S13_strategic_target`) и уводит её в
    doubtful, но doubtful можно принять через `ack_unresolved`; гейт стоит
    здесь, на самой записи, и не обходится ничем.
    """
    base_resolved = base.resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = base_resolved / candidate
    candidate = Path(os.path.normpath(str(candidate)))
    try:
        rel = candidate.relative_to(base_resolved)
    except ValueError:
        return Path(path)
    if rel.parts[:2] == STRATEGIC_PARTS:
        raise SpineError(
            "strategic_contour_forbidden",
            "нарушен инвариант S13: запись в стратегический контур {}/ запрещена — {}".format(
                "/".join(STRATEGIC_PARTS), label),
            violations=[violation(
                "strategic_contour_forbidden",
                "стратегические файлы правит руководитель, не скилл",
                field=str(rel), delta_ids=list(delta_ids))],
            payload={"path": str(rel), "label": label},
        )
    return Path(path)


def ensure_not_publication_target(path: Path, targets: Dict[str, str],
                                  label: str, delta_ids: Tuple[str, ...] = ()) -> None:
    """Терминальный запрет дельты в путь публикации ТЕКУЩЕГО прогона.

    `_summary.md` и файл протокола этой встречи пишет только spine, из принятой
    выжимки. Дельта в тот же путь опережает публикацию: create-only отдаст
    `created: false`, и в базе останется текст дельты вместо подтверждённой
    выжимки — молча. Остальной каталог протоколов гейтом не закрыт: там
    работает delta-уровень `S10_protocol_dir_target`, и сознательный
    `ack_unresolved` возможен (паритет со старым S11).

    Сравнение — по **канонизированному** пути (`realpath`), а не лексическому
    `normpath`: `alias/…_summary.md`, где `alias` — symlink внутрь базы на
    каталог протоколов, лексически не совпадает с целью, но `perform_operation`
    резолвит его в тот же файл и молча переписал бы публикацию (круг 2, Codex H1).
    """
    key = os.path.realpath(str(path))
    kind = targets.get(key) or targets.get(os.path.normpath(str(path)))
    if not kind:
        return
    key = os.path.normpath(str(path))
    raise SpineError(
        "publication_target_forbidden",
        "нарушен инвариант write-path: {} этого прогона публикует spine из принятой "
        "выжимки — дельта в этот файл не применяется ({})".format(kind, label),
        violations=[violation(
            "publication_target_forbidden",
            "путь публикации прогона принадлежит spine",
            field=key, delta_ids=list(delta_ids))],
        payload={"path": key, "publication": kind},
    )


PUBLICATION_LABELS = {"summary": "выжимка `_summary.md`", "protocol": "протокол встречи"}


def publication_targets(state: Dict[str, Any]) -> Dict[str, str]:
    """Пути, которые опубликует spine на этом apply: выжимка и (опц.) протокол.

    Единственный источник самих путей — `publication_paths` (B№4): два
    независимых построения тихо разъехались бы, и гейт перестал бы закрывать
    реальную цель. Ключи — и лексический `normpath`, и канонизированный
    `realpath`: symlink-alias внутрь базы обязан ловиться (Codex H1).
    """
    targets: Dict[str, str] = {}
    for kind, path in publication_paths(state).items():
        label = PUBLICATION_LABELS[kind]
        targets[os.path.normpath(str(path))] = label
        targets[os.path.realpath(str(path))] = label
    return targets


def publication_defaults(state: Dict[str, Any]) -> Dict[str, Any]:
    """Поля контура публикаций B№4 — optional: старый state читается с дефолтами."""
    state.setdefault("publication_conflicts", [])
    state.setdefault("publication_resolutions", {})
    state.setdefault("publication_refusals", {})
    side = state.setdefault("side_effects", {})
    side.setdefault("replaced", [])
    side.setdefault("kept", [])
    return state


def base_snapshot(base: Path) -> Dict[str, str]:
    """Hash'и всех файлов базы минус `zz_archive/` (пре-снимок apply).

    Symlink не разыменовывается, но и не пропускается молча: он попадает в
    снимок записью `symlink:<цель>`. Подмена файла или каталога symlink'ом между
    accept и postcheck обязана быть видимым расхождением, а не тихой записью.

    Снимок берётся один раз — до первой записи apply — и переживает и повтор
    apply, и restart-from: это baseline постчека, не текущее состояние.
    Названная граница (тест 4а, 30.07): пути публикаций входят в allowed
    постчека, а `zz_archive/` — вне снимка, поэтому ручной перенос занятого
    файла публикации в архив между попытками apply расхождением не считается;
    контент публикаций держит блок (г) постчека.
    """
    found: Dict[str, str] = {}
    for root, dirs, files in os.walk(base):
        root_path = Path(root)
        links = sorted(d for d in dirs if d != ARCHIVE_DIRNAME and (root_path / d).is_symlink())
        dirs[:] = sorted(d for d in dirs if d != ARCHIVE_DIRNAME and d not in links)
        for name in sorted(set(links) | set(files)):
            path = root_path / name
            try:
                rel = str(path.relative_to(base))
            except ValueError:
                continue
            if path.is_symlink():
                try:
                    found[rel] = "symlink:" + os.readlink(str(path))
                except OSError:
                    found[rel] = "symlink:?"
                continue
            if not path.is_file():
                continue
            try:
                found[rel] = sha256_file(path)
            except OSError:
                continue
    return found


# --------------------------------------------------------------------------- #
# Мини-валидатор JSON Schema (подмножество: type/required/properties/
# additionalProperties/items/enum/pattern/minLength/minItems)
# --------------------------------------------------------------------------- #

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[expected])


def check_schema(value: Any, schema: Dict[str, Any], path: str = "$") -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    expected = schema.get("type")
    if expected is not None:
        variants = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(value, variant) for variant in variants):
            errors.append(violation("type", "поле {}: ожидался тип {}".format(path, "|".join(variants)), field=path))
            return errors

    if "enum" in schema and value not in schema["enum"]:
        errors.append(violation("enum", "поле {}: значение вне допустимого набора".format(path), field=path))

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(violation("min_length", "поле {}: пустое или слишком короткое".format(path), field=path))
        if "pattern" in schema and not re.match(schema["pattern"], value):
            errors.append(violation("pattern", "поле {}: не совпало с форматом".format(path), field=path))

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(violation("min_items", "поле {}: список пуст".format(path), field=path))
        if isinstance(schema.get("items"), dict):
            for idx, item in enumerate(value):
                errors.extend(check_schema(item, schema["items"], "{}[{}]".format(path, idx)))

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(violation("required", "нет обязательного поля {}.{}".format(path, key), field="{}.{}".format(path, key)))
        properties = schema.get("properties", {})
        for key, sub_schema in properties.items():
            if key in value:
                errors.extend(check_schema(value[key], sub_schema, "{}.{}".format(path, key)))
        extra = schema.get("additionalProperties")
        if isinstance(extra, dict):
            for key, item in value.items():
                if key not in properties:
                    errors.extend(check_schema(item, extra, "{}.{}".format(path, key)))
    return errors


# --------------------------------------------------------------------------- #
# Манифесты узлов и таблица фаз (schema/nodes.json — единственный источник)
# --------------------------------------------------------------------------- #

_nodes_cache: Optional[Dict[str, Any]] = None


def load_nodes() -> Dict[str, Any]:
    global _nodes_cache
    if _nodes_cache is None:
        try:
            _nodes_cache = json.loads(NODES_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SpineError("nodes_manifest_broken", "schema/nodes.json не прочитан: {}".format(exc), exit_code=2)
    return _nodes_cache


def pipeline() -> List[Dict[str, Any]]:
    return load_nodes()["pipeline"]


def phase_names() -> List[str]:
    return [row["phase"] for row in pipeline()]


def phase_row(phase: str) -> Dict[str, Any]:
    for row in pipeline():
        if row["phase"] == phase:
            return row
    raise SpineError("unknown_phase", "неизвестная фаза: {}".format(phase), exit_code=2)


def phase_index(phase: str) -> int:
    return phase_names().index(phase)


def node_manifest(name: str) -> Dict[str, Any]:
    nodes = load_nodes()["nodes"]
    if name not in nodes:
        raise SpineError("unknown_node", "узел не объявлен в nodes.json: {}".format(name), exit_code=2)
    return nodes[name]


def require_implemented(phase: str) -> Dict[str, Any]:
    row = phase_row(phase)
    if not row.get("implemented"):
        raise SpineError(
            "phase_not_implemented",
            "фаза {} ещё не реализована".format(phase),
            exit_code=2,
            payload={"phase": phase},
        )
    return row


def initial_phase_status(phase: str) -> str:
    kind = phase_row(phase)["kind"]
    if kind == "hitl":
        return "awaiting_human"
    if kind == "spine":
        return "pending"
    return "awaiting_artifact"


_delta_schema_cache: Optional[Dict[str, Any]] = None


def delta_schema() -> Optional[Dict[str, Any]]:
    global _delta_schema_cache
    if _delta_schema_cache is None:
        try:
            _delta_schema_cache = json.loads(DELTA_SCHEMA_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
    return _delta_schema_cache


# --------------------------------------------------------------------------- #
# Base-level lock
# --------------------------------------------------------------------------- #

def lock_path(base_dir: Path) -> Path:
    return base_dir / LOCK_NAME


def read_lock(base_dir: Path) -> Optional[Dict[str, Any]]:
    path = lock_path(base_dir)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"run_id": None, "pid": None, "created_at": None, "broken": True}


def _pid_alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _lock_is_stale(base_dir: Path, info: Dict[str, Any]) -> bool:
    run_id = info.get("run_id")
    if run_id:
        state_file = base_dir / run_id / STATE_NAME
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return False
            return state.get("status") in TERMINAL_STATUSES
    # state.json нет: start упал между созданием lock и записью состояния.
    same_host = info.get("host") == socket.gethostname()
    if same_host and _pid_alive(info.get("pid")):
        return False
    if same_host:
        return True
    # Чужая машина: PID ничего не значит, судим по возрасту.
    return time.time() - lock_path(base_dir).stat().st_mtime > STALE_LOCK_SECONDS


def acquire_lock(base_dir: Path, run_id: str) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes({
        "run_id": run_id,
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "created_at": now_iso(),
    })
    for attempt in (1, 2):
        try:
            fd = os.open(str(lock_path(base_dir)), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            return
        except FileExistsError:
            info = read_lock(base_dir) or {}
            if attempt == 1 and _lock_is_stale(base_dir, info):
                try:
                    lock_path(base_dir).unlink()
                except OSError:
                    pass
                continue
            raise SpineError(
                "active_run_exists",
                "нарушен precondition single_active_run: по базе уже идёт run {}".format(info.get("run_id")),
                exit_code=1,
                payload={"active_run_id": info.get("run_id")},
            )


def release_lock(base_dir: Path, run_id: str) -> None:
    info = read_lock(base_dir)
    if info and info.get("run_id") in (run_id, None):
        try:
            lock_path(base_dir).unlink()
        except OSError:
            pass


# --------------------------------------------------------------------------- #
# Состояние run
# --------------------------------------------------------------------------- #

class Run:
    def __init__(self, base: Path, base_dir: Path, run_dir: Path, state: Dict[str, Any]) -> None:
        self.base = base
        self.base_dir = base_dir
        self.run_dir = run_dir
        self.state = state

    @property
    def artifacts(self) -> Path:
        return self.run_dir / ARTIFACTS_DIRNAME

    def path(self, rel: str) -> Path:
        return self.run_dir / rel


_state_schema_cache: Optional[Dict[str, Any]] = None


def state_schema() -> Optional[Dict[str, Any]]:
    global _state_schema_cache
    if _state_schema_cache is None:
        try:
            _state_schema_cache = json.loads(STATE_SCHEMA_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
    return _state_schema_cache


def empty_l2_state() -> Dict[str, Any]:
    return {
        "normalized": {},
        "phase_a": {"nodes": [], "kept": [], "dropped": []},
        "review": {"packages": [], "verdicts": {}, "no_evidence": [], "protocol_on_disk": None},
        "ledger": {"artifact": None, "hash": None},
        "post_validation": {"artifact": None, "hash": None, "ok": None},
        "questions": {"artifact": None, "hash": None},
        "compose": {"artifact": None, "hash": None, "map": None, "map_hash": None, "items": 0},
        "accept": {
            "artifact": None, "hash": None, "take": [], "reject": [], "already": [],
            "amended": [], "pending_amend": False, "ack_unresolved": False,
            "answers": {}, "base_manifest": {},
        },
        "apply": {"journal": None, "snapshot": None, "started_at": None, "completed_at": None},
        "postcheck": {"artifact": None, "hash": None, "ok": None},
        "deliver": {"decision": None, "artifact": None, "hash": None, "required": None,
                    "decisions": None},
        "unresolved": [],
        "deltas_id_map": {},
    }


def new_state(run_id: str, base: Path, transcript: Path, source_hash: str,
              map_path: str, map_hash: str, debug: bool = False) -> Dict[str, Any]:
    phases: Dict[str, Any] = {}
    for row in pipeline():
        phases[row["phase"]] = {
            "status": "pending",
            "artifact": None,
            "artifact_hash": None,
            "meta": {},
            "rework_count": 0,
            # Раздельный бюджет структурных отказов (волна D, D-B п.5а) и
            # монотонный счётчик отклонённых копий — вне бюджета.
            "structural_rework_count": 0,
            "rejection_seq": 0,
            "node": row.get("node"),
            "prompt_hash": None,
            "updated_at": None,
            "decision": None,
        }
    first = phase_names()[0]
    phases[first]["status"] = initial_phase_status(first)
    state = {
        "schema_version": STATE_SCHEMA_VERSION,
        "run_id": run_id,
        "base_id": compute_base_id(base),
        "base_path": str(base),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "status": "active",
        "phase": first,
        "phase_status": initial_phase_status(first),
        "apply_status": "not_started",
        # Режим показа и однократность реплик этапа — presentation-слой волны C.
        "debug": bool(debug),
        "business_last_announced_stage": None,
        "business_return_pending": False,
        "immutable": {
            "transcript_path": str(transcript),
            "source_hash": source_hash,
            "date": None,
            "topic": None,
        },
        "canon": {
            "meetings_map": map_path,
            "meetings_map_hash": map_hash,
        },
        "context": {
            "meeting_type": None,
            "protocol_dir": None,
            "protocol_dir_new": False,
            "protocol_required": None,
            "deliver_required": None,
            "allow_duplicate": False,
            "duplicates": [],
            "contours": [],
        },
        "phases": phases,
        "inputs": {},
        "blockers": [],
        "side_effects": {"applied": [], "published": [], "archived": [],
                         "apply_journal": None, "replaced": [], "kept": []},
        "publication_conflicts": [],
        "publication_resolutions": {},
        "publication_refusals": {},
        "history": [{"at": now_iso(), "event": "start", "phase": first, "detail": None}],
    }
    state.update(empty_l2_state())
    return state


def load_state(run_dir: Path) -> Dict[str, Any]:
    try:
        state = json.loads((run_dir / STATE_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpineError("state_unreadable", "state.json не прочитан: {}".format(exc), exit_code=2)
    for key, value in empty_l2_state().items():
        state.setdefault(key, value)
    # Поля presentation-слоя optional в схеме: run, начатый до волны C, читается
    # как бизнес-вид с неназванным этапом, а не падает на state_schema_violation.
    state.setdefault("debug", False)
    state.setdefault("business_last_announced_stage", None)
    state.setdefault("business_return_pending", False)
    # Контур публикаций B№4 — те же дефолты: run, начатый до B№4, читается.
    publication_defaults(state)
    # Счётчики hard-канала волны D — optional: run, начатый до неё, читается.
    for record in (state.get("phases") or {}).values():
        record.setdefault("structural_rework_count", 0)
        record.setdefault("rejection_seq", 0)
    # Волна G: run, начатый до фазы questions, читается — запись фазы появляется
    # дефолтом (прецедент волны C), L2-ключ `questions` даёт setdefault выше.
    (state.get("phases") or {}).setdefault("questions", {
        "status": "pending", "artifact": None, "artifact_hash": None,
        "meta": {}, "rework_count": 0, "structural_rework_count": 0,
        "rejection_seq": 0, "node": "questions", "prompt_hash": None,
        "updated_at": None, "decision": None,
    })
    return state


def check_publication_invariants(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Инварианты контура публикаций, которые мини-валидатор schema не выражает.

    `executed ⇒ полный scope` — условная JSON Schema не поддерживается, а на
    этом инварианте держатся ветка 0 §4в и обе роли постчека (д): резолюция без
    scope молча стала бы «исторической» и вернула бы решённый вопрос (Codex L6).
    Плюс инвариант §4б «не более одной нетерминальной записи на kind».
    """
    errors: List[Dict[str, Any]] = []
    for kind, record in sorted((state.get("publication_resolutions") or {}).items()):
        if not record.get("executed"):
            continue
        scope = record.get("scope") or {}
        if not scope.get("path") or not scope.get("payload_hash"):
            errors.append(violation(
                "publication_scope_incomplete",
                "исполненная резолюция {} без полного scope".format(kind),
                field="publication_resolutions.{}".format(kind)))
    open_records: Dict[str, int] = {}
    for record in state.get("side_effects", {}).get("replaced") or []:
        if record.get("stage") in ("done", "aborted"):
            continue
        open_records[record["publication"]] = open_records.get(record["publication"], 0) + 1
    for kind, count in sorted(open_records.items()):
        if count > 1:
            errors.append(violation(
                "replace_journal_forked",
                "у {} {} нетерминальных записей журнала замен".format(kind, count),
                field="side_effects.replaced"))
    return errors


def save_state(run_dir: Path, state: Dict[str, Any],
               enforce_invariants: bool = True) -> None:
    """Атомарная запись state. `enforce_invariants=False` — пути восстановления.

    Инварианты контура публикаций гейтят write-path, но НЕ должны запирать
    `abandon`/`restart-from` и сохранение blocker'а: битое состояние на диске
    (ручная правка, откат версии посреди run'а) иначе оставило бы run без
    выхода при живом base-level lock — «`failed` не тупик» перестал бы
    выполняться (круг 3, Opus L-2). На путях восстановления нарушения
    возвращаются наружу отчётом, а не исключением.
    """
    state["updated_at"] = now_iso()
    if enforce_invariants:
        invariants = check_publication_invariants(state)
        if invariants:
            raise SpineError(
                "state_invariant_violation",
                "внутренняя ошибка: нарушен инвариант контура публикаций",
                exit_code=2,
                violations=invariants,
            )
    schema = state_schema()
    if schema:
        errors = check_schema(state, schema)
        if errors:
            raise SpineError(
                "state_schema_violation",
                "внутренняя ошибка: state не соответствует run-state.schema.json",
                exit_code=2,
                violations=errors,
            )
    atomic_write_bytes(run_dir / STATE_NAME, (json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def log_event(state: Dict[str, Any], event: str, detail: Optional[str] = None) -> None:
    state["history"].append({"at": now_iso(), "event": event, "phase": state["phase"], "detail": detail})
    state["history"] = state["history"][-200:]


def iter_runs(base_dir: Path) -> List[Tuple[Path, Dict[str, Any]]]:
    if not base_dir.is_dir():
        return []
    found: List[Tuple[Path, Dict[str, Any]]] = []
    for child in sorted(base_dir.iterdir()):
        if not child.is_dir() or not (child / STATE_NAME).exists():
            continue
        try:
            found.append((child, json.loads((child / STATE_NAME).read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError):
            continue
    found.sort(key=lambda item: item[1].get("created_at") or "")
    return found


def find_active(base_dir: Path) -> Optional[Tuple[Path, Dict[str, Any]]]:
    info = read_lock(base_dir)
    if info and info.get("run_id"):
        run_dir = base_dir / info["run_id"]
        if (run_dir / STATE_NAME).exists():
            state = load_state(run_dir)
            if state.get("status") not in TERMINAL_STATUSES:
                return run_dir, state
    candidates = [item for item in iter_runs(base_dir) if item[1].get("status") not in TERMINAL_STATUSES]
    return candidates[-1] if candidates else None


def require_run(args: argparse.Namespace) -> Run:
    base = resolve_base(args.base)
    base_dir = base_runs_dir(base)
    if args.run:
        run_dir = base_dir / args.run
        if not (run_dir / STATE_NAME).exists():
            raise SpineError("run_not_found", "run {} по этой базе не найден".format(args.run))
        return Run(base, base_dir, run_dir, load_state(run_dir))
    found = find_active(base_dir)
    if not found:
        raise SpineError("no_active_run", "по базе нет активного run — начни со `start`")
    return Run(base, base_dir, found[0], found[1])


def require_live(state: Dict[str, Any]) -> None:
    if state["status"] in TERMINAL_STATUSES:
        raise SpineError("run_terminal", "run в статусе {} — действия недоступны".format(state["status"]))


def require_phase(state: Dict[str, Any], phase: str, allow: Tuple[str, ...] = ()) -> None:
    require_live(state)
    if state["status"] == "failed":
        raise SpineError(
            "run_failed",
            "нарушен precondition run_active: run в статусе failed — нужен `restart-from` или `abandon`",
        )
    allowed = (phase,) + tuple(allow)
    if state["phase"] not in allowed:
        raise SpineError(
            "phase_order",
            "нарушен precondition phase_order: текущая фаза {}, подана {}".format(state["phase"], phase),
        )


def set_phase(state: Dict[str, Any], phase: str) -> None:
    state["phase"] = phase
    state["phase_status"] = initial_phase_status(phase)
    state["phases"][phase]["status"] = state["phase_status"]


def mark_validated(state: Dict[str, Any], phase: str, artifact: Optional[str] = None,
                   digest: Optional[str] = None, **extra: Any) -> None:
    record = state["phases"][phase]
    record.update({"status": "validated", "updated_at": now_iso()})
    if artifact is not None:
        record["artifact"] = artifact
    if digest is not None:
        record["artifact_hash"] = digest
    record.update(extra)


def rel_to_run(path: Path, run_dir: Path) -> str:
    return str(path.relative_to(run_dir.resolve()))


def parse_meta(raw: List[str], phase: str) -> Dict[str, Any]:
    allowed = META_WHITELIST.get(phase, ())
    meta: Dict[str, Any] = {}
    for item in raw or []:
        if "=" not in item:
            raise SpineError("bad_meta", "--meta ожидает k=v, получено: {}".format(item), exit_code=2)
        key, value = item.split("=", 1)
        key = key.strip()
        if key not in allowed:
            raise SpineError(
                "meta_not_allowed",
                "ключ meta `{}` не разрешён на фазе {}".format(key, phase),
                exit_code=2,
            )
        low = value.strip().lower()
        meta[key] = True if low == "true" else False if low == "false" else value.strip()
    return meta


def record_input(state: Dict[str, Any], phase: str, name: str, path: Path, run_dir: Path) -> Dict[str, Any]:
    entry = {
        "path": rel_to_run(path, run_dir),
        "hash": artifact_hash(path),
        "recorded_at": now_iso(),
    }
    state["inputs"].setdefault(phase, {})[name] = entry
    return entry


def idempotent_ok(state: Dict[str, Any], phase: str, digest: str) -> bool:
    record = state["phases"][phase]
    return record["status"] == "validated" and record["artifact_hash"] == digest


# --------------------------------------------------------------------------- #
# Бизнес-слой: этап, реплика, режим показа
# --------------------------------------------------------------------------- #

def is_debug(state: Dict[str, Any]) -> bool:
    return bool(state.get("debug"))


def debug_label(state: Dict[str, Any]) -> str:
    return "технический (debug)" if is_debug(state) else "бизнес-вид"


def business_stage(phase: str) -> str:
    for stage, phases in BUSINESS_STAGES:
        if phase in phases:
            return stage
    return BUSINESS_STAGES[0][0]


def business_block(stage: str, say: Optional[str] = None) -> Dict[str, Any]:
    return {"stage": stage, "say": say}


def business_say_for_next(state: Dict[str, Any], phase: str) -> Dict[str, Any]:
    """Реплика этапа — однократно на этап; мутирует state, вызов требует save_state.

    Прогресс внутри этапа проходит молча: повторный `next` той же фазы (и любой
    другой фазы того же этапа) отдаёт say=null. Экраны решений — исключение: их
    текст нужен на каждый `next` паузы, показ повторно решает координатор.
    """
    stage = business_stage(phase)
    if state.get("business_return_pending"):
        # Реплика возврата — раньше экранной ветки: restart-from на саму паузу
        # обязан прозвучать возвратом, текст экрана идёт следом в той же реплике.
        say: Optional[str] = "Возвращаюсь к шагу: {}".format(stage)
        if phase in BUSINESS_PAUSE_SCREENS:
            say = "{} {}".format(say, BUSINESS_SCREENS[phase])
    elif phase in BUSINESS_PAUSE_SCREENS:
        say = BUSINESS_SCREENS[phase]
    elif phase in BUSINESS_SCREENS:
        # Экран 3: его текст отдаёт `show deliver`, названием этапа не говорим.
        say = None
    elif state.get("business_last_announced_stage") != stage:
        say = stage
    else:
        say = None
    state["business_last_announced_stage"] = stage
    state["business_return_pending"] = False
    return business_block(stage, say)


def business_resume_say(state: Dict[str, Any]) -> Dict[str, Any]:
    """`resume` говорит всегда: новая сессия не знает, что уже прозвучало."""
    stage = business_stage(state["phase"])
    date, topic = state["immutable"]["date"], state["immutable"]["topic"]
    if date and topic:
        say = "Продолжаю разбор встречи {} — {}, остановились на: {}".format(date, topic, stage)
    else:
        say = "Продолжаю разбор встречи, остановились на: {}".format(stage)
    return business_block(stage, say)


# --------------------------------------------------------------------------- #
# start
# --------------------------------------------------------------------------- #

def skill_version_gate(base: Path) -> Tuple[Optional[str], List[str]]:
    """Версионное рукопожатие через базу (пакет 0 волны G, 03_backlog 31.07).

    Builder кладёт в базу маркер версии + свежий `.skill`-артефакт; установленный
    ZIP-скилл несёт свою версию (штамп builder в SKILL_VERSION). Отставание →
    бизнес-строка «установите новую версию»; маркер с fail_closed (breaking) →
    отказ start. Spine видит ФС базы — гейт код-enforceable, в отличие от показа.
    dev-сборка из дерева и база без маркера гейт не включают.
    """
    if SKILL_VERSION == "dev":
        return None, []
    marker_path = base / SKILL_VERSION_MARKER
    if not marker_path.is_file():
        return None, []
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, []
    version = marker.get("version")
    if not version or version == SKILL_VERSION:
        return None, []
    say = ("В базе лежит новая версия навыка разбора встреч — установите файл "
           "{} (Settings → Skills) и начните новую сессию.".format(
               marker.get("artifact") or "архива навыка из базы"))
    if marker.get("fail_closed"):
        raise SpineError(
            "skill_version_stale",
            "нарушен precondition skill_version: установленная версия {} отстаёт от "
            "версии базы {} — обновление обязательно (breaking)".format(
                SKILL_VERSION, version),
            payload={"skill_version": SKILL_VERSION, "base_version": version,
                     "artifact": marker.get("artifact"),
                     "business": {"stage": None, "say": say}})
    return version, ["Пользователю: {}".format(say)]


def cmd_start(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    base = resolve_base(args.base)
    stale_version, version_lines = skill_version_gate(base)
    result = canon_check.check_canon(base, runs_root())
    if not result["ok"]:
        raise SpineError(
            "canon_check_failed",
            "нарушен precondition base_is_canonical: база не готова к пайплайну",
            violations=result["errors"],
        )

    transcript = Path(args.transcript).expanduser()
    if not transcript.is_absolute():
        transcript = Path.cwd() / transcript
    transcript = transcript.resolve()
    if not transcript.is_file():
        raise SpineError("transcript_missing", "транскрипт не найден: {}".format(transcript))

    base_dir = base_runs_dir(base)
    run_id = "{}-{}".format(time.strftime("%Y%m%d-%H%M%S"), uuid.uuid4().hex[:6])
    acquire_lock(base_dir, run_id)
    try:
        run_dir = base_dir / run_id
        (run_dir / ARTIFACTS_DIRNAME).mkdir(parents=True)
        # Карта встреч строится кодом один раз на run: узел locate получает её
        # на вход, а не скребёт базу сам (spine-contracts §5).
        meetings_map = canon_check.build_meetings_map(base)
        map_hash = write_json_artifact(run_dir / ART_MEETINGS_MAP, meetings_map)
        state = new_state(run_id, base, transcript, sha256_file(transcript), ART_MEETINGS_MAP,
                          map_hash, debug=bool(getattr(args, "debug", False)))
        save_state(run_dir, state)
    except Exception:
        release_lock(base_dir, run_id)
        raise

    payload = {
        "ok": True,
        "run_id": run_id,
        "base_id": state["base_id"],
        "base": str(base),
        "run_dir": str(run_dir),
        "phase": state["phase"],
        "phase_status": state["phase_status"],
        "canon": state["canon"],
        "meetings_dirs": len(meetings_map["meetings_dirs"]),
        "debug": is_debug(state),
        "next_command": "next",
    }
    if stale_version is not None:
        payload["skill_version"] = SKILL_VERSION
        payload["base_version"] = stale_version
    lines = [
        "Run начат: {}".format(run_id),
        "Run-каталог: {}".format(run_dir),
        "Карта встреч: каталогов meetings/ — {}".format(len(meetings_map["meetings_dirs"])),
        "Режим показа: {}".format(debug_label(state)),
        "Фаза: {} ({}) — дальше `next`".format(state["phase"], state["phase_status"]),
    ]
    return payload, version_lines + lines


# --------------------------------------------------------------------------- #
# status / list / next / resume / abandon / restart-from
# --------------------------------------------------------------------------- #

def status_payload(run: Run) -> Dict[str, Any]:
    state = run.state
    return {
        "ok": True,
        "run_id": state["run_id"],
        "base_id": state["base_id"],
        "base": state["base_path"],
        "run_dir": str(run.run_dir),
        "status": state["status"],
        "phase": state["phase"],
        "phase_status": state["phase_status"],
        "apply_status": state["apply_status"],
        "debug": is_debug(state),
        "date": state["immutable"]["date"],
        "topic": state["immutable"]["topic"],
        "blockers": state["blockers"],
        "side_effects": state["side_effects"],
        # Контур публикаций (B№4): обе оси состояний kinds + носитель отказа.
        "publication_conflicts": state.get("publication_conflicts") or [],
        "publication_resolutions": state.get("publication_resolutions") or {},
        "publication_refusals": state.get("publication_refusals") or {},
        "phases": {
            name: {
                "status": record["status"],
                "artifact": record["artifact"],
                "artifact_hash": record["artifact_hash"],
                "rework_count": record["rework_count"],
            }
            for name, record in state["phases"].items()
        },
    }


def cmd_status(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    run = require_run(args)
    payload = status_payload(run)
    payload["stage"] = business_stage(run.state["phase"])
    lines = [
        "Run {} — {}".format(payload["run_id"], payload["status"]),
        "Фаза: {} ({})".format(payload["phase"], payload["phase_status"]),
        "Этап разбора: {}".format(payload["stage"]),
        "Режим показа: {}".format(debug_label(run.state)),
        "Встреча: {} / {}".format(payload["date"] or "—", payload["topic"] or "—"),
        "Run-каталог: {}".format(payload["run_dir"]),
    ]
    for item in payload["blockers"]:
        lines.append("Блокер [{}]: {}".format(item.get("code"), item.get("message")))
    # Пауза публикаций — производное состояние, отдельной строкой (B№4 §2 п.2).
    if payload["publication_conflicts"]:
        lines.append("Пауза публикаций: конфликтов {}".format(
            len(payload["publication_conflicts"])))
        lines += ["  [{}] {} · {}".format(item["kind"], item["reason"], item["path"])
                  for item in payload["publication_conflicts"]]
    for kind, item in sorted(payload["publication_resolutions"].items()):
        lines.append("  решение {}: {}{}".format(
            kind, item["choice"], " (исполнено)" if item.get("executed") else ""))
    for kind in sorted(payload["publication_refusals"]):
        lines.append("  отказ от записи: {}".format(kind))
    for record in run.state["side_effects"].get("replaced") or []:
        # Включая терминальные aborted-записи с копиями в архиве: осиротевшие
        # копии видимы между попытками, не только в abandon.
        lines.append("  журнал замены {}: {} → {}".format(
            record["publication"], record["stage"], record.get("to") or "—"))
    return payload, lines


def cmd_debug(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    """Переключатель режима показа — доступен в любой момент run, включая паузы."""
    run = require_run(args)
    state = run.state
    if bool(args.on) == bool(args.off):
        raise SpineError("bad_usage", "нужен ровно один из флагов --on / --off", exit_code=2)
    state["debug"] = bool(args.on)
    log_event(state, "debug", detail="on" if args.on else "off")
    save_state(run.run_dir, state)

    payload = status_payload(run)
    payload["debug"] = state["debug"]
    lines = ["Режим показа: {}".format(debug_label(state))]
    # Экран решений — файл, связанный hash'ем: переключение режима его не
    # перерисовывает. Пересобирает штатный повторный `compose`; номера пунктов и
    # compose-map детерминированы, поэтому механизм accept от этого не меняется.
    payload["compose_rerender_required"] = bool(
        state["phase"] == "accept" and state["compose"]["hash"])
    if payload["compose_rerender_required"]:
        lines.append("Экран решений собран в прежнем режиме — повтори `compose`, "
                     "чтобы увидеть его в новом (номера пунктов не изменятся)")
    return payload, lines


def cmd_list(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    base = resolve_base(args.base)
    base_dir = base_runs_dir(base)
    runs = []
    for run_dir, state in iter_runs(base_dir):
        runs.append({
            "run_id": state["run_id"],
            "status": state["status"],
            "phase": state["phase"],
            "phase_status": state["phase_status"],
            "created_at": state["created_at"],
            "date": state["immutable"]["date"],
            "topic": state["immutable"]["topic"],
            "run_dir": str(run_dir),
        })
    payload = {"ok": True, "base": str(base), "base_id": compute_base_id(base), "runs": runs}
    lines = ["Runs по базе {}: {}".format(base, len(runs))]
    for item in runs:
        lines.append("  {}  {:<9} {:<9} {} / {}".format(
            item["run_id"], item["status"], item["phase"], item["date"] or "—", item["topic"] or "—"))
    return payload, lines


def meetings_map_discrepancy(run: Run) -> Optional[Dict[str, Any]]:
    """Фактический hash карты встреч против зафиксированного на `start`.

    Карта — единственный вход маршрутизации узла locate. Её подмена между `start`
    и выбором места обязана быть видимой, иначе граница КОД/LLM декларативна.
    """
    canon = run.state.get("canon") or {}
    rel = canon.get("meetings_map")
    if not rel:
        return None
    path = run.run_dir / rel
    if not path.is_file():
        return violation("artifact_missing", "карта встреч исчезла из run-каталога", path=str(path))
    try:
        digest = artifact_hash(path)
    except SpineError as exc:
        return violation("artifact_unreadable", exc.message, path=str(path))
    if digest != canon.get("meetings_map_hash"):
        return violation("artifact_hash_mismatch", "карта встреч изменена после start", path=str(path))
    return None


def require_meetings_map(run: Run) -> None:
    item = meetings_map_discrepancy(run)
    if not item:
        return
    raise SpineError(
        item["code"],
        "карта встреч расходится с зафиксированной на start: {}".format(item["message"]),
        violations=[item],
        payload={"recovery": "карта неизменяема внутри run — начни run заново (`start`)",
                 "error_class": "blocker"},
    )


def resolve_node_inputs(manifest: Dict[str, Any], run: Run) -> List[Dict[str, Any]]:
    state = run.state
    resolved: List[Dict[str, Any]] = []
    for item in manifest.get("inputs", []):
        entry = {"name": item["name"], "from": item["from"], "optional": bool(item.get("optional"))}
        source = item["from"]
        value: Optional[str] = None
        if source == "run.transcript":
            value = state["immutable"]["transcript_path"]
        elif source == "run.meetings_map":
            # Выдача карты узлу — точка сверки hash: подменённую карту не отдаём.
            require_meetings_map(run)
            canon = state.get("canon") or {}
            if canon.get("meetings_map"):
                value = str(run.run_dir / canon["meetings_map"])
                entry["hash"] = canon.get("meetings_map_hash")
        elif source.startswith("phase:"):
            phase_name, field = source[len("phase:"):].split(".", 1)
            record = state["phases"].get(phase_name, {})
            if field == "artifact" and record.get("artifact"):
                value = str(run.run_dir / record["artifact"])
                entry["hash"] = record.get("artifact_hash")
            elif field == "normalized":
                norm = state["normalized"].get(phase_name)
                if norm:
                    value = str(run.run_dir / norm["path"])
                    entry["hash"] = norm["hash"]
        elif source.startswith("input:"):
            phase_name, field = source[len("input:"):].split(".", 1)
            record = state["inputs"].get(phase_name, {}).get(field)
            if record:
                value = str(run.run_dir / record["path"])
                entry["hash"] = record["hash"]
        elif source == "deliver.decisions":
            record = state["deliver"].get("decisions")
            if record:
                candidate = run.run_dir / record["path"]
                # Гейт целостности: пропавший или подменённый вход не отдаётся
                # узлу как available (связка B5: Codex Medium, kimi M2).
                if candidate.is_file() and artifact_hash(candidate) == record["hash"]:
                    value = str(candidate)
                    entry["hash"] = record["hash"]
        entry["path"] = value
        entry["available"] = value is not None
        if value is None and not entry["optional"]:
            entry["unresolved"] = True
        resolved.append(entry)
    return resolved


HITL_MANIFEST = {
    "confirm": {
        "instruction": "Ожидание человека: покажи пользователю рендер `show summary` и передай его решение",
        "expected_commands": [
            "show summary",
            "submit confirm --approved [--corrections <файл>]",
            "submit confirm --rejected --corrections <файл>",
        ],
        # `debug` разрешён на паузе: пользователь спрашивает «откуда это?» именно
        # здесь, и техдетали должны включаться без выхода из паузы (kimi H1).
        "allowed_commands": ["show summary", "submit confirm", "debug", "status", "resume",
                             "restart-from", "abandon"],
        "lines": [
            "Покажи пользователю: show summary",
            "Затем: submit confirm --approved | --rejected --corrections <файл>",
        ],
    },
    "accept": {
        "instruction": "Ожидание человека: покажи пользователю рендер `compose` и передай "
                       "ответы на вопросы + решения по остальным пунктам",
        "expected_commands": [
            "accept --answer <q>=<опция|default> … [--take <id|№,…>] [--reject <id|№,…>] "
            "[--already <id|№,…>] [--amend <id>=<файл>] [--meta ack_unresolved=true]",
        ],
        "allowed_commands": ["accept", "compose", "compose --expand", "debug", "status",
                             "resume", "restart-from", "abandon"],
        # Показ = полный текст рендера в сообщении (правило волны E): компактность
        # — свойство самого рендера v3, а не право координатора сокращать.
        "lines": [
            "Покажи пользователю полный текст рендера `compose` в сообщении",
            "По каждому вопросу экрана получи ответ и передай: accept --answer <q>=<опция|default> "
            "(«решайте сами» → default)",
            "По советуемым достаточно одной фразы: «берём всё советуемое» → --take по всем "
            "непокрытым номерам; исключения — поимённо; ответ на вопрос старше bulk-фразы",
            "Отклонённое со словами «уже есть/уже делаем» помечай --already — "
            "это включит пункт в Telegram-план как идущую работу",
            "«Покажи пункт полностью» → compose --expand <№,…|all>",
        ],
    },
}


def publication_pause_manifest(run: Run, state: Dict[str, Any], pause: Dict[str, Any]
                               ) -> Tuple[Dict[str, Any], List[str]]:
    """Манифест паузы публикаций по состояниям конфликтов (B№4 §6)."""
    phase = "apply"
    stage = business_stage(phase)
    resolvable, unreadable = pause["resolvable"], pause["unreadable"]
    unreadable_only = bool(unreadable) and not resolvable
    if unreadable_only:
        # Блокер-флоу: `say` пуст осознанно — говорит координатор по шаблону
        # блокера SKILL.md; реплику этапа не тратим.
        business = business_block(stage)
    else:
        business = business_say_for_next(state, phase)
        if pause["say"]:
            business["say"] = ("{} {}".format(business["say"], pause["say"])
                               if business["say"] else pause["say"])
        save_state(run.run_dir, state)

    allowed = ["resolve-publications", "apply", "slice", "debug", "status", "resume",
               "restart-from", "abandon"]
    # `resolve-publications` уходит из allowed, только когда решать нечего вовсе
    # (все конфликты нечитаемы). Решённые, но не исполненные — передумать можно
    # до исполнения (§6; круг 2, Opus L2).
    if not any(item["choices"] for item in pause["conflicts"]):
        allowed = [item for item in allowed if item != "resolve-publications"]
    payload = {
        "ok": True,
        "run_id": state["run_id"],
        "kind": "hitl" if (resolvable or unreadable) else "spine",
        "phase": phase,
        "phase_status": state["phase_status"],
        "apply_status": state["apply_status"],
        "pause": "publication_conflict",
        "instruction": ("Ожидание человека: передай пользователю вопрос о занятом файле "
                        "и его решение" if resolvable else
                        "Ожидание человека: нечитаемый путь публикации чинится в базе руками"),
        "publication_conflicts": pause["conflicts"],
        "publication_resolutions": state.get("publication_resolutions") or {},
        "publication_refusals": state.get("publication_refusals") or {},
        "expected_commands": pause["expected_commands"],
        "allowed_commands": allowed,
        "business": business,
    }
    lines = []
    if resolvable:
        lines.append("Пауза: путь публикации занят — нужно решение пользователя")
        lines += ["Затем: {}".format(item) for item in pause["expected_commands"]]
    elif unreadable:
        lines.append("apply встанет на нечитаемой цели — сначала почини базу")
    else:
        lines.append("Решения записаны — повтори `apply`")
    if resolvable and unreadable:
        lines.append("После решений останется нечитаемая цель — её чинить в базе руками")
    for item in pause["execution_blockers"]:
        # Манифест никогда не обещает невозможный прогресс.
        lines.append("Повтор не поможет, пока не устранена причина: {}".format(
            item.get("message")))
    if is_debug(state):
        # Техдетали (пути, hash'и, kind, стадии журнала) — в payload всегда,
        # в text-строках только в debug (§6).
        lines += ["  [{}] {} · {}".format(item["kind"], item["reason"], item["path"])
                  for item in pause["conflicts"]]
        lines += ["  журнал: {} {} ({})".format(record["publication"], record["stage"],
                                                record["from"])
                  for record in state["side_effects"].get("replaced") or []
                  if record["stage"] not in ("done", "aborted")]
    if business["say"]:
        lines.append("Пользователю: {}".format(business["say"]))
    return payload, lines


def cmd_next(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    run = require_run(args)
    state = run.state
    phase = state["phase"]

    if state["status"] in TERMINAL_STATUSES:
        payload = {
            "ok": True,
            "run_id": state["run_id"],
            "status": state["status"],
            "kind": "terminal",
            "allowed_commands": ["list", "status", "start"],
            "business": business_block(business_stage(phase)),
        }
        return payload, ["Run {} — {}: действий не требуется".format(state["run_id"], state["status"])]

    if state["status"] == "failed":
        # Цель рестарта — из блокера: источник расхождения бывает выше по графу,
        # и рестарт фазы падения там перебирает верную сторону (находка №22).
        target = next((b.get("restart_phase") for b in state["blockers"]
                       if b.get("restart_phase")), phase)
        payload = {
            "ok": True,
            "run_id": state["run_id"],
            "status": "failed",
            "kind": "failed",
            "phase": phase,
            "blockers": state["blockers"],
            "restart_phase": target,
            "allowed_commands": [
                "resume", "status",
                "restart-from --phase {}".format(target),
                "abandon",
            ],
            # Про блокер пользователю говорит координатор по шаблону класса
            # (SKILL.md), а не реплика этапа — say здесь пуст осознанно.
            "business": business_block(business_stage(phase)),
        }
        lines = ["Run в статусе failed на фазе {}".format(phase)]
        lines += ["Блокер [{}]: {}".format(b.get("code"), b.get("message")) for b in state["blockers"]]
        lines.append("Доступно: restart-from --phase {} / resume / abandon".format(target))
        return payload, lines

    # Ситуативная пауза публикаций (B№4 §6): не новая фаза графа и не 4-й экран —
    # производное состояние `phase == apply` + непустые конфликты.
    pause = publication_pause(state)
    if pause is not None:
        return publication_pause_manifest(run, state, pause)

    row = require_implemented(phase)

    # Реплика этапа считается один раз на вызов и сразу фиксируется в state:
    # иначе повторный `next` внутри этапа заново объявил бы пользователю то же.
    business = business_say_for_next(state, phase)
    save_state(run.run_dir, state)
    say_lines = ["Пользователю: {}".format(business["say"])] if business["say"] else []

    if row["kind"] == "hitl":
        manifest = HITL_MANIFEST[phase]
        payload = {
            "ok": True,
            "run_id": state["run_id"],
            "kind": "hitl",
            "phase": phase,
            "phase_status": state["phase_status"],
            "instruction": manifest["instruction"],
            "expected_commands": list(manifest["expected_commands"]),
            "allowed_commands": list(manifest["allowed_commands"]),
            "business": business,
        }
        return payload, (["Фаза {}: ожидание человека".format(phase)]
                         + list(manifest["lines"]) + say_lines)

    if row["kind"] == "spine":
        command = row["command"]
        payload = {
            "ok": True,
            "run_id": state["run_id"],
            "kind": "spine",
            "phase": phase,
            "phase_status": state["phase_status"],
            "expected_commands": [command],
            "allowed_commands": [command, "status", "resume", "restart-from", "abandon"],
            "business": business,
        }
        return payload, ["Фаза {}: команда spine — `{}`".format(phase, command)] + say_lines

    if phase == "review":
        packages = state["review"]["packages"]
        if not packages:
            payload = {
                "ok": True,
                "run_id": state["run_id"],
                "kind": "spine",
                "phase": phase,
                "phase_status": state["phase_status"],
                "expected_commands": ["export-review"],
                "allowed_commands": ["export-review", "status", "resume", "restart-from", "abandon"],
                "business": business,
            }
            return payload, (["Фаза review: сперва `export-review` — spine нарежет пакеты ревьюеров"]
                             + say_lines)
        manifest = node_manifest("review")
        prompt_path = SKILL_ROOT / manifest["prompt"]
        done = state["review"]["verdicts"]
        pending = [p for p in packages if p["package_id"] not in done]
        # Частично покрытые пакеты: недостающее считается по копилке. Копилка
        # hash-bound и здесь: битый/подменённый файл — пакет требуется целиком
        # (submit сбросит копилку тем же hash-чеком), next не падает (kimi L2).
        partial_missing: Dict[str, List[str]] = {}
        for item in packages:
            record = (state["review"].get("partial") or {}).get(item["package_id"])
            if not record:
                continue
            try:
                stored = run.path(record["path"])
                if not stored.is_file() or artifact_hash(stored) != record["hash"]:
                    raise ValueError("копилка недействительна")
                got = {v["delta_id"] for v in load_json_file(stored).get("verdicts", [])}
                partial_missing[item["package_id"]] = [
                    did for did in item["delta_ids"] if did not in got]
            except (SpineError, OSError, ValueError, KeyError, TypeError):
                partial_missing[item["package_id"]] = list(item["delta_ids"])
        payload = {
            "ok": True,
            "run_id": state["run_id"],
            "kind": "fanout",
            "phase": phase,
            "phase_status": state["phase_status"],
            "node": "review",
            "model": manifest.get("model"),
            "prompt": str(prompt_path),
            "prompt_exists": prompt_path.is_file(),
            "references": [str(SKILL_ROOT / ref) for ref in manifest.get("references", [])],
            "packages": [
                {
                    "package_id": item["package_id"],
                    "file": item["file"],
                    "path": str(run.run_dir / item["path"]),
                    "package_hash": item["package_hash"],
                    "delta_count": len(item["delta_ids"]),
                    "done": item["package_id"] in done,
                    # Частичное покрытие: недостающие delta_id названы прямо в
                    # манифесте — переспрашивается адресно, не пакет целиком.
                    "missing_delta_ids": partial_missing.get(item["package_id"]),
                    # Путь сдачи вердиктов: ревьюер пишет json-файл сюда сам
                    # (Write), как любой другой узел — координатор ничего не
                    # перекладывает и содержимое вердиктов не видит.
                    "output": str(run.run_dir / ART_VERDICTS_DIR / "{}.json".format(item["package_id"])),
                }
                for item in packages
            ],
            "pending": [item["package_id"] for item in pending],
            "verdict_file_contract": {
                "format": "json",
                "required": ["verdicts"],
                "verdict_item": ["delta_id", "verdict", "attack?",
                                 "dispute_class?", "reason?", "revised_text?"],
                "verdict_values": ["accept", "revise", "reject",
                                   "escalate_insufficient_evidence", "escalate_spec_gap"],
                # package_id/package_hash в файле не нужны: их проставляет spine
                # на приёме — привязка держится на --package и покрытии delta_id.
                "stamped_by_spine": ["package_id", "package_hash"],
            },
            "expected_commands": [
                "submit review --package {} --verdict {}".format(
                    item["package_id"],
                    run.run_dir / ART_VERDICTS_DIR / "{}.json".format(item["package_id"]))
                for item in pending
            ],
            "allowed_commands": ["submit review", "status", "resume", "restart-from", "abandon"],
            "business": business,
        }
        lines = ["Фаза review: {} пакет(ов), не покрыто {}".format(len(packages), len(pending))]
        lines += ["  {} → {} · package_hash {}".format(item["package_id"], item["file"], item["package_hash"])
                  for item in pending]
        lines.append("Один пакет = один независимый субагент-ревьюер (модель {})".format(manifest.get("model")))
        lines.append("Ревьюер сдаёт вердикты сам: json-файл по пути `output` его пакета (Write), "
                     "затем `submit review --package <id> --verdict <этот путь>`")
        lines.append("Форма файла — verdict_file_contract; package_id и package_hash "
                     "в файле не нужны, spine проставит их на приёме")
        return payload, lines

    if phase == "deliver":
        manifest = node_manifest(row["node"])
        prompt_path = SKILL_ROOT / manifest["prompt"]
        required = bool(state["context"].get("deliver_required"))
        payload = {
            "ok": True,
            "run_id": state["run_id"],
            "kind": "node",
            "phase": phase,
            "phase_status": state["phase_status"],
            "node": row["node"],
            "model": manifest.get("model"),
            "prompt": str(prompt_path),
            "prompt_exists": prompt_path.is_file(),
            "required": required,
            "inputs": resolve_node_inputs(manifest, run),
            "output": {"path": str(run.run_dir / manifest["output"]["path"]),
                       "format": manifest["output"].get("format")},
            "expected_commands": [
                "submit deliver --artifact {}".format(run.run_dir / manifest["output"]["path"]),
                "submit deliver --skip",
            ],
            # Третья HITL-пауза живёт отдельной веткой (не в HITL_MANIFEST) —
            # `debug` добавляется здесь же, иначе на экране 3 переключателя нет.
            "allowed_commands": ["submit deliver", "show deliver", "debug", "status", "resume",
                                 "restart-from", "abandon"],
            # say экрана 3 — в ответе `show deliver`: здесь текста сводки ещё нет.
            "business": business,
        }
        lines = [
            "Фаза deliver ({}): узел {}".format("обязательна" if required else "опциональна", row["node"]),
            "Затем: submit deliver --artifact <файл> либо --skip (решение пользователя)",
        ]
        return payload, lines + say_lines

    manifest = node_manifest(row["node"])
    prompt_path = SKILL_ROOT / manifest["prompt"]
    prompt_hash = sha256_file(prompt_path) if prompt_path.is_file() else None
    output = run.run_dir / manifest["output"]["path"]
    payload = {
        "ok": True,
        "run_id": state["run_id"],
        "kind": "node",
        "phase": phase,
        "phase_status": state["phase_status"],
        "node": row["node"],
        "model": manifest.get("model"),
        "prompt": str(prompt_path),
        "prompt_exists": prompt_path.is_file(),
        "prompt_hash": prompt_hash,
        "references": [str(SKILL_ROOT / ref) for ref in manifest.get("references", [])],
        "inputs": resolve_node_inputs(manifest, run),
        "output": {"path": str(output), "format": manifest["output"].get("format")},
        "rework_limit": manifest.get("rework_limit"),
        "rework_count": state["phases"][phase]["rework_count"],
        "expected_commands": ["submit {} --artifact {}".format(phase, output)],
        "allowed_commands": ["submit {}".format(phase), "status", "resume", "restart-from", "abandon"],
        "business": business,
    }

    state["phases"][phase]["prompt_hash"] = prompt_hash
    save_state(run.run_dir, state)

    lines = [
        "Фаза {}: узел {} (модель {})".format(phase, row["node"], manifest.get("model")),
        "Промпт: {}{}".format(prompt_path, "" if prompt_path.is_file() else " — файла ещё нет"),
        "Выход: {}".format(output),
        "Затем: submit {} --artifact {}".format(phase, output),
    ]
    return payload, lines + say_lines


def cmd_resume(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    run = require_run(args)
    state = run.state
    discrepancies: List[Dict[str, Any]] = []

    for name, record in state["phases"].items():
        if not record["artifact"]:
            continue
        path = run.run_dir / record["artifact"]
        if not path.is_file():
            discrepancies.append(violation("artifact_missing", "артефакт фазы {} исчез".format(name), phase=name, path=str(path)))
            continue
        try:
            digest = artifact_hash(path)
        except SpineError as exc:
            discrepancies.append(violation("artifact_unreadable", exc.message, phase=name, path=str(path)))
            continue
        if digest != record["artifact_hash"]:
            discrepancies.append(violation("artifact_hash_mismatch", "артефакт фазы {} изменён после submit".format(name), phase=name, path=str(path)))

    map_item = meetings_map_discrepancy(run)
    if map_item:
        discrepancies.append(dict(map_item, phase="start"))

    transcript = Path(state["immutable"]["transcript_path"])
    if state["status"] != "done":
        if not transcript.is_file():
            discrepancies.append(violation("transcript_missing", "транскрипт исчез", path=str(transcript)))
        elif sha256_file(transcript) != state["immutable"]["source_hash"]:
            discrepancies.append(violation("source_hash_mismatch", "транскрипт изменён после start", path=str(transcript)))

    compose = state["compose"]
    if compose["hash"]:
        path = run.run_dir / compose["artifact"]
        if not path.is_file():
            discrepancies.append(violation("compose_missing", "compose.md исчез", path=str(path)))
        elif sha256_file(path) != compose["hash"]:
            discrepancies.append(violation("compose_hash_mismatch", "compose.md изменён после рендера", path=str(path)))

    for item in state["side_effects"]["applied"]:
        path = Path(item["path"])
        if not path.is_file():
            discrepancies.append(violation("applied_file_missing", "применённый файл исчез", path=str(path)))
        elif item.get("hash_after") and sha256_file(path) != item["hash_after"]:
            discrepancies.append(violation("applied_file_changed", "применённый файл изменён после apply", path=str(path)))

    payload = status_payload(run)
    payload["discrepancies"] = discrepancies
    payload["ok"] = not discrepancies
    # Восстановление в новой сессии: реплика идёт независимо от last_announced —
    # пользователь не помнит, на чём остановились, а state читает только spine.
    payload["business"] = business_resume_say(state)
    lines = [
        "Run {} — {} (фаза {} / {})".format(state["run_id"], state["status"], state["phase"], state["phase_status"]),
        "Пользователю: {}".format(payload["business"]["say"]),
        "Расхождений: {}".format(len(discrepancies)),
    ]
    # Пауза публикаций — производное состояние: `resume` называет её отдельной
    # строкой, состояние восстанавливает `next` (B№4 §8).
    if publication_pause(state):
        lines.append("Пауза публикаций: конфликтов {} — дальше `next`".format(
            len(state["publication_conflicts"])))
    for item in discrepancies:
        lines.append("  - [{}] {}".format(item["code"], item["message"]))
    if discrepancies:
        raise SpineError("resume_discrepancies", "состояние run расходится с диском", violations=discrepancies, payload=payload)
    return payload, lines


def cmd_abandon(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    run = require_run(args)
    state = run.state
    if state["status"] == "abandoned":
        payload = status_payload(run)
        payload["already"] = True
        return payload, ["Run {} уже abandoned".format(state["run_id"])]
    require_live(state)

    state["status"] = "abandoned"
    log_event(state, "abandon")
    invariants = check_publication_invariants(state)
    save_state(run.run_dir, state, enforce_invariants=False)
    release_lock(run.base_dir, state["run_id"])

    side = state["side_effects"]
    # applied группируется по дельте: move — одна операция со списком путей,
    # а не набор строк по файлам (Codex final, Medium).
    applied_grouped: Dict[Tuple[Any, Any], Dict[str, Any]] = {}
    for item in side["applied"]:
        key = (item.get("delta_id"), item.get("operation"))
        rec = applied_grouped.setdefault(
            key, {"delta_id": item.get("delta_id"), "operation": item.get("operation"), "paths": []})
        if item.get("path") not in rec["paths"]:
            rec["paths"].append(item.get("path"))
    remaining = list(applied_grouped.values()) + list(side["published"]) + list(side["archived"])
    indeterminate: List[Dict[str, Any]] = []
    # Частичный apply: side_effects.applied заполняется только в конце apply,
    # правду о записях держит журнал (ревью 30.07, High: abandon обязан назвать
    # следы, а не рапортовать чистоту). done — оставшийся след; intent —
    # неопределённая операция обрыва, пути проверяются руками.
    if state["apply_status"] == "in_progress":
        base = Path(state["base_path"])
        for entry in read_journal(run):
            record = {"delta_id": entry.get("delta_id"),
                      "operation": entry.get("operation"),
                      "paths": [str(base / item["path"]) for item in entry.get("files", [])]}
            if entry.get("stage") == "done":
                remaining.append(record)
            else:
                indeterminate.append(record)
    # Журнал замен читается независимо от apply_status: done-копия в архиве —
    # реальный след и после completed (B№4 §4б).
    for record in state["side_effects"].get("replaced") or []:
        paths = [record["from"]] + ([record["to"]] if record.get("to") else [])
        item = {"delta_id": None, "operation": "replace:{}".format(record["publication"]),
                "paths": paths, "stage": record["stage"]}
        if record["stage"] == "done":
            remaining.append(item)
        elif record["stage"] == "aborted":
            if record.get("to") and record.get("aborted_from_stage") in ("archived", "unlinked"):
                item["operation"] = "отменённая замена, копия осталась"
                remaining.append(item)
            else:
                # Прерванный `intent`: копия не подтверждена — ровно
                # неопределённость обрыва, а не «следов нет» (круг 2, Opus L7).
                item["operation"] = "отменённая замена, копия не подтверждена"
                indeterminate.append(item)
        else:
            indeterminate.append(item)
    payload = status_payload(run)
    payload["ok"] = True
    payload["remaining_side_effects"] = remaining
    payload["indeterminate_side_effects"] = indeterminate
    payload["state_invariants"] = invariants
    def describe(item: Dict[str, Any]) -> str:
        if "paths" in item:  # запись из журнала apply
            return "{} ({}): {}".format(item.get("delta_id"), item.get("operation"),
                                        ", ".join(item["paths"]))
        return "{}: {}".format(item.get("delta_id") or item.get("kind") or "запись",
                               item.get("path", "?"))

    lines = ["Run {} прекращён.".format(state["run_id"])]
    if not (remaining or indeterminate):
        lines.append("Следов в базе не осталось")
    else:
        # Контракт (spine-contracts §5): вывод перечисляет side effects, а не
        # только считает их — пользователь видит, что именно осталось в базе.
        lines.append("В базе осталось записей: {}".format(len(remaining) + len(indeterminate)))
        lines += ["  - {}".format(describe(item)) for item in remaining]
        if indeterminate:
            lines.append("Неопределённые операции обрыва apply — проверь пути вручную:")
            lines += ["  - {}".format(describe(item)) for item in indeterminate]
    return payload, lines


# Артефакты L2 и фаза-производитель: каскадная инвалидация сносит всё, что
# произведено фазой ≥ target (артефакт самой target-фазы — по общему правилу
# итерации 1: запись в state обнуляется, файл остаётся).
L2_PRODUCERS: Tuple[Tuple[str, str, Tuple[str, ...]], ...] = (
    ("deltas", "normalized:deltas", (ART_DELTAS_NORM,)),
    ("canon", "normalized:canon", (ART_CANON_NORM,)),
    ("canon", "phase_a", ()),
    ("review", "review", (ART_PACKAGES_DIR, ART_VERDICTS_DIR)),
    ("review", "ledger", (ART_LEDGER,)),
    ("review", "post_validation", (ART_POST_VALIDATION,)),
    ("questions", "questions", (ART_QUESTIONS,)),
    ("compose", "compose", (ART_COMPOSE, ART_COMPOSE_HASH, ART_COMPOSE_MAP)),
    ("accept", "accept", (ART_ACCEPT,)),
    ("postcheck", "postcheck", (ART_POSTCHECK,)),
    # Вход deliver производится постчеком: рестарт ≤ postcheck сбрасывает его,
    # рестарт с deliver — сохраняет (узлу нужен вход).
    ("postcheck", "deliver", (ART_DELIVER_INPUT,)),
)


def invalidate_l2(run: Run, target_idx: int) -> None:
    state = run.state
    fresh = empty_l2_state()
    for phase, key, paths in L2_PRODUCERS:
        if phase_index(phase) < target_idx:
            continue
        if key.startswith("normalized:"):
            state["normalized"].pop(key.split(":", 1)[1], None)
        else:
            state[key] = fresh[key]
        for rel in paths:
            path = run.run_dir / rel
            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()
    state["unresolved"] = [
        item for item in state["unresolved"]
        if item["phase"] in phase_names() and phase_index(item["phase"]) < target_idx
    ]


def cmd_restart_from(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    run = require_run(args)
    state = run.state
    target = args.phase
    if target not in phase_names():
        raise SpineError("unknown_phase", "неизвестная фаза: {}".format(target), exit_code=2)
    require_implemented(target)
    if state["status"] in TERMINAL_STATUSES:
        raise SpineError("run_terminal", "run в статусе {} — restart недоступен".format(state["status"]))

    target_idx = phase_index(target)
    if target_idx > phase_index(state["phase"]):
        raise SpineError(
            "restart_forward",
            "нарушен precondition phase_order: restart-from вперёд (текущая фаза {}, подана {}) запрещён".format(
                state["phase"], target),
        )
    if state["apply_status"] == "completed" and target_idx <= phase_index("apply"):
        raise SpineError(
            "point_of_no_return",
            "нарушен precondition point_of_no_return: apply завершён, restart на фазы ≤ apply запрещён",
        )

    invalidated: List[str] = []
    for name in phase_names():
        idx = phase_index(name)
        if idx < target_idx:
            continue
        record = state["phases"][name]
        if idx > target_idx:
            if record["artifact"]:
                path = run.run_dir / record["artifact"]
                if path.is_file():
                    path.unlink()
            if record["status"] != "pending" or record["artifact"]:
                invalidated.append(name)
            state["inputs"].pop(name, None)
        record.update({
            "status": "pending",
            "artifact": None,
            "artifact_hash": None,
            "meta": {},
            "decision": None,
            "updated_at": now_iso(),
            # Явный рестарт фазы человеком снимает и её rework-счётчик — оба
            # бюджета. `rejection_seq` остаётся монотонным: нумерация копий
            # отклонённых артефактов — журнал разбора, а не бюджет.
            "rework_count": 0,
            "structural_rework_count": 0,
        })
        # Флаг деградации questions живёт в записи фазы ровно затем, чтобы
        # чистый повторный прогон вернул вопросный вид (hitl-v3-spec).
        record.pop("fallback", None)

    invalidate_l2(run, target_idx)

    # B№4 §8: цель ≤ apply чистит конфликты публикаций и НЕИСПОЛНЕННЫЕ решения
    # (стирание неисполненного keep ставит `publication_refusals` — отказ
    # пользователя переживает restart-from); executed-резолюции живут со своим
    # scope, журнал замен не трогается и предупреждает stage-aware.
    replacement_warnings: List[str] = []
    if target_idx <= phase_index("apply"):
        state["publication_conflicts"] = []
        for kind in sorted((state.get("publication_resolutions") or {})):
            drop_publication_resolution(state, kind)
        # Отказ, переживший рестарт, помечается: следующий цикл говорит о нём
        # нейтрально («ранее вы решили не записывать»), а свежий отказ этого же
        # цикла — штатным текстом `kept_target_vanished` (круг 2, Opus L1).
        for item in (state.get("publication_refusals") or {}).values():
            item["carried_over"] = True
        # Stage-aware предупреждения — часть контракта restart-from именно на
        # фазы ≤ apply (§8): на postcheck/deliver журнал ничего не меняет.
        for record in state["side_effects"].get("replaced") or []:
            if record["stage"] == "intent":
                replacement_warnings.append(
                    "замена {} была начата, копия не подтверждена — проверь {}".format(
                        record["from"], record["to"]))
            elif record["stage"] in ("archived", "unlinked"):
                replacement_warnings.append(
                    "в архиве осталась копия: {}".format(record["to"]))
            elif record["stage"] == "done" and record.get("to"):
                replacement_warnings.append("замена {} состоялась: старый в архиве {}".format(
                    record["from"], record["to"]))

    state["blockers"] = []
    if state["status"] == "failed":
        state["status"] = "active"
    # Возврат внутри этапа пользователя не касается; переход через границу этапа
    # обязан прозвучать заново — реплику скажет следующий `next`.
    crossed_stage = business_stage(target) != business_stage(state["phase"])
    set_phase(state, target)
    if crossed_stage:
        state["business_last_announced_stage"] = None
        state["business_return_pending"] = True
    log_event(state, "restart-from", detail=target)
    invariants = check_publication_invariants(state)
    save_state(run.run_dir, state, enforce_invariants=False)

    payload = status_payload(run)
    payload["restarted_from"] = target
    payload["invalidated"] = invalidated
    payload["state_invariants"] = invariants
    payload["business"] = business_block(business_stage(target))
    payload["replacement_warnings"] = replacement_warnings
    lines = [
        "Рестарт с фазы {}".format(target),
        "Инвалидировано фаз: {}".format(len(invalidated)),
    ]
    lines += ["  - {}".format(item) for item in replacement_warnings]
    return payload, lines


# --------------------------------------------------------------------------- #
# submit: locate / l1 / confirm
# --------------------------------------------------------------------------- #

def require_artifact(args: argparse.Namespace, run: Run) -> Path:
    if not args.artifact:
        raise SpineError("missing_artifact", "команда требует --artifact <путь>", exit_code=2)
    path = resolve_within(args.artifact, run.run_dir, "--artifact", "run-каталога")
    if not path.is_file():
        raise SpineError("artifact_missing", "артефакт не найден: {}".format(path))
    return path


def validate_protocol_dir(raw: str, run: Run, allow_new: bool = False) -> Tuple[Optional[Path], List[Dict[str, Any]]]:
    """Место протокола выбрал узел locate по карте встреч — spine проверяет четыре вещи.

    Path confinement (внутри базы, не symlink) · путь лежит в контуре `meetings`
    (допустима подпапка любой глубины: `.../meetings/one-to-one/petrov`) и не
    уходит в служебный каталог карты (`zz_archive`, `_private`, `_templates`…) ·
    существующий путь — именно каталог · каталог существует ЛИБО подан как
    create-предложение (`protocol_dir_new: true` в context-manifest).
    """
    base = run.base.resolve()
    errors: List[Dict[str, Any]] = []

    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / raw
    if path.is_symlink():
        errors.append(violation("protocol_dir_symlink", "protocol_dir — symlink, запрещено", field="$.protocol_dir"))
        return None, errors
    resolved = path.resolve()
    if resolved != base and base not in resolved.parents:
        errors.append(violation("protocol_dir_outside_base", "protocol_dir вне корня базы", field="$.protocol_dir"))
        return None, errors
    # Компоненты — от НЕрезолвнутого пути: resolve() съедает промежуточный
    # symlink, и обход ниже прошёл бы уже по реальным каталогам (Codex v3)
    try:
        parts = path.relative_to(base).parts
    except ValueError:
        parts = resolved.relative_to(base).parts
    if any(name in ("..", ".") for name in parts):
        errors.append(violation("protocol_dir_outside_base",
                                "protocol_dir содержит '.'/'..' — задай путь от корня базы",
                                field="$.protocol_dir"))
        return None, errors
    if MEETINGS_DIRNAME not in parts:
        errors.append(violation(
            "protocol_dir_not_meetings",
            "protocol_dir обязан лежать в каталоге `meetings` базы",
            field="$.protocol_dir",
        ))
        return None, errors

    # Служебное карта пропускает при обходе — местом протокола оно быть не может
    # НИ В КАКОЙ позиции пути (kimi v2 M1: `zz_archive/{узел}/meetings/` после
    # архивации узла существует и прошёл бы проверку только хвоста).
    service = [name for name in parts if name in canon_check.SCAN_SKIP]
    if service:
        errors.append(violation(
            "protocol_dir_service_component",
            "protocol_dir проходит через служебный каталог: {}".format(", ".join(sorted(set(service)))),
            field="$.protocol_dir",
        ))
        return None, errors

    # Покомпонентный обход существующих префиксов (Codex v2 / kimi L5): файл
    # или symlink в СЕРЕДИНЕ create-пути отклоняется на locate, а не на apply.
    probe = base
    for name in parts:
        probe = probe / name
        if probe.is_symlink():
            errors.append(violation(
                "protocol_dir_symlink",
                "компонент пути protocol_dir — symlink: {}".format(name),
                field="$.protocol_dir",
            ))
            return None, errors
        if probe.exists() and not probe.is_dir():
            errors.append(violation(
                "protocol_dir_not_a_directory",
                "компонент пути protocol_dir — не каталог: {}".format(name),
                field="$.protocol_dir",
            ))
            return None, errors
        if not probe.exists():
            break

    if not resolved.is_dir() and not allow_new:
        errors.append(violation(
            "protocol_dir_missing",
            "каталога протоколов нет в базе; новая папка — только create-предложением "
            "(`protocol_dir_new: true` в context-manifest)",
            field="$.protocol_dir",
        ))
    return (None if errors else resolved), errors


# Сколько мест-однофамильцев показать в отказе по контуру: подсказка, а не отчёт.
CONTOUR_CANDIDATE_LIMIT = 5


def contour_candidates(base: Path, wanted: str, limit: int = CONTOUR_CANDIDATE_LIMIT) -> List[str]:
    """Существующие места базы с тем же именем — подсказка к отказу по контуру.

    Узел locate ошибается в префиксе, а не в имени: `01_company/04_implementation`
    вместо корневого `04_implementation/`. Поэтому ищем по последнему сегменту —
    каталоги и файлы (у файла сравниваем и имя со суффиксом, и без).
    """
    name = delta_rules.norm_path(wanted).rstrip("/").rsplit("/", 1)[-1].lower()
    if not name:
        return []
    base_resolved = base.resolve()
    base_depth = len(base_resolved.parts)
    found: List[str] = []
    for root, dirnames, filenames in os.walk(str(base_resolved)):
        root_path = Path(root)
        if len(root_path.parts) - base_depth >= canon_check.SCAN_DEPTH:
            dirnames[:] = []
            continue
        dirnames[:] = sorted(d for d in dirnames
                             if d not in canon_check.SCAN_SKIP and not (root_path / d).is_symlink())
        for entry in list(dirnames) + sorted(filenames):
            low = entry.lower()
            if low == name or Path(entry).stem.lower() == name:
                found.append((root_path / entry).relative_to(base_resolved).as_posix())
    return sorted(set(found))[:limit]


def validate_contours(raw_items: List[Any], run: Run,
                      pending_dir: Optional[Path] = None) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Контур обязан существовать в базе — каталогом ИЛИ файлом (находки №20/№24).

    Spine принимал `contours` на веру, и выдуманный узел доживал до инвариантов
    пакета кодом A3 («затронутый узел не получил ни одной дельты») — там он
    выглядел ошибкой дельт и был непочиним по построению: дельты в несуществующий
    путь взяться неоткуда. Проверка стоит здесь, у источника.

    Файл — законный контур: по scaffold карточка разворачивается в каталог, и до
    разворачивания она файл. Покрытие такого контура держит A3 точным совпадением
    с `target_file` (`validate_deltas.py`), поэтому здесь `is_dir` не требуется.

    `pending_dir` — согласованное create-предложение `protocol_dir`: узла базы
    ещё нет, его заводит этот прогон, и контур-префикс такого каталога законно
    не существует. Единственное исключение из проверки.

    Возвращает пути от корня базы в POSIX-виде — дальше с ними сравнивает A3.
    """
    base = run.base.resolve()
    errors: List[Dict[str, Any]] = []
    normalized: List[str] = []

    for index, raw in enumerate(raw_items):
        field = "$.contours[{}]".format(index)
        text = str(raw or "").strip()
        if not text:
            errors.append(violation("contour_invalid_path", "контур пуст", field=field))
            continue
        path = Path(text).expanduser()
        if path.is_absolute():
            errors.append(violation(
                "contour_outside_base",
                "контур {} задан абсолютным путём — нужен путь от корня базы".format(text),
                field=field))
            continue
        parts = path.parts
        if any(name in ("..", ".") for name in parts):
            errors.append(violation(
                "contour_outside_base",
                "контур {} содержит '.'/'..' — задай путь от корня базы".format(text),
                field=field))
            continue
        service = [name for name in parts if name in canon_check.SCAN_SKIP]
        if service:
            errors.append(violation(
                "contour_service_component",
                "контур {} проходит через служебный каталог: {}".format(
                    text, ", ".join(sorted(set(service)))),
                field=field))
            continue

        probe = base
        broken = False
        for name in parts:
            probe = probe / name
            if probe.is_symlink():
                errors.append(violation(
                    "contour_symlink",
                    "компонент пути контура {} — symlink: {}".format(text, name),
                    field=field))
                broken = True
                break
        if broken:
            continue

        target = base / path
        pending = pending_dir is not None and (
            target == pending_dir or target in pending_dir.parents)
        if pending:
            normalized.append(Path(os.path.normpath(str(path))).as_posix())
            continue
        if not target.exists():
            errors.append(violation(
                "contour_missing",
                "контура {} нет в базе — путь взят не из дерева базы".format(text),
                field=field,
                candidates=contour_candidates(base, text)))
            continue
        resolved = target.resolve()
        if resolved != base and base not in resolved.parents:
            errors.append(violation(
                "contour_outside_base",
                "контур {} уводит за корень базы".format(text),
                field=field))
            continue
        normalized.append(resolved.relative_to(base).as_posix())

    return ([] if errors else normalized), errors


def find_duplicates(run: Run, protocol_dir: Path, date: str, topic: str) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    prefix = "{}_{}".format(date, topic)
    if protocol_dir.is_dir():
        for child in sorted(protocol_dir.iterdir()):
            if child.is_file() and child.name.startswith(prefix):
                found.append({"kind": "file", "path": str(child)})
    for run_dir, state in iter_runs(run.base_dir):
        if run_dir == run.run_dir:
            continue
        if state.get("status") == "done" and state["immutable"]["date"] == date and state["immutable"]["topic"] == topic:
            found.append({"kind": "run", "run_id": state["run_id"], "path": str(run_dir)})
    return found


def submit_locate(args: argparse.Namespace, run: Run) -> Tuple[Dict[str, Any], List[str]]:
    state = run.state
    require_live(state)
    # Место выбрано по карте — принимаем выбор только если карта та же самая.
    require_meetings_map(run)
    path = require_artifact(args, run)
    manifest, digest = read_structural_json(run, "locate", path)
    if idempotent_ok(state, "locate", digest):
        payload = status_payload(run)
        payload["idempotent"] = True
        return payload, ["Тот же артефакт locate уже принят — состояние не изменилось"]
    require_phase(state, "locate")
    meta = parse_meta(args.meta, "locate")

    errors = check_schema(manifest, CONTEXT_MANIFEST_SCHEMA)
    if not errors:
        try:
            datetime.strptime(manifest["date"], "%Y-%m-%d")
        except ValueError:
            errors.append(violation("date_invalid", "поле $.date не является календарной датой", field="$.date"))
    errors.extend(l1_context_unknown_fields(manifest))
    if errors:
        raise structural_reject(
            run, "locate", "context_manifest_invalid",
            "context-manifest не прошёл проверку схемы",
            structural_recovery("context_manifest_invalid", "locate", items=violation_digest(errors)),
            artifact=path, violations=errors)

    # Гейт размера — сразу после схемы и ДО привязки immutable/context: отказ не
    # оставляет за собой ни одного поля фазы (инвариант отказа D-B п.5е).
    size_report = payload_size_report(path, path.read_bytes(), manifest)
    if size_report["total_bytes"] > CONTEXT_MAX_BYTES and not meta.get("allow_large_context"):
        raise structural_reject(
            run, "locate", "context_oversize",
            "context-manifest {} Б превышает лимит {} Б".format(
                size_report["total_bytes"], CONTEXT_MAX_BYTES),
            structural_recovery("context_oversize", "locate",
                                n=CONTEXT_MAX_BYTES // 1024,
                                field=size_report["largest"] or "l1_context"),
            artifact=path,
            violations=[violation(
                "context_oversize",
                "манифест {} Б при лимите {} Б".format(size_report["total_bytes"], CONTEXT_MAX_BYTES),
                field=size_report["largest"])],
            payload={"size_report": size_report})

    protocol_dir_new = bool(manifest.get("protocol_dir_new", False))
    protocol_dir, dir_errors = validate_protocol_dir(manifest["protocol_dir"], run, protocol_dir_new)
    if dir_errors:
        raise structural_reject(
            run, "locate", "context_manifest_invalid", "protocol_dir не прошёл проверку",
            structural_recovery("context_manifest_invalid", "locate", items=violation_digest(dir_errors)),
            artifact=path, violations=dir_errors)

    contours, contour_errors = validate_contours(
        manifest["contours"], run,
        pending_dir=protocol_dir if protocol_dir_new and not protocol_dir.is_dir() else None)
    if contour_errors:
        raise structural_reject(
            run, "locate", "contours_invalid", "контуры не прошли проверку по дереву базы",
            structural_recovery("contours_invalid", "locate", items=violation_digest(
                contour_errors, key="message")),
            artifact=path, violations=contour_errors,
            payload={"candidates": {
                item["field"]: item["candidates"]
                for item in contour_errors if item.get("candidates")}})

    date, topic = manifest["date"], manifest["topic"]
    for field, value in (("date", date), ("topic", topic)):
        fixed = state["immutable"][field]
        if fixed is not None and fixed != value:
            raise SpineError(
                "immutable_field",
                "нарушен precondition immutable_fields: {} зафиксирован как {}".format(field, fixed),
            )

    duplicates = find_duplicates(run, protocol_dir, date, topic)
    if duplicates and not meta.get("allow_duplicate"):
        raise SpineError(
            "duplicate_meeting",
            "нарушен precondition no_duplicate: за ({}, {}) уже есть протокол/выжимка — это дообработка или новая встреча?".format(date, topic),
            violations=[violation("duplicate_found", "найден дубль", **item) for item in duplicates],
            payload={
                "duplicates": duplicates,
                "resolution": "решение пользователя: повтор с --meta allow_duplicate=true",
            },
        )

    state["immutable"]["date"] = date
    state["immutable"]["topic"] = topic
    state["context"].update({
        "meeting_type": manifest["meeting_type"],
        "protocol_dir": str(protocol_dir),
        "protocol_dir_new": protocol_dir_new and not protocol_dir.is_dir(),
        "protocol_required": bool(manifest.get("protocol_required", True)),
        "deliver_required": bool(manifest.get("deliver_required", False)),
        "allow_duplicate": bool(meta.get("allow_duplicate", False)),
        "duplicates": duplicates,
        # Пути от корня базы, канонизированные validate_contours: с ними
        # сравнивает A3, поэтому вид должен быть один и тот же.
        "contours": contours,
    })
    mark_validated(state, "locate", rel_to_run(path, run.run_dir), digest, meta=meta)
    set_phase(state, "l1")
    log_event(state, "submit:locate")
    save_state(run.run_dir, state)

    payload = status_payload(run)
    payload["artifact_hash"] = digest
    payload["duplicates"] = duplicates
    # Наблюдаемость размера — на успешном исходе тоже: разбивка байтов видна
    # координатору до того, как манифест дорастёт до гейта (D-C п.7).
    payload["size_report"] = size_report
    lines = [
        "locate принят: {} / {}".format(date, topic),
        "Протоколы: {}{}".format(protocol_dir, " (новая папка — создастся на apply)"
                                 if state["context"]["protocol_dir_new"] else ""),
        "Фаза: {} ({})".format(state["phase"], state["phase_status"]),
    ]
    return payload, lines


def submit_l1(args: argparse.Namespace, run: Run) -> Tuple[Dict[str, Any], List[str]]:
    state = run.state
    require_live(state)
    path = require_artifact(args, run)
    digest = artifact_hash(path)
    if idempotent_ok(state, "l1", digest):
        payload = status_payload(run)
        payload["idempotent"] = True
        return payload, ["Та же выжимка уже принята — состояние не изменилось"]
    require_phase(state, "l1")
    parse_meta(args.meta, "l1")

    text = path.read_text(encoding="utf-8")
    errors: List[Dict[str, Any]] = []
    if not text.strip():
        errors.append(violation("summary_empty", "выжимка пуста"))
    elif not any(line.startswith("## ") for line in text.splitlines()):
        errors.append(violation("summary_no_sections", "в выжимке нет ни одной секции `## `"))
    if errors:
        raise structural_reject(
            run, "l1", "summary_invalid", "выжимка не прошла проверку",
            structural_recovery("summary_invalid", "l1", reason=violation_digest(errors, key="message")),
            artifact=path, violations=errors)

    mark_validated(state, "l1", rel_to_run(path, run.run_dir), digest)
    set_phase(state, "confirm")
    log_event(state, "submit:l1")
    save_state(run.run_dir, state)

    payload = status_payload(run)
    payload["artifact_hash"] = digest
    lines = [
        "Выжимка принята ({} симв.)".format(len(text)),
        "Фаза: confirm — ожидание человека, показывай `show summary`",
    ]
    return payload, lines


# Куда рестартовать при нарушении инварианта: источник ошибки не всегда та фаза,
# на которой она поймана (находка №22). A3 сверяет дельты с контурами узла
# locate — рестарт фазы deltas там перебирает верную сторону расхождения.
VIOLATION_SOURCE_PHASE: Dict[str, str] = {"A3": "locate"}


def restart_target(phase: str, violations: Optional[List[Any]] = None) -> str:
    """Фаза для `restart-from`: источник нарушения, а не место поимки."""
    for item in violations or []:
        code = item.get("code") if isinstance(item, dict) else getattr(item, "code", None)
        source = VIOLATION_SOURCE_PHASE.get(str(code or ""))
        if source:
            return source
    return phase


def write_escalation(run: Run, phase: str, reason: str, detail: str,
                     restart_phase: Optional[str] = None) -> Path:
    target = restart_phase or phase
    path = run.artifacts / "escalation.md"
    text = "\n".join([
        "# Эскалация: {}".format(reason),
        "",
        "- run_id: {}".format(run.state["run_id"]),
        "- фаза: {}".format(phase),
        "- база: {}".format(run.state["base_path"]),
        "- встреча: {} / {}".format(run.state["immutable"]["date"], run.state["immutable"]["topic"]),
        "",
        detail,
        "",
        "Дальше — решение пользователя: `restart-from --phase {}` либо `abandon`.".format(target),
        "",
    ] + ([
        "Рестарт назначен фазе {}, а не {}: расхождение пришло оттуда.".format(target, phase),
        "",
    ] if target != phase else []))
    atomic_write_text(path, text)
    return path


def fail_run(run: Run, phase: str, code: str, message: str, detail: str,
             violations: Optional[List[Dict[str, Any]]] = None,
             restart_phase: Optional[str] = None) -> SpineError:
    state = run.state
    state["status"] = "failed"
    target = restart_phase or phase
    state["blockers"] = [{"code": code, "message": message, "phase": phase,
                          "restart_phase": target}]
    log_event(state, "failed", detail=code)
    escalation = write_escalation(run, phase, message, detail, restart_phase=target)
    save_state(run.run_dir, state)
    payload = status_payload(run)
    payload["escalation"] = str(escalation)
    payload["error_class"] = "blocker"
    return SpineError(code, message, violations=violations or [], payload=payload)


# --------------------------------------------------------------------------- #
# Hard-канал структурных отказов submit (волна D, D-B п.5)
# --------------------------------------------------------------------------- #

# Реестр первой очереди — задан явно. `review` в реестр НЕ входит: он разбирает
# JSON тем же читателем, но остаётся целиком в существующем поведении
# (per-package семантика счётчиков и копий — отдельный дизайн, вторая очередь).
STRUCTURAL_CODES: Dict[str, Tuple[str, ...]] = {
    "artifact_not_json": ("locate", "deltas", "canon", "questions"),
    "context_manifest_invalid": ("locate",),
    "contours_invalid": ("locate",),
    "context_oversize": ("locate",),
    "package_invalid": ("deltas", "canon"),
    "summary_invalid": ("l1",),
    # Волна G: 4 кода валидации questions.json. Исчерпание бюджета фазы
    # questions в failed не ведёт — submit_questions уходит в собственный
    # fallback ДО вызова structural_reject (контракт «(в) исчерпание → failed»
    # общей функции цел).
    "questions_coverage": ("questions",),
    "questions_invalid": ("questions",),
    "questions_leak": ("questions",),
    "questions_overflow": ("questions",),
}

# Отказы вне валидационного бюджета: `attempt` не растёт, `seq` растёт, копия
# пишется. Единственный маршрут остановки цикла — вопрос пользователю из
# recovery-строки: правил отбора у узла первой очереди нет.
STRUCTURAL_OFF_BUDGET = ("context_oversize",)

# `error_class` (Ф9, 12-factor): класс реакции координатора в payload каждого
# ПРОЦЕССНОГО отказа. rework — перезапусти узел с recovery, пользователю молчи;
# question — дальше только после ответа пользователя; blocker — пайплайн стоит,
# формы «Шаг не принялся» / «Блокер шага». Отказ без error_class — ошибка
# вызова или целостности: координатор чинит команду сам, человеку не носит.
# Скрепка с STRUCTURAL_OFF_BUDGET: сегодня оба реестра — {context_oversize},
# но по разным причинам (вне бюджета ≠ вопрос). Новый off-budget код обязан
# явно решить свой класс, автоматом question он не станет.
STRUCTURAL_QUESTION_CODES = ("context_oversize",)

# Recovery-строки — ДОСЛОВНЫЙ контракт спеки волны D. Это тексты новых
# machine-сообщений (код, не промпт): меняются только вместе со спекой.
RECOVERY_TEXTS: Dict[str, str] = {
    "apply_dry_run_failed": (
        "набор не применится без обрыва: `restart-from --phase accept` — пересдать решения "
        "(reject конфликтной дельты), `restart-from --phase canon` — пересобрать дельты, "
        "либо почини указанный файл базы"),
    "context_oversize": (
        "манифест превышает {n} КиБ: срежь поля из разбивки (наибольшее — {field}) и подай "
        "заново; не выходит срезать — спроси пользователя, продолжать ли с раздутым "
        "(обход подаёт координатор)"),
    "package_invalid:canon": (
        "перезапусти узел canonize: id копируй из deltas.normalized.json дословно, "
        "состав и порядок — тот же"),
    "package_invalid:deltas": (
        "перезапусти узел build-deltas: пакет не прошёл структурные проверки spine — "
        "поправь названные поля и подай пакет целиком заново"),
    "artifact_not_json": (
        "артефакт не парсится как JSON — перезапусти узел, файл подай целиком заново"),
    "context_manifest_invalid": (
        "манифест не прошёл схему: {items} — поправь названные поля и подай заново"),
    "contours_invalid": (
        "контур не сошёлся с деревом базы: {items} — перезапусти узел locate-context и возьми "
        "путь контура из карты базы, а не из догадки о структуре; кандидаты с тем же именем — "
        "в поле `candidates` отказа"),
    "summary_invalid": (
        "выжимка не прошла структурную проверку: {reason} — перезапусти узел l1"),
    "questions_invalid": (
        "questions.json не прошёл проверку формы: {items} — раскладка decisions каждой "
        "опции покрывает ровно covers, default ссылается на существующую опцию и не несёт "
        "take_ack_unresolved; поправь названные поля и подай файл целиком заново"),
    "questions_coverage": (
        "вопросы не разбивают состав: {items} — каждый пункт с сомнением или вопросом о "
        "доме входит ровно в один вопрос, covers попарно не пересекаются и берут только "
        "живые пункты; поправь covers и подай файл целиком заново"),
    "questions_leak": (
        "в текстах вопросов внутренние id или служебная лексика: {items} — перепиши "
        "формулировки языком пользователя (без id дельт и сущностей, без терминов "
        "процесса) и подай заново"),
    "questions_overflow": (
        "решений {n} при потолке {limit}: счёт решений = вопросы + 1 за блок «Советую», "
        "когда советуемые пункты остаются вне вопросов — поэтому вопросов сейчас допустимо "
        "не больше {allowed}; сгруппируй вопросы по общим причинам/домам до этого числа "
        "и подай заново"),
}


def structural_recovery(code: str, phase: str, **fmt: Any) -> str:
    """Recovery-строка кода реестра; per-phase вариант приоритетнее общего."""
    template = RECOVERY_TEXTS.get("{}:{}".format(code, phase)) or RECOVERY_TEXTS[code]
    return template.format(**fmt)


def violation_digest(items: List[Dict[str, Any]], key: str = "field") -> str:
    """Перечень нарушений для recovery-строки: без дублей, в порядке появления."""
    seen: List[str] = []
    for item in items:
        value = item.get(key) or item.get("message") or item.get("code")
        if value and value not in seen:
            seen.append(str(value))
    return ", ".join(seen)


def structural_limit(phase: str) -> int:
    node = phase_row(phase).get("node")
    return int(node_manifest(node).get("rework_limit", 0)) if node else 0


def save_rejected_artifact(run: Run, phase: str, seq: int, artifact: Optional[Path]) -> Optional[str]:
    """Копия отклонённого артефакта — `<phase>.rejected-<seq>.<ext>` в artifacts/.

    Без неё разбор следующего такого сбоя опять будет реконструкцией: успешная
    попытка перезаписывает файл узла. Расширение берётся у исходного артефакта
    (json у locate/deltas/canon, md у l1) — копия обязана читаться как есть.
    """
    if artifact is None or not artifact.is_file():
        return None
    rel = "{}/{}.rejected-{}{}".format(ARTIFACTS_DIRNAME, phase, seq, artifact.suffix or ".json")
    try:
        atomic_write_bytes(run.path(rel), artifact.read_bytes())
    except OSError:
        return None
    return rel


def structural_reject(run: Run, phase: str, code: str, message: str, recovery: str,
                      artifact: Optional[Path] = None,
                      violations: Optional[List[Dict[str, Any]]] = None,
                      payload: Optional[Dict[str, Any]] = None) -> SpineError:
    """Структурный отказ submit: восстановимый цикл вместо глухого exit 1.

    Контракт D-B п.5: (а) раздельный счётчик `structural_rework_count` per phase —
    валидационный бюджет не съедается, лимит из nodes.json; (б) деградации в
    doubtful нет; (в) исчерпание → `failed` + эскалация; (г) payload всегда несёт
    `recovery`; (д) history-событие `submit_rejected` + копия `<phase>.rejected-<seq>`,
    где `rejection_seq` монотонен и отделён от бюджета.

    Инвариант (е): не-терминальный отказ мутирует РОВНО {счётчик, rejection_seq,
    history, rejected-копия} и ничего больше — отклонённый артефакт не оставляет
    за собой ни одного поля фазы (повтор с другим topic проходит без
    `immutable_field`). Терминальный — плюс штатный вклад `fail_run`.
    """
    # Реестр — рантайм-контракт, а не документация: код вне него не должен
    # тихо получить hard-канал (и бюджет чужой фазы) через новый call site.
    if phase not in STRUCTURAL_CODES.get(code, ()):
        raise SpineError(
            "structural_registry_violation",
            "внутренняя ошибка: код {} не объявлен структурным для фазы {} "
            "(реестр STRUCTURAL_CODES)".format(code, phase),
            exit_code=2)

    state = run.state
    record = state["phases"][phase]
    record.setdefault("structural_rework_count", 0)
    record.setdefault("rejection_seq", 0)

    seq = record["rejection_seq"] + 1
    record["rejection_seq"] = seq
    saved = save_rejected_artifact(run, phase, seq, artifact)

    off_budget = code in STRUCTURAL_OFF_BUDGET
    # Механическая скрепка (kimi L5): off-budget код без несгораемого бюджета
    # обязан быть вопросом — иначе rework-цикл без эскалации бесконечен.
    if off_budget and code not in STRUCTURAL_QUESTION_CODES:
        raise SpineError(
            "structural_registry_violation",
            "внутренняя ошибка: off-budget код {} не объявлен question — "
            "цикл без бюджета обязан останавливаться словом пользователя".format(code),
            exit_code=2)
    limit = structural_limit(phase)
    attempt = record["structural_rework_count"]
    if not off_budget:
        attempt += 1
        record["structural_rework_count"] = attempt

    body = dict(payload or {})
    body.update({
        "recovery": recovery,
        "phase": phase,
        "structural_rework_count": record["structural_rework_count"],
        "structural_rework_limit": limit,
        "rejection_seq": seq,
        "off_budget": off_budget,
        "error_class": ("question" if code in STRUCTURAL_QUESTION_CODES else "rework"),
    })
    if saved:
        body["rejected_artifact"] = saved

    state["history"].append({"at": now_iso(), "event": "submit_rejected", "phase": phase,
                             "detail": code, "code": code, "attempt": attempt, "seq": seq})
    state["history"] = state["history"][-200:]

    if not off_budget and attempt > limit:
        exc = fail_run(
            run, phase, code, message,
            "Структурных отказов подряд: {} при лимите {}.\n\nRecovery: {}".format(
                attempt, limit, recovery),
            violations=violations or [])
        exc.payload.update(body)
        # Исчерпание бюджета — уже не rework: класс терминального исхода.
        exc.payload["error_class"] = "blocker"
        return exc

    save_state(run.run_dir, state)
    return SpineError(code, message, violations=violations or [], payload=body)


def read_structural_json(run: Run, phase: str, path: Path) -> Tuple[Any, str]:
    """`read_json_artifact` с проводкой `artifact_not_json` через hard-канал."""
    try:
        return read_json_artifact(path)
    except SpineError as exc:
        if exc.code != "artifact_not_json":
            raise
        raise structural_reject(
            run, phase, "artifact_not_json", exc.message,
            structural_recovery("artifact_not_json", phase), artifact=path)


def payload_size_report(path: Path, raw_bytes: bytes, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Разбивка размера артефакта locate в байтах UTF-8 — одно место кода (D-C п.7).

    Полный размер = длина raw-байтов файла на диске; каждое строковое поле
    `l1_context.*` = `len(value.encode("utf-8"))`; остаток — JSON-overhead.
    """
    total = len(raw_bytes)
    fields: List[Dict[str, Any]] = []
    block = manifest.get("l1_context")
    if isinstance(block, dict):
        for key, value in block.items():
            if isinstance(value, str):
                fields.append({"field": "l1_context.{}".format(key),
                               "bytes": len(value.encode("utf-8"))})
    fields.sort(key=lambda item: (-item["bytes"], item["field"]))
    accounted = sum(item["bytes"] for item in fields)
    return {
        "path": str(path),
        "total_bytes": total,
        "limit_bytes": CONTEXT_MAX_BYTES,
        "fields": fields,
        "largest": fields[0]["field"] if fields else None,
        "json_overhead_bytes": total - accounted,
    }


def l1_context_unknown_fields(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Неизвестные ключи внутри `l1_context` — кодовая проверка (D-C п.9).

    Мини-валидатор `check_schema` не поддерживает `additionalProperties: false`,
    поэтому проверка живёт рядом с гейтом размера, а не в схеме.
    """
    block = manifest.get("l1_context")
    if not isinstance(block, dict):
        return []
    return [violation("l1_context_unknown_field",
                      "неизвестное поле l1_context: {}".format(key),
                      field="$.l1_context.{}".format(key))
            for key in sorted(block) if key not in L1_CONTEXT_FIELDS]


def submit_confirm(args: argparse.Namespace, run: Run) -> Tuple[Dict[str, Any], List[str]]:
    state = run.state
    if args.approved == args.rejected:
        raise SpineError("bad_usage", "нужен ровно один из флагов --approved / --rejected", exit_code=2)
    require_phase(state, "confirm")
    if state["phase_status"] != "awaiting_human":
        raise SpineError("phase_status", "нарушен precondition awaiting_human: фаза confirm не готова к решению")
    parse_meta(args.meta, "confirm")

    corrections: Optional[Path] = None
    if args.corrections:
        corrections = resolve_within(args.corrections, run.run_dir, "--corrections", "run-каталога")
        if not corrections.is_file():
            raise SpineError("corrections_missing", "файл корректур не найден: {}".format(corrections))

    if args.approved:
        mark_validated(state, "confirm", decision="approved")
        entry = None
        if corrections:
            # Corrections — обязательный hash-вход узла deltas: потерять нельзя.
            entry = record_input(state, "deltas", "corrections", corrections, run.run_dir)
        set_phase(state, "deltas")
        log_event(state, "submit:confirm", detail="approved")
        save_state(run.run_dir, state)

        payload = status_payload(run)
        payload["decision"] = "approved"
        payload["corrections"] = entry
        lines = [
            "Выжимка утверждена.",
            "Корректуры записаны как вход фазы deltas" if entry else "Корректур нет",
            "Фаза: deltas — дальше `next`",
        ]
        return payload, lines

    # --rejected: rework-цикл узла l1
    if not corrections:
        raise SpineError("bad_usage", "--rejected требует --corrections <файл>", exit_code=2)

    limit = node_manifest(phase_row("l1")["node"]).get("rework_limit", 0)
    count = state["phases"]["l1"]["rework_count"] + 1
    state["phases"]["confirm"].update({"status": "pending", "decision": "rejected", "updated_at": now_iso()})
    entry = record_input(state, "l1", "corrections", corrections, run.run_dir)

    if count > limit:
        state["phases"]["l1"]["rework_count"] = count
        state["phase"] = "l1"
        state["phase_status"] = "pending"
        state["phases"]["l1"]["status"] = "pending"
        log_event(state, "submit:confirm", detail="rejected:limit")
        exc = fail_run(
            run, "l1", "rework_limit_exceeded",
            "rework-лимит узла l1 исчерпан ({} из {}) — run переведён в failed".format(count, limit),
            "Отклонений подряд: {} при лимите {}. Последние корректуры: {}".format(count, limit, entry["path"]),
            violations=[violation("rework_limit_exceeded", "нужен restart-from или abandon", phase="l1")],
        )
        exc.payload.update({"decision": "rejected", "rework_count": count, "rework_limit": limit})
        raise exc

    state["phases"]["l1"].update({
        "status": "awaiting_artifact",
        "artifact": None,
        "artifact_hash": None,
        "rework_count": count,
        "updated_at": now_iso(),
    })
    state["phase"] = "l1"
    state["phase_status"] = "awaiting_artifact"
    log_event(state, "submit:confirm", detail="rejected")
    save_state(run.run_dir, state)

    payload = status_payload(run)
    payload["decision"] = "rejected"
    payload["rework_count"] = count
    payload["rework_limit"] = limit
    payload["corrections"] = entry
    lines = [
        "Выжимка отклонена — rework узла l1 ({} из {})".format(count, limit),
        "Корректуры записаны входом узла: {}".format(entry["path"]),
        "Фаза: l1 (awaiting_artifact)",
    ]
    return payload, lines


# --------------------------------------------------------------------------- #
# Пакет дельт: нормализация, валидация, retry-политика
# --------------------------------------------------------------------------- #

def violations_out(items: List[Any]) -> List[Dict[str, Any]]:
    """Вывод нарушений: код + уровень + поле + delta_ids, без контента дельт."""
    out = []
    for item in items:
        if isinstance(item, dict):
            out.append(item)
        else:
            out.append(item.as_dict())
    return out


def spine_violation(code: str, msg: str, level: str, delta_ids=(), field=None):
    return delta_rules.Violation(code, msg, delta_ids, level=level, field=field)


def package_meta(run: Run) -> Dict[str, Any]:
    state = run.state
    base = Path(state["base_path"])
    protocol_dir = state["context"]["protocol_dir"]
    rel = None
    if protocol_dir:
        try:
            rel = str(Path(protocol_dir).relative_to(base))
        except ValueError:
            rel = None
    return {
        "protocol_required": bool(state["context"]["protocol_required"]),
        "protocol_path": rel,
        "meeting_nodes": list(state["context"].get("contours") or []),
    }


def structural_checks(package: Dict[str, Any], run: Run) -> List[Any]:
    """Проверки уровня spine: схема пакета и path confinement путей дельт.

    Пары «E00 ↔ сущность типа protocol» здесь больше нет: под вариантом (а)
    сущности-протокола не существует вовсе, и запрещает её валидатор
    (`S10_protocol_entity_forbidden`), а не резервирование id.
    """
    found: List[Any] = []
    schema = delta_schema()
    if schema:
        for err in check_schema(package, schema):
            found.append(spine_violation(
                "package_schema", err["message"], delta_rules.LEVEL_PACKAGE, field=err.get("field")))
    if found:
        return found

    base = Path(run.state["base_path"])
    resolved_by_delta: List[Tuple[Dict[str, Any], str, Dict[str, Path]]] = []
    for delta in package.get("deltas", []):
        did = delta.get("id") or "?"
        resolved: Dict[str, Path] = {}
        bad = False
        for field in ("target_file", "source_file"):
            raw = delta.get(field)
            if not raw:
                continue
            try:
                resolved[field] = resolve_base_relative(raw, base, field)
            except SpineError as exc:
                bad = True
                found.append(spine_violation(
                    "path_confinement", exc.message, delta_rules.LEVEL_DELTA, [did], field=field))
        if not bad:
            resolved_by_delta.append((delta, did, resolved))

    # Публикации этого apply (протокол, выжимка) под собственным терминальным
    # гейтом — перехватывать их структурным отказом значит подменять его слабее.
    published = set(publication_targets(run.state))
    for delta, did, resolved in resolved_by_delta:
        found.extend(existence_checks(delta, resolved, did, published))
    return found


def existence_checks(delta: Dict[str, Any], resolved: Dict[str, Path], did: str,
                     published: set) -> List[Any]:
    """Адреса создающих операций сверяются с деревом базы (находка №23, сужена).

    Проверяются только `create` и `move`, и только по каталогу-родителю: обе
    делают `mkdir(parents=True)` перед записью, поэтому выдуманный путь молча
    заводит НОВУЮ ВЕТКУ дерева базы клиента — это и есть дыра. Новый узел базы
    появляется решением человека, а не дельтой.

    Отсутствие самого файла у `add`/`update`/`delete`/`merge` здесь НЕ ошибка:
    продукт обрабатывает такой адрес иначе и раньше — пометкой «файл не найден в
    базе» на compose (её видит пользователь) и pre-apply dry-run'ом. Дублировать
    их структурным отказом значит отнимать у пользователя решение.

    Пути, которых ещё нет, но которые появятся к записи, исключены: публикации
    этого apply (у них собственный терминальный гейт) и цели `create`-дельт того
    же пакета.
    """
    operation = delta.get("operation")
    target = resolved.get("target_file")
    out: List[Any] = []
    if target is None or operation not in ("create", "move") or str(target) in published:
        return out

    if operation == "create" and target.exists():
        out.append(spine_violation(
            "create_target_exists",
            "operation=create: целевой файл уже есть в базе — нужна add/update",
            delta_rules.LEVEL_DELTA, [did], field="target_file"))
        return out

    if not target.parent.is_dir():
        out.append(spine_violation(
            "create_parent_missing",
            "operation={}: каталога {} в базе нет — новая ветка дерева заводится "
            "решением человека, не дельтой".format(operation, target.parent.name),
            delta_rules.LEVEL_DELTA, [did], field="target_file"))
    return out


def normalize_delta_ids(package: Dict[str, Any]) -> Dict[str, str]:
    """ID дельт назначает spine: d001…, порядок пакета сохраняется."""
    id_map: Dict[str, str] = {}
    for index, delta in enumerate(package.get("deltas", []), start=1):
        assigned = "d{:03d}".format(index)
        incoming = delta.get("id")
        if incoming:
            id_map.setdefault(str(incoming), assigned)
        delta["id"] = assigned
    return id_map


def validate_package(package: Dict[str, Any], phase: str) -> List[Any]:
    try:
        return delta_rules.validate(package, phase)
    except delta_rules.ValidationInputError as exc:
        raise SpineError("package_input_invalid", str(exc))


def degrade_to_doubtful(package: Dict[str, Any], violations: List[Any]) -> List[str]:
    """Политика продукта: непочиненное за rework — doubtful `unresolved`."""
    ids = set()
    for item in violations:
        if item.level in delta_rules.HARD_LEVELS:
            continue
        ids.update(item.delta_ids)
    degraded = []
    for delta in package.get("deltas", []):
        if delta.get("id") in ids and delta.get("section") != "doubtful":
            delta["section"] = "doubtful"
            delta["doubt_reason"] = "unresolved"
            delta.pop("home_question", None)
            degraded.append(delta["id"])
    return sorted(degraded)


# Recovery инвариантных отказов (находка №21): rework уходил без единого слова о
# том, что чинить, и бюджет тратился вслепую. Ключ — код нарушения, значение —
# что делать помимо общего «перезапусти узел».
VIOLATION_RECOVERY: Dict[str, str] = {
    "A3": ("контур, названный на locate, не получил ни одной дельты: либо дельты в него "
           "действительно не собраны, либо контур назван неверно и чинится он, а не пакет — "
           "тогда возврат к узлу locate-context (`restart-from --phase locate`)"),
}


def rework_recovery(node: str, violations: List[Any]) -> str:
    """Что делать с нарушениями: общий рецепт узла плюс адресные по кодам."""
    base = ("перезапусти узел {}: почини названные нарушения и подай пакет "
            "целиком заново".format(node))
    extra: List[str] = []
    for item in violations:
        code = str(getattr(item, "code", "") or "")
        hint = VIOLATION_RECOVERY.get(code)
        if hint and hint not in extra:
            extra.append("{} — {}".format(code, hint))
    return " · ".join([base] + extra)


def retry_or_degrade(run: Run, phase: str, node: str, package: Dict[str, Any],
                     validation_phase: str, violations: List[Any]) -> Tuple[List[str], List[Any]]:
    """§3: package/node → rework узла → failed; entity/delta → doubtful unresolved."""
    state = run.state
    record = state["phases"][phase]
    limit = node_manifest(node).get("rework_limit", 0)
    count = record["rework_count"] + 1
    record["rework_count"] = count

    if count <= limit:
        save_state(run.run_dir, state)
        raise SpineError(
            "validation_failed",
            "пакет фазы {} не прошёл инварианты — rework узла {} ({} из {})".format(phase, node, count, limit),
            violations=violations_out(violations),
            payload={"phase": phase, "rework_count": count, "rework_limit": limit,
                     "recovery": rework_recovery(node, violations),
                     "error_class": "rework"},
        )

    if delta_rules.is_hard(violations):
        hard = [v for v in violations if v.level in delta_rules.HARD_LEVELS]
        raise fail_run(
            run, phase, "validation_failed_hard",
            "нарушения уровня package/node не починены за {} rework — run переведён в failed".format(limit),
            "Коды: {}\n\nRecovery: {}".format(
                ", ".join(sorted({v.code for v in hard})), rework_recovery(node, hard)),
            violations=violations_out(violations),
            restart_phase=restart_target(phase, hard),
        )

    degraded = degrade_to_doubtful(package, violations)
    rest = validate_package(package, validation_phase)
    if delta_rules.is_hard(rest):
        hard = [v for v in rest if v.level in delta_rules.HARD_LEVELS]
        raise fail_run(
            run, phase, "validation_failed_hard",
            "после перевода в doubtful остались нарушения package/node — run переведён в failed",
            "Коды: {}\n\nRecovery: {}".format(
                ", ".join(sorted({v.code for v in hard})), rework_recovery(node, hard)),
            violations=violations_out(rest),
            restart_phase=restart_target(phase, hard),
        )
    return degraded, rest


def record_unresolved(state: Dict[str, Any], phase: str, violations: List[Any], degraded: List[str]) -> None:
    for item in violations:
        state["unresolved"].append({
            "phase": phase,
            "code": item.code,
            "level": item.level,
            "field": item.field,
            "delta_ids": list(item.delta_ids),
            "msg": item.msg,
            "at": now_iso(),
        })
    for did in degraded:
        state["unresolved"].append({
            "phase": phase,
            "code": "degraded_to_doubtful",
            "level": delta_rules.LEVEL_DELTA,
            "field": "section",
            "delta_ids": [did],
            "msg": "дельта переведена в doubtful `unresolved` по политике retry",
            "at": now_iso(),
        })


def store_normalized(run: Run, phase: str, rel: str, package: Dict[str, Any]) -> str:
    digest = write_json_artifact(run.path(rel), package)
    run.state["normalized"][phase] = {"path": rel, "hash": digest}
    return digest


def load_normalized(run: Run, phase: str) -> Dict[str, Any]:
    record = run.state["normalized"].get(phase)
    if not record:
        raise SpineError("artifact_missing", "нормализованный пакет фазы {} отсутствует".format(phase))
    path = run.path(record["path"])
    if not path.is_file():
        raise SpineError("artifact_missing", "нормализованный пакет фазы {} исчез".format(phase))
    package, digest = read_json_artifact(path)
    if digest != record["hash"]:
        raise SpineError(
            "artifact_hash_mismatch",
            "нормализованный пакет фазы {} изменён после записи".format(phase),
        )
    return package


# --------------------------------------------------------------------------- #
# submit deltas / canon
# --------------------------------------------------------------------------- #

def submit_deltas(args: argparse.Namespace, run: Run) -> Tuple[Dict[str, Any], List[str]]:
    state = run.state
    require_live(state)
    path = require_artifact(args, run)
    package, digest = read_structural_json(run, "deltas", path)
    if idempotent_ok(state, "deltas", digest):
        payload = status_payload(run)
        payload["idempotent"] = True
        return payload, ["Тот же пакет дельт уже принят — состояние не изменилось"]
    require_phase(state, "deltas")
    parse_meta(args.meta, "deltas")

    package = dict(package)
    package.update(package_meta(run))
    structural = structural_checks(package, run)
    if structural:
        raise structural_reject(
            run, "deltas", "package_invalid",
            "пакет дельт не прошёл структурные проверки spine",
            structural_recovery("package_invalid", "deltas"),
            artifact=path, violations=violations_out(structural))

    id_map = normalize_delta_ids(package)
    violations = validate_package(package, "coverage")
    degraded: List[str] = []
    if violations:
        degraded, violations = retry_or_degrade(run, "deltas", "build-deltas", package, "coverage", violations)
        record_unresolved(state, "deltas", violations, degraded)

    store_normalized(run, "deltas", ART_DELTAS_NORM, package)
    state["deltas_id_map"] = id_map
    mark_validated(state, "deltas", rel_to_run(path, run.run_dir), digest)
    set_phase(state, "canon")
    log_event(state, "submit:deltas")

    # Условный canon (кандидат ускорения 31.07): Фаза A уже удовлетворяет
    # финальным инвариантам и каждый узел покрыт recommended-дельтой — узлу
    # canonize нечего решать (единственный дом на сущность есть, снимать узлы
    # с причиной не нужно). Фаза исполняется кодом identity-пакетом, LLM-узел
    # не вызывается; сомнение в пропуске лечится `restart-from --phase canon` —
    # там узел зовётся как обычно.
    canon_pkg = dict(package)
    phase_a_nodes = sorted({delta_rules.node_of(d.get("target_file", ""))
                            for d in package.get("deltas", [])})
    canon_pkg["phase_a_nodes"] = phase_a_nodes
    rec_nodes = {delta_rules.node_of(d.get("target_file", ""))
                 for d in package.get("deltas", []) if d.get("section") == "recommended"}
    # Условие пропуска (связка 04.08): валидатор final возвращает СПИСОК
    # нарушений (пустой = чисто, не bool) · деградаций на этой фазе не было ·
    # каждая doubtful-дельта уже несёт вопрос пользователю (валидатор непустоту
    # doubt_question не требует — держим здесь) · пакет непуст.
    canon_auto = (bool(package.get("deltas"))
                  and not degraded
                  and not validate_package(canon_pkg, "final")
                  and all(node in rec_nodes for node in phase_a_nodes)
                  and all((d.get("doubt_question") or "").strip()
                          for d in package.get("deltas", [])
                          if d.get("section") == "doubtful"))
    if canon_auto:
        canon_digest = write_json_artifact(run.path(ART_CANON_AUTO), canon_pkg)
        store_normalized(run, "canon", ART_CANON_NORM, canon_pkg)
        state["phase_a"] = {"nodes": phase_a_nodes, "kept": list(phase_a_nodes), "dropped": []}
        mark_validated(state, "canon", ART_CANON_AUTO, canon_digest)
        set_phase(state, "review")
        log_event(state, "canon:auto-pass", detail="финальные инварианты чисты")
    save_state(run.run_dir, state)

    payload = status_payload(run)
    payload["artifact_hash"] = digest
    payload["delta_count"] = len(package.get("deltas", []))
    payload["entity_count"] = len(package.get("entities", []))
    payload["degraded"] = degraded
    payload["id_map"] = id_map
    payload["canon_skipped"] = canon_auto
    lines = [
        "Пакет дельт принят: {} дельт, {} сущностей".format(payload["delta_count"], payload["entity_count"]),
        "ID назначены spine: d001…d{:03d}".format(payload["delta_count"]) if payload["delta_count"] else "Дельт нет",
    ]
    if canon_auto:
        lines.append("Фаза canon исполнена кодом: дубли и дома чисты, узел не нужен")
        lines.append("Фаза: review — дальше `export-review`")
    else:
        lines.append("Фаза: canon — дальше `next`")
    if degraded:
        lines.append("Переведено в doubtful `unresolved`: {}".format(", ".join(degraded)))
    return payload, lines


def canon_id_sequence(expected_ids: List[str], actual_ids: List[Any]) -> Dict[str, Any]:
    """Полная сверка последовательности id пакета canon против Фазы A (D-B п.4).

    Кодовая проверка контракта: промпт канонизатора не трогаем (вторая очередь),
    но контракт «тот же список, той же длины, в том же порядке» обязан быть
    исполнимым независимо от промпта. Молча выброшенная дельта, дубликат id и
    перестановка ловятся здесь, а не всплывают на apply.
    """
    present = [str(item) for item in actual_ids if item]
    expected_set, actual_set = set(expected_ids), set(present)
    missing = [item for item in expected_ids if item not in actual_set]
    unexpected = [item for item in present if item not in expected_set]
    duplicate = sorted({item for item in present if present.count(item) > 1})
    # Порядок сверяется по общей части, без дублей: перестановка видна как
    # позиции, где фактический id разошёлся с ожидаемым.
    common_actual = [item for item in dict.fromkeys(present) if item in expected_set]
    common_expected = [item for item in expected_ids if item in actual_set]
    reordered = [a for a, e in zip(common_actual, common_expected) if a != e]
    return {
        "missing": missing,
        "unexpected": unexpected,
        "duplicate": duplicate,
        "reordered": reordered,
        "expected_count": len(expected_ids),
        "actual_count": len(actual_ids),
    }


def canon_sequence_violations(check: Dict[str, Any]) -> List[Any]:
    """Нарушения последовательности id → уровень package (hard, без деградации)."""
    found: List[Any] = []
    if check["missing"]:
        found.append(spine_violation(
            "canon_delta_id_missing_from_package",
            "дельты Фазы A отсутствуют в canon.json: {}".format(", ".join(check["missing"])),
            delta_rules.LEVEL_PACKAGE, tuple(check["missing"]), field="id"))
    if check["duplicate"]:
        found.append(spine_violation(
            "canon_delta_id_duplicate",
            "id дельты встречается в пакете дважды: {}".format(", ".join(check["duplicate"])),
            delta_rules.LEVEL_PACKAGE, tuple(check["duplicate"]), field="id"))
    if check["reordered"]:
        # Порядок — контракт формы canonize; отказ осознанно фатальный.
        found.append(spine_violation(
            "canon_delta_ids_reordered",
            "порядок дельт изменён: {}".format(", ".join(check["reordered"])),
            delta_rules.LEVEL_PACKAGE, tuple(check["reordered"]), field="id"))
    if check["expected_count"] != check["actual_count"]:
        found.append(spine_violation(
            "canon_package_length_mismatch",
            "длина пакета {} против {} на Фазе A".format(
                check["actual_count"], check["expected_count"]),
            delta_rules.LEVEL_PACKAGE, field="deltas"))
    return found


def submit_canon(args: argparse.Namespace, run: Run) -> Tuple[Dict[str, Any], List[str]]:
    state = run.state
    require_live(state)
    path = require_artifact(args, run)
    package, digest = read_structural_json(run, "canon", path)
    if idempotent_ok(state, "canon", digest):
        payload = status_payload(run)
        payload["idempotent"] = True
        return payload, ["Тот же canon.json уже принят — состояние не изменилось"]
    require_phase(state, "canon")
    parse_meta(args.meta, "canon")

    phase_a = load_normalized(run, "deltas")
    expected_ids = [d["id"] for d in phase_a.get("deltas", [])]
    known_ids = set(expected_ids)
    phase_a_nodes = sorted({delta_rules.node_of(d.get("target_file", "")) for d in phase_a.get("deltas", [])})

    package = dict(package)
    package.update(package_meta(run))
    package["phase_a_nodes"] = phase_a_nodes

    structural = structural_checks(package, run)
    for delta in package.get("deltas", []):
        did = delta.get("id")
        if not did:
            structural.append(spine_violation(
                "canon_delta_id_missing",
                "дельта без id: канонизатор обязан сохранять id, назначенные spine",
                delta_rules.LEVEL_PACKAGE, field="id"))
        elif did not in known_ids:
            structural.append(spine_violation(
                "canon_delta_id_unknown",
                "id дельты отсутствует в пакете Фазы A: канонизатор не добавляет дельты",
                delta_rules.LEVEL_PACKAGE, [did], field="id"))
    actual_ids = [d.get("id") for d in package.get("deltas", [])]
    id_check = canon_id_sequence(expected_ids, actual_ids)
    structural.extend(canon_sequence_violations(id_check))
    dropped_nodes = package.get("dropped_nodes", []) or []
    for item in dropped_nodes:
        if item.get("node") not in phase_a_nodes:
            structural.append(spine_violation(
                "dropped_node_unknown",
                "dropped_nodes ссылается на узел вне Фазы A: {}".format(item.get("node")),
                delta_rules.LEVEL_NODE, field="dropped_nodes"))
    if structural:
        raise structural_reject(
            run, "canon", "package_invalid",
            "canon.json не прошёл структурные проверки spine",
            structural_recovery("package_invalid", "canon"),
            artifact=path, violations=violations_out(structural),
            payload=dict(id_check, id_check=id_check))

    violations = validate_package(package, "final")
    degraded: List[str] = []
    if violations:
        degraded, violations = retry_or_degrade(run, "canon", "canonize", package, "final", violations)
        record_unresolved(state, "canon", violations, degraded)

    # Сверка Фазы A: каждый узел — kept (есть recommended-дельта) либо dropped с причиной.
    rec_nodes = {delta_rules.node_of(d.get("target_file", ""))
                 for d in package.get("deltas", []) if d.get("section") == "recommended"}
    dropped_map = {item["node"]: item["reason"] for item in dropped_nodes}
    kept = [n for n in phase_a_nodes if n in rec_nodes]
    dropped = [{"node": n, "reason": dropped_map.get(n)} for n in phase_a_nodes if n not in rec_nodes]
    state["phase_a"] = {"nodes": phase_a_nodes, "kept": kept, "dropped": dropped}

    store_normalized(run, "canon", ART_CANON_NORM, package)
    mark_validated(state, "canon", rel_to_run(path, run.run_dir), digest)
    set_phase(state, "review")
    log_event(state, "submit:canon")
    save_state(run.run_dir, state)

    payload = status_payload(run)
    payload["artifact_hash"] = digest
    payload["phase_a"] = state["phase_a"]
    payload["degraded"] = degraded
    lines = [
        "canon.json принят: узлов Фазы A {}, оставлено {}, снято {}".format(
            len(phase_a_nodes), len(kept), len(dropped)),
        "Фаза: review — дальше `export-review`",
    ]
    if degraded:
        lines.append("Переведено в doubtful `unresolved`: {}".format(", ".join(degraded)))
    return payload, lines


# --------------------------------------------------------------------------- #
# export-review / submit review
# --------------------------------------------------------------------------- #

NO_EVIDENCE_QUESTION = "Нет зафиксированной опоры в выжимке — принимать правку?"


def cmd_export_review(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    run = require_run(args)
    state = run.state
    require_phase(state, "review")
    if state["phases"]["canon"]["status"] != "validated":
        raise SpineError("precondition_canon", "нарушен precondition canon_validated: canon ещё не принят")

    package = load_normalized(run, "canon")
    meta = package_meta(run)
    base = Path(state["base_path"])
    date, topic = state["immutable"]["date"], state["immutable"]["topic"]

    # R8: сверка декларации протокола с фактом на диске делается spine, не ревьюером.
    protocol_dir = Path(state["context"]["protocol_dir"])
    protocol_on_disk = False
    if protocol_dir.is_dir():
        prefix = "{}_{}".format(date, topic)
        protocol_on_disk = any(
            child.is_file() and child.name.startswith(prefix) and not child.name.endswith("_summary.md")
            for child in protocol_dir.iterdir()
        )
    if meta["protocol_required"] and protocol_on_disk:
        raise SpineError(
            "protocol_declaration_mismatch",
            "нарушен precondition protocol_state: locate объявил protocol_required=true, "
            "но протокол этой встречи уже на диске",
            violations=[violation("protocol_on_disk", "протокол существует", field="protocol_required")],
            payload={"recovery": "restart-from --phase canon", "error_class": "blocker"},
        )

    # R6: дельта без source_evidence в ревью не идёт — сразу doubtful.
    no_evidence: List[str] = []
    reviewable: List[Dict[str, Any]] = []
    for delta in package.get("deltas", []):
        if not (delta.get("source_evidence") or "").strip():
            delta["section"] = "doubtful"
            delta["doubt_reason"] = "dispute"
            delta["doubt_question"] = NO_EVIDENCE_QUESTION
            delta["no_evidence"] = True
            delta.pop("home_question", None)
            no_evidence.append(delta["id"])
        else:
            reviewable.append(delta)

    if no_evidence:
        store_normalized(run, "canon", ART_CANON_NORM, package)

    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for delta in reviewable:
        by_file.setdefault(delta["target_file"], []).append(delta)

    packages: List[Dict[str, Any]] = []
    packages_dir = run.path(ART_PACKAGES_DIR)
    if packages_dir.is_dir():
        shutil.rmtree(packages_dir)
    packages_dir.mkdir(parents=True, exist_ok=True)
    for index, target_file in enumerate(sorted(by_file), start=1):
        items = sorted(by_file[target_file], key=lambda d: d["id"])
        package_id = "p{:02d}".format(index)
        target_path = base / target_file
        body = {
            "package_id": package_id,
            "target_file": target_file,
            "file_exists": target_path.is_file(),
            "meeting": {"date": date, "topic": topic},
            "meta": {
                "protocol_required": meta["protocol_required"],
                "protocol_path": meta["protocol_path"],
                "protocol_on_disk": protocol_on_disk,
            },
            "deltas": items,
        }
        rel = "{}/{}.json".format(ART_PACKAGES_DIR, package_id)
        package_hash = write_json_artifact(run.path(rel), body)
        packages.append({
            "package_id": package_id,
            "file": target_file,
            "path": rel,
            "delta_ids": [d["id"] for d in items],
            "package_hash": package_hash,
        })

    verdicts_dir = run.path(ART_VERDICTS_DIR)
    if verdicts_dir.is_dir():
        shutil.rmtree(verdicts_dir)
    verdicts_dir.mkdir(parents=True, exist_ok=True)

    state["review"] = {
        "packages": packages,
        "verdicts": {},
        "no_evidence": no_evidence,
        "protocol_on_disk": protocol_on_disk,
    }
    log_event(state, "export-review", detail="{} пакет(ов)".format(len(packages)))
    save_state(run.run_dir, state)

    payload = status_payload(run)
    payload["packages"] = packages
    payload["no_evidence"] = no_evidence
    payload["protocol_on_disk"] = protocol_on_disk
    lines = ["Пакетов ревью: {}".format(len(packages))]
    lines += ["  {} → {} ({} дельт)".format(p["package_id"], p["file"], len(p["delta_ids"])) for p in packages]
    if no_evidence:
        lines.append("Без source_evidence → сразу «Сомневаюсь»: {}".format(", ".join(no_evidence)))
    lines.append("Каждый пакет — отдельный независимый субагент-ревьюер (`next` даёт манифест)")
    return payload, lines


def apply_verdict(delta: Dict[str, Any], item: Dict[str, Any]) -> None:
    """Детерминированный маппинг вердикта ревью на дельту (prompts/review.md)."""
    verdict = (item.get("verdict") or "").strip()
    dispute = (item.get("dispute_class") or "").strip()
    reason = (item.get("reason") or "").strip()
    delta["review_verdict"] = verdict or "unknown"

    if verdict in REVIEW_ACCEPTING:
        if verdict == "revise" and (item.get("revised_text") or "").strip():
            delta["proposed_text"] = item["revised_text"]
        return

    # reject / escalate_* / вердикт вне словаря
    if dispute == "home_choice" and delta.get("role") == "canonical" \
            and delta.get("section") == "recommended":
        delta["home_question"] = reason or "Дом сущности спорен — выбери из легитимных вариантов"
        return

    delta["section"] = "doubtful"
    delta["doubt_reason"] = "dispute"
    delta["doubt_question"] = reason or "Ревью не подтвердило правку — принимать?"
    delta.pop("home_question", None)


def aggregate_review(run: Run) -> Tuple[Dict[str, Any], List[str], List[Any]]:
    """Атомарная агрегация вердиктов в ledger + пост-ревью final-валидация."""
    state = run.state
    package = load_normalized(run, "canon")
    by_id = {d["id"]: d for d in package.get("deltas", [])}

    for entry in state["review"]["packages"]:
        record = state["review"]["verdicts"][entry["package_id"]]
        verdict_file = run.path(record["path"])
        body = load_json_file(verdict_file)
        for item in body.get("verdicts", []):
            delta = by_id.get(item["delta_id"])
            if delta is not None:
                apply_verdict(delta, item)

    violations = validate_package(package, "final")
    degraded: List[str] = []
    if violations:
        if delta_rules.is_hard(violations):
            hard = [v for v in violations if v.level in delta_rules.HARD_LEVELS]
            raise fail_run(
                run, "review", "post_review_validation_failed",
                "пост-ревью валидация: нарушения уровня package/node — нужен `restart-from --phase canon`",
                "Коды: {}".format(", ".join(sorted({v.code for v in hard}))),
                violations=violations_out(violations),
            )
        degraded = degrade_to_doubtful(package, violations)
        rest = validate_package(package, "final")
        if delta_rules.is_hard(rest):
            hard = [v for v in rest if v.level in delta_rules.HARD_LEVELS]
            raise fail_run(
                run, "review", "post_review_validation_failed",
                "пост-ревью валидация: после перевода в doubtful остались нарушения package/node",
                "Коды: {}".format(", ".join(sorted({v.code for v in hard}))),
                violations=violations_out(rest),
            )
        violations = rest
    return package, degraded, violations


def submit_review(args: argparse.Namespace, run: Run) -> Tuple[Dict[str, Any], List[str]]:
    state = run.state
    require_phase(state, "review")
    parse_meta(args.meta, "review")
    if not args.package:
        raise SpineError("bad_usage", "команда требует --package <id>", exit_code=2)
    if not args.verdict:
        raise SpineError("bad_usage", "команда требует --verdict <файл>", exit_code=2)

    packages = state["review"]["packages"]
    if not packages:
        raise SpineError("precondition_export_review",
                         "нарушен precondition packages_exported: сначала `export-review`")
    entry = next((p for p in packages if p["package_id"] == args.package), None)
    if entry is None:
        raise SpineError("unknown_package", "пакет {} отсутствует в манифесте ревью".format(args.package))

    path = resolve_within(args.verdict, run.run_dir, "--verdict", "run-каталога")
    if not path.is_file():
        raise SpineError("artifact_missing", "файл вердиктов не найден: {}".format(path))
    body, digest = read_json_artifact(path)

    done = state["review"]["verdicts"]
    if entry["package_id"] in done and done[entry["package_id"]]["hash"] == digest:
        payload = status_payload(run)
        payload["idempotent"] = True
        return payload, ["Тот же вердикт пакета {} уже принят".format(entry["package_id"])]

    errors = check_schema(body, VERDICT_SCHEMA)
    if errors:
        raise SpineError("verdict_invalid", "файл вердиктов не прошёл проверку схемы", violations=errors)

    covered = [item["delta_id"] for item in body["verdicts"]]
    expected = set(entry["delta_ids"])
    extra = sorted(set(covered) - expected)
    duplicates = sorted({i for i in covered if covered.count(i) > 1})
    problems = []
    if extra:
        problems.append(violation("verdict_alien", "вердикт на дельты вне пакета",
                                  field="verdicts", delta_ids=extra))
    if duplicates:
        problems.append(violation("verdict_duplicate", "повторный вердикт на дельту",
                                  field="verdicts", delta_ids=duplicates))
    if problems:
        raise SpineError("verdict_incomplete", "вердикты содержат чужие или повторные дельты",
                         violations=problems, payload={"error_class": "rework"})

    # Частичный приём (кандидат ускорения 31.07): валидный файл, покрывающий не
    # весь пакет, не сжигает уже полученные вердикты — недостающие дельты
    # переспрашиваются адресно, принятые копятся до полного покрытия.
    partial_store = state["review"].setdefault("partial", {})
    merged: Dict[str, Dict[str, Any]] = {}
    prior = partial_store.get(entry["package_id"])
    if prior:
        prior_path = run.path(prior["path"])
        # Копилка hash-bound: подменённый .partial.json не считается принятым.
        # Запись сбрасывается тут же — следующая подача начинает пакет с нуля.
        if not prior_path.is_file() or artifact_hash(prior_path) != prior["hash"]:
            partial_store.pop(entry["package_id"], None)
            save_state(run.run_dir, state)
            raise SpineError(
                "artifact_hash_mismatch",
                "копилка вердиктов пакета {} изменена после приёма — частичные "
                "вердикты недействительны, подай их заново".format(entry["package_id"]),
                payload={"error_class": "rework",
                         "recovery": "подай вердикты пакета заново: копилка сброшена"})
        prior_body = load_json_file(prior_path)
        for item in prior_body.get("verdicts", []):
            merged[item["delta_id"]] = item
        # Принятый вердикт неизменяем: пересечение новой подачи с копилкой —
        # отказ, а не тихое замещение (независимость ревьюера, Codex H2).
        overlap = sorted(set(merged) & {item["delta_id"] for item in body["verdicts"]})
        if overlap:
            raise SpineError(
                "verdict_duplicate",
                "повторный вердикт на уже принятые дельты пакета {}: принятые вердикты "
                "неизменяемы до полного покрытия".format(entry["package_id"]),
                violations=[violation("verdict_duplicate", "дельта уже покрыта копилкой",
                                      field="verdicts", delta_ids=overlap)],
                payload={"error_class": "rework",
                         "recovery": "подай вердикты только по недостающим дельтам: {}".format(
                             ", ".join(sorted(expected - set(merged))))})
    for item in body["verdicts"]:
        merged[item["delta_id"]] = item
    missing = sorted(expected - set(merged))
    if missing:
        partial_body = {"verdicts": [merged[k] for k in sorted(merged)]}
        rel = "{}/{}.partial.json".format(ART_VERDICTS_DIR, entry["package_id"])
        pdigest = write_json_artifact(run.path(rel), partial_body)
        partial_store[entry["package_id"]] = {"path": rel, "hash": pdigest,
                                              "updated_at": now_iso()}
        log_event(state, "submit:review", detail="{}:partial".format(entry["package_id"]))
        save_state(run.run_dir, state)
        payload = status_payload(run)
        payload["package_id"] = entry["package_id"]
        payload["partial"] = True
        payload["accepted_delta_ids"] = sorted(merged)
        payload["missing_delta_ids"] = missing
        payload["recovery"] = (
            "вердиктов не хватает на дельты: {} — перезапусти ревьюера пакета только по "
            "ним и подай файл с этими вердиктами; уже принятые повторять не нужно".format(
                ", ".join(missing)))
        return payload, [
            "Вердикт пакета {} принят частично: {} из {}".format(
                entry["package_id"], len(merged), len(expected)),
            "Не хватает вердиктов: {} — переспроси ревьюера только по ним".format(
                ", ".join(missing)),
        ]
    if prior:
        # Пакет добит переподачей: полный состав собирается из копилки,
        # порядок — по манифесту пакета.
        body = {"verdicts": [merged[did] for did in entry["delta_ids"]]}
    partial_store.pop(entry["package_id"], None)

    # Привязку к пакету проставляет spine: --package называет пакет, hash берётся
    # из манифеста. Значения из файла (если ревьюер их написал) перекрываются —
    # сверки нет, а значит нет и re-review пакета из-за описки копирования.
    body["package_id"] = entry["package_id"]
    body["package_hash"] = entry["package_hash"]
    stored_rel = "{}/{}.json".format(ART_VERDICTS_DIR, entry["package_id"])
    stored = run.path(stored_rel)
    digest = write_json_artifact(stored, body)
    state["review"]["verdicts"][entry["package_id"]] = {
        "path": stored_rel, "hash": digest, "recorded_at": now_iso()}

    pending = [p["package_id"] for p in packages if p["package_id"] not in state["review"]["verdicts"]]
    if pending:
        log_event(state, "submit:review", detail=entry["package_id"])
        save_state(run.run_dir, state)
        payload = status_payload(run)
        payload["package_id"] = entry["package_id"]
        payload["pending"] = pending
        return payload, [
            "Вердикт пакета {} принят".format(entry["package_id"]),
            "Осталось пакетов: {}".format(len(pending)),
        ]

    # Все пакеты покрыты → атомарно: агрегация → пост-ревью валидация → compose-ready.
    package, degraded, violations = aggregate_review(run)
    ledger_hash = write_json_artifact(run.path(ART_LEDGER), package)
    state["ledger"] = {"artifact": ART_LEDGER, "hash": ledger_hash}
    report = {
        "phase": "final",
        "ok": not violations,
        "violations": violations_out(violations),
        "degraded": degraded,
        "ledger_hash": ledger_hash,
    }
    post_hash = write_json_artifact(run.path(ART_POST_VALIDATION), report)
    state["post_validation"] = {"artifact": ART_POST_VALIDATION, "hash": post_hash, "ok": not violations}
    if violations or degraded:
        record_unresolved(state, "review", violations, degraded)
    mark_validated(state, "review", ART_LEDGER, ledger_hash)
    # Auto-pass волны G — здесь, ДО set_phase: пустое покрываемое множество не
    # рождает живую фазу questions (манифест узла не выдаётся, LLM не
    # вызывается). В submit_questions такая проверка бесполезна — узел уже
    # вызван (hitl-v3-spec, круг 2 инженера).
    required = questions_required_ids(live_deltas(package.get("deltas", [])))
    if required:
        set_phase(state, "questions")
        next_line = "Фаза: questions — дальше `next` (узел формулирует вопросы пользователю)"
    else:
        q_hash = write_json_artifact(run.path(ART_QUESTIONS), {"questions": []})
        state["questions"] = {"artifact": ART_QUESTIONS, "hash": q_hash}
        mark_validated(state, "questions", ART_QUESTIONS, q_hash)
        log_event(state, "questions:auto-pass", detail="вопросов нет")
        set_phase(state, "compose")
        next_line = "Вопросов к пользователю нет — экран решений ниже (compose исполнен этим же вызовом)"
    log_event(state, "submit:review", detail="aggregated")
    save_state(run.run_dir, state)

    lines = [
        "Вердикт пакета {} принят — покрыты все пакеты".format(entry["package_id"]),
        "Пост-ревью валидация: {}".format("чисто" if not violations else "нарушения переведены в doubtful"),
        next_line,
    ]
    if required:
        payload = status_payload(run)
    else:
        # Автосцепка код-фаз: auto-pass questions ведёт в compose — код, экран
        # решений рендерится этим же вызовом (минус ход координатора).
        payload, compose_lines = perform_compose(run)
        lines += compose_lines
    payload["package_id"] = entry["package_id"]
    payload["pending"] = []
    payload["ledger_hash"] = ledger_hash
    payload["post_review_validation"] = {"hash": post_hash, "ok": not violations, "degraded": degraded}
    payload["questions_required"] = required
    return payload, lines


# --------------------------------------------------------------------------- #
# questions (волна G): валидация файла вопросов и fallback
# --------------------------------------------------------------------------- #

# Entity-id (E01, Е01 — латиница и кириллица) в человекочитаемых полях: та же
# дыра канона, что и delta-id (находка 31.07 — humanize закрывал только d\d+).
_ENTITY_ID_TOKEN = re.compile(r"\b[EЕ][0-9]{2,}\b")

# Стоп-слова утечек — только однозначно служебная лексика. Бытовые омонимы
# («дельта», «пакет», «ревью», «атака») в реестр не входят — их ловят рубрика
# и негативы eval. Правило сравнения фиксировано: casefold, границы слова.
_QUESTIONS_STOPWORDS = ("doubtful", "bucket", "section", "compose", "ledger",
                        "spine", "канонизация")
_QUESTIONS_STOPWORD_RE = re.compile(
    r"(?<!\w)(?:{})(?!\w)".format("|".join(_QUESTIONS_STOPWORDS)), re.IGNORECASE)

_questions_schema_cache: Optional[Dict[str, Any]] = None


def questions_schema() -> Dict[str, Any]:
    global _questions_schema_cache
    if _questions_schema_cache is None:
        try:
            _questions_schema_cache = json.loads(QUESTIONS_SCHEMA_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SpineError("questions_schema_broken",
                             "schema/questions.schema.json не прочитан: {}".format(exc), exit_code=2)
    return _questions_schema_cache


def questions_cap(question_count: int, uncovered_count: int, required_count: int) -> Tuple[int, int]:
    """Счётчик решений экрана и его кап — одна формула для шапки и валидатора.

    N = вопросы + (1, если блок «Советую» непуст); кап — по числу РЕШЕНИЙ:
    max(7, ⌈покрываемых пунктов / 4⌉ + 1). На классе churn_analysis это ≤7; на
    десятках разнородных сомнений компактность деградирует линейно — честная
    граница спеки.
    """
    n = question_count + (1 if uncovered_count else 0)
    cap = max(7, (required_count + 3) // 4 + 1)
    return n, cap


def questions_schema_violations(body: Any) -> List[Dict[str, Any]]:
    """questions_invalid: схема + словарь формы поверх неё.

    Словарь: id вопросов и опций без повторов, covers без дублей, раскладка
    decisions каждой опции покрывает РОВНО covers, default ссылается на
    существующую опцию и не несёт take_ack_unresolved (двойная защита риска:
    вторая половина — fail-closed пер-пунктного ack в accept).
    """
    problems = check_schema(body, questions_schema())
    if problems:
        return problems
    seen_q: set = set()
    for question in body["questions"]:
        qid = question["id"]
        if qid in seen_q:
            problems.append(violation("question_duplicate", "повтор id вопроса {}".format(qid), field=qid))
        seen_q.add(qid)
        covers = question["covers"]
        dup_covers = sorted({d for d in covers if covers.count(d) > 1})
        if dup_covers:
            problems.append(violation("covers_duplicate", "повтор пункта в covers вопроса {}".format(qid),
                                      field=qid, delta_ids=dup_covers))
        opt_ids = [opt["id"] for opt in question["options"]]
        dup_opts = sorted({o for o in opt_ids if opt_ids.count(o) > 1})
        if dup_opts:
            problems.append(violation("option_duplicate", "повтор id опции в вопросе {}".format(qid),
                                      field=qid))
        covers_set = set(covers)
        for opt in question["options"]:
            decided = set(opt["decisions"])
            if decided != covers_set:
                problems.append(violation(
                    "option_partition",
                    "раскладка опции {} вопроса {} покрывает не ровно covers".format(opt["id"], qid),
                    field="{}.{}".format(qid, opt["id"]),
                    delta_ids=sorted(covers_set ^ decided)))
        default_opt = next((o for o in question["options"] if o["id"] == question["default"]), None)
        if default_opt is None:
            problems.append(violation("default_unknown",
                                      "default вопроса {} не ссылается на существующую опцию".format(qid),
                                      field=qid))
        elif "take_ack_unresolved" in default_opt["decisions"].values():
            problems.append(violation(
                "default_carries_risk",
                "default-опция вопроса {} несёт take_ack_unresolved — "
                "риск не может быть ответом по умолчанию".format(qid),
                field=qid))
    return problems


def questions_coverage_violations(body: Dict[str, Any], live: List[Dict[str, Any]],
                                  all_ids: set) -> List[Dict[str, Any]]:
    """questions_coverage: вопросы разбивают живой состав (предикат по bucket).

    Каждый живой пункт с bucket ≠ 0 и каждый с home_question — ровно в одном
    covers; covers попарно не пересекаются и берут только живые пункты
    (merged-дельта — адресная строка). Блок «Советую» — остаток разбиения,
    отдельной проверки не требует.
    """
    live_ids = {d.get("id") for d in live}
    required = set(questions_required_ids(live))
    problems: List[Dict[str, Any]] = []
    seen: Dict[str, str] = {}
    for question in body["questions"]:
        qid = question["id"]
        for did in question["covers"]:
            if did in seen and seen[did] != qid:
                problems.append(violation(
                    "covers_overlap",
                    "пункт {} в covers двух вопросов ({} и {})".format(did, seen[did], qid),
                    field=did, delta_ids=[did]))
            seen.setdefault(did, qid)
            if did not in live_ids:
                if did in all_ids:
                    problems.append(violation(
                        "covers_merged",
                        "пункт {} слит с другим — в covers не берётся".format(did),
                        field=did, delta_ids=[did]))
                else:
                    problems.append(violation(
                        "covers_alien",
                        "пункт {} вне живого состава ledger".format(did),
                        field=did, delta_ids=[did]))
    uncovered_required = sorted(required - set(seen))
    if uncovered_required:
        problems.append(violation(
            "required_uncovered",
            "пункты с сомнением или вопросом о доме не покрыты вопросами: {}".format(
                ", ".join(uncovered_required)),
            field="covers", delta_ids=uncovered_required))
    return problems


def questions_leak_violations(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """questions_leak: внутренние id и служебная лексика в человекочитаемых полях.

    Срабатывание — отказ ФОРМЫ с recovery, не запрет темы: узел переформулирует
    той же сутью без служебного словаря.
    """
    problems: List[Dict[str, Any]] = []

    def scan(qid: str, field: str, text: str) -> None:
        hits = (_DELTA_ID_TOKEN.findall(text) + _ENTITY_ID_TOKEN.findall(text)
                + _QUESTIONS_STOPWORD_RE.findall(text))
        if hits:
            problems.append(violation(
                "questions_leak",
                "{}.{}: служебное в тексте — {}".format(qid, field, ", ".join(sorted(set(hits)))),
                field="{}.{}".format(qid, field)))

    for question in body["questions"]:
        scan(question["id"], "text", question["text"])
        scan(question["id"], "why", question["why"])
        for opt in question["options"]:
            scan(question["id"], "label:{}".format(opt["id"]), opt["label"])
    return problems


def questions_budget_exhausted(state: Dict[str, Any]) -> bool:
    record = state["phases"]["questions"]
    return record.get("structural_rework_count", 0) + 1 > structural_limit("questions")


def questions_fallback_outcome(run: Run, code: str, artifact: Optional[Path]
                               ) -> Tuple[Dict[str, Any], List[str]]:
    """Исчерпание бюджета questions — НЕ failed: собственный успешный исход.

    Контракт structural_reject «(в) исчерпание → failed» не трогается — эта
    ветка живёт в submit_questions ДО его вызова (hitl-v3-spec, круг 2).
    Запись фазы получает status degraded + fallback: рендер compose уходит в
    поимённый v2-вид, run жив, accept работает по-старому (флаги партиции +
    глобальный ack). Одно history-событие — на переход, не на каждый рендер.
    """
    state = run.state
    record = state["phases"]["questions"]
    seq = record.get("rejection_seq", 0) + 1
    record["rejection_seq"] = seq
    saved = save_rejected_artifact(run, "questions", seq, artifact)
    record.update({"status": "degraded", "fallback": True, "updated_at": now_iso()})
    log_event(state, "questions_degraded", detail=code)
    set_phase(state, "compose")
    save_state(run.run_dir, state)
    fallback_lines = [
        "Вопросы не сложились ({}) — бюджет доработок узла исчерпан".format(code),
        "Экран решений пойдёт поимённым списком",
    ]
    # Автосцепка код-фаз: фолбэк тоже рендерит экран этим же вызовом
    # (expected_commands больше не нужен — compose уже исполнен).
    payload, compose_lines = perform_compose(run)
    payload["outcome"] = "questions_degraded"
    payload["reason"] = code
    if saved:
        payload["rejected_artifact"] = saved
    return payload, fallback_lines + compose_lines


def submit_questions(args: argparse.Namespace, run: Run) -> Tuple[Dict[str, Any], List[str]]:
    state = run.state
    require_live(state)
    path = require_artifact(args, run)

    try:
        body, digest = read_json_artifact(path)
    except SpineError as exc:
        if exc.code != "artifact_not_json":
            raise
        require_phase(state, "questions")
        if questions_budget_exhausted(state):
            return questions_fallback_outcome(run, "artifact_not_json", path)
        raise structural_reject(run, "questions", "artifact_not_json", str(exc),
                                structural_recovery("artifact_not_json", "questions"),
                                artifact=path)
    if idempotent_ok(state, "questions", digest):
        payload = status_payload(run)
        payload["idempotent"] = True
        return payload, ["Тот же файл вопросов уже принят — состояние не изменилось"]
    require_phase(state, "questions")
    parse_meta(args.meta, "questions")

    all_deltas = ledger_deltas(run)
    live = live_deltas(all_deltas)
    all_ids = {d.get("id") for d in all_deltas}
    required = questions_required_ids(live)

    def reject(code: str, message: str, problems: List[Dict[str, Any]],
               **fmt: Any) -> Tuple[Dict[str, Any], List[str]]:
        if questions_budget_exhausted(state):
            return questions_fallback_outcome(run, code, path)
        raise structural_reject(run, "questions", code, message,
                                structural_recovery(code, "questions", **fmt),
                                artifact=path, violations=problems)

    problems = questions_schema_violations(body)
    if problems:
        return reject("questions_invalid", "файл вопросов не прошёл словарь формы",
                      problems, items=violation_digest(problems))
    problems = questions_coverage_violations(body, live, all_ids)
    if problems:
        return reject("questions_coverage", "вопросы не покрывают решаемые пункты разбиением",
                      problems, items=violation_digest(problems, key="message"))
    problems = questions_leak_violations(body)
    if problems:
        return reject("questions_leak", "в текстах вопросов утечка внутренних id или служебной лексики",
                      problems, items=violation_digest(problems))
    covered = {did for q in body["questions"] for did in q["covers"]}
    uncovered_live = [d.get("id") for d in live if d.get("id") not in covered]
    n_decisions, cap = questions_cap(len(body["questions"]), len(uncovered_live), len(required))
    if n_decisions > cap:
        # allowed — сколько ВОПРОСОВ узлу реально можно: кап минус 1 за непустой
        # блок «Советую». Recovery без этого числа не чинит: узел видит «потолок
        # 7», имеет 7 вопросов и не понимает нарушения (живой прогон 31.07).
        return reject("questions_overflow", "число решений превышает кап экрана",
                      [violation("questions_overflow",
                                 "решений {} при потолке {}".format(n_decisions, cap),
                                 field="questions")],
                      n=n_decisions, limit=cap,
                      allowed=cap - (1 if uncovered_live else 0))

    stored = run.path(ART_QUESTIONS)
    if path.resolve() != stored.resolve():
        write_json_artifact(stored, body)
    state["questions"] = {"artifact": ART_QUESTIONS, "hash": digest}
    mark_validated(state, "questions", ART_QUESTIONS, digest)
    set_phase(state, "compose")
    log_event(state, "submit:questions", detail="{}".format(len(body["questions"])))
    save_state(run.run_dir, state)

    accepted_line = "Принято: {} {} · решений на экране: {}".format(
        len(body["questions"]),
        plural_ru(len(body["questions"]), "вопрос", "вопроса", "вопросов"),
        n_decisions)
    # Автосцепка код-фаз: compose — код, экран решений рендерится этим же
    # вызовом. Отказ рендера не отменяет приём вопросов: состояние сохранено,
    # повтор — командой `compose`.
    payload, lines = perform_compose(run)
    payload["artifact_hash"] = digest
    return payload, [accepted_line] + lines


# --------------------------------------------------------------------------- #
# compose
# --------------------------------------------------------------------------- #

def ledger_deltas(run: Run) -> List[Dict[str, Any]]:
    record = run.state["ledger"]
    if not record["hash"]:
        raise SpineError("precondition_review", "нарушен precondition review_aggregated: ledger не собран")
    path = run.path(record["artifact"])
    package, digest = read_json_artifact(path)
    if digest != record["hash"]:
        raise SpineError("artifact_hash_mismatch", "ledger изменён после агрегации ревью")
    return package.get("deltas", [])


def compose_bucket(delta: Dict[str, Any]) -> int:
    if delta.get("section") != "doubtful":
        return 0
    return 2 if delta.get("doubt_reason") == "unresolved" else 1


def live_deltas(deltas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Живой состав ledger — чистый фильтр, без I/O (hash-сверка в ledger_deltas).

    Единственное определение живости для всех потребителей: auto-pass в
    submit_review, валидация submit_questions, рендер compose. До ребейза
    второй очереди волны D `merged_into` в ledger не существует — фильтр
    passthrough; после — слитые дельты выпадают из состава.
    """
    return [d for d in deltas if not d.get("merged_into")]


def questions_required_ids(deltas: List[Dict[str, Any]]) -> List[str]:
    """Покрываемое множество вопросов: предикат по bucket, не по полям вердикта.

    Каждый живой пункт с bucket ≠ 0 и каждый с home_question обязан войти ровно
    в один вопрос (hitl-v3-spec, questions_coverage); пустое множество — auto-pass
    фазы questions ещё в submit_review.
    """
    return [d.get("id") for d in deltas
            if d.get("id") and (compose_bucket(d) != 0 or d.get("home_question"))]


# Секции экрана 2. Нейтральные формулировки: home-вопрос бывает и у «уверенного»
# пункта, поэтому bucket не подменяется темой вопроса (hitl-ux-spec, экран 2 п.5).
COMPOSE_SECTIONS: Tuple[Tuple[int, str], ...] = (
    (0, "Советую"),
    (1, "Нужен ваш выбор"),
    (2, "Не прошло автоматическую проверку — решать вам"),
)

# doubt_reason человеческой строкой — только в debug (находка №16 живого
# прогона №2): пользователю обе формулировки нечитаемы, в бизнес-виде причина
# не выводится вовсе — сомнение читается из самого doubt_question, пункт
# остаётся отдельным номером (гранулярность решения не теряется).
DOUBT_REASON_HUMAN: Dict[str, str] = {
    "dispute": "независимая проверка не подтвердила правку",
    "unresolved": "правка не прошла автоматическую проверку",
}

# Внутренние id дельт в прозе вопросов («дублирует d016» — пишет ревьюер) в
# бизнес-виде заменяются экранным номером пункта: №N — тот же номер, которым
# пользователь отвечает на accept (маппинг «номер → delta_id» уже несёт
# compose-map, механизм resolve_ids). Неизвестный id гасится «№?»: утечка
# внутренней нумерации хуже потери точности ссылки. Debug показывает как есть.
_DELTA_ID_TOKEN = re.compile(r"\bd\d{3,}\b")


def humanize_question(text: str, number_by_id: Dict[str, int],
                      entity_by_id: Optional[Dict[str, int]] = None) -> str:
    def swap(match: "re.Match[str]") -> str:
        number = number_by_id.get(match.group(0))
        return "№{}".format(number) if number is not None else "№?"

    def swap_entity(match: "re.Match[str]") -> str:
        # Entity-id (E01/Е01) заменяется экранным номером ТОЛЬКО при попадании в
        # карту entity→delta живого состава (tie-break — минимальный номер);
        # неизвестный id остаётся как есть: id сущности не совпадает с
        # нумерацией пунктов, «№?» здесь потерял бы больше, чем спрятал.
        number = (entity_by_id or {}).get(match.group(0))
        return "№{}".format(number) if number is not None else match.group(0)

    return _ENTITY_ID_TOKEN.sub(swap_entity, _DELTA_ID_TOKEN.sub(swap, text))


def plural_ru(count: int, one: str, few: str, many: str) -> str:
    """Число в тексте экрана согласовано: 1 изменение · 4 изменения · 5 изменений."""
    if 11 <= count % 100 <= 14:
        return many
    tail = count % 10
    if tail == 1:
        return one
    if 2 <= tail <= 4:
        return few
    return many


def target_title(base: Path, target: str) -> Optional[str]:
    """Роль файла = его H1: первая `# `-строка существующего target-файла.

    В context.json роли файлов фактически нет (закрыто связкой 30.07), поэтому
    заголовок читается с диска детерминированно. Файла нет, H1 нет, не читается —
    возвращаем None: заголовком группы остаётся путь (осознанный остаток).

    Defense-in-depth: абсолютный target и любой выход за базу (включая symlink
    наружу) — None, читать нечего. Confinement дельт живёт выше, но эта функция
    кладёт текст в hash-bound compose.md — свой отказ обязателен. Symlink,
    остающийся внутри базы, легален.
    """
    if not target:
        return None
    rel = Path(target)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    path = base / rel
    try:
        if not str(path.resolve()).startswith(str(base.resolve()) + os.sep):
            return None
    except OSError:
        return None
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("# "):
                    return line[2:].strip() or None
    except (OSError, UnicodeDecodeError):
        return None
    return None


def compose_group_header(base: Path, target: str, operation: Optional[str]) -> str:
    title = target_title(base, target)
    if title:
        return "{} · {}".format(title, target)
    if operation == "create":
        return "новый файл: {}".format(target)
    return target


# Глагол однострочника v3 — механика по operation, без LLM (hitl-v3-spec).
OPERATION_VERBS: Dict[str, str] = {
    "add": "добавлю",
    "update": "обновлю",
    "delete": "удалю",
    "move": "перенесу",
    "create": "заведу файл",
    "merge": "объединю",
}

_ONELINE_CHECKBOX = re.compile(r"^\[[ xX]\]\s+")


def truncate_line(text: str, limit: int = 100) -> str:
    """Обрез ~limit символов по границе слова (однострочник v3)."""
    if len(text) <= limit:
        return text
    cut = text[:limit + 1]
    cut = cut[:cut.rfind(" ")] if " " in cut else text[:limit]
    return cut.rstrip(" ,.;:·—-") + "…"


def one_liner_head(text: str, operation: Optional[str], anchor: Optional[str]) -> str:
    """Первая строка proposed_text без list-маркера и чекбокс-префикса.

    `delete` с пустым/коротким текстом берёт суть из обрезанного anchor —
    иначе однострочник удаления не называет, что удаляется.
    """
    raw = (text or "").strip()
    head = raw.splitlines()[0] if raw else ""
    if head.startswith("- ") or head.startswith("* "):
        head = head[2:]
    head = _ONELINE_CHECKBOX.sub("", head).strip()
    if operation == "delete" and len(head) < 20:
        anchor_raw = (anchor or "").strip()
        anchor_head = anchor_raw.splitlines()[0].strip() if anchor_raw else ""
        if anchor_head:
            head = anchor_head
    return truncate_line(head)


def compose_class_signals(deltas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Машинные признаки класса пакета — в payload compose, не на экран.

    Класс churn_analysis (hitl-v3-spec, Eval): ≥25 живых дельт · ≥1 кластер
    одного дома ≥5 пунктов (по target_file) · ≥3 живых doubtful, различных по
    target_file либо entity_id. Порог живёт ОФФЛАЙН (мини-суита); в живом
    смоуке признаки — наблюдение отчёта, не гейт.
    """
    by_target: Dict[str, int] = {}
    for delta in deltas:
        key = delta.get("target_file") or ""
        by_target[key] = by_target.get(key, 0) + 1
    doubtful_keys = {(delta.get("target_file"), delta.get("entity_id"))
                     for delta in deltas if delta.get("section") == "doubtful"}
    return {
        "live_count": len(deltas),
        "max_target_cluster": max(by_target.values(), default=0),
        "doubtful_distinct": len(doubtful_keys),
    }


def questions_for_render(run: Run, items: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """Вопросы для v3-вида; None → поимённый v2-вид.

    None в трёх случаях: запись фазы несёт fallback (деградация узла или ранее
    зафиксированная несходимость), артефакт отсутствует/не сходится по hash,
    covers вышли за живой состав. Свежая несходимость фиксируется флагом
    fallback записи фазы + ОДНИМ history-событием — повторные рендеры событий
    не плодят (state сохранит вызывающий: cmd_compose/cmd_accept).
    """
    state = run.state
    record = (state.get("phases") or {}).get("questions") or {}
    if record.get("fallback"):
        return None
    rec = state.get("questions") or {}
    if not rec.get("hash"):
        # Run старше волны G либо фаза ещё впереди — v2 без события.
        return None
    live_ids = {item["delta_id"] for item in items}
    body: Dict[str, Any] = {}
    reason: Optional[str] = None
    path = run.path(rec["artifact"])
    if not path.is_file():
        reason = "questions.json исчез"
    else:
        try:
            body, digest = read_json_artifact(path)
        except SpineError:
            reason = "questions.json не парсится"
        else:
            if digest != rec["hash"]:
                reason = "hash questions.json разошёлся с записанным"
            else:
                covered = {did for q in body.get("questions", [])
                           for did in q.get("covers", [])}
                if not covered <= live_ids:
                    reason = "covers вне живого состава"
    if reason is not None:
        record["fallback"] = True
        record["updated_at"] = now_iso()
        log_event(state, "questions_fallback", detail=reason)
        return None
    return body.get("questions", [])


def questions_tech_block(questions: List[Dict[str, Any]],
                         answers: Dict[str, Any]) -> List[str]:
    """Debug-техблок questions: id, covers, раскладка decisions рядом с label."""
    out = ["— Вопросы (questions) —"]
    for question in questions:
        out.append("{} · covers: {} · default: {}".format(
            question["id"], ", ".join(question["covers"]), question["default"]))
        for opt in question["options"]:
            decisions = " ".join("{}={}".format(k, v)
                                 for k, v in sorted(opt["decisions"].items()))
            out.append("  - {} «{}»: {}".format(opt["id"], opt["label"], decisions))
    if answers:
        out.append("answers: " + " · ".join(
            "{}={} ({})".format(qid, entry.get("option"), entry.get("mode"))
            for qid, entry in sorted(answers.items())))
    return out


def render_compose(run: Run, deltas: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """Экран 2: v3-вид «вопросы вместо портянки» и поимённый v2-вид.

    Сортировка `(bucket, target_file, id)`, состав `items[]` и маппинг «номер →
    delta_id» ОДИНАКОВЫ во всех видах: номера пунктов — это механизм
    take/reject, и он не имеет права зависеть от режима показа. Debug — полный
    v2-вид + техблок questions; бизнес-вид — v3 (экран ведут вопросы), а при
    fallback записи фазы questions или несходимости артефакта — поимённый v2.
    """
    state = run.state
    base = Path(state["base_path"])
    debug = is_debug(state)
    # `or ""`: явный JSON null в target_file/id не должен ронять сортировку TypeError'ом.
    ordered = sorted(live_deltas(deltas),
                     key=lambda d: (compose_bucket(d), d.get("target_file") or "", d.get("id") or ""))
    items: List[Dict[str, Any]] = []
    for number, delta in enumerate(ordered, start=1):
        target = delta.get("target_file") or ""
        missing_addressee = delta.get("operation") != "create" and not (base / target).is_file()
        items.append({
            "n": number,
            "delta_id": delta.get("id"),
            "entity_id": delta.get("entity_id"),
            "bucket": compose_bucket(delta),
            "target_file": target,
            "operation": delta.get("operation"),
            "section": delta.get("section"),
            "doubt_reason": delta.get("doubt_reason"),
            "home_question": delta.get("home_question"),
            "doubt_question": delta.get("doubt_question"),
            "missing_addressee": missing_addressee,
            "text": delta.get("proposed_text") or "",
        })

    number_by_id = {i["delta_id"]: i["n"] for i in items if i["delta_id"]}
    entity_by_id: Dict[str, int] = {}
    for item in items:
        eid = item.get("entity_id")
        if eid and eid not in entity_by_id:
            entity_by_id[eid] = item["n"]
    delta_by_number = {item["n"]: delta for item, delta in zip(items, ordered)}
    questions = questions_for_render(run, items)
    answers = (state.get("accept") or {}).get("answers") or {}

    covered_by: Dict[str, str] = {}
    for question in questions or []:
        for did in question.get("covers", []):
            covered_by[did] = question["id"]
    advised = [i for i in items if i["delta_id"] not in covered_by]
    n_decisions, decisions_cap = questions_cap(
        len(questions or []), len(advised) if questions is not None else 0,
        len(questions_required_ids(ordered)))
    max_covers = max((len(q.get("covers", [])) for q in (questions or [])), default=0)

    def bullet(item: Dict[str, Any]) -> List[str]:
        raw = (item["text"] or "").strip()
        lines = raw.splitlines() or [""]
        head_line = lines[0]
        # Свой list-marker правки съедается номером пункта: «- [1] - текст» —
        # мусор на экране, а содержание строки от снятия маркера не меняется.
        if head_line.startswith("- ") or head_line.startswith("* "):
            head_line = head_line[2:]
        out = ["- [{}] {}".format(item["n"], head_line)] + ["  " + line for line in lines[1:]]
        if item["missing_addressee"]:
            out.append("  (⚠ файл, к которому относится правка, не найден в базе)")
        if debug:
            tech = ["{}".format(item["delta_id"]), "section={}".format(item["section"]),
                    "bucket={}".format(item["bucket"]), "operation={}".format(item["operation"]),
                    "target={}".format(item["target_file"])]
            if item["doubt_reason"]:
                tech.append("doubt_reason={}".format(item["doubt_reason"]))
            out.append("  [debug] " + " · ".join(tech))
        return out

    def one_liner(item: Dict[str, Any]) -> List[str]:
        """Однострочник v3: глагол по operation + первая строка текста + H1 дома.

        Решение-несущая пометка missing_addressee переживает сжатие поимённо —
        той же строкой, что в v2 (тест-якорь).
        """
        delta = delta_by_number[item["n"]]
        verb = OPERATION_VERBS.get(item["operation"] or "", "изменю")
        body = one_liner_head(item["text"], item["operation"], delta.get("anchor"))
        title = target_title(base, item["target_file"]) or item["target_file"]
        line = "- [{}] {}".format(item["n"], verb)
        if body:
            line += ": {}".format(body)
        if title:
            line += " → {}".format(title)
        out_lines = [line]
        if item["missing_addressee"]:
            out_lines.append("  (⚠ файл, к которому относится правка, не найден в базе)")
        return out_lines

    counts = {bucket: len([i for i in items if i["bucket"] == bucket]) for bucket, _ in COMPOSE_SECTIONS}
    total = len(items)
    # date/topic по схеме nullable: незаполненное поле не должно печатать «None»
    # на бизнес-экране (та же ветка есть у business_resume_say).
    date, topic = state["immutable"]["date"], state["immutable"]["topic"]
    if date and topic:
        head = "# По встрече {} — {}".format(date, topic)
    elif date or topic:
        head = "# По встрече {}".format(date or topic)
    else:
        head = "# По встрече"

    # Тексты вопросов в бизнес-виде проходят humanize_question (находка №16 +
    # entity-дыра волны G): внутренние id → экранные номера.
    def question_text(raw: str) -> str:
        return raw if debug else humanize_question(raw, number_by_id, entity_by_id)

    if debug or questions is None:
        # Полный поимённый вид: debug всегда (v2 + техблок questions), бизнес —
        # только при fallback фазы questions.
        out: List[str] = [
            head,
            "",
            "Предлагаю {} {} базы: {} советую, {} — нужен ваш выбор, {} — не прошли "
            "автоматическую проверку.".format(
                total, plural_ru(total, "изменение", "изменения", "изменений"),
                counts[0], counts[1], counts[2]),
            "",
            "Решение нужно по каждому номеру: назовите, что берём и что нет. Текст пункта можно "
            "поправить — скажите, какой и как: я внесу правку и покажу обновлённый список перед записью.",
            "",
        ]

        # Вопросы, требующие слова пользователя, — первыми: без них по остальному
        # списку решение принимать нечем.
        home = [i for i in items if i["home_question"]]
        if home:
            out.append("## Где записать — решаете вы")
            out.append("")
            for item in home:
                line = "- [{}] Куда положить: {}".format(item["n"], question_text(item["home_question"]))
                out.append(line + (" · [debug] {}".format(item["delta_id"]) if debug else ""))
            out.append("")
        doubts = [i for i in items if i["doubt_question"]]
        if doubts:
            out.append("## Спорные пункты")
            out.append("")
            for item in doubts:
                line = "- [{}] Сомнение: {}".format(item["n"], question_text(item["doubt_question"]))
                if debug:
                    # Техпричина («независимая проверка…») — только в debug
                    # (находка №16): в бизнес-виде причина не выводится, сомнение
                    # читается из самого вопроса, пункт остаётся отдельным номером.
                    reason = DOUBT_REASON_HUMAN.get(item["doubt_reason"] or "")
                    if reason:
                        line += " Причина: {}.".format(reason)
                    line += " · [debug] {}".format(item["delta_id"])
                out.append(line)
            out.append("")

        for bucket, title in COMPOSE_SECTIONS:
            out.append("## {}".format(title))
            out.append("")
            block = [i for i in items if i["bucket"] == bucket]
            if not block:
                out.append("_нет пунктов_")
                out.append("")
                continue
            current: Optional[str] = None
            for item in block:
                if item["target_file"] != current:
                    if current is not None:
                        out.append("")
                    current = item["target_file"]
                    out.append("### {}".format(
                        compose_group_header(base, item["target_file"], item["operation"])))
                out.extend(bullet(item))
            out.append("")

        if debug:
            # Машинный хвост — только в debug: в бизнес-виде решение пользователь
            # называет словами, команды складывает координатор.
            out.append("— Решение пользователя —")
            if questions:
                out.append("accept --answer <q>=<опция|default> … --take <№,…> --reject <№,…> "
                           "по непокрытым [--already <№,…>] [--amend <id>=<файл>]")
            else:
                out.append("accept --take <№,…> --reject <№,…> [--already <№,…>] [--amend <id>=<файл>]")
            out.append("")
            if questions is not None:
                out.extend(questions_tech_block(questions, answers))
                out.append("")
    else:
        # v3: экран ведут вопросы (hitl-v3-spec). Полные тексты пунктов — по
        # `compose --expand` и в debug; чтение артефактов в обход рендеров
        # по-прежнему запрещено.
        out = [head, ""]
        if questions:
            if advised:
                out.append("Решений: {} — {} {} и одна фраза по советуемым.".format(
                    n_decisions, len(questions),
                    plural_ru(len(questions), "вопрос", "вопроса", "вопросов")))
            else:
                out.append("Решений: {} — по числу вопросов.".format(n_decisions))
        else:
            out.append("Вопросов у меня нет — предлагаю взять всё советуемое.")
        out.append("Изменений: {} — {} советую, {} — нужен ваш выбор, {} — не прошли "
                   "автоматическую проверку.".format(total, counts[0], counts[1], counts[2]))
        out.append("")
        if questions:
            out.append("## Нужны ваши ответы")
            out.append("")
            for idx, question in enumerate(questions, start=1):
                out.append("**Вопрос {}.** {}".format(idx, question_text(question["text"])))
                out.append("Что зависит от ответа: {}".format(question_text(question["why"])))
                out.append("Варианты:")
                for opt in question["options"]:
                    line = "- {}".format(question_text(opt["label"]))
                    if opt["id"] == question["default"]:
                        line += " — так и сделаю, если скажете «решайте сами»"
                    out.append(line)
                block = [i for i in items if covered_by.get(i["delta_id"]) == question["id"]]
                out.append("Закрывает {} {}:".format(
                    len(block), plural_ru(len(block), "пункт", "пункта", "пунктов")))
                for item in block:
                    out.extend(one_liner(item))
                out.append("")
        if advised:
            out.append("## Советую взять как есть ({})".format(len(advised)))
            out.append("")
            for item in advised:
                out.extend(one_liner(item))
            out.append("")
            out.append("По этому блоку достаточно одной фразы: «берём всё советуемое» — "
                       "или назовите исключения: «всё, кроме №7».")
            out.append("")

    mapping: Dict[str, Any] = {
        "items": items,
        "debug": debug,
        "class_signals": compose_class_signals(ordered),
    }
    if questions is not None:
        mapping["questions"] = questions
        mapping["decisions"] = n_decisions
        mapping["decisions_cap"] = decisions_cap
        mapping["max_covers"] = max_covers
    return "\n".join(out), mapping


def do_compose(run: Run) -> Tuple[str, str, Dict[str, Any]]:
    state = run.state
    deltas = ledger_deltas(run)
    text, mapping = render_compose(run, deltas)
    compose_path = run.path(ART_COMPOSE)
    atomic_write_text(compose_path, text)
    digest = sha256_file(compose_path)
    atomic_write_text(run.path(ART_COMPOSE_HASH), digest + "\n")
    mapping["compose_hash"] = digest
    write_json_artifact(run.path(ART_COMPOSE_MAP), mapping)
    state["compose"] = {
        "artifact": ART_COMPOSE,
        "hash": digest,
        "map": ART_COMPOSE_MAP,
        "map_hash": artifact_hash(run.path(ART_COMPOSE_MAP)),
        "items": len(mapping["items"]),
    }
    return text, digest, mapping


def compose_expand(run: Run, raw_tokens: List[str]) -> Tuple[Dict[str, Any], List[str]]:
    """`compose --expand <№…|all>` — читающий режим: полные тексты пунктов.

    State не мутирует, compose.md/compose-map/hash не трогает (ранний выход до
    do_compose); вывод — тем же каналом показа. До первого compose →
    precondition_compose (load_compose_map); при pending_amend и при экране,
    собранном в прежнем режиме показа (debug-переключение), — отказ «пересобери
    compose»; несуществующий номер — названный отказ со списком валидных.
    """
    state = run.state
    require_phase(state, "compose", allow=("accept",))
    mapping = load_compose_map(run)
    if state["accept"].get("pending_amend"):
        raise SpineError(
            "compose_stale",
            "экран собран до amend — пересобери `compose` и показывай свежий")
    if "debug" in mapping and bool(mapping.get("debug")) != is_debug(state):
        raise SpineError(
            "compose_stale",
            "экран собран в прежнем режиме показа — пересобери `compose`")

    items = mapping["items"]
    tokens = parse_id_tokens(raw_tokens)
    if not tokens or any(t.lower() == "all" for t in tokens):
        selected = list(items)
    else:
        by_number = {str(item["n"]): item for item in items}
        by_id = {item["delta_id"]: item for item in items if item.get("delta_id")}
        selected, unknown = [], []
        for token in tokens:
            found = by_number.get(token) or by_id.get(token)
            if found is None:
                unknown.append(token)
            else:
                selected.append(found)
        if unknown:
            raise SpineError(
                "unknown_delta_id",
                "--expand содержит номера вне состава compose; валидные: 1–{}".format(len(items)),
                violations=[violation("unknown_delta_id", "вне состава compose",
                                      field="--expand", delta_ids=unknown)])
        seen: set = set()
        selected = [i for i in selected if not (i["n"] in seen or seen.add(i["n"]))]

    lines = ["Полные тексты пунктов ({}):".format(len(selected)), ""]
    for item in selected:
        raw = (item["text"] or "").strip()
        body_lines = raw.splitlines() or [""]
        head_line = body_lines[0]
        if head_line.startswith("- ") or head_line.startswith("* "):
            head_line = head_line[2:]
        lines.append("- [{}] {}".format(item["n"], head_line))
        lines += ["  " + line for line in body_lines[1:]]
        if item.get("missing_addressee"):
            lines.append("  (⚠ файл, к которому относится правка, не найден в базе)")

    payload = {
        "ok": True,
        "run_id": state["run_id"],
        "phase": state["phase"],
        "expand": [item["n"] for item in selected],
        "items": [{"n": item["n"], "delta_id": item.get("delta_id"),
                   "text": item.get("text")} for item in selected],
        "business": business_block(business_stage("accept")),
    }
    return payload, lines


def cmd_compose(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    run = require_run(args)
    if getattr(args, "expand", None):
        return compose_expand(run, args.expand)
    return perform_compose(run)


def perform_compose(run: Run) -> Tuple[Dict[str, Any], List[str]]:
    """Рендер экрана решений. Вызывается и командой `compose`, и автосцепкой
    код-фаз: приём questions (включая fallback и auto-pass) рендерит экран этим
    же вызовом — минус ход координатора (кандидат ускорения 31.07)."""
    state = run.state
    require_phase(state, "compose", allow=("accept",))
    if not state["post_validation"]["hash"]:
        raise SpineError(
            "precondition_post_review",
            "нарушен precondition compose_ready: пост-ревью валидация не выполнена",
        )
    post_path = run.path(state["post_validation"]["artifact"])
    if not post_path.is_file() or artifact_hash(post_path) != state["post_validation"]["hash"]:
        raise SpineError("artifact_hash_mismatch", "post_review_validation.json изменён после записи")

    before = state["compose"]["hash"]
    text, digest, mapping = do_compose(run)
    idempotent = before == digest
    if state["phase"] == "compose":
        mark_validated(state, "compose", ART_COMPOSE, digest)
        set_phase(state, "accept")
    else:
        # Re-compose из фазы accept (amend, переключение debug): фазовая запись
        # обязана держать hash файла на диске — иначе `resume` объявит штатную
        # пересборку подменой (artifact_hash_mismatch).
        record = state["phases"]["compose"]
        record["artifact"] = ART_COMPOSE
        record["artifact_hash"] = digest
        record["updated_at"] = now_iso()
    log_event(state, "compose", detail=digest[:12])
    save_state(run.run_dir, state)

    payload = status_payload(run)
    payload["compose_hash"] = digest
    payload["compose_path"] = str(run.path(ART_COMPOSE))
    payload["map_path"] = str(run.path(ART_COMPOSE_MAP))
    payload["items"] = len(mapping["items"])
    payload["idempotent"] = idempotent
    payload["compose"] = text
    # Наблюдаемость v3 для eval-порога (счёт решений — кодом, порог — оффлайн).
    payload["class_signals"] = mapping.get("class_signals")
    if "questions" in mapping:
        payload["decisions"] = mapping.get("decisions")
        payload["decisions_cap"] = mapping.get("decisions_cap")
        payload["max_covers"] = mapping.get("max_covers")
        payload["question_count"] = len(mapping["questions"])
    else:
        payload["questions_fallback"] = bool(
            (state["phases"].get("questions") or {}).get("fallback"))
    payload["business"] = business_block(business_stage("accept"), BUSINESS_SCREENS["accept"])
    lines = [text.rstrip("\n")]
    if is_debug(state):
        # Путь run-каталога и собственный hash compose — техблок stdout; внутрь
        # hash-bound файла hash не пишется.
        lines += ["", "Источник правды: {}".format(run.path(ART_COMPOSE)),
                  "compose.hash: {}".format(digest)]
    return payload, lines


# --------------------------------------------------------------------------- #
# accept
# --------------------------------------------------------------------------- #

def load_compose_map(run: Run) -> Dict[str, Any]:
    state = run.state
    if not state["compose"]["hash"]:
        raise SpineError("precondition_compose", "нарушен precondition compose_done: compose ещё не собран")
    compose_path = run.path(state["compose"]["artifact"])
    if not compose_path.is_file():
        raise SpineError("artifact_missing", "compose.md исчез")
    if sha256_file(compose_path) != state["compose"]["hash"]:
        raise SpineError(
            "compose_hash_mismatch",
            "нарушен precondition compose_binding: compose.md изменён после рендера — повтори `compose`",
        )
    map_path = run.path(state["compose"]["map"])
    if not map_path.is_file():
        raise SpineError("artifact_missing", "compose-map.json исчез")
    if artifact_hash(map_path) != state["compose"].get("map_hash"):
        raise SpineError(
            "artifact_hash_mismatch",
            "compose-map.json изменён после рендера — повтори `compose`",
        )
    return load_json_file(map_path)


def parse_id_tokens(values: Optional[List[str]]) -> List[str]:
    tokens: List[str] = []
    for chunk in values or []:
        for token in str(chunk).replace(";", ",").split(","):
            token = token.strip()
            if token:
                tokens.append(token)
    return tokens


def resolve_ids(tokens: List[str], mapping: Dict[str, Any], label: str) -> List[str]:
    by_number = {str(item["n"]): item["delta_id"] for item in mapping["items"]}
    known = {item["delta_id"] for item in mapping["items"]}
    out: List[str] = []
    unknown: List[str] = []
    for token in tokens:
        if token in by_number:
            out.append(by_number[token])
        elif token in known:
            out.append(token)
        else:
            unknown.append(token)
    if unknown:
        raise SpineError(
            "unknown_delta_id",
            "нарушен precondition compose_scope: {} содержит id/номера вне состава compose".format(label),
            violations=[violation("unknown_delta_id", "вне состава compose", field=label, delta_ids=unknown)],
        )
    return out


def read_amend_text(path: Path) -> str:
    """Amend меняет только proposed_text: структурные поля неизменяемы."""
    if path.suffix == ".json":
        body = load_json_file(path, code="amend_not_json")
        if not isinstance(body, dict):
            raise SpineError("amend_invalid", "файл amend должен быть объектом либо текстом")
        extra = sorted(k for k in body if k not in ("proposed_text", "id", "delta_id"))
        if extra:
            raise SpineError(
                "amend_structural_change",
                "amend меняет только proposed_text: смена дома/операции — reject и новый цикл",
                violations=[violation("amend_structural_change", "поле неизменяемо", field=name) for name in extra],
            )
        text = body.get("proposed_text")
        if not isinstance(text, str) or not text.strip():
            raise SpineError("amend_invalid", "в файле amend нет непустого proposed_text")
        return text
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise SpineError("amend_invalid", "файл amend пуст")
    return text


def cmd_accept(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    run = require_run(args)
    state = run.state
    require_phase(state, "accept", allow=("compose",))
    meta = parse_meta(args.meta, "accept")
    mapping = load_compose_map(run)

    composition = [item["delta_id"] for item in mapping["items"]]
    take_flags = resolve_ids(parse_id_tokens(args.take), mapping, "--take")
    reject_flags = resolve_ids(parse_id_tokens(args.reject), mapping, "--reject")

    # --- Мост «ответ → партиция» (волна G). Порядок дословно по hitl-v3-spec:
    # (1) развернуть decisions отвеченных вопросов; (2) override явным флагом по
    # покрытому номеру — замещением, легален только при поданном --answer его
    # вопроса; (3) явные флаги по непокрытым; (4) существующие гейты на
    # объединённой партиции; (5) гейт риска — пер-пунктный. Наивная надстройка
    # «--answer сверху» без этого порядка ломает missing_decisions.
    questions = {q["id"]: q for q in (mapping.get("questions") or [])}
    covered_by_q: Dict[str, str] = {}
    for qid, question in questions.items():
        for did in question.get("covers", []):
            covered_by_q[did] = qid

    answers: Dict[str, Dict[str, Any]] = {}
    for raw in args.answer or []:
        if "=" not in raw:
            raise SpineError("bad_usage", "--answer ожидает <вопрос>=<опция|default>", exit_code=2)
        qid, opt_token = (part.strip() for part in raw.split("=", 1))
        question = questions.get(qid)
        if question is None:
            raise SpineError(
                "unknown_question",
                "вопрос {} отсутствует в составе экрана{}".format(
                    qid, "" if questions else " (экран без вопросов — accept флагами партиции)"),
                violations=[violation("unknown_question", "нет такого вопроса", field="--answer")])
        if qid in answers:
            raise SpineError("bad_usage", "повторный --answer по вопросу {}".format(qid), exit_code=2)
        mode = "default" if opt_token == "default" else "explicit"
        opt_id = question["default"] if mode == "default" else opt_token
        option = next((o for o in question["options"] if o["id"] == opt_id), None)
        if option is None:
            raise SpineError(
                "unknown_option",
                "у вопроса {} нет опции {} (есть: {})".format(
                    qid, opt_id, ", ".join(o["id"] for o in question["options"])),
                violations=[violation("unknown_option", "опция вне вопроса", field="--answer")])
        answers[qid] = {"option": opt_id, "mode": mode, "decisions": option["decisions"]}

    # Fail-closed: каждый вопрос экрана обязан иметь ответ.
    unanswered = sorted(set(questions) - set(answers))
    if unanswered:
        raise SpineError(
            "question_unanswered",
            "нарушен precondition questions_answered: нет ответа на {}".format(", ".join(unanswered)),
            violations=[violation("question_unanswered", "нужен --answer <вопрос>=<опция|default>",
                                  field="--answer", delta_ids=[])],
            payload={"error_class": "question", "unanswered": unanswered})

    # (1) раскладка ответов; источник решения — для гейта риска и вывода ack.
    answer_take: set = set()
    answer_reject: set = set()
    answer_already: set = set()
    partition_source: Dict[str, Tuple[str, str, str]] = {}  # did -> (qid, mode, effect)
    for qid, entry in answers.items():
        for did, effect in entry["decisions"].items():
            partition_source[did] = (qid, entry["mode"], effect)
            if effect in ("take", "take_ack_unresolved"):
                answer_take.add(did)
            else:  # reject, reject_already
                answer_reject.add(did)
                if effect == "reject_already":
                    answer_already.add(did)

    # (2) override замещением + (3) флаги по непокрытым. Флаг по покрытому
    # номеру без --answer его вопроса до сюда не доходит (question_unanswered
    # покрывает все вопросы) — но именованный гейт остаётся на случай ответа
    # НЕ на тот вопрос: замещение легально только внутри отвеченного вопроса.
    override_take = [did for did in take_flags if did in covered_by_q]
    override_reject = [did for did in reject_flags if did in covered_by_q]
    take = sorted(((answer_take - set(override_reject)) | set(override_take))
                  | {did for did in take_flags if did not in covered_by_q})
    reject = sorted(((answer_reject - set(override_take)) | set(override_reject))
                    | {did for did in reject_flags if did not in covered_by_q})
    # Источник решения: флаг, ДУБЛИРУЮЩИЙ раскладку, override'ом не считается —
    # иначе «--take по всем номерам» поверх explicit-ответа съедал бы ack риска.
    for did in override_take:
        prev = partition_source.get(did)
        if prev is None or prev[2] not in ("take", "take_ack_unresolved"):
            partition_source[did] = (covered_by_q[did], "override", "take")
    for did in override_reject:
        prev = partition_source.get(did)
        if prev is None or prev[2] not in ("reject", "reject_already"):
            partition_source[did] = (covered_by_q[did], "override", "reject")

    # (4) существующие гейты — на объединённой партиции.
    both = sorted(set(take) & set(reject))
    if both:
        raise SpineError(
            "conflicting_decisions",
            "нарушен precondition partition: id одновременно в take и reject",
            violations=[violation("conflicting_decisions", "решение неоднозначно", field="--take/--reject", delta_ids=both)],
        )
    missing = sorted(set(composition) - set(take) - set(reject))
    if missing:
        raise SpineError(
            "missing_decisions",
            "нарушен precondition partition: решение принято не по всем пунктам compose",
            violations=[violation("missing_decisions", "нет решения", field="--take/--reject", delta_ids=missing)],
            payload={"error_class": "question", "missing": missing},
        )

    # --already по ИТОГОВОЙ партиции: reject_already раскладки даёт пометку
    # автоматически; ручной флаг легален и поверх покрытого номера.
    already = sorted(set(resolve_ids(parse_id_tokens(args.already), mapping, "--already"))
                     | (answer_already & set(reject)))
    stray = sorted(set(already) - set(reject))
    if stray:
        raise SpineError(
            "already_not_rejected",
            "нарушен precondition already_subset: --already помечает только отклонённые пункты",
            violations=[violation("already_not_rejected", "пункт не в reject",
                                  field="--already", delta_ids=stray)],
        )

    # (5) гейт риска — пер-пунктный (волна G): take пункта bucket 2 легален,
    # если (а) он пришёл из раскладки опции с mode explicit — сам ответ и есть
    # согласие на риск; либо (б) пункт не покрыт вопросом и подан глобальный
    # --meta ack_unresolved=true (как раньше). mode default источником риска
    # быть не может (двойная защита: валидация узла + этот fail-closed).
    unresolved_taken = sorted(
        item["delta_id"] for item in mapping["items"]
        if item["delta_id"] in take and item["bucket"] == 2
    )
    ack_via_answers: List[str] = []
    unacked: List[str] = []
    for did in unresolved_taken:
        source = partition_source.get(did)
        if source is not None and source[1] == "explicit":
            ack_via_answers.append(did)
            continue
        if did not in covered_by_q and meta.get("ack_unresolved"):
            continue
        unacked.append(did)
    if unacked:
        raise SpineError(
            "unresolved_requires_ack",
            "нарушен precondition ack_unresolved: приём unresolved-пункта требует явного "
            "согласия — ответом на его вопрос либо --meta ack_unresolved=true по непокрытым",
            violations=[violation("unresolved_requires_ack", "нужен явный ack", field="--meta", delta_ids=unacked)],
        )

    amendments: Dict[str, str] = {}
    for raw in args.amend or []:
        if "=" not in raw:
            raise SpineError("bad_usage", "--amend ожидает <id>=<файл>", exit_code=2)
        key, value = raw.split("=", 1)
        target = resolve_ids([key.strip()], mapping, "--amend")[0]
        if target not in take:
            raise SpineError(
                "amend_not_taken",
                "amend возможен только поверх принятой дельты",
                violations=[violation("amend_not_taken", "дельта не в take", field="--amend", delta_ids=[target])],
            )
        path = resolve_within(value.strip(), run.run_dir, "--amend", "run-каталога")
        if not path.is_file():
            raise SpineError("artifact_missing", "файл amend не найден: {}".format(path))
        amendments[target] = read_amend_text(path)

    # Отказ до мутации ledger: amend поверх дельты, применённой частичным apply,
    # разошёлся бы с журналом (см. гейт partition_conflicts_journal ниже).
    if amendments and state["apply_status"] == "in_progress":
        applied_done = {e["delta_id"] for e in read_journal(run)
                        if e.get("stage") == "done" and e.get("delta_id")}
        blocked = sorted(set(amendments) & applied_done)
        if blocked:
            raise SpineError(
                "partition_conflicts_journal",
                "нарушен precondition partition_covers_journal: дельта уже применена в базу "
                "до обрыва apply — amend невозможен, прими её в исходном виде",
                violations=[violation("applied_delta_amended",
                                      "дельта применена в базу до обрыва apply — amend невозможен",
                                      field="--amend", delta_ids=[did]) for did in blocked],
            )

    if amendments:
        package = load_normalized(run, "canon")
        ledger = load_json_file(run.path(state["ledger"]["artifact"]))
        by_id = {d["id"]: d for d in ledger.get("deltas", [])}
        for delta_id, text in amendments.items():
            by_id[delta_id]["proposed_text"] = text
            by_id[delta_id]["amended_by"] = "approver"
        ledger["deltas"] = [by_id[d["id"]] for d in ledger.get("deltas", [])]
        ledger.update(package_meta(run))
        ledger["phase_a_nodes"] = state["phase_a"]["nodes"]
        ledger["dropped_nodes"] = package.get("dropped_nodes", [])
        violations = validate_package(ledger, "coverage") + validate_package(ledger, "final")
        if violations:
            raise SpineError(
                "amend_validation_failed",
                "амендованный пакет не прошёл полный стек инвариантов",
                violations=violations_out(violations),
            )
        state["ledger"]["hash"] = write_json_artifact(run.path(ART_LEDGER), ledger)
        _, compose_digest, _ = do_compose(run)
        # Amend переписывает ledger.json и compose.md на диске — фазовые записи
        # review/compose обязаны держать hash'и файлов (resume сверяет по ним,
        # застарелая запись объявила бы штатный amend подменой артефакта).
        state["phases"]["review"].update({
            "artifact": ART_LEDGER, "artifact_hash": state["ledger"]["hash"],
            "updated_at": now_iso()})
        state["phases"]["compose"].update({
            "artifact": ART_COMPOSE, "artifact_hash": compose_digest,
            "updated_at": now_iso()})
        state["accept"].update({
            "take": take, "reject": reject,
            "amended": sorted(amendments), "pending_amend": True,
            "ack_unresolved": bool(meta.get("ack_unresolved")) or bool(ack_via_answers),
            "answers": {qid: {"option": e["option"], "mode": e["mode"]}
                        for qid, e in answers.items()},
        })
        log_event(state, "accept:amend", detail=",".join(sorted(amendments)))
        save_state(run.run_dir, state)
        payload = status_payload(run)
        payload["amended"] = sorted(amendments)
        payload["compose_hash"] = state["compose"]["hash"]
        payload["pending_amend"] = True
        lines = [
            "Амендовано дельт: {}".format(len(amendments)),
            "Состав пересобран — новый compose.hash {}".format(state["compose"]["hash"][:12]),
            "Повтори `accept` без --amend по новому составу",
        ]
        return payload, lines

    # Финальный accept: фиксируем партицию и per-file base_hash.
    base = Path(state["base_path"])
    ledger = {d["id"]: d for d in ledger_deltas(run)}

    # Партиция против журнала частичного apply (restart-from canon после обрыва):
    # применённую до обрыва дельту нельзя ни отклонить, ни амендовать — запись в
    # базе уже есть, write-path отмену не умеет, а постчек считал бы её легитимной.
    # Названный блокер вместо тихого «отклонено пользователем, но осталось в базе».
    if state["apply_status"] == "in_progress":
        journal_by_id = {e["delta_id"]: e for e in read_journal(run) if e.get("delta_id")}
        journal_done = {did for did, e in journal_by_id.items() if e.get("stage") == "done"}
        problems = [violation("applied_delta_rejected",
                              "дельта применена в базу до обрыва apply — отклонить нельзя, прими её",
                              field="--take/--reject", delta_ids=[did])
                    for did in sorted(journal_done - set(take))]
        problems += [violation("applied_delta_amended",
                               "дельта применена в базу до обрыва apply — amend невозможен",
                               field="--amend", delta_ids=[did])
                     for did in sorted(journal_done & set(state["accept"]["amended"]))]
        # Содержательная сверка (ревью 30.07, High×2): совпавший id — не та же
        # дельта. Первичный механизм — семантический fingerprint журнала: он
        # различает и то, чего в базе не видно (delete со сменённым anchor), и
        # защищает intent от ложного дозакрытия под новую версию дельты — apply
        # после гейта работает только с проверенно-идентичным составом.
        # Intent-записи вне take гейт не трогает: их ловит postcheck (journal_incomplete).
        for did in sorted(set(take) & set(journal_by_id)):
            entry, delta = journal_by_id[did], ledger[did]
            if entry.get("fingerprint"):
                diverged = entry["fingerprint"] != delta_fingerprint(delta)
            else:
                # Журнал без отпечатков (записан до этого фикса). intent и
                # delete наблюдением базы не верифицируются (delete не оставляет
                # текста) — fail closed (Codex final, High). Для done не-delete:
                # operation + наличие текста; пути не сравниваем — intent хранит
                # сырые строки, done нормализованные (ложный positive).
                if entry.get("stage") != "done" or "delete" in (
                        entry.get("operation"), delta.get("operation")):
                    problems.append(violation(
                        "applied_delta_unverifiable",
                        "запись журнала без отпечатка не поддаётся сверке (intent/delete) — "
                        "`abandon` и ручная сверка базы",
                        field="--take", delta_ids=[did]))
                    continue
                diverged = entry.get("operation") != delta.get("operation")
                if not diverged:
                    diverged = not text_present(base, delta)
            if diverged:
                problems.append(violation(
                    "applied_delta_diverged",
                    "запись журнала apply расходится с принятой версией дельты "
                    "(операция/адрес/anchor/текст) — переиграть запись apply не может",
                    field="--take", delta_ids=[did]))
        if problems:
            raise SpineError(
                "partition_conflicts_journal",
                "нарушен precondition partition_covers_journal: частичный apply уже записал "
                "дельты — прими их в применённом виде (при расхождении верни содержание "
                "через restart-from canon) либо `abandon`",
                violations=problems,
            )
    # Ранний сигнал коллизии write-set (D-A п.2): дешёвый, без чтения базы.
    # Авторитетен pre-apply dry-run — здесь набор отклоняется до фиксации
    # партиции, чтобы пользователь переиграл решение, а не упирался в apply.
    # Отказ — только по точному якорю (строгое подмножество авторитета);
    # near-identical идёт предупреждением в payload, не exit 1.
    collisions, near_identical = take_footprint_conflicts(take, ledger, base)
    if collisions:
        raise SpineError(
            "take_anchor_collision",
            "нарушен precondition write_set: принятый набор правит один фрагмент дважды — "
            "вторая правка не найдёт своего места; отклони лишний пункт",
            violations=collisions,
        )

    manifest: Dict[str, Optional[str]] = {}
    for delta_id in take:
        delta = ledger[delta_id]
        for field in ("target_file", "source_file"):
            raw = delta.get(field)
            if not raw:
                continue
            path = resolve_base_relative(raw, base, field)
            rel = str(path.relative_to(base))
            manifest[rel] = sha256_file(path) if path.is_file() else None

    body = {
        "compose_hash": state["compose"]["hash"],
        "ledger_hash": state["ledger"]["hash"],
        "take": take,
        "reject": reject,
        "already": already,
        "amended": state["accept"]["amended"],
        # Наблюдаемые ответы (волна G): источник каждого решения по покрытым
        # пунктам; mode фиксирует explicit/default, но не факт показа вопроса
        # (named boundary спеки).
        "answers": {qid: {"option": e["option"], "mode": e["mode"]}
                    for qid, e in answers.items()},
        # «Ack получен любым каналом»: глобальный --meta ∪ explicit-ответы,
        # взявшие unresolved-пункты. Машинный след согласия не обнуляется.
        "ack_unresolved": bool(meta.get("ack_unresolved")) or bool(ack_via_answers)
                          or state["accept"]["ack_unresolved"],
        "base_manifest": manifest,
    }
    digest = write_json_artifact(run.path(ART_ACCEPT), body)
    state["accept"].update({
        "artifact": ART_ACCEPT, "hash": digest, "take": take, "reject": reject,
        "already": already, "pending_amend": False, "base_manifest": manifest,
        "ack_unresolved": body["ack_unresolved"],
        "answers": body["answers"],
    })
    mark_validated(state, "accept", ART_ACCEPT, digest, decision="accepted")
    set_phase(state, "apply")
    log_event(state, "accept", detail="take={} reject={}".format(len(take), len(reject)))
    save_state(run.run_dir, state)

    payload = status_payload(run)
    payload["take"] = take
    payload["reject"] = reject
    payload["answers"] = body["answers"]
    payload["accept_hash"] = digest
    # Подсказка, не запрет: авторитет по write-set — dry-run на входе apply.
    payload["write_set_warnings"] = near_identical
    lines = [
        "Принято: {} · отклонено: {}".format(len(take), len(reject)),
        "Фаза: apply — дальше `apply`",
    ]
    if near_identical:
        lines.append("Похожие якоря в наборе: {} — проверит dry-run на apply".format(
            len(near_identical)))
    return payload, lines


# --------------------------------------------------------------------------- #
# apply
# --------------------------------------------------------------------------- #

def read_journal(run: Run) -> List[Dict[str, Any]]:
    path = run.path(ART_JOURNAL)
    if not path.is_file():
        return []
    body = load_json_file(path)
    return body.get("entries", [])


def write_journal(run: Run, entries: List[Dict[str, Any]]) -> None:
    write_json_artifact(run.path(ART_JOURNAL), {"run_id": run.state["run_id"], "entries": entries})


def file_hash_or_none(path: Path) -> Optional[str]:
    return sha256_file(path) if path.is_file() else None


def perform_operation(delta: Dict[str, Any], base: Path,
                      publications: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """Файловая операция дельты. Возвращает список затронутых путей (rel).

    Семантика якоря по операциям — выведена из тела этой же функции и держится
    дифференциальным тестом (волна D, D-A п.3). «Разрушает» = якорь после
    операции в файле НЕ переживает.

    | операция | где ищет якорь | читает | разрушает | без якоря |
    |---|---|---|---|---|
    | `add`    | `target_file` | да | нет (вставка ПОСЛЕ якоря, якорь сохраняется) | append в конец |
    | `update` | `target_file` | да | да (замена фрагмента) | append в конец |
    | `merge`  | `target_file` | да | да (замена фрагмента — по контракту §2, не дописывание) | append в конец |
    | `delete` | `target_file` | да | да (вырезание) | отказ `delete_without_anchor` |
    | `move`   | `source_file` | да | да (вырезание из source) | отказ `move_incomplete`; в target — append без якоря |
    | `create` | — | нет | нет | create-only, `create_target_exists` на занятый путь |

    `base` — параметр, а не константа: pre-apply dry-run исполняет ту же функцию
    на копии затронутых файлов в песочнице run'а. Семантика симуляции тождественна
    по построению — та же функция, те же проверки, те же байты.
    """
    operation = delta["operation"]
    text = delta.get("proposed_text") or ""
    target = resolve_base_relative(delta["target_file"], base, "target_file")
    target_rel = str(target.relative_to(base))
    anchor = delta.get("anchor")
    # Гейты S13 и write-path стоят и здесь, у самой файловой операции: apply
    # проверяет набор заранее, но ни одна запись не должна зависеть от того, что
    # её проверили выше. Здесь путь уже канонизирован `resolve_base_relative` —
    # symlink-alias внутрь базы этот заход не переживает (Codex H1).
    ensure_not_strategic(target, base, "target_file дельты {}".format(delta["id"]), (delta["id"],))
    if publications:
        ensure_not_publication_target(target, publications,
                                      "target_file дельты {}".format(delta["id"]),
                                      (delta["id"],))
    if delta.get("source_file"):
        source_resolved = resolve_base_relative(delta["source_file"], base, "source_file")
        ensure_not_strategic(source_resolved, base,
                             "source_file дельты {}".format(delta["id"]), (delta["id"],))
        if publications:
            ensure_not_publication_target(source_resolved, publications,
                                          "source_file дельты {}".format(delta["id"]),
                                          (delta["id"],))

    if operation == "create":
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            raise SpineError(
                "create_target_exists",
                "operation=create: целевой файл уже существует",
                violations=[violation("create_target_exists", "create-only нарушен",
                                      field="target_file", delta_ids=[delta["id"]])],
            )
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        return [target_rel]

    if operation == "move":
        source_raw = delta.get("source_file")
        if not source_raw or not anchor:
            raise SpineError(
                "move_incomplete",
                "operation=move требует source_file и anchor",
                violations=[violation("move_incomplete", "нет source_file/anchor",
                                      field="source_file", delta_ids=[delta["id"]])],
            )
        source = resolve_base_relative(source_raw, base, "source_file")
        needle = text.strip()
        if source == target:
            # Перенос внутри одного файла: обе подоперации умещаются в одну
            # атомарную запись — окна для обрыва нет, порядок не важен.
            if not target.is_file():
                raise SpineError(
                    "target_missing", "файл-источник move не существует",
                    violations=[violation("target_missing", "нет файла", field="source_file",
                                          delta_ids=[delta["id"]])])
            body = target.read_text(encoding="utf-8")
            if anchor not in body:
                if needle and needle in body:
                    return [target_rel]  # уже перенесено — идемпотентный повтор
                raise SpineError(
                    "anchor_not_found", "anchor не найден в файле-источнике",
                    violations=[violation("anchor_not_found", "anchor отсутствует", field="anchor",
                                          delta_ids=[delta["id"]])])
            atomic_write_text(target, join_block(body.replace(anchor, "", 1), text))
            return [target_rel]

        # Порядок подопераций перевёрнут (crash-safety): сперва текст ПОЯВЛЯЕТСЯ
        # в target и только потом ИСЧЕЗАЕТ из source. Обрыв между записями
        # оставляет текст в обоих файлах — это безопасно, resume дорезает
        # source. Обратный порядок терял текст: journal-запись `intent` не
        # отличает «вырезал, не дописал» от «сделал всё».
        target_body = target.read_text(encoding="utf-8") if target.is_file() else ""
        source_body = source.read_text(encoding="utf-8") if source.is_file() else None
        anchor_in_source = source_body is not None and anchor in source_body

        # Шаг 1: append в target. Текст уже там — это resume, шаг пропускается.
        if not (needle and needle in target_body):
            if source_body is None:
                raise SpineError(
                    "target_missing", "файл-источник move не существует",
                    violations=[violation("target_missing", "нет файла", field="source_file",
                                          delta_ids=[delta["id"]])])
            if not anchor_in_source:
                raise SpineError(
                    "anchor_not_found", "anchor не найден в файле-источнике",
                    violations=[violation("anchor_not_found", "anchor отсутствует", field="anchor",
                                          delta_ids=[delta["id"]])])
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(target, join_block(target_body, text))
        maybe_fault("apply:move_between_steps:{}".format(delta["id"]))
        # Шаг 2: вырезать anchor из source. Якоря уже нет — это resume.
        if anchor_in_source:
            atomic_write_text(source, source_body.replace(anchor, "", 1))
        return sorted({str(source.relative_to(base)), target_rel})

    if operation == "delete":
        if not anchor:
            raise SpineError(
                "delete_without_anchor",
                "operation=delete требует anchor — удаляемый фрагмент",
                violations=[violation("delete_without_anchor", "нет anchor", field="anchor",
                                      delta_ids=[delta["id"]])])
        if not target.is_file():
            raise SpineError(
                "target_missing", "целевой файл не существует",
                violations=[violation("target_missing", "нет файла", field="target_file",
                                      delta_ids=[delta["id"]])])
        body = target.read_text(encoding="utf-8")
        if anchor not in body:
            raise SpineError(
                "anchor_not_found", "anchor не найден в целевом файле",
                violations=[violation("anchor_not_found", "anchor отсутствует", field="anchor",
                                      delta_ids=[delta["id"]])])
        atomic_write_text(target, body.replace(anchor, "", 1))
        return [target_rel]

    # add / update / merge — чтение + правка + tmp + os.replace
    if not target.is_file():
        raise SpineError(
            "target_missing",
            "целевой файл не существует: для нового файла нужна operation=create",
            violations=[violation("target_missing", "нет файла", field="target_file",
                                  delta_ids=[delta["id"]])])
    body = target.read_text(encoding="utf-8")
    if anchor:
        if anchor not in body:
            raise SpineError(
                "anchor_not_found", "anchor не найден в целевом файле",
                violations=[violation("anchor_not_found", "anchor отсутствует", field="anchor",
                                      delta_ids=[delta["id"]])])
        if operation == "add":
            # Якорь у add — точка размещения, не заменяемый фрагмент: вставка ПОСЛЕ
            # якоря, сам якорь сохраняется — иначе первая дельта секции съедает
            # заголовок, и соседние дельты с тем же якорем падают (живой смоук 29.07)
            atomic_write_text(
                target, body.replace(anchor, anchor + "\n\n" + text.strip("\n"), 1)
            )
        else:
            atomic_write_text(target, body.replace(anchor, text, 1))
    else:
        atomic_write_text(target, join_block(body, text))
    return [target_rel]


def join_block(body: str, text: str) -> str:
    body = body.rstrip("\n")
    block = text.strip("\n")
    if not body:
        return block + "\n"
    return body + "\n\n" + block + "\n"


def text_present(base: Path, delta: Dict[str, Any]) -> bool:
    target = base / delta["target_file"]
    if not target.is_file():
        return False
    needle = (delta.get("proposed_text") or "").strip()
    if not needle:
        return True
    return needle in target.read_text(encoding="utf-8")


def source_anchor_removed(base: Path, delta: Dict[str, Any]) -> bool:
    """Вторая подоперация move состоялась: якорь исчез из файла-источника."""
    source_raw = delta.get("source_file")
    anchor = delta.get("anchor") or ""
    if not source_raw or not anchor:
        return True
    source = base / source_raw
    if not source.is_file():
        return True
    return anchor not in source.read_text(encoding="utf-8")


def move_completed(base: Path, delta: Dict[str, Any]) -> bool:
    """move завершён = текст есть в target И якорь исчез из source.

    «Изменился хотя бы один файл» для move недостаточно: обрыв между двумя
    подоперациями меняет ровно один файл, и дельта была бы засчитана
    завершённой — с потерей текста либо с дублем.
    """
    return text_present(base, delta) and source_anchor_removed(base, delta)


# --------------------------------------------------------------------------- #
# Write-set: footprint дельты, journal-aware реконструкция, pre-apply dry-run
# (волна D, D-A)
# --------------------------------------------------------------------------- #

FOOTPRINT_DESTROY = "destroy"
FOOTPRINT_READ = "read"
FOOTPRINT_CREATE = "create"

# Классы реконструкции журнала. Общие для apply и dry-run: симуляция обязана
# делить их с реальной записью, иначе на resume она давала бы ложные
# `create_target_exists`/`anchor_not_found` и повторную вставку add.
RESUME_DONE = "done"
RESUME_INTENT_COMPLETED = "intent_completed"
RESUME_INTENT_PENDING = "intent_pending"
RESUME_NEW = "new"

# Песочница dry-run внутри run-каталога (вне базы клиента).
DRY_RUN_DIRNAME = "tmp/dry-run"


def apply_order(take: Any) -> List[str]:
    """ЕДИНСТВЕННЫЙ порядок применения набора: accept-гейт, dry-run и запись.

    Порядок несущий: им определены и класс `anchor_destroyed_by`, и правило
    «читатель после разрушающей». Симуляция авторитетна ровно настолько,
    насколько она проигрывает ТОТ ЖЕ порядок, что и реальная запись, поэтому
    список выводится одной функцией и в `cmd_apply` вычисляется один раз на
    все три точки. Отдельно названная опасность: состав compose отсортирован
    `(bucket, target_file, id)` — конфликтующие дельты одного файла легко
    оказываются в разных бакетах, и compose-порядок в этот список прокрасться
    не должен ни при каком рефакторинге.
    """
    return sorted(take)


def norm_anchor(anchor: Optional[str]) -> str:
    """Нормализация якоря: trim + схлопывание пробелов. Только для предупреждений."""
    return " ".join((anchor or "").split())


def anchor_bearing_file(delta: Dict[str, Any]) -> Optional[str]:
    """Файл, в котором `perform_operation` ищет anchor этой дельты."""
    if delta.get("operation") == "move" and delta.get("source_file"):
        return delta.get("source_file")
    return delta.get("target_file")


def base_rel(raw: Optional[str], root: Path, field: str) -> Optional[str]:
    """Base-relative ключ пути существующим резолвером; неразрешимый путь → None."""
    if not raw:
        return None
    try:
        return str(resolve_base_relative(raw, root, field).relative_to(root.resolve()))
    except (SpineError, ValueError):
        return None


def mutation_footprint(delta: Dict[str, Any], base: Path) -> List[Tuple[Tuple[str, str], str]]:
    """Ключи write-set одной дельты — ЕДИНСТВЕННАЯ реализация (D-A п.2).

    Общий helper для раннего сигнала на `accept` и для сверки классификации
    dry-run. Авторитетен dry-run: accept — ранняя вежливость без чтения базы.

    Ключ — `(base-relative путь, ТОЧНЫЙ якорь)`: та же строка, которую
    сравнивает `perform_operation` (`anchor in body`, `replace(anchor, …, 1)`).
    Нормализация в ключ не входит: два якоря, различающиеся лишь пробельным
    прогоном, — два РАЗНЫХ адреса, и жёсткий отказ по нормализованному
    совпадению был бы ложным там, где реальная запись прошла бы. Нормализованное
    пересечение остаётся, но как предупреждение (`take_footprint_conflicts`) —
    слой accept по спеке «ранняя вежливость», авторитетен dry-run.

    Роль — `destroy` (фрагмент по якорю не переживает), `read` (якорь нужен как
    адрес и переживает) либо `create` (ключ существования пути, якоря нет).
    Разложение по операциям — таблица в докстринге `perform_operation`.
    Пустой/отсутствующий якорь в ключе не участвует: anchorless-append легален
    и множественный.
    """
    operation = delta.get("operation")
    anchor = delta.get("anchor") or ""

    if operation == "create":
        target = base_rel(delta.get("target_file"), base, "target_file")
        return [((target, ""), FOOTPRINT_CREATE)] if target else []
    if operation == "move":
        # Разрушающий ключ — по source; append в target ключа не имеет.
        source = base_rel(delta.get("source_file"), base, "source_file")
        return [((source, anchor), FOOTPRINT_DESTROY)] if source and anchor else []
    if not anchor:
        return []
    target = base_rel(delta.get("target_file"), base, "target_file")
    if not target:
        return []
    role = FOOTPRINT_READ if operation == "add" else FOOTPRINT_DESTROY
    return [((target, anchor), role)]


def take_footprint_conflicts(take: List[str], ledger: Dict[str, Any],
                             base: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Коллизии write-set принятого набора (D-A п.2) → (отказы, предупреждения).

    Порядок — `apply_order`, тот же, что у dry-run и записи. Правило: на один
    ключ — не более одной разрушающей дельты и ни одного читателя ПОСЛЕ
    разрушающей; два `create` одного пути — отказ.

    Два канала намеренно разведены: отказ (exit 1) считается по ТОЧНОМУ якорю —
    строгое подмножество того, что поймает авторитетный dry-run, ложных отказов
    нет; пересечение только после нормализации идёт предупреждением в payload —
    это подсказка «похоже на дубль», а не запрет: в накопительном файле оба
    варианта фрагмента могут существовать как два разных адреса, и запись
    прошла бы. Near-identical якоря всё равно ловятся — на dry-run, до первой
    записи.
    """
    destroyer: Dict[Tuple[str, str], str] = {}
    creator: Dict[str, str] = {}
    norm_seen: Dict[Tuple[str, str], Tuple[str, str]] = {}
    problems: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    for delta_id in apply_order(take):
        delta = ledger.get(delta_id)
        if not delta:
            continue
        for key, role in mutation_footprint(delta, base):
            if role == FOOTPRINT_CREATE:
                first = creator.get(key[0])
                if first:
                    problems.append(violation(
                        "take_create_collision",
                        "два create одного пути в принятом наборе: {}".format(key[0]),
                        field=key[0], delta_ids=[first, delta_id]))
                else:
                    creator[key[0]] = delta_id
                continue
            first = destroyer.get(key)
            if role == FOOTPRINT_DESTROY:
                if first:
                    problems.append(violation(
                        "take_anchor_collision",
                        "две разрушающие правки одного фрагмента: {}".format(key[0]),
                        field=key[0], delta_ids=[first, delta_id]))
                else:
                    destroyer[key] = delta_id
            elif first:
                problems.append(violation(
                    "take_anchor_collision",
                    "правка читает фрагмент {}, который до неё уже заменён".format(key[0]),
                    field=key[0], delta_ids=[first, delta_id]))

            # Предупреждение: якоря совпали ТОЛЬКО после нормализации, то есть
            # это два разных адреса, похожих на дубль. Точное совпадение сюда не
            # попадает — оно уже разобрано отказами выше.
            norm_key = (key[0], norm_anchor(key[1]))
            if not norm_key[1]:
                continue
            twin = norm_seen.setdefault(norm_key, (delta_id, key[1]))
            if twin[0] != delta_id and twin[1] != key[1]:
                warnings.append(violation(
                    "take_anchor_near_identical",
                    "якоря совпадают после нормализации пробелов — возможно, дубль: {}".format(
                        key[0]),
                    field=key[0], delta_ids=[twin[0], delta_id]))
    return problems, warnings


def intent_effect_landed(delta: Dict[str, Any], entry: Dict[str, Any], base: Path) -> bool:
    """Записан intent, но файловая операция де-факто состоялась.

    Обрыв между file-op и журналом: intent отличает своё изменение от чужого —
    файл сдвинулся против `hash_before` ⇒ операция прошла. `move` — исключение
    (две подоперации: «изменился хотя бы один файл» засчитал бы обрыв между
    ними как завершённую дельту); `delete` — тоже (текста не оставляет,
    `text_present` для пустого `proposed_text` вакуумно True).
    """
    if delta["operation"] == "move":
        return move_completed(base, delta)
    if delta["operation"] == "delete":
        target_file = base / delta["target_file"]
        return (not target_file.is_file()
                or (delta.get("anchor") or "") not in target_file.read_text(encoding="utf-8"))
    moved = any(file_hash_or_none(base / item["path"]) != item["hash_before"]
                for item in entry["files"])
    return moved or text_present(base, delta)


def resume_class(delta: Dict[str, Any], entry: Optional[Dict[str, Any]], base: Path) -> str:
    """Класс дельты против журнала: done / intent-completed / intent-pending / new.

    Один импортируемый шаг для apply и dry-run — не парафраз: разъехавшаяся
    классификация означала бы, что симуляция проверяет не тот набор, который
    исполнит реальная запись.
    """
    if not entry:
        return RESUME_NEW
    if entry.get("stage") == RESUME_DONE:
        return RESUME_DONE
    if entry.get("stage") == "intent":
        return RESUME_INTENT_COMPLETED if intent_effect_landed(delta, entry, base) else RESUME_INTENT_PENDING
    return RESUME_NEW


def dry_run_failure(delta: Dict[str, Any], file_rel: Optional[str], klass: str,
                    message: str, **extra: Any) -> SpineError:
    """Отказ dry-run: exit 1, ноль записей в базу, `apply_status` не трогается."""
    payload: Dict[str, Any] = {
        "delta_id": delta.get("id"),
        "file": file_rel,
        "step": delta.get("operation"),
        "class": klass,
        "recovery": RECOVERY_TEXTS["apply_dry_run_failed"],
        "error_class": "blocker",
    }
    payload.update({key: value for key, value in extra.items() if value is not None})
    return SpineError(
        "apply_dry_run_failed",
        "принятый набор не применится без обрыва ({}): {}".format(delta.get("id"), message),
        violations=[violation(klass, message, field=file_rel,
                              delta_ids=[delta.get("id")] if delta.get("id") else [])],
        payload=payload,
    )


def classify_anchor_loss(history: Dict[str, List[Tuple[Optional[str], Optional[str]]]],
                         rel: Optional[str], anchor: str) -> Tuple[str, Optional[str]]:
    """`anchor_not_found` в песочнице: якоря не было изначально или его съели.

    История тел файла ведётся по шагам симуляции, поэтому виновник называется
    точно, а не «последним, кто трогал файл».
    """
    entries = history.get(rel or "") or []
    if not entries or not entries[0][1] or anchor not in entries[0][1]:
        return "anchor_not_found_initial", None
    for delta_id, body in entries[1:]:
        if not body or anchor not in body:
            return "anchor_destroyed_by", delta_id
    return "anchor_not_found_initial", None


def dry_run_write_set(run: Run, base: Path, ledger: Dict[str, Any],
                      accepted: List[str], entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pre-apply dry-run: набор исполняется РЕАЛЬНЫМ `perform_operation` на копии.

    Затронутые набором файлы копируются в tmp-каталог run'а с сохранением
    относительной структуры, `perform_operation(delta, sandbox)` исполняется
    над копией as-is, результат выбрасывается. Порядок — тот же, что в apply;
    классификация журнала — общей функцией `resume_class`.

    Граница воспроизводимости песочницы названа честно: копия переносит
    содержимое regular-файлов, симлинки и права не воспроизводит, поэтому
    отказы реальной записи от подмены симлинком или прав МЕЖДУ dry-run и apply
    остаются возможными — их держат существующие пер-записьные гейты
    (`ensure_not_strategic`, O_NOFOLLOW-примитивы), dry-run их не подменяет.
    Дрейф самих файлов базы ловит base_manifest-гейт, стоящий до dry-run.
    """
    global _SIMULATION_DEPTH
    root = run.path(DRY_RUN_DIRNAME)
    shutil.rmtree(root, ignore_errors=True)
    sandbox = root / "base"
    sandbox.mkdir(parents=True)
    _SIMULATION_DEPTH += 1
    try:
        return simulate_write_set(base, sandbox, ledger, accepted, entries)
    finally:
        _SIMULATION_DEPTH -= 1
        shutil.rmtree(root, ignore_errors=True)


def read_body(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def simulate_write_set(base: Path, sandbox: Path, ledger: Dict[str, Any],
                       accepted: List[str], entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    base_resolved = base.resolve()
    by_delta = {item["delta_id"]: item for item in entries if item.get("delta_id")}
    history: Dict[str, List[Tuple[Optional[str], Optional[str]]]] = {}

    # Копия затронутых файлов — regular-содержимое, каталожная структура.
    for delta_id in accepted:
        delta = ledger[delta_id]
        for field in ("target_file", "source_file"):
            rel = base_rel(delta.get(field), base_resolved, field)
            if rel is None or rel in history:
                continue
            src, dst = base_resolved / rel, sandbox / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_file() and not src.is_symlink():
                shutil.copyfile(str(src), str(dst))
            history[rel] = [(None, read_body(dst))]

    simulated: List[str] = []
    skipped: Dict[str, str] = {}
    steps: List[Dict[str, Any]] = []
    for delta_id in accepted:
        delta = ledger.get(delta_id)
        if delta is None:
            # Партиция валидирована на accept; несогласованный ledger — именованный
            # отказ, а не KeyError с трейсбеком (симметрия с footprint-гейтом).
            raise SpineError(
                "apply_dry_run_failed",
                "принятый набор ссылается на дельту вне ledger: {}".format(delta_id),
                payload={"delta_id": delta_id, "class": "delta_not_in_ledger",
                         "recovery": RECOVERY_TEXTS["apply_dry_run_failed"],
                         "error_class": "blocker"})
        klass = resume_class(delta, by_delta.get(delta_id), base_resolved)
        if klass in (RESUME_DONE, RESUME_INTENT_COMPLETED):
            # Эффект уже в фактических файлах, с которых стартовал overlay:
            # переисполнение дало бы ложный отказ либо повторную вставку.
            skipped[delta_id] = klass
            continue
        touched = simulate_delta(delta, sandbox, history)
        simulated.append(delta_id)
        # Пошаговый след — материал для сверки последовательности симуляции с
        # последовательностью реальной записи (журналом).
        steps.append({"delta_id": delta_id, "operation": delta.get("operation"),
                      "touched": sorted(touched)})
    return {"simulated": simulated, "skipped": skipped, "steps": steps}


def simulate_delta(delta: Dict[str, Any], sandbox: Path,
                   history: Dict[str, List[Tuple[Optional[str], Optional[str]]]]) -> List[str]:
    operation = delta.get("operation")
    anchor = delta.get("anchor") or ""
    rel = None
    if anchor and operation != "create":
        rel = base_rel(anchor_bearing_file(delta), sandbox, "anchor_file")
        body = read_body(sandbox / rel) if rel else None
        if body is not None:
            # Отказ ТОЛЬКО по точному счёту — той же строке, что сравнивает
            # `perform_operation`. Нормализованный счёт идёт в payload
            # информационно: отказ по нему дал бы односторонние ложные отказы
            # без аналога в реальной записи.
            exact = body.count(anchor)
            if exact > 1:
                normalized = norm_anchor(anchor)
                raise dry_run_failure(
                    delta, rel, "anchor_ambiguous",
                    "якорь встречается в файле {} раз — правка первого вхождения запрещена".format(exact),
                    anchor_count=exact,
                    anchor_count_normalized=(norm_anchor(body).count(normalized)
                                             if normalized else None))

    try:
        touched = perform_operation(delta, sandbox)
    except SpineError as exc:
        klass, culprit = exc.code, None
        if exc.code == "anchor_not_found":
            klass, culprit = classify_anchor_loss(history, rel, anchor)
        raise dry_run_failure(delta, rel or delta.get("target_file"), klass, exc.message,
                              destroyed_by=culprit)

    for item in touched:
        history.setdefault(item, [(None, None)])
        history[item].append((delta.get("id"), read_body(sandbox / item)))
    return list(touched)


def confirmed_summary_text(run: Run) -> str:
    """Подтверждённая выжимка: текст фазы l1 + правки пользователя verbatim.

    Пользователь утверждает выжимку на `confirm`; поданные там corrections —
    обязательный вход узла deltas и часть того, что он подтвердил. Публикации
    (`_summary.md` и протокол) обязаны нести обе части, иначе в базу уезжает
    текст, который пользователь явно правил.
    """
    state = run.state
    text = run.path(state["phases"]["l1"]["artifact"]).read_text(encoding="utf-8")
    entry = (state["inputs"].get("deltas") or {}).get("corrections")
    if not entry:
        return text
    path = run.path(entry["path"])
    if not path.is_file():
        raise SpineError(
            "corrections_missing",
            "вход corrections фазы deltas исчез из run-каталога: {}".format(path),
        )
    corrections = path.read_text(encoding="utf-8")
    if not corrections.strip():
        return text
    return text.rstrip("\n") + "\n\n## Правки пользователя\n\n" + corrections


def publication_tmp_path(parent: Path, kind: str, pid: Optional[int] = None) -> Path:
    """Имя tmp-файла публикации — единственный источник схемы.

    `publish_file` создаёт его, шаг 8 §4г подметает по префиксу `TMP_PUB_PREFIX`:
    расхождение сделало бы норматив подметания декоративным (круг 2, Sonnet M2).
    """
    return parent / "{}{}-{}".format(TMP_PUB_PREFIX, os.getpid() if pid is None else pid, kind)


def read_publication_bytes(target: Path) -> Optional[bytes]:
    """Содержимое занятого пути публикации — без следования symlink'ам.

    `O_NOFOLLOW` здесь принципиален: подменённый symlink'ом путь не должен даже
    читаться наружу базы. Нечитаемый путь (symlink, каталог, нет прав) —
    `None`, для вызывающего это коллизия, а не совпадение.
    """
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(str(target), os.O_RDONLY | nofollow)
    except OSError:
        return None
    try:
        with os.fdopen(fd, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def publish_file(run: Run, path: Path, text: str, kind: str) -> Dict[str, Any]:
    """Публикация create-only: существующий файл не перезаписывается.

    Confinement проверяется здесь заново, а не только на locate: и сам файл, и
    каждый каталог на пути (включая создаваемый по create-предложению).
    """
    base = Path(run.state["base_path"])
    label = "публикация ({})".format(kind)
    target = ensure_inside_base(path, base, label)
    ensure_not_strategic(target, base, label)
    mkdir_inside_base(target.parent, base, "каталог публикации ({})".format(kind))
    # Атомарный create-only (Codex v3): контент пишется во временный файл и
    # встаёт под целевое имя одним os.link — обрыв не оставляет частичного
    # файла под целевым именем, а существующий файл не перезаписывается
    # (link на занятое имя = FileExistsError; symlink на месте цели — тоже занят).
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    tmp = publication_tmp_path(target.parent, kind)
    tmp.unlink(missing_ok=True)  # осиротевший tmp прошлого обрыва
    fd = os.open(str(tmp), os.O_CREAT | os.O_EXCL | os.O_WRONLY | nofollow, 0o644)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(str(tmp), str(target))
        except FileExistsError:
            # Целевое имя занято. Create-only не перезаписывает — но и промолчать
            # нельзя: «опубликовано» обязано означать «в файле принятая выжимка».
            # Тот же текст (повтор apply после обрыва) — идемпотентный успех;
            # другой текст — блокер, решает пользователь (Codex, повторная проверка).
            existing = read_publication_bytes(target)
            payload = text.encode("utf-8")
            if existing == payload:
                return {"path": str(target), "kind": kind, "created": False,
                        "hash": sha256_bytes(existing)}
            raise SpineError(
                "publication_conflict",
                "нарушен инвариант publication_content: файл публикации ({}) уже существует "
                "с другим содержимым — принятая выжимка не опубликована".format(kind),
                violations=[violation(
                    "publication_conflict",
                    "существующий файл не совпадает с публикуемым текстом"
                    if existing is not None else
                    "существующий путь публикации нечитаем (symlink/каталог)",
                    field=str(target))],
                payload={
                    "path": str(target),
                    "kind": kind,
                    "recovery": "файл публикации уже существует с другим содержимым — "
                                "реши коллизию: переименуй/удали файл или "
                                "`restart-from --phase canon`",
                    "error_class": "blocker",
                },
            )
    finally:
        tmp.unlink(missing_ok=True)
    return {"path": str(target), "kind": kind, "created": True, "hash": sha256_file(target)}


# --------------------------------------------------------------------------- #
# Публикации: занятый путь — решение пользователя (B№4)
# Спека: dev/meeting-analysis/b4-publication-conflict-spec.md
# --------------------------------------------------------------------------- #

PUBLICATION_KINDS = ("summary", "protocol")
TMP_PUB_PREFIX = ".tmp-pub-"
TMP_ARCHIVE_PREFIX = ".tmp-arch-"
# Страховка §4г шаг 4: dest, занимаемый чужим раз за разом, не должен крутить
# бесконечный цикл aborted-записей. Модель угроз v1 такого противника не знает.
ARCHIVE_REDEST_LIMIT = 3

# §3: `choices` — единственный источник решаемости конфликта.
CONFLICT_CHOICES: Dict[str, List[str]] = {
    "content_differs": ["replace", "keep"],
    "kept_target_vanished": ["replace"],
    "superseded_externally": ["keep"],
    "unreadable": [],
}

# §6: тексты паузы публикаций — часть таблицы экранов (единственный источник).
PUBLICATION_SCREENS: Dict[Tuple[str, str], str] = {
    ("content_differs", "summary"):
        "Файл с итогами этой встречи уже есть в базе — похоже, остался от прошлой "
        "обработки. Заменить его свежей версией (старый перенесу в архив рядом) "
        "или оставить прежний?",
    ("content_differs", "protocol"):
        "Протокол этой встречи уже есть в базе. Заменить его новой версией "
        "(старый перенесу в архив рядом) или оставить прежний?",
    ("kept_target_vanished", "summary"):
        "Файл, который вы решили оставить, исчез из базы. Записать свежую версию — "
        "или остановимся, чтобы вы разобрались с базой?",
    ("kept_target_vanished", "protocol"):
        "Файл, который вы решили оставить, исчез из базы. Записать свежую версию — "
        "или остановимся, чтобы вы разобрались с базой?",
    ("superseded_externally", "summary"):
        "Пока я ждала, файл итогов уже обновили до свежей версии — прежнего текста "
        "в нём нет. Оставить как есть?",
    ("superseded_externally", "protocol"):
        "Пока я ждала, протокол встречи уже обновили до свежей версии — прежнего "
        "текста в нём нет. Оставить как есть?",
}

# Пауза по отказу прошлого цикла (`publication_refusals` пережил restart-from):
# нейтральный текст — пользователь этого цикла про «оставить» ничего не говорил.
PUBLICATION_DECLINED_SCREEN = (
    "Ранее вы решили не записывать итоги этой встречи — файла на месте нет. "
    "Записать свежую версию или остановить разбор?")

PUBLICATION_MIXED_WARNING = (
    "Один из файлов прочитать не могу — после ваших решений останется препятствие, "
    "его нужно починить в базе руками")

PUBLICATION_MANY = "Решение нужно по каждому файлу."

EXECUTION_BLOCKERS = ("publication_archive_failed", "publication_unlink_failed",
                      "publication_write_failed")


def observe_target(path: Path) -> Dict[str, Any]:
    """Единый read-примитив цели публикации (§2 п.6).

    `lstat` → не regular (symlink/каталог/FIFO) → класс `unreadable`: FIFO и
    каталог не открываются, blocking open исключён. ENOENT → класс `absent`
    (ENOENT ≠ нечитаемость). Иначе `O_NOFOLLOW`-open, чтение ОДНИМ буфером и
    sha256 этого буфера — архивная копия кладётся из него же, без второго чтения.
    EACCES и прочие OSError чтения → `unreadable`.
    """
    try:
        info = os.lstat(str(path))
    except FileNotFoundError:
        return {"class": "absent", "hash": None, "bytes": None}
    except OSError:
        return {"class": "unreadable", "hash": None, "bytes": None}
    if not stat.S_ISREG(info.st_mode):
        return {"class": "unreadable", "hash": None, "bytes": None}
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(str(path), os.O_RDONLY | nofollow)
    except FileNotFoundError:
        return {"class": "absent", "hash": None, "bytes": None}
    except OSError:
        return {"class": "unreadable", "hash": None, "bytes": None}
    try:
        with os.fdopen(fd, "rb") as handle:
            data = handle.read()
    except OSError:
        return {"class": "unreadable", "hash": None, "bytes": None}
    return {"class": "regular", "hash": sha256_bytes(data), "bytes": data}


def publication_paths(state: Dict[str, Any]) -> Dict[str, Path]:
    """kind → путь публикации этого прогона (протокол — только при required)."""
    protocol_dir = Path(state["context"]["protocol_dir"])
    date, topic = state["immutable"]["date"], state["immutable"]["topic"]
    paths = {"summary": protocol_dir / "{}_{}_summary.md".format(date, topic)}
    if state["context"]["protocol_required"]:
        paths["protocol"] = protocol_dir / "{}_{}.md".format(date, topic)
    return paths


def archive_publication_dest(protocol_dir: Path, name: str,
                             reserved: Optional[set] = None) -> Path:
    """dest архивной копии заменяемой публикации; коллизия имени → `-2`, `-3`…

    Занятыми считаются и имена, **зарезервированные журналом** (в т.ч. записями
    `aborted` до создания копии): иначе новая замена с другим hash получила бы
    тот же dest, и §10 п.8 («новая запись с dest `-2`») не выполнялся бы
    (круг 2, Codex L7).
    """
    archive = protocol_dir / ARCHIVE_DIRNAME
    # Обе стороны нормализуются одинаково: в журнале `to` лежит резолвнутым
    # (Opus L8), кандидат строится из `protocol_dir` — при неканоническом
    # каталоге множества иначе тихо разъехались бы (круг 3, Opus L-4).
    taken = {os.path.realpath(str(item)) for item in (reserved or ())}
    stem, suffix = Path(name).stem, Path(name).suffix
    candidate = archive / name
    number = 2
    while candidate.exists() or candidate.is_symlink() \
            or os.path.realpath(str(candidate)) in taken:
        candidate = archive / "{}-{}{}".format(stem, number, suffix)
        number += 1
    return candidate


# --- чистый диспетчер §4в (машинный перебор — suites/spine/tests/test_b4_matrix) --- #

def publication_step(*, stage, record_kind, payload_hash_is_payload, to_class,
                     choice, existing_hash, obs, refusal) -> Tuple[str, Optional[str]]:
    """Ячейка §4в для одного шага диспетчеризации + переход.

    **Единственная точка классификации write-path**: её зовёт и рабочий
    `_process_publication_kind`, и машинный перебор (`publication_trace`).
    Отдельной «модели для теста» не существует — иначе неимплементированная
    ветка проходит перебор незамеченной (круг 2 связки, Opus H1/H2).

    Символьный кортеж: `obs`/`existing_hash` — `P` (текущий payload), `PH`
    (`payload_hash` записи), `H` (`hash` записи), `X`/`X2` (третьи байты), плюс
    `absent`/`unreadable` у наблюдения. Переход: `promote` (запись повышается до
    `archived`), `terminalize` (запись терминализована, дальше ветки 2–3).
    """
    # Ветка 0: резолюция исполнена и её scope совпадает с прогоном — kind
    # пропускается целиком (keep: публикации нет by design; replace: запись
    # `done`, публикация уже в `published`). Приоритет выше журнала и наблюдения.
    if choice == "executed_in_scope":
        return "0", None

    live_replace = choice == "replace"
    live_keep = choice == "keep"
    obs_is_record_hash = record_kind == "normal" and obs == "H"

    if stage == "intent":
        # payload_hash сам по себе выполнение replace не доказывает — только
        # вместе с подтверждённой архивной копией, поэтому сперва наблюдаем `to`.
        if to_class == "hash":
            return "1а-copy-confirmed", "promote"
        if to_class == "foreign":
            return "1а-copy-foreign", "terminalize"
        if obs_is_record_hash and live_replace and existing_hash == "H":
            return "1а-continue", None
        return "1а-abort", "terminalize"

    if stage in ("archived", "unlinked"):
        # Guard продолжения: обязательство записи устарело после restart-from.
        if not payload_hash_is_payload and obs in ("absent", "P"):
            return "1б-guard-abort", "terminalize"
        if obs == "absent":
            if live_keep:
                return "1б-1-vanished-keep", None
            if live_replace:
                return "1б-2-executed", None
            return ("1б-2-refusal-pause" if refusal else "1б-2-publish"), None
        if obs == "P":
            if live_keep:
                return (("1б-4-keep-published" if existing_hash == "P"
                         else "1б-5-superseded"), None)
            return "1б-3-replace-done", None
        if obs == "PH":
            return "1б-6-close-foreign", "terminalize"
        if obs == "unreadable":
            return "1б-9-unreadable", None
        if obs_is_record_hash and live_replace and existing_hash == "H" and stage == "archived":
            return "1б-7-continue", None
        return "1б-8-abort", "terminalize"

    if live_replace or live_keep:
        if obs == "unreadable":
            return "2-5-unreadable", None
        if obs == "absent":
            if existing_hash is None:
                return (("2-1a-vanished-replace" if live_replace
                         else "2-1b-vanished-keep"), None)
            return ("2-2a-vanished-note" if live_replace else "2-2b-keep-vanished"), None
        if existing_hash == obs:
            return "2-1c-execute", None
        return ("2-3-superseded" if obs == "P" else "2-4-content-differs"), None

    if obs == "absent":
        return ("3-1a-refusal-pause" if refusal else "3-1b-publish"), None
    if obs == "unreadable":
        return "3-4-unreadable", None
    return ("3-2-idempotent" if obs == "P" else "3-3-content-differs"), None


def publication_trace(**kwargs: Any) -> List[str]:
    """Трасса кортежа: тонкая обёртка над `publication_step` — тем же вызовом,
    что делает `_process_publication_kind`. Своей логики классификации не несёт.
    """
    cursor = dict(kwargs)
    trace: List[str] = []
    for _ in range(4):
        cell, transition = publication_step(**cursor)
        trace.append(cell)
        if transition == "promote":
            cursor["stage"] = "archived"
            continue
        if transition == "terminalize":
            cursor.update(stage=None, record_kind="none",
                          payload_hash_is_payload=None, to_class=None)
            continue
        return trace
    return trace


def publication_symbols(obs: Dict[str, Any], existing_hash: Optional[str],
                        payload_hash: str, record: Optional[Dict[str, Any]]
                        ) -> Tuple[str, Optional[str]]:
    """Символьный кортеж §4в: (наблюдение, `existing_hash` воли).

    Именованные символы — `P` (текущий payload), `PH` (`payload_hash` записи),
    `H` (`hash` записи). Прочие байты получают РАЗНЫЕ метки (`X`, `X2`…):
    диспетчер сравнивает волю с наблюдением по символу, и склейка двух разных
    чужих hash'ей в один `X` превратила бы «файл подменили третьими байтами»
    в «воля совпала с наблюдением» — replace унёс бы в архив не те байты.
    """
    known: Dict[str, str] = {}
    known.setdefault(payload_hash, "P")
    if record:
        if record.get("payload_hash"):
            known.setdefault(record["payload_hash"], "PH")
        if record.get("hash"):
            known.setdefault(record["hash"], "H")
    counter = [0]

    def label(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if value not in known:
            counter[0] += 1
            known[value] = "X" if counter[0] == 1 else "X{}".format(counter[0])
        return known[value]

    if obs["class"] == "absent":
        obs_symbol = "absent"
    elif obs["class"] == "unreadable":
        obs_symbol = "unreadable"
    else:
        obs_symbol = label(obs["hash"])
    return obs_symbol, label(existing_hash)


# --- журнал `side_effects.replaced` (§4б) --------------------------------- #

def replaced_records(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return state["side_effects"].setdefault("replaced", [])


def open_replaced_record(state: Dict[str, Any], kind: str) -> Optional[Dict[str, Any]]:
    """Нетерминальная запись kind. Инвариант §4б: их не более одной."""
    for record in replaced_records(state):
        if record["publication"] == kind and record["stage"] not in ("done", "aborted"):
            return record
    return None


def abort_replaced_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Немедленная терминализация: продолжать нечем (§4б)."""
    record["aborted_from_stage"] = record["stage"]
    record["stage"] = "aborted"
    record["closed_at"] = now_iso()
    return record


def close_replaced_record(record: Dict[str, Any]) -> Dict[str, Any]:
    record["stage"] = "done"
    record["closed_at"] = now_iso()
    return record


def confined_or_none(path: Path, base: Path, label: str) -> Optional[Path]:
    """Покомпонентный confinement перед наблюдением/удалением. None — путь негоден.

    `O_NOFOLLOW` закрывает только последний компонент: symlink на родительском
    `zz_archive/` пропустил бы наружную копию как «свою» (Codex H2). Проверяется
    и стратегический контур — деструктивная операция туда запрещена нормой S13.
    """
    try:
        confined = ensure_inside_base(path, base, label)
        ensure_not_strategic(confined, base, label)
    except SpineError:
        return None
    return confined


def observe_archive_copy(record: Dict[str, Any], base: Path) -> str:
    """Класс наблюдения архивной копии записи: hash | absent | foreign.

    Негодный по confinement путь — `foreign`, не `hash`: чужая копия вне базы не
    должна засчитываться как собственная и открывать unlink старого файла.
    """
    if not record.get("to"):
        return "absent"
    copy = confined_or_none(Path(record["to"]), base, "архивная копия")
    if copy is None:
        return "foreign"
    obs = observe_target(copy)
    if obs["class"] == "absent":
        return "absent"
    if obs["class"] == "regular" and obs["hash"] == record.get("hash"):
        return "hash"
    return "foreign"


def new_replaced_record(state: Dict[str, Any], kind: str, source: Path,
                        dest: Optional[Path], source_hash: Optional[str],
                        payload_hash: str, stage: str) -> Dict[str, Any]:
    record = {
        "publication": kind,
        "from": str(source),
        "to": str(dest) if dest is not None else None,
        "hash": source_hash,
        "payload_hash": payload_hash,
        "stage": stage,
        "at": now_iso(),
    }
    replaced_records(state).append(record)
    return record


# --- конфликты, резолюции, отказ ------------------------------------------ #

def publication_conflict_item(kind: str, path: Path, existing_hash: Optional[str],
                              reason: str, origin: Optional[str] = None) -> Dict[str, Any]:
    item = {
        "kind": kind,
        "path": str(path),
        "existing_hash": existing_hash,
        "reason": reason,
        "choices": list(CONFLICT_CHOICES[reason]),
    }
    if origin:
        # Служебная пометка для выбора текста паузы (§6): «отказ прошлого цикла»
        # звучит нейтрально, а не «файл, который вы решили оставить».
        item["origin"] = origin
    return item


def upsert_publication_conflict(state: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
    """Список конфликтов событийный: заход обновляет элемент kind, не пересоздаёт."""
    conflicts = state.setdefault("publication_conflicts", [])
    for idx, existing in enumerate(conflicts):
        if existing["kind"] == item["kind"]:
            conflicts[idx] = item
            return item
    conflicts.append(item)
    return item


def drop_publication_conflict(state: Dict[str, Any], kind: str) -> None:
    state["publication_conflicts"] = [
        item for item in state.setdefault("publication_conflicts", [])
        if item["kind"] != kind]


def publication_resolution(state: Dict[str, Any], kind: str) -> Optional[Dict[str, Any]]:
    return state.setdefault("publication_resolutions", {}).get(kind)


def drop_publication_resolution(state: Dict[str, Any], kind: str) -> Optional[str]:
    """Снятие неисполненной воли. Снятый `keep` ставит отказ (§4б)."""
    record = state.setdefault("publication_resolutions", {}).get(kind)
    if not record or record.get("executed"):
        return None
    state["publication_resolutions"].pop(kind, None)
    if record["choice"] == "keep":
        state.setdefault("publication_refusals", {})[kind] = {
            "declined_at": now_iso(),
            "path": record.get("path"),
        }
    return record["choice"]


def resolution_axis(state: Dict[str, Any], kind: str, path: Path,
                    payload_hash: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Ось решения §3: none | replace | keep | executed_in_scope | historical."""
    record = publication_resolution(state, kind)
    if not record:
        return "none", None
    if record.get("executed"):
        scope = record.get("scope") or {}
        if scope.get("path") == str(path) and scope.get("payload_hash") == payload_hash:
            return "executed_in_scope", record
        return "executed_historical", record
    return record["choice"], record


def upsert_published(state: Dict[str, Any], item: Dict[str, Any]) -> None:
    """Публикация пути замещает прежнюю запись этого пути (§4г шаг 8).

    Append-if-absent недостаточен: после restart-from с новым payload прежняя
    запись держала бы устаревший hash и постчек (г) давал бы невосстановимый
    `publication_changed`.
    """
    published = state["side_effects"]["published"]
    for idx, existing in enumerate(published):
        if existing["path"] == item["path"]:
            published[idx] = item
            return
    published.append(item)


def drop_published_path(state: Dict[str, Any], path: Path) -> None:
    state["side_effects"]["published"] = [
        item for item in state["side_effects"]["published"] if item["path"] != str(path)]


def sweep_tmp(directory: Path, prefix: str) -> None:
    """Осиротевший tmp прошлого процесса — по префиксу, не по pid (§4г шаг 8).

    Tmp чужого pid лежит внутри снимка и дал бы `foreign_file_created`;
    base-level lock (§0.4 контрактов) делает префиксную очистку безопасной.
    """
    if not directory.is_dir():
        return
    for stray in sorted(directory.glob(prefix + "*")):
        try:
            if stray.is_file() and not stray.is_symlink():
                stray.unlink()
        except OSError:
            continue


def _observation_conflict(state: Dict[str, Any], kind: str, path: Path,
                          obs: Dict[str, Any], payload_hash: str) -> Dict[str, Any]:
    """Конфликт по свежему наблюдению (ветки 2/3, обёртка шага 8)."""
    if obs["class"] == "absent":
        return publication_conflict_item(kind, path, None, "kept_target_vanished")
    if obs["class"] == "unreadable":
        return publication_conflict_item(kind, path, None, "unreadable")
    if obs["hash"] == payload_hash:
        return publication_conflict_item(kind, path, obs["hash"], "superseded_externally")
    return publication_conflict_item(kind, path, obs["hash"], "content_differs")


def commit_replace_done(run: Run, state: Dict[str, Any], kind: str, path: Path,
                        record: Optional[Dict[str, Any]], published: Dict[str, Any],
                        payload_hash: str, note: Optional[str] = None) -> None:
    """Commit `replace-done`: журнал done + published + executed/scope + сброс отказа."""
    if record is not None:
        close_replaced_record(record)
    upsert_published(state, published)
    resolution = publication_resolution(state, kind)
    if resolution and resolution["choice"] == "replace" and not resolution.get("executed"):
        resolution["executed"] = True
        resolution["scope"] = {"path": str(path), "payload_hash": payload_hash}
        if note:
            resolution["note"] = note
    drop_publication_conflict(state, kind)
    state.setdefault("publication_refusals", {}).pop(kind, None)
    save_state(run.run_dir, state)


def commit_keep_published(run: Run, state: Dict[str, Any], kind: str, path: Path,
                          record: Optional[Dict[str, Any]], obs: Dict[str, Any],
                          payload_hash: str) -> None:
    """Commit `keep-published` (§4г шаг 9): файл и есть собственная публикация.

    Именованное исключение из снятия `published` общей keep-веткой: запись
    отражает факт публикации, (г) и (д) сверяют один hash.
    """
    if record is not None:
        close_replaced_record(record)
    upsert_published(state, {"path": str(path), "kind": kind, "created": False,
                             "hash": obs["hash"]})
    resolution = publication_resolution(state, kind)
    if resolution and not resolution.get("executed"):
        resolution["executed"] = True
        resolution["scope"] = {"path": str(path), "payload_hash": payload_hash}
    state["side_effects"].setdefault("kept", []).append(
        {"kind": kind, "path": str(path), "existing_hash": obs["hash"], "at": now_iso()})
    drop_publication_conflict(state, kind)
    state.setdefault("publication_refusals", {}).pop(kind, None)
    save_state(run.run_dir, state)


def commit_superseded(run: Run, state: Dict[str, Any], kind: str, path: Path,
                      record: Optional[Dict[str, Any]], obs: Dict[str, Any]) -> Dict[str, Any]:
    """Commit `superseded` (1б-5): журнал done + published + сброс keep + отказ."""
    if record is not None:
        close_replaced_record(record)
    upsert_published(state, {"path": str(path), "kind": kind, "created": False,
                             "hash": obs["hash"]})
    drop_publication_resolution(state, kind)
    conflict = upsert_publication_conflict(
        state, publication_conflict_item(kind, path, obs["hash"], "superseded_externally"))
    save_state(run.run_dir, state)
    return conflict


def execute_keep(run: Run, state: Dict[str, Any], kind: str, path: Path,
                 resolution: Dict[str, Any], payload_hash: str) -> Optional[Dict[str, Any]]:
    """Исполнение `keep` — режим [исполнение] (§4г): re-verify перед фиксацией."""
    obs = observe_target(path)
    if obs["class"] != "regular" or obs["hash"] != resolution.get("existing_hash"):
        drop_publication_resolution(state, kind)
        conflict = upsert_publication_conflict(
            state, _observation_conflict(state, kind, path, obs, payload_hash))
        save_state(run.run_dir, state)
        return conflict
    resolution["executed"] = True
    resolution["scope"] = {"path": str(path), "payload_hash": payload_hash}
    # Append-only носитель факта: переживает restart-from и перезапись слота
    # новой волей — allowed-membership постчека (д) держится на нём.
    state["side_effects"].setdefault("kept", []).append(
        {"kind": kind, "path": str(path), "existing_hash": obs["hash"], "at": now_iso()})
    # Stale published-запись пути (пережившая restart-from) снимается: иначе (г)
    # сверял бы прежнюю публикацию с keep-файлом и давал ложный publication_changed.
    drop_published_path(state, path)
    drop_publication_conflict(state, kind)
    state.setdefault("publication_refusals", {}).pop(kind, None)
    save_state(run.run_dir, state)
    return None


def _archive_copy(run: Run, state: Dict[str, Any], kind: str,
                  record: Dict[str, Any], data: bytes, base: Path) -> bool:
    """Шаг 4 §4г: копия из того же буфера, create-only. False — dest занят чужим."""
    dest = Path(record["to"])
    label = "архивная копия ({})".format(kind)
    ensure_not_strategic(dest, base, label)
    mkdir_inside_base(dest.parent, base, "каталог архива ({})".format(kind))
    dest = ensure_inside_base(dest, base, label)
    sweep_tmp(dest.parent, TMP_ARCHIVE_PREFIX)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    tmp = dest.parent / "{}{}-{}".format(TMP_ARCHIVE_PREFIX, os.getpid(), kind)
    try:
        fd = os.open(str(tmp), os.O_CREAT | os.O_EXCL | os.O_WRONLY | nofollow, 0o644)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(str(tmp), str(dest))
            except FileExistsError:
                observed = observe_target(dest)
                if observed["class"] == "regular" and observed["hash"] == record.get("hash"):
                    return True  # копия этой замены легла до крэша — зачёт
                return False     # занято чужим/негодным → новая запись с новым dest
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass
    except OSError as exc:
        raise SpineError(
            "publication_archive_failed",
            "архивная копия ({}) не записана: {}".format(kind, exc),
            payload={"path": str(dest), "kind": kind,
                     "recovery": "почини причину и повтори `apply`",
                     "error_class": "blocker"},
        )
    return True


PUBLICATION_RETRY = {"retry": True}


def _publish_and_commit(run: Run, state: Dict[str, Any], kind: str, path: Path,
                        record: Optional[Dict[str, Any]], text: str,
                        payload_hash: str, base: Path, note: Optional[str] = None
                        ) -> Optional[Dict[str, Any]]:
    """Шаги 8–9 §4г: очистка tmp по префиксу, publish_file в обёртке, commit."""
    # Confinement каталога публикации ДО подметания: удаление — тоже запись в
    # базу, и она не должна идти через подменённый родительский каталог.
    parent = confined_or_none(path.parent, base, "каталог публикации ({})".format(kind))
    if parent is not None:
        sweep_tmp(parent, TMP_PUB_PREFIX)
    try:
        published = publish_file(run, path, text, kind)
    except SpineError as exc:
        if exc.code != "publication_conflict":
            raise
        except_obs = observe_target(path)
        if except_obs["class"] == "absent" and publication_resolution(state, kind):
            # Двойная гонка: интерлопер исчез между `os.link` и перечитыванием.
            # Конфликта нет — воля жива, диспетчер доиграет заход (Sonnet L1).
            return PUBLICATION_RETRY
        # TOCTOU-окно между наблюдением и `os.link`: сырой publication_conflict
        # со старым recovery-текстом не пробрасывается — запись терминализуется
        # немедленно (§4б), неисполненная воля снимается (иначе `next` считает
        # конфликт решённым и обещает прогресс — круг 2, Opus M2/Codex M4),
        # конфликт становится штатной паузой.
        if record is not None and except_obs["class"] == "regular":
            abort_replaced_record(record)
        drop_publication_resolution(state, kind)
        conflict = upsert_publication_conflict(
            state, _observation_conflict(state, kind, path, except_obs, payload_hash))
        save_state(run.run_dir, state)
        return conflict
    except OSError as exc:
        # Именованный resumable blocker вместо exit 2: каждая точка отказа
        # write-path обязана быть наблюдаемой (круг 2, Opus M3).
        raise SpineError(
            "publication_write_failed",
            "публикация ({}) не записана: {}".format(kind, exc),
            payload={"path": str(path), "kind": kind,
                     "recovery": "почини причину и повтори `apply`",
                     "error_class": "blocker"},
        )
    maybe_fault("apply:after_publish:{}".format(kind))
    commit_replace_done(run, state, kind, path, record, published, payload_hash, note)
    return None


def execute_replace(run: Run, state: Dict[str, Any], kind: str, path: Path,
                    record: Optional[Dict[str, Any]], text: str, payload_hash: str,
                    source: Dict[str, Any], base: Path, protocol_dir: Path,
                    note: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Файловые примитивы `replace` (§4г шаги 1–9). Возвращает конфликт либо None."""
    attempts = 0
    while True:
        if record is None:
            reserved = {item["to"] for item in replaced_records(state) if item.get("to")}
            dest = archive_publication_dest(protocol_dir, path.name, reserved)
            # Резолвнутый dest пишется в журнал: постчек (е) и повторное
            # наблюдение обязаны сверять ровно тот файл, который положил
            # `os.link` (Opus L8). Отказ confinement — код контура §7, а не
            # сырое path-нарушение: подменённый `zz_archive` обязан звучать
            # блокером исполнения (круг 3, Opus L-3).
            confined = confined_or_none(dest, base, "архивная копия ({})".format(kind))
            if confined is None:
                raise SpineError(
                    "publication_archive_failed",
                    "каталог архива ({}) не проходит confinement — копия не сделана".format(kind),
                    payload={"path": str(dest), "kind": kind,
                             "recovery": "почини путь в базе и повтори `apply`",
                             "error_class": "blocker"},
                )
            dest = confined
            record = new_replaced_record(state, kind, path, dest, source["hash"],
                                         payload_hash, "intent")
            save_state(run.run_dir, state)  # write-ahead: intent ДО файловых операций
            maybe_fault("apply:after_archive_intent:{}".format(kind))
        if record["stage"] == "intent":
            if not _archive_copy(run, state, kind, record, source["bytes"], base):
                abort_replaced_record(record)
                save_state(run.run_dir, state)
                attempts += 1
                if attempts >= ARCHIVE_REDEST_LIMIT:
                    raise SpineError(
                        "publication_archive_failed",
                        "каталог архива занимают под целью замены ({}): "
                        "{} попытки подряд".format(kind, attempts),
                        payload={"path": str(record["to"]), "kind": kind,
                                 "recovery": "почини причину и повтори `apply`",
                                 "error_class": "blocker"},
                    )
                record = None
                continue
            maybe_fault("apply:after_archive_copy:{}".format(kind))
            record["stage"] = "archived"
            save_state(run.run_dir, state)
            maybe_fault("apply:after_archive_stage:{}".format(kind))
        if record["stage"] == "archived":
            observed = observe_target(path)
            if observed["class"] == "regular" and observed["hash"] == record["hash"]:
                # Покомпонентный confinement непосредственно перед удалением:
                # деструктивная операция не полагается на проверку выше по стеку
                # (spine-contracts §5; круг 2, Codex H2 / Opus L4).
                victim = confined_or_none(path, base, "старый файл публикации ({})".format(kind))
                if victim is None:
                    raise SpineError(
                        "publication_unlink_failed",
                        "путь публикации ({}) не проходит confinement — удаление отменено".format(kind),
                        payload={"path": str(path), "kind": kind,
                                 "recovery": "почини путь в базе и повтори `apply`",
                                 "error_class": "blocker"},
                    )
                try:
                    os.unlink(str(victim))
                except OSError as exc:
                    raise SpineError(
                        "publication_unlink_failed",
                        "старый файл публикации ({}) не удалён: {}".format(kind, exc),
                        payload={"path": str(path), "kind": kind,
                                 "recovery": "почини причину и повтори `apply`",
                                 "error_class": "blocker"},
                    )
                maybe_fault("apply:after_unlink_op:{}".format(kind))
            elif observed["class"] == "unreadable":
                # Терминализовать нечем — наблюдение недоступно; запись ждёт
                # починки базы (второе ожидание §4б).
                drop_publication_resolution(state, kind)
                conflict = upsert_publication_conflict(
                    state, publication_conflict_item(kind, path, None, "unreadable"))
                save_state(run.run_dir, state)
                return conflict
            elif observed["class"] == "regular":
                abort_replaced_record(record)
                drop_publication_resolution(state, kind)
                conflict = upsert_publication_conflict(
                    state, _observation_conflict(state, kind, path, observed, payload_hash))
                save_state(run.run_dir, state)
                return conflict
            record["stage"] = "unlinked"
            save_state(run.run_dir, state)
            maybe_fault("apply:after_unlink:{}".format(kind))
        return _publish_and_commit(run, state, kind, path, record, text, payload_hash,
                                   base, note)


def publication_prepass(run: Run, state: Dict[str, Any], paths: Dict[str, Path],
                        base: Path) -> List[Dict[str, Any]]:
    """Глобальный [скан]-pre-pass журнала: записи с выпавшим `from` (§4в).

    Приоритет — доказательство публикации: файл на старом `from` == `payload_hash`
    записи → `done`, иначе `aborted`. Дозакрытия ветки 1 к чужим целям не
    применяются, `published` не трогается — прогон этот путь больше не публикует.
    """
    terminated: List[Dict[str, Any]] = []
    for record in replaced_records(state):
        if record["stage"] in ("done", "aborted"):
            continue
        target = paths.get(record["publication"])
        if target is not None and str(target) == record["from"]:
            continue
        if record["stage"] == "intent" and observe_archive_copy(record, base) == "hash":
            record["stage"] = "archived"  # честный aborted_from_stage
        obs = observe_target(Path(record["from"]))
        # Доказанное продвижение стадии (§4б) применяется и к выпавшей цели:
        # `archived` + ENOENT — unlink состоялся де-факто, и запись обязана уйти
        # в `unlinked` ДО терминализации, иначе постчек не освободит `from`
        # от `foreign_file_removed` (круг 2, Codex M3).
        if record["stage"] == "archived" and obs["class"] == "absent":
            record["stage"] = "unlinked"
        if obs["class"] == "regular" and obs["hash"] == record["payload_hash"]:
            close_replaced_record(record)
        else:
            abort_replaced_record(record)
        terminated.append({"publication": record["publication"], "from": record["from"],
                           "to": record["to"], "stage": record["stage"],
                           "aborted_from_stage": record.get("aborted_from_stage")})
    if terminated:
        log_event(state, "apply:terminated_replacements", detail=str(len(terminated)))
        save_state(run.run_dir, state)
    return terminated


def publication_pass(run: Run, state: Dict[str, Any], mode: str, text: str,
                     base: Path, protocol_dir: Path) -> Dict[str, Any]:
    """Алгоритм §4в по всем kind в режиме `scan` либо `execute`.

    `scan` — только наблюдения и мутации state (пре-скан на входе apply: ноль
    записей в базу клиента); `execute` — плюс действия §4г. Возвращает
    `{conflicts, published, terminated}`.
    """
    payload_hash = sha256_bytes(text.encode("utf-8"))
    paths = publication_paths(state)
    terminated = publication_prepass(run, state, paths, base) if mode == "scan" else []
    conflicts: List[Dict[str, Any]] = []
    for kind in PUBLICATION_KINDS:
        path = paths.get(kind)
        if path is None:
            continue
        conflict = _process_publication_kind(run, state, kind, path, text, payload_hash,
                                             mode, base, protocol_dir)
        if conflict is not None:
            conflicts.append(conflict)
    return {"conflicts": conflicts, "terminated": terminated}


def _process_publication_kind(run: Run, state: Dict[str, Any], kind: str, path: Path,
                              text: str, payload_hash: str, mode: str, base: Path,
                              protocol_dir: Path) -> Optional[Dict[str, Any]]:
    """Ветки 0–3 §4в для одного kind. Ячейки [исполнение] на скане молчат."""
    # Рамка символов фиксируется по записи, которая была живой на входе: после
    # терминализации `H`/`PH` обязаны остаться различимыми (иначе воля про старые
    # байты «совпала» бы с чужим файлом на пути).
    symbol_record: Optional[Dict[str, Any]] = None
    for _ in range(6):
        record = open_replaced_record(state, kind)
        if record is not None:
            symbol_record = record
        obs = observe_target(path)
        # Доказанное продвижение стадии (§4б): наблюдённый ENOENT у `archived`
        # атомарно двигает запись в `unlinked` ДО пауз и терминализаций.
        if record is not None and record["stage"] == "archived" and obs["class"] == "absent":
            record["stage"] = "unlinked"
            save_state(run.run_dir, state)
        to_class = observe_archive_copy(record, base) if (
            record is not None and record["stage"] == "intent") else None
        choice, resolution = resolution_axis(state, kind, path, payload_hash)
        refusal = bool(state.setdefault("publication_refusals", {}).get(kind))
        obs_symbol, eh_symbol = publication_symbols(
            obs,
            (resolution or {}).get("existing_hash") if choice in ("replace", "keep") else None,
            payload_hash, symbol_record)
        cell, _transition = publication_step(
            stage=None if record is None else record["stage"],
            record_kind=("none" if record is None else
                         ("vanished" if record.get("hash") is None else "normal")),
            payload_hash_is_payload=(None if record is None
                                     else record.get("payload_hash") == payload_hash),
            to_class=to_class,
            choice=choice,
            existing_hash=eh_symbol,
            obs=obs_symbol,
            refusal=refusal,
        )

        # --- ветка 0: исполненная резолюция в scope --------------------------- #
        if cell == "0":
            return None

        # --- 1а: стадия intent ------------------------------------------------ #
        if cell == "1а-copy-confirmed":
            record["stage"] = "archived"
            save_state(run.run_dir, state)
            continue
        if cell in ("1а-copy-foreign", "1а-abort", "1б-guard-abort", "1б-8-abort"):
            abort_replaced_record(record)
            save_state(run.run_dir, state)
            continue
        if cell == "1а-continue":
            if mode != "execute":
                return None
            result = execute_replace(run, state, kind, path, record, text, payload_hash,
                                     obs, base, protocol_dir)
            if result is PUBLICATION_RETRY:
                continue
            return result

        # --- 1б: archived / unlinked ------------------------------------------ #
        if cell == "1б-1-vanished-keep":
            drop_publication_resolution(state, kind)
            conflict = upsert_publication_conflict(
                state, publication_conflict_item(kind, path, None, "kept_target_vanished"))
            save_state(run.run_dir, state)
            return conflict
        if cell in ("1б-2-refusal-pause", "3-1a-refusal-pause"):
            carried = bool((state["publication_refusals"].get(kind) or {}).get("carried_over"))
            conflict = upsert_publication_conflict(
                state, publication_conflict_item(
                    kind, path, None, "kept_target_vanished",
                    origin="declined_earlier" if carried else None))
            save_state(run.run_dir, state)
            return conflict
        if cell in ("1б-2-publish", "1б-2-executed"):
            if mode != "execute":
                return None
            note = None
            if (resolution is not None and choice == "replace"
                    and resolution.get("existing_hash") != record.get("hash")):
                note = "target_vanished"
            result = _publish_and_commit(run, state, kind, path, record, text,
                                         payload_hash, base, note)
            if result is PUBLICATION_RETRY:
                continue
            return result
        if cell == "1б-3-replace-done":
            # [скан]-дозакрытие: published собирается из наблюдения (hash == payload
            # доказан чтением), publish_file не вызывается — на скане он создавал
            # бы tmp в каталоге публикации.
            commit_replace_done(run, state, kind, path, record,
                                {"path": str(path), "kind": kind, "created": False,
                                 "hash": obs["hash"]}, payload_hash)
            return None
        if cell == "1б-4-keep-published":
            commit_keep_published(run, state, kind, path, record, obs, payload_hash)
            return None
        if cell == "1б-5-superseded":
            return commit_superseded(run, state, kind, path, record, obs)
        if cell == "1б-6-close-foreign":
            # Замена состоялась в своей реальности: только журнал `done`,
            # published/резолюции/конфликты не трогаются — ими займутся ветки 2–3.
            close_replaced_record(record)
            save_state(run.run_dir, state)
            continue
        if cell == "1б-7-continue":
            if mode != "execute":
                return None
            result = execute_replace(run, state, kind, path, record, text, payload_hash,
                                     obs, base, protocol_dir)
            if result is PUBLICATION_RETRY:
                continue
            return result
        if cell in ("1б-9-unreadable", "2-5-unreadable", "3-4-unreadable"):
            drop_publication_resolution(state, kind)
            conflict = upsert_publication_conflict(
                state, publication_conflict_item(kind, path, None, "unreadable"))
            save_state(run.run_dir, state)
            return conflict

        # --- ветка 2: живая резолюция ----------------------------------------- #
        if cell in ("2-1b-vanished-keep", "2-2b-keep-vanished"):
            drop_publication_resolution(state, kind)
            conflict = upsert_publication_conflict(
                state, publication_conflict_item(kind, path, None, "kept_target_vanished"))
            save_state(run.run_dir, state)
            return conflict
        if cell in ("2-1a-vanished-replace", "2-2a-vanished-note"):
            if mode != "execute":
                return None
            # Архивировать нечего: запись создаётся сразу в `unlinked`.
            record = new_replaced_record(state, kind, path, None, None,
                                         payload_hash, "unlinked")
            save_state(run.run_dir, state)
            note = "target_vanished" if cell == "2-2a-vanished-note" else None
            result = _publish_and_commit(run, state, kind, path, record, text,
                                         payload_hash, base, note)
            if result is PUBLICATION_RETRY:
                continue
            return result
        if cell == "2-1c-execute":
            if mode != "execute":
                return None
            if choice == "keep":
                return execute_keep(run, state, kind, path, resolution, payload_hash)
            result = execute_replace(run, state, kind, path, None, text, payload_hash,
                                     obs, base, protocol_dir)
            if result is PUBLICATION_RETRY:
                continue
            return result
        if cell in ("2-3-superseded", "2-4-content-differs"):
            drop_publication_resolution(state, kind)
            conflict = upsert_publication_conflict(
                state, _observation_conflict(state, kind, path, obs, payload_hash))
            save_state(run.run_dir, state)
            return conflict

        # --- ветка 3: резолюции нет ------------------------------------------- #
        if cell in ("3-1b-publish", "3-2-idempotent"):
            if mode != "execute":
                return None
            parent = confined_or_none(path.parent, base,
                                      "каталог публикации ({})".format(kind))
            if parent is not None:
                sweep_tmp(parent, TMP_PUB_PREFIX)
            try:
                published = publish_file(run, path, text, kind)
            except SpineError as exc:
                if exc.code != "publication_conflict":
                    raise
                # Та же обёртка, что на шаге 8: TOCTOU-гонка становится штатной
                # паузой, а не сырым publication_conflict со старым recovery.
                # Отказ (`publication_refusals`) не снимается: исполнения решения
                # здесь не было — воли по kind не звучало.
                fresh = observe_target(path)
                conflict = upsert_publication_conflict(
                    state, _observation_conflict(state, kind, path, fresh, payload_hash))
                save_state(run.run_dir, state)
                return conflict
            except OSError as exc:
                raise SpineError(
                    "publication_write_failed",
                    "публикация ({}) не записана: {}".format(kind, exc),
                    payload={"path": str(path), "kind": kind,
                             "recovery": "почини причину и повтори `apply`",
                             "error_class": "blocker"},
                )
            upsert_published(state, published)
            drop_publication_conflict(state, kind)
            save_state(run.run_dir, state)
            return None
        if cell == "3-3-content-differs":
            conflict = upsert_publication_conflict(
                state, publication_conflict_item(kind, path, obs["hash"], "content_differs"))
            save_state(run.run_dir, state)
            return conflict
        raise SpineError("internal_publication_cell",
                         "внутренняя ошибка: ячейка {} без обработчика".format(cell),
                         exit_code=2)
    # Заход не сошёлся (серия гонок на пути публикации) — именованный resumable
    # blocker, а не внутренняя ошибка: повтор apply штатно доигрывает (Opus M3).
    raise SpineError(
        "publication_write_failed",
        "путь публикации ({}) переписывают во время записи — заход не сошёлся".format(kind),
        payload={"path": str(path), "kind": kind,
                 "recovery": "почини причину и повтори `apply`",
                 "error_class": "blocker"},
    )


def publication_conflict_error(state: Dict[str, Any],
                               conflicts: List[Dict[str, Any]]) -> SpineError:
    """Агрегированный blocker: один круг паузы на все конфликты захода."""
    resolvable = [item for item in conflicts if item["choices"]]
    recovery = ("`resolve-publications …`, затем `apply`" if resolvable
                else "почини путь в базе и повтори `apply`")
    if resolvable and len(resolvable) != len(conflicts):
        recovery = ("`resolve-publications …`, затем `apply`; нечитаемую цель "
                    "почини в базе руками")
    violations = [
        violation("publication_target_unreadable" if not item["choices"]
                  else "publication_conflict",
                  "путь публикации нечитаем" if not item["choices"]
                  else "путь публикации занят: {}".format(item["reason"]),
                  field=item["path"])
        for item in conflicts
    ]
    return SpineError(
        "publication_conflict",
        "путь публикации занят — нужно решение пользователя ({})".format(
            ", ".join(item["kind"] for item in conflicts)),
        violations=violations,
        payload={"publication_conflicts": conflicts, "recovery": recovery,
                 "next_command": "next", "error_class": "question"},
    )


def cmd_resolve_publications(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    """Решение пользователя «заменить/оставить» — §4а. Базу не трогает."""
    run = require_run(args)
    state = run.state
    require_phase(state, "apply")
    conflicts = state.setdefault("publication_conflicts", [])
    resolvable = [item for item in conflicts if item["choices"]]
    if not resolvable:
        message = ("остались только нечитаемые цели — почини базу и повтори `apply`"
                   if conflicts else "конфликтов публикации нет")
        raise SpineError("no_pending_conflicts",
                         "решать нечего: {}".format(message),
                         payload={"publication_conflicts": conflicts})

    wanted: Dict[str, str] = {}
    for choice, values in (("replace", args.replace), ("keep", args.keep)):
        for kind in values or []:
            if kind not in PUBLICATION_KINDS:
                raise SpineError("bad_usage", "неизвестный kind: {}".format(kind), exit_code=2)
            if kind in wanted:
                raise SpineError("bad_usage",
                                 "kind {} назван и в --replace, и в --keep".format(kind),
                                 exit_code=2)
            wanted[kind] = choice

    by_kind = {item["kind"]: item for item in conflicts}
    violations: List[Dict[str, Any]] = []
    for kind, choice in sorted(wanted.items()):
        item = by_kind.get(kind)
        if item is None:
            violations.append(violation("unknown_conflict",
                                        "конфликта по {} нет".format(kind), field=kind))
            continue
        if not item["choices"]:
            violations.append(violation("conflict_not_resolvable",
                                        "цель {} нечитаема — чинится руками".format(kind),
                                        field=kind))
            continue
        if choice not in item["choices"]:
            violations.append(violation("choice_not_allowed",
                                        "решение {} недоступно для {}".format(choice, kind),
                                        field=kind))
    for item in resolvable:
        if item["kind"] not in wanted:
            violations.append(violation("missing_decisions",
                                        "нет решения по {}".format(item["kind"]),
                                        field=item["kind"]))

    # Hash-binding: сверка со свежим наблюдением по примитиву §2 п.6.
    observations: Dict[str, Dict[str, Any]] = {}
    changed: List[str] = []
    for kind in sorted(wanted):
        item = by_kind.get(kind)
        if item is None or not item["choices"]:
            continue
        obs = observe_target(Path(item["path"]))
        observations[kind] = obs
        if obs["class"] == "unreadable":
            violations.append(violation("conflict_unreadable",
                                        "цель {} стала нечитаемой".format(kind), field=kind))
            # Конфликт пересобирается и здесь, симметрично `conflict_changed`:
            # иначе `next` честно предложит команду, которая заведомо откажет
            # (круг 2, Sonnet M1).
            changed.append(kind)
            continue
        if obs["class"] == "absent":
            continue  # обеднение безопасно: воля пишется с existing_hash: null
        if obs["hash"] != item["existing_hash"]:
            violations.append(violation(
                "conflict_changed",
                "на пути {} другое содержимое, чем показано".format(kind), field=kind))
            changed.append(kind)

    if violations:
        # Конфликт пересобирается по свежему наблюдению; перестал быть
        # конфликтом (== payload без ЖИВОЙ воли) — снимается. Payload читается
        # один раз до цикла: иначе отсутствующий corrections отдал бы наружу
        # `corrections_missing` вместо контрактного кода (Opus L9).
        payload_hash = (sha256_bytes(confirmed_summary_text(run).encode("utf-8"))
                        if changed else None)
        for kind in changed:
            item = by_kind[kind]
            obs = observations[kind]
            # Живой считается только неисполненная воля: историческая
            # `executed`-резолюция после rework решением не является и не мешает
            # снять исчерпавшийся конфликт (круг 2, Codex M4).
            live, _ = resolution_axis(state, kind, Path(item["path"]), payload_hash or "")
            if obs["class"] == "regular" and obs["hash"] == payload_hash \
                    and live not in ("replace", "keep"):
                drop_publication_conflict(state, kind)
            else:
                upsert_publication_conflict(
                    state, _observation_conflict(state, kind, Path(item["path"]),
                                                 obs, payload_hash))
        if changed:
            save_state(run.run_dir, state)
        raise SpineError(
            violations[0]["code"], "решения не записаны — {}".format(violations[0]["message"]),
            violations=violations,
            payload={"publication_conflicts": state["publication_conflicts"],
                     "recovery": "конфликт исчерпан — повтори `apply`" if not
                     state["publication_conflicts"] else "посмотри `next` и реши заново",
                     # error_class: question только при живых конфликтах — иначе
                     # это ошибка вызова координатора, класса не положено.
                     **({"error_class": "question"} if state["publication_conflicts"] else {})},
        )

    decided = []
    for kind, choice in sorted(wanted.items()):
        item = by_kind[kind]
        obs = observations[kind]
        record = {
            "choice": choice,
            "path": item["path"],
            "existing_hash": None if obs["class"] == "absent" else obs["hash"],
            "decided_at": now_iso(),
        }
        state["publication_resolutions"][kind] = record
        # Наблюдение конфликта приводится к тому, по которому записана воля
        # (обеднение: файл исчез к моменту команды → `existing_hash: null`).
        # Иначе ось «воля отвечает конфликту» разошлась бы на ровном месте и
        # пауза повторилась бы после честного ответа (круг 3, Codex M).
        item["existing_hash"] = record["existing_hash"]
        # Успешный вызов снимает отказ всех kinds партиции — атомарно с волей.
        state.setdefault("publication_refusals", {}).pop(kind, None)
        decided.append({"kind": kind, "choice": choice, "path": item["path"],
                        "existing_hash": record["existing_hash"]})
    log_event(state, "resolve-publications",
              detail=", ".join("{}={}".format(d["kind"], d["choice"]) for d in decided))
    save_state(run.run_dir, state)

    unreadable = [item["kind"] for item in conflicts if not item["choices"]]
    payload = status_payload(run)
    payload["resolutions"] = decided
    payload["unreadable_conflicts"] = unreadable
    lines = ["{}: {}".format(item["kind"], item["choice"]) for item in decided]
    lines.append("Дальше: `apply`")
    if unreadable:
        lines.append("apply встанет на нечитаемой цели — сначала почини базу")
    return payload, lines


def resolution_answers(state: Dict[str, Any], conflict: Dict[str, Any]) -> bool:
    """Отвечает ли записанная воля именно ЭТОМУ конфликту (ось живой резолюции).

    Наличия неисполненной резолюции мало: после `conflict_changed` прежняя воля
    остаётся в слоте (all-or-nothing ничего не пишет и ничего не стирает), а
    конфликт уже пересобран по свежему наблюдению. Считать такой kind «решённым»
    значит обещать пользователю прогресс и подарить ему гарантированно холостой
    круг: `apply` эту волю сбросит веткой 2 и снова встанет на паузу (круг 3,
    Codex M). Воля отвечает конфликту только при совпадении `(path,
    existing_hash)`; исполненная — не отвечает вовсе (§3).
    """
    record = publication_resolution(state, conflict["kind"])
    if not record or not record.get("choice") or record.get("executed"):
        return False
    return (record.get("path") == conflict["path"]
            and record.get("existing_hash") == conflict.get("existing_hash"))


def publication_pause(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Ситуативная пауза внутри этапа apply: манифест по состояниям (§6)."""
    conflicts = state.get("publication_conflicts") or []
    if state["phase"] != "apply" or not conflicts:
        return None
    pending = [item for item in conflicts if not resolution_answers(state, item)]
    resolvable = [item for item in pending if item["choices"]]
    unreadable = [item for item in conflicts if not item["choices"]]
    texts = []
    for item in resolvable:
        if item.get("origin") == "declined_earlier":
            texts.append(PUBLICATION_DECLINED_SCREEN)
        else:
            texts.append(PUBLICATION_SCREENS[(item["reason"], item["kind"])])
    if len(texts) > 1:
        texts.append(PUBLICATION_MANY)
    if resolvable and unreadable:
        texts.append(PUBLICATION_MIXED_WARNING)
    commands: List[str] = []
    if resolvable:
        options = [[(item["kind"], choice) for choice in item["choices"]]
                   for item in resolvable]
        for combo in _cartesian(options):
            commands.append("resolve-publications " + " ".join(
                "--{} {}".format(choice, kind) for kind, choice in combo))
    blockers = [item for item in state["blockers"] if item.get("code") in EXECUTION_BLOCKERS]
    return {
        "conflicts": conflicts,
        "resolvable": resolvable,
        "unreadable": unreadable,
        "decided": [item for item in conflicts if item not in pending],
        "expected_commands": commands or ["apply"],
        "say": " ".join(texts) if texts else None,
        "execution_blockers": blockers,
    }


def _cartesian(options: List[List[Any]]) -> List[List[Any]]:
    combos: List[List[Any]] = [[]]
    for group in options:
        combos = [combo + [item] for combo in combos for item in group]
    return combos


def cmd_apply(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    run = require_run(args)
    state = run.state
    require_live(state)
    if state["apply_status"] == "completed":
        raise SpineError(
            "apply_already_completed",
            "нарушен precondition apply_status: apply уже завершён — повторное применение запрещено",
            payload={"apply_status": state["apply_status"]},
        )
    require_phase(state, "apply")
    if state["phases"]["accept"]["status"] != "validated" or not state["accept"]["hash"]:
        raise SpineError("precondition_accept", "нарушен precondition accept_validated: решение пользователя не принято")

    accept_path = run.path(state["accept"]["artifact"])
    if not accept_path.is_file() or artifact_hash(accept_path) != state["accept"]["hash"]:
        raise SpineError("artifact_hash_mismatch", "accept.json изменён после фиксации решения")
    compose_path = run.path(state["compose"]["artifact"])
    if not compose_path.is_file() or sha256_file(compose_path) != state["compose"]["hash"]:
        raise SpineError(
            "compose_hash_mismatch",
            "нарушен precondition compose_binding: состав compose изменён после accept",
            payload={"recovery": "compose → accept заново", "error_class": "blocker"},
        )

    base = Path(state["base_path"])
    # protocol_dir проверяли на locate — с тех пор его могли подменить symlink'ом.
    # Отказ здесь, до пре-снимка, стоит ноль записей в базу.
    protocol_dir = ensure_inside_base(Path(state["context"]["protocol_dir"]), base, "protocol_dir")
    if protocol_dir.exists() and not protocol_dir.is_dir():
        raise SpineError(
            "protocol_dir_not_a_directory",
            "protocol_dir перестал быть каталогом после locate",
            payload={"path": str(protocol_dir), "recovery": "почини базу и повтори `apply`",
                     "error_class": "blocker"},
        )
    ledger = {d["id"]: d for d in ledger_deltas(run)}
    # Порядок применения выводится ОДИН раз на все точки этого захода: входные
    # гейты, dry-run и цикл записи получают один и тот же список — физически
    # разойтись они не могут (защита допущения, на котором стоит авторитетность
    # симуляции; см. `apply_order`).
    accepted = apply_order(state["accept"]["take"])

    # Гейты до пре-снимка и до первой записи: принятая дельта в стратегический
    # контур либо в путь публикации прогона останавливает apply целиком, даже
    # если пришла через ack_unresolved.
    publications = publication_targets(state)
    for delta_id in accepted:
        delta = ledger[delta_id]
        ensure_not_strategic(base / delta["target_file"], base,
                             "target_file дельты {}".format(delta_id), (delta_id,))
        ensure_not_publication_target(base / delta["target_file"], publications,
                                      "target_file дельты {}".format(delta_id), (delta_id,))
        if delta.get("source_file"):
            ensure_not_strategic(base / delta["source_file"], base,
                                 "source_file дельты {}".format(delta_id), (delta_id,))
            # Гейт распространён на source_file (B№4 §4г «Совместимости»):
            # move-дельта не может резать файл, судьба которого решается
            # replace/keep — терминальный отказ до пре-скана и любых записей.
            ensure_not_publication_target(base / delta["source_file"], publications,
                                          "source_file дельты {}".format(delta_id),
                                          (delta_id,))

    entries = read_journal(run)
    # Файлы, которые правил сам apply: их расхождение с accept-манифестом —
    # собственный след, а не чужая правка (журнал + intent отличают одно от другого).
    own = {item["path"] for entry in entries for item in entry["files"]}

    # base_hash per-file: базу правили между accept и apply → recovery, не перезапись.
    drift = []
    for rel, expected in state["accept"]["base_manifest"].items():
        if rel in own:
            continue
        current = file_hash_or_none(base / rel)
        if current != expected:
            drift.append(violation("base_hash_mismatch", "файл базы изменён после accept", field=rel))
    if drift:
        raise SpineError(
            "base_hash_mismatch",
            "нарушен precondition base_unchanged: база правилась между accept и apply",
            violations=drift,
            payload={"recovery": "restart-from --phase canon", "error_class": "blocker"},
        )

    # Пре-скан публикаций (B№4 §2 п.1): payload читается здесь — `corrections_missing`
    # становится ошибкой входа, а конфликт занятого пути — паузой ДО пре-снимка,
    # журнала дельт и первой записи. Мутации state инвариант «ноль записей в базу»
    # не нарушают: run-каталог вне базы.
    summary_text = confirmed_summary_text(run)
    scan = publication_pass(run, state, "scan", summary_text, base, protocol_dir)
    if scan["conflicts"]:
        exc = publication_conflict_error(state, scan["conflicts"])
        state["blockers"] = [{"code": exc.code, "message": exc.message, "phase": "apply"}]
        # Сохранение blocker'а — диагностический путь: инвариант здесь не должен
        # подменять исходный диагноз своей внутренней ошибкой (круг 3, Opus L-2).
        save_state(run.run_dir, state, enforce_invariants=False)
        exc.payload.setdefault("apply_status", state["apply_status"])
        raise exc
    terminated = scan["terminated"]

    # Pre-apply dry-run (волна D, D-A п.1): реальный `perform_operation` на копии
    # затронутых файлов. Порядок входа зафиксирован — base_manifest-drift →
    # пре-скан публикаций B№4 → dry-run → пре-снимок/журнал. Отказ стоит ноль
    # записей в базу и вне всех rework-счётчиков: это свойство принятого набора
    # против живой базы, а не ошибка узла и не структурный отказ артефакта.
    try:
        dry_run = dry_run_write_set(run, base, ledger, accepted, entries)
    except SpineError as exc:
        if exc.code != "apply_dry_run_failed":
            raise
        state["blockers"] = [{"code": exc.code, "message": exc.message, "phase": "apply"}]
        # Диагностический путь: инвариант state не должен подменять исходный
        # диагноз своей внутренней ошибкой (тот же принцип, что у B№4).
        save_state(run.run_dir, state, enforce_invariants=False)
        exc.payload.setdefault("apply_status", state["apply_status"])
        raise

    # Осиротевший `.tmp-pub-*` прошлого процесса подметается ДО пре-снимка:
    # иначе он попадает в снимок, а норматив шага 8 сносит его — и постчек даёт
    # `foreign_file_removed` на ровном месте (круг 2, Opus M1). Порядок «после
    # паузы» сохраняет инвариант «отказ стоит ноль записей в базу».
    sweep_parent = confined_or_none(protocol_dir, base, "каталог публикаций")
    if sweep_parent is not None:
        sweep_tmp(sweep_parent, TMP_PUB_PREFIX)

    if state["apply_status"] == "not_started":
        snapshot = {"taken_at": now_iso(), "files": base_snapshot(base)}
        write_json_artifact(run.path(ART_SNAPSHOT), snapshot)
        state["apply"]["snapshot"] = ART_SNAPSHOT
        state["apply"]["started_at"] = now_iso()
        state["apply_status"] = "in_progress"
        state["side_effects"]["apply_journal"] = ART_JOURNAL
        write_journal(run, [])
        save_state(run.run_dir, state)
        entries = []

    by_delta = {e["delta_id"]: e for e in entries if e.get("delta_id")}

    for delta_id in accepted:
        delta = ledger[delta_id]
        existing = by_delta.get(delta_id)
        # Классификация журнала — общая с dry-run функция (D-A п.1): один шаг,
        # не парафраз. `done` пропускаем; `intent-completed` дозакрываем без
        # повторной файловой операции; `intent-pending` переисполняем.
        klass = resume_class(delta, existing, base)
        if klass == RESUME_DONE:
            continue
        if klass == RESUME_INTENT_COMPLETED:
            existing["stage"] = "done"
            existing["files"] = [
                {"path": item["path"], "hash_before": item["hash_before"],
                 "hash_after": file_hash_or_none(base / item["path"])}
                for item in existing["files"]
            ]
            existing["closed_at"] = now_iso()
            write_journal(run, entries)
            continue
        if klass == RESUME_INTENT_PENDING:
            entries.remove(existing)

        planned = [delta["target_file"]]
        if delta.get("source_file"):
            planned.append(delta["source_file"])
        intent = {
            "delta_id": delta_id,
            "operation": delta["operation"],
            "fingerprint": delta_fingerprint(delta),
            "stage": "intent",
            "files": [{"path": rel, "hash_before": file_hash_or_none(base / rel), "hash_after": None}
                      for rel in sorted(set(planned))],
            "at": now_iso(),
        }
        entries.append(intent)
        write_journal(run, entries)  # write-ahead: intent ДО файловой операции
        maybe_fault("apply:after_intent:{}".format(delta_id))

        try:
            touched = perform_operation(delta, base, publications)
        except SpineError as exc:
            state["blockers"] = [{"code": exc.code, "message": exc.message, "phase": "apply"}]
            save_state(run.run_dir, state, enforce_invariants=False)
            exc.payload.setdefault("apply_status", state["apply_status"])
            exc.payload.setdefault("recovery", "почини причину и повтори `apply` — журнал возобновит с этой дельты")
            raise
        maybe_fault("apply:after_fileop:{}".format(delta_id))

        intent["stage"] = "done"
        intent["files"] = [{"path": rel,
                            "hash_before": next((f["hash_before"] for f in intent["files"] if f["path"] == rel), None),
                            "hash_after": file_hash_or_none(base / rel)}
                           for rel in touched]
        intent["closed_at"] = now_iso()
        write_journal(run, entries)  # журнальная запись атомарно ПОСЛЕ каждой дельты

    # Таблица side effects пересобирается из журнала — источника правды apply.
    applied: List[Dict[str, Any]] = []
    for entry in entries:
        if entry.get("stage") != "done":
            continue
        for item in entry["files"]:
            applied.append({
                "path": str(base / item["path"]),
                "delta_id": entry["delta_id"],
                "operation": entry["operation"],
                "hash_after": item["hash_after"],
            })

    # Публикации: выжимка всегда, протокол — только при protocol_required.
    # Оба файла несут подтверждённую выжимку: дельтой протокол не заводится
    # (E00, вариант (а)), путь — только protocol_dir из locate. Занятый путь —
    # решение пользователя (B№4 §4в/§4г), не молчаливая перезапись.
    state["side_effects"]["applied"] = applied
    try:
        step = publication_pass(run, state, "execute", summary_text, base, protocol_dir)
    except SpineError as exc:
        state["blockers"] = [{"code": exc.code, "message": exc.message, "phase": "apply"}]
        # Сохранение blocker'а — диагностический путь: инвариант здесь не должен
        # подменять исходный диагноз своей внутренней ошибкой (круг 3, Opus L-2).
        save_state(run.run_dir, state, enforce_invariants=False)
        exc.payload.setdefault("apply_status", state["apply_status"])
        exc.payload.setdefault("recovery", "почини причину и повтори `apply`")
        raise
    if step["conflicts"]:
        # Конфликт посреди apply: он уже записан в state — `next` сразу
        # показывает паузу, холостого apply не нужно.
        exc = publication_conflict_error(state, step["conflicts"])
        state["blockers"] = [{"code": exc.code, "message": exc.message, "phase": "apply"}]
        # Сохранение blocker'а — диагностический путь: инвариант здесь не должен
        # подменять исходный диагноз своей внутренней ошибкой (круг 3, Opus L-2).
        save_state(run.run_dir, state, enforce_invariants=False)
        exc.payload.setdefault("apply_status", state["apply_status"])
        raise exc
    published = list(state["side_effects"]["published"])

    state["apply_status"] = "completed"
    state["apply"]["journal"] = ART_JOURNAL
    state["apply"]["completed_at"] = now_iso()
    state["blockers"] = []
    mark_validated(state, "apply")
    set_phase(state, "postcheck")
    log_event(state, "apply", detail="{} дельт".format(len(accepted)))
    save_state(run.run_dir, state)

    apply_lines = [
        "Применено дельт: {}".format(len(accepted)),
        "Публикаций: {}".format(len(published)),
    ]
    if terminated:
        apply_lines.append("Замен по выпавшим целям закрыто: {}".format(len(terminated)))
    # Автосцепка код-фаз: между apply и postcheck нет ни HITL, ни LLM — сверка
    # исполняется этим же вызовом (минус ход координатора). Отказ postcheck
    # приходит обычным блокером: apply уже сохранён, состояние это переживает.
    payload, post_lines = perform_postcheck(run)
    payload["applied"] = applied
    payload["published"] = published
    # След симуляции: последовательность dry-run обязана совпадать с журналом
    # реальной записи — наблюдаемо, а не только утверждается (D-A п.1).
    payload["dry_run"] = dry_run
    # Терминализация записей с выпавшим `from` — не violation и не blocker:
    # строка вывода + поле payload (§4б).
    payload["terminated_replacements"] = terminated
    return payload, apply_lines + post_lines


# --------------------------------------------------------------------------- #
# postcheck
# --------------------------------------------------------------------------- #

def build_deliver_decisions(run: Run) -> Dict[str, Any]:
    """Вход deliver-узла: партиция accept в компактном виде.

    Telegram-сводка — план работы по итогу встречи, не пересказ (Эрик 30.07):
    задачи в план идут из принятых дельт; отклонённые несут already_tracked —
    авторитетное слово пользователя «работа уже идёт» (`accept --already`),
    единственный критерий включения; текст причины — контекст, не критерий.
    """
    state = run.state
    ledger = {d["id"]: d for d in ledger_deltas(run)}
    already = set(state["accept"].get("already") or [])

    def slim(delta: Dict[str, Any], with_reason: bool) -> Dict[str, Any]:
        item = {
            "id": delta.get("id"),
            "entity_id": delta.get("entity_id"),
            "entity_type": delta.get("entity_type"),
            "role": delta.get("role"),
            "owner": delta.get("owner"),
            "operation": delta.get("operation"),
            "target_file": delta.get("target_file"),
            "text": delta.get("proposed_text") or "",
        }
        if with_reason:
            # already_tracked — авторитетное слово пользователя («отклоняю как
            # уже идущее»), критерий включения в план; текст причины — контекст.
            item["already_tracked"] = delta.get("id") in already
            verdict = delta.get("review_verdict")
            item["reason"] = (delta.get("doubt_question") or delta.get("home_question")
                              or (verdict if verdict and verdict not in REVIEW_ACCEPTING else None)
                              or "отклонено пользователем без названной причины")
        return item

    return {
        "accepted": [slim(ledger[i], False) for i in sorted(state["accept"]["take"]) if i in ledger],
        "rejected": [slim(ledger[i], True) for i in sorted(state["accept"]["reject"]) if i in ledger],
    }


def cmd_postcheck(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    run = require_run(args)
    state = run.state
    if getattr(args, "recheck", False):
        # Живой шов: повторная сверка базы в любой момент после apply — без
        # фазовых переходов (сама фаза postcheck исполняется автосцепкой apply).
        # На failed запрещён: чистая сверка при стоящем блокере дала бы
        # противоречивый исход «exit 0 при failed» — сначала restart-from.
        require_live(state)
        if state["status"] == "failed":
            raise SpineError(
                "run_failed",
                "нарушен precondition run_active: run в статусе failed — "
                "сначала `restart-from` или `abandon`, потом повторная сверка")
        report = postcheck_report(run)
        save_state(run.run_dir, state)
        payload = status_payload(run)
        payload["postcheck"] = report
        payload["recheck"] = True
        return payload, [
            "Повторная сверка чиста: проверено файлов {}".format(report["checked_files"]),
            "Фаза: {}".format(state["phase"]),
        ]
    if state["phases"]["postcheck"].get("status") == "validated" and state["phase"] != "postcheck":
        # Идемпотентный повтор: сверка уже исполнена автосцепкой apply → postcheck.
        # На failed запрещён симметрично --recheck: «postcheck чист» по отчёту,
        # опровергнутому более поздней сверкой, — противоречивый исход (kimi M2).
        require_live(state)
        if state["status"] == "failed":
            raise SpineError(
                "run_failed",
                "нарушен precondition run_active: run в статусе failed — "
                "сначала `restart-from` или `abandon`")
        # Отчёт hash-bound: подменённый postcheck.json доверенным не считается.
        report_path = run.path(state["postcheck"]["artifact"])
        if not report_path.is_file() or artifact_hash(report_path) != state["postcheck"]["hash"]:
            raise SpineError(
                "artifact_hash_mismatch",
                "postcheck.json изменён после сверки — доверенного отчёта нет; "
                "повторная сверка: `postcheck --recheck`")
        report = load_json_file(report_path)
        payload = status_payload(run)
        payload["postcheck"] = report
        payload["idempotent"] = True
        return payload, [
            "postcheck чист: проверено файлов {}".format(report["checked_files"]),
            "Фаза: {}".format(state["phase"]),
        ]
    return perform_postcheck(run)


def postcheck_report(run: Run) -> Dict[str, Any]:
    """Сверка (а)–(е) применённого с ledger: пишет отчёт, при расхождениях —
    fail_run. Фазу не двигает — переходы держит perform_postcheck."""
    state = run.state
    if state["apply_status"] != "completed":
        raise SpineError("precondition_apply", "нарушен precondition apply_completed: apply не завершён")

    base = Path(state["base_path"])
    snapshot = load_json_file(run.path(state["apply"]["snapshot"]))["files"]
    entries = read_journal(run)
    ledger = {d["id"]: d for d in ledger_deltas(run)}
    discrepancies: List[Dict[str, Any]] = []

    touched: Dict[str, Optional[str]] = {}
    writers: Dict[str, List[str]] = {}
    for entry in entries:
        for item in entry["files"]:
            touched[item["path"]] = item["hash_after"]
            writers.setdefault(item["path"], []).append(entry["delta_id"])

    # Журнал обязан быть закрыт. Незакрытый intent — файловая операция обрыва,
    # которую никто не подтвердил: если дельта выпала из состава после restart,
    # её след маскируется записью другой дельты в тот же файл, а text-проверка
    # пропускает id вне нового ledger (kimi M1, 30.07). Именованный блокер
    # вместо тишины; в зелёных потоках apply закрывает или удаляет свои intent.
    for entry in entries:
        if entry.get("stage") != "done":
            discrepancies.append(violation(
                "journal_incomplete",
                "журнал apply содержит незакрытую запись — файловая операция обрыва не подтверждена",
                field=(entry.get("files") or [{}])[0].get("path"),
                delta_ids=[entry.get("delta_id")]))

    # (а)+(б) применённые файлы: текст на месте, посторонних правок нет.
    # Hash сверяется с ФИНАЛЬНОЙ журнальной записью файла: несколько дельт в один
    # файл — штатный случай, промежуточные hash_after неактуальны по построению
    # (живой смоук 29.07: ложный applied_file_changed на второй дельте файла).
    for path_rel, expected in touched.items():
        current = file_hash_or_none(base / path_rel)
        if current is None:
            discrepancies.append(violation("applied_file_missing", "применённый файл исчез",
                                           field=path_rel, delta_ids=writers[path_rel]))
        elif current != expected:
            discrepancies.append(violation("applied_file_changed",
                                           "применённый файл изменён после apply (посторонняя правка)",
                                           field=path_rel, delta_ids=writers[path_rel]))
    for entry in entries:
        delta = ledger.get(entry["delta_id"])
        if not delta or delta["operation"] == "delete":
            continue
        if not text_present(base, delta):
            discrepancies.append(violation("applied_text_missing", "текста дельты нет в целевом файле",
                                           field=delta["target_file"], delta_ids=[entry["delta_id"]]))
            continue
        # move проверяется с обеих сторон: перенесённый текст в target есть,
        # якорь из source исчез. Половина move — расхождение, а не успех.
        if delta["operation"] == "move" and not source_anchor_removed(base, delta):
            discrepancies.append(violation("moved_source_not_cut",
                                           "перенос не завершён: фрагмент остался в файле-источнике",
                                           field=delta.get("source_file"),
                                           delta_ids=[entry["delta_id"]]))

    published = {item["path"] for item in state["side_effects"]["published"]}
    # (в) всё, что вне applied-set и публикаций, не изменилось против пре-снимка.
    current_files = base_snapshot(base)

    def _rel(raw: str) -> Optional[str]:
        try:
            return str(Path(raw).relative_to(base))
        except ValueError:
            return None

    allowed = set(touched) | {str(Path(p).relative_to(base)) for p in published}
    # (д) роль вторая: членство keep-путей в allowed-set — по append-only
    # `side_effects.kept`, независимо от scope и перезаписи слота новой волей.
    # Пользователь легитимировал присутствие файла; ни rework, ни новое решение
    # эту легитимацию не отзывают (иначе исторический keep-файл вне пре-снимка
    # давал бы тупиковый `foreign_file_created` после точки невозврата).
    for item in state["side_effects"].get("kept") or []:
        rel = _rel(item["path"])
        if rel:
            allowed.add(rel)
    # Пути `from` журнальных записей, достигших unlink, освобождаются от
    # `foreign_file_removed` — и только от него, и только при подтверждённом
    # lstat → ENOENT: любой существующий объект на таком пути остаётся расхождением.
    freed: set = set()
    for record in state["side_effects"].get("replaced") or []:
        reached = (record["stage"] in ("unlinked", "done")
                   or (record["stage"] == "aborted"
                       and record.get("aborted_from_stage") == "unlinked"))
        if not reached:
            continue
        rel = _rel(record["from"])
        if rel and observe_target(Path(record["from"]))["class"] == "absent":
            freed.add(rel)
    for rel, digest in sorted(current_files.items()):
        if rel in allowed:
            continue
        if rel not in snapshot:
            discrepancies.append(violation("foreign_file_created", "в базе появился посторонний файл", field=rel))
        elif snapshot[rel] != digest:
            discrepancies.append(violation("foreign_file_changed", "файл вне applied-set изменён", field=rel))
    for rel in sorted(snapshot):
        if rel not in current_files and rel not in allowed and rel not in freed:
            discrepancies.append(violation("foreign_file_removed", "файл вне applied-set исчез", field=rel))

    # (г) протокол и выжимка на диске — и именно в базе, а не по symlink наружу.
    for item in state["side_effects"]["published"]:
        path = Path(item["path"])
        if path.is_symlink():
            discrepancies.append(violation("publication_symlink", "публикация подменена symlink'ом",
                                           field=item["path"]))
            continue
        if not path.is_file():
            discrepancies.append(violation("publication_missing", "публикация исчезла", field=item["path"]))
            continue
        try:
            ensure_inside_base(path, base, "публикация")
        except SpineError as exc:
            discrepancies.append(violation("publication_outside_base", exc.message, field=item["path"]))
            continue
        # Наличия мало: «опубликовано» значит «в файле ровно опубликованный текст».
        if item.get("hash") and sha256_file(path) != item["hash"]:
            discrepancies.append(violation("publication_changed",
                                           "публикация изменена после apply — в файле не тот текст",
                                           field=item["path"]))
    # (д) роль первая — hash-сверка исполненных keep со совпавшим scope (B№4 §5).
    # Исторические резолюции после rework не проверяются: авторитет — hash решения,
    # не пре-снимок (пользователь решал про конкретное содержимое).
    executed_keeps = [(kind, item) for kind, item
                      in sorted((state.get("publication_resolutions") or {}).items())
                      if item.get("choice") == "keep" and item.get("executed")]
    paths = publication_paths(state) if executed_keeps else {}
    # payload читается только когда есть что сверять со scope: постчек не обязан
    # падать на отсутствующем входе corrections там, где keep не исполнялся.
    payload_hash = (sha256_bytes(confirmed_summary_text(run).encode("utf-8"))
                    if executed_keeps else None)
    kept_in_scope: Dict[str, Dict[str, Any]] = {}
    for kind, resolution in executed_keeps:
        scope = resolution.get("scope") or {}
        target = paths.get(kind)
        if target is None or scope.get("path") != str(target) \
                or scope.get("payload_hash") != payload_hash:
            continue
        kept_in_scope[kind] = resolution
        path = Path(resolution["path"])
        if path.is_symlink():
            discrepancies.append(violation("kept_publication_symlink",
                                           "оставленный файл подменён symlink'ом",
                                           field=resolution["path"]))
            continue
        observed = observe_target(path)
        if observed["class"] == "absent":
            discrepancies.append(violation("kept_publication_missing",
                                           "оставленный файл исчез", field=resolution["path"]))
        elif observed["class"] == "unreadable":
            code = ("kept_publication_not_regular" if path.exists() and not path.is_file()
                    else "kept_publication_unreadable")
            discrepancies.append(violation(code, "оставленный файл не читается",
                                           field=resolution["path"]))
        elif observed["hash"] != resolution.get("existing_hash"):
            discrepancies.append(violation("kept_publication_changed",
                                           "оставленный файл изменён после решения",
                                           field=resolution["path"]))

    # (е) архивные копии: обещание «старый перенесу в архив» проверяемо по журналу
    # (`zz_archive/` вне снимка by design). Vanished-замены (`to: null`) не в счёт.
    for record in state["side_effects"].get("replaced") or []:
        if not record.get("to"):
            continue
        confirmed = (record["stage"] in ("done", "archived", "unlinked")
                     or (record["stage"] == "aborted"
                         and record.get("aborted_from_stage") in ("archived", "unlinked")))
        if not confirmed:
            continue
        copy = confined_or_none(Path(record["to"]), base, "архивная копия")
        if copy is None:
            discrepancies.append(violation("archive_copy_missing",
                                           "архивная копия недостижима внутри базы",
                                           field=record["to"]))
            continue
        observed = observe_target(copy)
        if observed["class"] != "regular":
            discrepancies.append(violation("archive_copy_missing",
                                           "архивной копии заменённого файла нет",
                                           field=record["to"]))
        elif observed["hash"] != record.get("hash"):
            discrepancies.append(violation("archive_copy_changed",
                                           "архивная копия не совпадает с заменённым файлом",
                                           field=record["to"]))
    # Гейт журнала замен: все пути apply обязаны его терминализовать.
    for record in state["side_effects"].get("replaced") or []:
        if record["stage"] not in ("done", "aborted"):
            discrepancies.append(violation(
                "replace_journal_incomplete",
                "журнал замены публикации не закрыт — операция обрыва не подтверждена",
                field=record["from"]))

    if state["context"]["protocol_required"] and not any(
            item["kind"] == "protocol" for item in state["side_effects"]["published"]) \
            and "protocol" not in kept_in_scope:
        # Исключение: исполненный `keep` со совпавшим scope делает отсутствие
        # публикации решением пользователя; историческая резолюция — не делает.
        discrepancies.append(violation("protocol_missing", "протокол не опубликован", field="protocol_required"))

    report = {
        "ok": not discrepancies,
        "checked_files": len(current_files),
        "applied_files": sorted(touched),
        "published": sorted(published),
        "discrepancies": discrepancies,
    }
    digest = write_json_artifact(run.path(ART_POSTCHECK), report)
    state["postcheck"] = {"artifact": ART_POSTCHECK, "hash": digest, "ok": not discrepancies}

    if discrepancies:
        raise fail_run(
            run, "postcheck", "postcheck_discrepancy",
            "postcheck нашёл расхождения — авто-правок нет, решение пользователя",
            "Расхождений: {}\n\n".format(len(discrepancies)) + "\n".join(
                "- [{}] {}".format(d["code"], d.get("field")) for d in discrepancies),
            violations=discrepancies,
        )

    return report


def perform_postcheck(run: Run) -> Tuple[Dict[str, Any], List[str]]:
    """Фаза postcheck: сверка + переход к deliver/finalize. Вызывается командой
    `postcheck` (живой путь) и автосцепкой в конце `apply`."""
    state = run.state
    require_phase(state, "postcheck")
    report = postcheck_report(run)
    digest = state["postcheck"]["hash"]

    required = bool(state["context"].get("deliver_required"))
    state["deliver"]["required"] = required
    # Вход deliver собирается всегда (restart-from deliver легален и после
    # not_required) и ДО mark_validated — обрыв записи не оставит
    # validated-постчек без входа узла (связка B5: kimi M2/L4, Codex M4).
    decisions = build_deliver_decisions(run)
    decisions_hash = write_json_artifact(run.path(ART_DELIVER_INPUT), decisions)
    state["deliver"]["decisions"] = {"path": ART_DELIVER_INPUT, "hash": decisions_hash}
    mark_validated(state, "postcheck", ART_POSTCHECK, digest)
    if required:
        set_phase(state, "deliver")
    else:
        state["phases"]["deliver"].update({"status": "validated", "decision": "not_required",
                                           "updated_at": now_iso()})
        state["deliver"]["decision"] = "not_required"
        set_phase(state, "finalize")
    log_event(state, "postcheck")
    save_state(run.run_dir, state)

    payload = status_payload(run)
    payload["postcheck"] = report
    lines = [
        "postcheck чист: проверено файлов {}".format(report["checked_files"]),
        "Фаза: {}".format(state["phase"]),
    ]
    return payload, lines


# --------------------------------------------------------------------------- #
# deliver / finalize
# --------------------------------------------------------------------------- #

def submit_deliver(args: argparse.Namespace, run: Run) -> Tuple[Dict[str, Any], List[str]]:
    state = run.state
    require_phase(state, "deliver")
    parse_meta(args.meta, "deliver")
    if bool(args.artifact) == bool(args.skip):
        raise SpineError("bad_usage", "нужен ровно один из: --artifact <файл> либо --skip", exit_code=2)

    if args.skip:
        state["phases"]["deliver"].update({"status": "validated", "decision": "skip", "updated_at": now_iso()})
        state["deliver"].update({"decision": "skip", "artifact": None, "hash": None})
        set_phase(state, "finalize")
        log_event(state, "submit:deliver", detail="skip")
        save_state(run.run_dir, state)
        payload = status_payload(run)
        payload["decision"] = "skip"
        return payload, ["Отправка пропущена — решение пользователя зафиксировано", "Фаза: finalize"]

    # Fail-fast: артефакт узла без честного входа — молчаливая регрессия к
    # «плану из одной выжимки» (связка B5: kimi M2). Вход обязан существовать
    # и совпадать с hash постчека.
    record = state["deliver"].get("decisions")
    if not record or not (run.run_dir / record["path"]).is_file() \
            or artifact_hash(run.run_dir / record["path"]) != record["hash"]:
        raise SpineError(
            "deliver_input_missing",
            "нарушен precondition deliver_input: вход decisions отсутствует или подменён — "
            "повтори `postcheck` (restart-from --phase postcheck)",
        )

    path = require_artifact(args, run)
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise SpineError("deliver_empty", "текст отправки пуст",
                         violations=[violation("deliver_empty", "пустой артефакт", field="--artifact")])
    digest = artifact_hash(path)
    mark_validated(state, "deliver", rel_to_run(path, run.run_dir), digest, decision="artifact")
    state["deliver"].update({"decision": "artifact", "artifact": rel_to_run(path, run.run_dir), "hash": digest})
    set_phase(state, "finalize")
    log_event(state, "submit:deliver", detail="artifact")
    save_state(run.run_dir, state)

    payload = status_payload(run)
    payload["decision"] = "artifact"
    payload["artifact_hash"] = digest
    return payload, ["Текст отправки принят ({} симв.)".format(len(text)),
                     "Показывай: show deliver · отправка — вне spine", "Фаза: finalize"]


def archive_target(protocol_dir: Path, date: str, topic: str) -> Path:
    archive = protocol_dir / ARCHIVE_DIRNAME
    stem = "{}_{}_transcript".format(date, topic)
    candidate = archive / (stem + ".md")
    suffix = 2
    while candidate.exists():
        candidate = archive / "{}-{}.md".format(stem, suffix)
        suffix += 1
    return candidate


def cmd_finalize(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    run = require_run(args)
    state = run.state
    require_phase(state, "finalize")
    if state["phases"]["postcheck"]["status"] != "validated":
        raise SpineError("precondition_postcheck", "нарушен precondition postcheck_ok: postcheck не пройден")
    if state["context"].get("deliver_required") and state["deliver"]["decision"] not in ("artifact", "skip"):
        raise SpineError(
            "deliver_required",
            "нарушен precondition deliver_decided: фаза deliver обязательна — подай артефакт либо --skip",
        )

    transcript = Path(state["immutable"]["transcript_path"])
    base = Path(state["base_path"])
    # Между apply и finalize каталог протоколов тоже могли подменить — сверяем заново.
    protocol_dir = ensure_inside_base(Path(state["context"]["protocol_dir"]), base, "protocol_dir")
    date, topic = state["immutable"]["date"], state["immutable"]["topic"]
    archived = list(state["side_effects"]["archived"])

    if not archived:
        if not transcript.is_file():
            raise SpineError("transcript_missing", "транскрипт исчез — архивировать нечего")
        target = archive_target(protocol_dir, date, topic)
        ensure_not_strategic(target, base, "архив транскрипта")
        mkdir_inside_base(target.parent, base, "каталог архива")
        target = ensure_inside_base(target, base, "архив транскрипта")
        inside_base = base == transcript.parent or base in transcript.parents
        payload_bytes = transcript.read_bytes()
        fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        if inside_base:
            transcript.unlink()
        archived.append({
            "path": str(target),
            "source": str(transcript),
            "mode": "move" if inside_base else "copy",
            "hash": sha256_bytes(payload_bytes),
        })

    state["side_effects"]["archived"] = archived
    mark_validated(state, "finalize")
    state["status"] = "done"
    state["phase_status"] = "validated"
    log_event(state, "finalize")
    save_state(run.run_dir, state)
    release_lock(run.base_dir, state["run_id"])

    payload = status_payload(run)
    payload["archived"] = archived
    lines = [
        "Run завершён: {}".format(state["run_id"]),
        "Транскрипт в архиве: {} ({})".format(archived[0]["path"], archived[0]["mode"]),
    ]
    return payload, lines


SUBMITTERS = {
    "locate": submit_locate,
    "l1": submit_l1,
    "confirm": submit_confirm,
    "deltas": submit_deltas,
    "canon": submit_canon,
    "review": submit_review,
    "questions": submit_questions,
    "deliver": submit_deliver,
}


def cmd_submit(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    phase = args.phase
    if phase not in phase_names():
        raise SpineError("unknown_phase", "неизвестная фаза: {}".format(phase), exit_code=2)
    if phase not in SUBMITTERS:
        raise SpineError("phase_not_submittable",
                         "фаза {} не принимает артефакт — это команда spine".format(phase), exit_code=2)
    require_implemented(phase)
    run = require_run(args)
    return SUBMITTERS[phase](args, run)


# --------------------------------------------------------------------------- #
# show / slice
# --------------------------------------------------------------------------- #

# Экран 1, находка №14 живого прогона №2: пользователю нужен показ всех
# извлечённых сущностей компактно (решение Эрика 30.07; «под кат» в терминале
# невозможен). Источник — сама выжимка: ростер на confirm ещё не существует
# (его строит узел build-deltas в фазе deltas).
SUMMARY_ENTITIES_HEADER = "## Извлечённые сущности"
_OWNER_BLOCK = re.compile(r"^\[(?P<owner>[^\]]+)\]:\s*$")
_CHECKBOX = re.compile(r"^\[[ xX]\]\s+")


def summary_entity_digest(text: str) -> List[Tuple[str, List[str]]]:
    """Компактный список сущностей выжимки: по типам, одна строка на сущность.

    Читается каноническая секция `## Извлечённые сущности` (шаблон узла
    extract-entities): тип — `### `-подзаголовок, сущность — первая строка
    `- `-пункта без чекбокса и без хвоста «Опора: …»; owner-блоки задач
    (`[Имя]:`) дают пометку « — {имя}». Выжимка без канонической секции →
    пустой список, экран остаётся без блока: компактный показ — представление,
    а не гейт формата l1 (structural-гейт summary_invalid живёт в submit).
    """
    groups: List[Tuple[str, List[str]]] = []
    in_section = False
    current_type: Optional[str] = None
    current_owner: Optional[str] = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip() == SUMMARY_ENTITIES_HEADER:
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith("## "):
            break
        if line.startswith("### "):
            # Пустой заголовок типа → подраздел игнорируется целиком (None
            # закрывает и предыдущий тип: чужие пункты в него не утекают).
            current_type = line[4:].strip() or None
            current_owner = None
            if current_type:
                groups.append((current_type, []))
            continue
        if current_type is None:
            continue
        owner_match = _OWNER_BLOCK.match(line)
        if owner_match:
            current_owner = owner_match.group("owner").strip()
            continue
        if not line.startswith("- "):
            # Продолжения пункта (опоры, вложенные спецификации) — не сущности.
            continue
        body = _CHECKBOX.sub("", line[2:].strip())
        cut = body.find("Опора:")
        if cut != -1:
            body = body[:cut].rstrip(" \t·—-").rstrip(".")
        if current_owner:
            body = "{} — {}".format(body, current_owner)
        if body:
            groups[-1][1].append(body)
    return [(title, items) for title, items in groups if items]


def render_entity_digest(digest: List[Tuple[str, List[str]]]) -> List[str]:
    lines = ["Кратко — все сущности из выжимки:", ""]
    for title, items in digest:
        lines.append("{}:".format(title))
        lines += ["- {}".format(item) for item in items]
        lines.append("")
    return lines[:-1]


def show_summary(run: Run) -> Tuple[Dict[str, Any], List[str]]:
    state = run.state
    record = state["phases"]["l1"]
    if record["status"] != "validated" or not record["artifact"]:
        raise SpineError("summary_not_ready", "нарушен precondition l1_validated: выжимки ещё нет")
    path = run.run_dir / record["artifact"]
    if not path.is_file():
        raise SpineError("artifact_missing", "артефакт выжимки исчез: {}".format(path))
    digest = artifact_hash(path)
    if digest != record["artifact_hash"]:
        raise SpineError(
            "artifact_hash_mismatch",
            "выжимка изменена после submit — покажи актуальную через restart-from l1",
        )

    content = path.read_text(encoding="utf-8")
    # Форма решения — имена команд и путь run-каталога: техника, не язык экрана.
    form = [
        "— Форма решения пользователя —",
        "Принять:   submit confirm --approved [--corrections <файл в run-каталоге>]",
        "Отклонить: submit confirm --rejected --corrections <файл в run-каталоге>",
    ]
    business = business_block(business_stage("confirm"), BUSINESS_SCREENS["confirm"])
    # Компактный блок сущностей (№14) — в обоих режимах, ближе к вопросу
    # пользователя: полный текст выжимки выше, краткий индекс — перед say.
    entity_digest = summary_entity_digest(content)
    payload = {
        "ok": True,
        "run_id": state["run_id"],
        "phase": state["phase"],
        "artifact": record["artifact"],
        "artifact_hash": digest,
        "summary": content,
        "entities_compact": [{"type": title, "items": items} for title, items in entity_digest],
        "corrections_form": form,
        "business": business,
    }
    lines = [content.rstrip("\n")]
    if entity_digest:
        lines += [""] + render_entity_digest(entity_digest)
    lines += ["", business["say"]]
    if is_debug(state):
        lines += [""] + form + ["Артефакт: {} · hash {}".format(path, digest)]
    return payload, lines


def show_deliver(run: Run) -> Tuple[Dict[str, Any], List[str]]:
    state = run.state
    record = state["deliver"]
    if record["decision"] != "artifact" or not record["artifact"]:
        raise SpineError("deliver_not_ready", "нарушен precondition deliver_submitted: текста отправки нет")
    path = run.run_dir / record["artifact"]
    if not path.is_file():
        raise SpineError("artifact_missing", "артефакт отправки исчез: {}".format(path))
    if artifact_hash(path) != record["hash"]:
        raise SpineError("artifact_hash_mismatch", "текст отправки изменён после submit")
    content = path.read_text(encoding="utf-8")
    # Экран 3: say живёт здесь, а не в `next` фазы deliver — там текста сводки
    # ещё нет. Отправка вне spine, поэтому вопрос один: отправляем?
    business = business_block(business_stage("deliver"), BUSINESS_SCREENS["deliver"])
    payload = {
        "ok": True,
        "run_id": state["run_id"],
        "phase": state["phase"],
        "artifact": record["artifact"],
        "artifact_hash": record["hash"],
        "deliver": content,
        "business": business,
    }
    lines = [content.rstrip("\n"), "", business["say"]]
    if is_debug(state):
        lines += ["", "Артефакт: {} · hash {}".format(path, record["hash"])]
    return payload, lines


def cmd_show(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    run = require_run(args)
    if args.what == "summary":
        return show_summary(run)
    return show_deliver(run)


def slice_head(text: str) -> Tuple[str, bool]:
    """Вывод до первого заголовка `## `; frontmatter и H1 включаются."""
    lines = text.splitlines(keepends=True)
    out: List[str] = []
    idx = 0
    if lines and lines[0].strip() == "---":
        out.append(lines[0])
        idx = 1
        while idx < len(lines):
            out.append(lines[idx])
            closed = lines[idx].strip() == "---"
            idx += 1
            if closed:
                break
    in_fence = False
    truncated = False
    while idx < len(lines):
        line = lines[idx]
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            truncated = True
            break
        out.append(line)
        idx += 1
    return "".join(out), truncated


def cmd_slice(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[str]]:
    base = resolve_base(args.base)
    path = resolve_within(args.file, base, "--file", "корня базы")
    if not path.is_file():
        raise SpineError("file_missing", "файл не найден: {}".format(path))
    content, truncated = slice_head(path.read_text(encoding="utf-8"))
    payload = {"ok": True, "file": str(path), "truncated": truncated, "content": content}
    return payload, [content.rstrip("\n")]


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

HANDLERS = {
    "start": cmd_start,
    "status": cmd_status,
    "debug": cmd_debug,
    "list": cmd_list,
    "next": cmd_next,
    "resume": cmd_resume,
    "abandon": cmd_abandon,
    "restart-from": cmd_restart_from,
    "submit": cmd_submit,
    "export-review": cmd_export_review,
    "compose": cmd_compose,
    "accept": cmd_accept,
    "apply": cmd_apply,
    "resolve-publications": cmd_resolve_publications,
    "postcheck": cmd_postcheck,
    "finalize": cmd_finalize,
    "show": cmd_show,
    "slice": cmd_slice,
}


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base", default=argparse.SUPPRESS, help="корень базы (по умолчанию — текущий каталог)")
    common.add_argument("--run", default=argparse.SUPPRESS, help="run_id вместо активного run")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="машинный вывод")

    parser = argparse.ArgumentParser(
        prog="meeting_spine.py",
        parents=[common],
        description="Spine пайплайна meeting-analysis (start → … → finalize)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", parents=[common], help="начать run по транскрипту")
    start.add_argument("--transcript", required=True)
    start.add_argument("--debug", action="store_true",
                       help="технический режим показа с первого шага (дефолт — бизнес-вид)")

    sub.add_parser("status", parents=[common], help="состояние активного run")

    debug_cmd = sub.add_parser("debug", parents=[common],
                               help="переключить режим показа (доступно и на HITL-паузах)")
    debug_cmd.add_argument("--on", action="store_true")
    debug_cmd.add_argument("--off", action="store_true")
    sub.add_parser("list", parents=[common], help="runs по базе")
    sub.add_parser("next", parents=[common], help="манифест следующего шага")
    sub.add_parser("resume", parents=[common], help="состояние + перепроверка hash'ей на диске")
    sub.add_parser("abandon", parents=[common], help="прекратить run")
    sub.add_parser("export-review", parents=[common], help="нарезать пакеты ревьюеров")
    compose_cmd = sub.add_parser("compose", parents=[common], help="рендер решений пользователю")
    compose_cmd.add_argument("--expand", action="append", default=[],
                             help="читающий режим: полные тексты пунктов (№ через запятую | all)")
    sub.add_parser("apply", parents=[common], help="применить принятое в базу")

    resolve = sub.add_parser("resolve-publications", parents=[common],
                             help="решение пользователя по занятому пути публикации")
    resolve.add_argument("--replace", action="append", default=[],
                         help="kind (summary|protocol): старый файл в архив, публикуем свежий")
    resolve.add_argument("--keep", action="append", default=[],
                         help="kind (summary|protocol): оставить существующий файл")
    postcheck_cmd = sub.add_parser("postcheck", parents=[common],
                                   help="сверка применённого с ledger")
    postcheck_cmd.add_argument("--recheck", action="store_true",
                               help="повторная сверка базы без фазовых переходов")
    sub.add_parser("finalize", parents=[common], help="архив транскрипта и завершение run")

    restart = sub.add_parser("restart-from", parents=[common], help="рестарт с фазы, каскадная инвалидация")
    restart.add_argument("--phase", required=True)

    submit = sub.add_parser("submit", parents=[common], help="приём артефакта или решения фазы")
    submit.add_argument("phase")
    submit.add_argument("--artifact")
    submit.add_argument("--meta", action="append", default=[])
    submit.add_argument("--approved", action="store_true")
    submit.add_argument("--rejected", action="store_true")
    submit.add_argument("--corrections")
    submit.add_argument("--package")
    submit.add_argument("--verdict")
    submit.add_argument("--skip", action="store_true")

    accept = sub.add_parser("accept", parents=[common], help="партиция решений пользователя")
    accept.add_argument("--take", action="append", default=[])
    accept.add_argument("--reject", action="append", default=[])
    # Подмножество --reject: «отклоняю как уже идущее» (дубль существующей
    # записи, работа уже в базе). Авторитетная причина пользователя для
    # deliver-плана — узел не гадает по тексту ревью (Codex B5, High).
    accept.add_argument("--already", action="append", default=[])
    accept.add_argument("--amend", action="append", default=[])
    accept.add_argument("--meta", action="append", default=[])
    # Волна G: ответ на вопрос экрана — линза над номерами; разворачивание в
    # партицию делает код cmd_accept, не пересказ координатора.
    accept.add_argument("--answer", action="append", default=[],
                        help="ответ на вопрос экрана: <q>=<опция|default>")

    show = sub.add_parser("show", parents=[common], help="рендер для показа пользователю")
    show.add_argument("what", choices=["summary", "deliver"])

    slice_cmd = sub.add_parser("slice", parents=[common], help="срез файла до первого `## `")
    slice_cmd.add_argument("--file", required=True)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.json = getattr(args, "json", False)
    args.base = getattr(args, "base", None)
    args.run = getattr(args, "run", None)

    try:
        payload, lines = HANDLERS[args.command](args)
    except SpineError as exc:
        return emit_error(args, exc)
    except OSError as exc:
        return emit_error(args, SpineError("io_error", str(exc), exit_code=2))
    emit(args, payload, lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
