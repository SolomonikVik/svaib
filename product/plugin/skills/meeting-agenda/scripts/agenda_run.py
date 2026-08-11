#!/usr/bin/env python3
"""agenda_run.py — драйвер прогона повестки: состояние, маркеры, доставка.

Единственный владелец state.json и принятых артефактов.

Цепочка восьми обязательных переходов:
    object_resolved → sources_collected → metrics_resolved → drafted
    → validated → rendered → previewed_ack → delivered

ДВА ПРАВИЛА, БЕЗ КОТОРЫХ ЦЕПОЧКА — ЖУРНАЛ, А НЕ МЕХАНИЗМ (найдено ревью 31.07):

1. **Принятый артефакт копируется в run-каталог и дальше используется только
   копия.** Иначе файл можно перезаписать после `submit`, и вся цепочка ниже
   продолжит опираться на hash версии, которой уже нет на диске.

2. **Маркер ставится за исполнение шага, а не за существование файла.**
   Входящие артефакты проверяются на предметные признаки своего шага, а
   детерминированные шаги (`validated`, `rendered`) драйвер исполняет сам из
   принятой копии — подать под их видом посторонний файл нельзя.

Доставка — команда драйвера: `deliver` сверяет hash отправляемого текста с
показанным и ставит `delivered` только при нулевом коде возврата канала.

ЧЕГО ЗДЕСЬ НЕТ НАМЕРЕННО: промптов LLM-узлов, счётчика попыток починки и
rework-фазы. Починка после провала валидации — повторный `submit drafted`,
а не состояние драйвера.

Коды возврата: 0 — ок; 1 — ожидаемое нарушение порядка или контракта;
2 — usage/IO/внутренняя ошибка.

Stdlib-only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import collect_sources as sources_lib  # noqa: E402  — владелец чек-листа и индекса встреч
import metrics_gateway as gateway  # noqa: E402  — шов к вертикали metrics
import render_agenda as render_lib  # noqa: E402  — лежит рядом, путь добавлен выше
import resolve_object as resolver  # noqa: E402  — валидация выбора объекта
import validate_agenda as form  # noqa: E402  — библиотека инвариантов формы

STATE_SCHEMA_FILE = SKILL_ROOT / "schema" / "run-state.schema.json"

STATE_SCHEMA_VERSION = 1
HISTORY_LIMIT = 200
ACCEPTED_DIR = "accepted"

STEP_ORDER: Tuple[str, ...] = (
    "object_resolved",
    "sources_collected",
    "metrics_resolved",
    "drafted",
    "validated",
    "rendered",
    "previewed_ack",
    "delivered",
)

# Единственный шаг, чей артефакт приходит извне, — черновик LLM. Всё
# детерминированное драйвер производит сам: пока `sources`, `metrics` и выбор
# объекта принимались снаружи, согласованный на вид подлог проходил цепочку до
# доставки, ни разу не запустив collector, gateway и резолвер.
SUBMITTABLE: Tuple[str, ...] = ("drafted",)

ACCEPTED_NAME = {
    "object_resolved": "object.json",
    "sources_collected": "sources.json",
    "metrics_resolved": "metrics.json",
    "drafted": "agenda.json",
    "validated": "validation.json",
    "rendered": "agenda.txt",
    "delivered": "delivery.json",
}

STEP_HINT = {
    "object_resolved": "построй карту мест (`resolve_object.py map`) и назови объект: `resolve --object <путь> --kind node|goal|person`",
    "sources_collected": "команда `collect` — драйвер соберёт чек-лист источников и индекс встреч сам",
    "metrics_resolved": "команда `metrics` — драйвер получит перечень метрик объекта сам",
    "drafted": "прогони каталог проверок, напиши черновик, влей машинные поля (`assemble_agenda.py`)",
    "validated": "команда `validate` — драйвер проверит форму сам",
    "rendered": "команда `render` — драйвер отрендерит сам",
    "previewed_ack": "покажи повестку человеку и подтверди показ командой `ack`",
    "delivered": "команда `deliver` — прямой вызов канала в обход драйвера запрещён",
}

TELEGRAM_ENV = "SVAIB_TELEGRAM_SCRIPT"

#: Порядок предпочтения канала доставки: rich первым. Константа, а не список
#: внутри функции, потому что на неё опирается генератор манифестов кластера —
#: он задаёт путь явным флагом, и разъезд двух мест переводит боевую повестку
#: на плоский канал молча.
CHANNEL_PREFERENCE = ("send_telegram_rich.sh", "send_telegram.sh")


class RunError(Exception):
    def __init__(self, code: str, message: str, exit_code: int = 1, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code
        self.payload = payload or {}


# --------------------------------------------------------------------------- #
# Расположение run-каталога
# --------------------------------------------------------------------------- #


def default_runs_root() -> Path:
    """Платформенный state-каталог для run-артефактов.

    ТРЕТИЙ экземпляр резолвера (первые два — в скилле meeting-analysis). Общей
    библиотеки быть не может: гейт изоляции требует, чтобы пакет скилла был
    самодостаточен, а межскилловый импорт эту самодостаточность ломает.
    Эквивалентность трёх копий держится не комментарием, а общими test vectors.
    """
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "")
        root = Path(local) if local and Path(local).is_absolute() else Path.home() / "AppData" / "Local"
        return root / "svaib" / "runs"
    xdg = os.environ.get("XDG_STATE_HOME", "")
    root = Path(xdg) if xdg and Path(xdg).is_absolute() else Path.home() / ".local" / "state"
    return root / "svaib" / "runs"


def runs_root() -> Path:
    env = os.environ.get("SVAIB_RUNS_DIR", "")
    base = Path(env) if env else default_runs_root()
    # Подкаталог обязателен: у meeting-analysis корень — <runs_root>/<base_id>/,
    # и класть свои run в то же пространство значит ломать его list/resume.
    return base / "agenda"


def base_id_of(base: Path) -> str:
    return hashlib.sha256(str(base).encode("utf-8")).hexdigest()[:12]


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Хеши и запись
# --------------------------------------------------------------------------- #


def artifact_hash(path: Path) -> str:
    """Hash артефакта: для .json — канонический hash содержимого, иначе байты."""
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(str(tmp), str(path))


# --------------------------------------------------------------------------- #
# Предметная проверка входящих артефактов
# --------------------------------------------------------------------------- #


def require_keys(payload: Any, keys: Tuple[str, ...], step: str) -> None:
    if not isinstance(payload, dict):
        raise RunError("artifact_shape", "артефакт шага «{0}» — не объект JSON".format(step))
    missing = [k for k in keys if k not in payload]
    if missing:
        raise RunError(
            "artifact_shape",
            "артефакт шага «{0}» не похож на результат этого шага: нет полей {1}".format(step, ", ".join(missing)),
            payload={"missing": missing},
        )


def check_agenda(payload: Any) -> None:
    require_keys(payload, ("meeting", "frame", "metrics", "tasks", "focus", "questions", "flags"), "drafted")


ARTIFACT_CHECKS: Dict[str, Callable[[Any], None]] = {
    "drafted": check_agenda,
}


# --------------------------------------------------------------------------- #
# Состояние
# --------------------------------------------------------------------------- #


def empty_steps() -> Dict[str, Any]:
    return {name: {"status": "pending", "artifact": None, "artifact_hash": None,
                   "input_hash": None, "updated_at": None, "meta": None} for name in STEP_ORDER}


def new_state(base: Path, run_id: str, phrase: Optional[str]) -> Dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "run_id": run_id,
        "base_id": base_id_of(base),
        "base_path": str(base),
        "created_at": now(),
        "updated_at": now(),
        "status": "active",
        "phrase": phrase,
        "object": None,
        "steps": empty_steps(),
        "preview": None,
        "blockers": [],
        "history": [{"at": now(), "event": "start", "step": None, "detail": str(base)}],
    }


def run_dir(base: Path, run_id: str) -> Path:
    return runs_root() / base_id_of(base) / run_id


def accepted_path(base: Path, run_id: str, step: str) -> Path:
    return run_dir(base, run_id) / ACCEPTED_DIR / ACCEPTED_NAME[step]


def state_file(base: Path, run_id: str) -> Path:
    return run_dir(base, run_id) / "state.json"


def list_runs(base: Path) -> List[str]:
    root = runs_root() / base_id_of(base)
    if not root.is_dir():
        return []
    return sorted((p.name for p in root.iterdir() if (p / "state.json").is_file()), reverse=True)


def active_run(base: Path) -> Optional[str]:
    for run_id in list_runs(base):
        if load_state(base, run_id)["status"] == "active":
            return run_id
    return None


def load_state(base: Path, run_id: str) -> Dict[str, Any]:
    path = state_file(base, run_id)
    if not path.is_file():
        raise RunError("run_not_found", "прогона {0} нет для этой базы".format(run_id))
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(base: Path, state: Dict[str, Any]) -> None:
    state["updated_at"] = now()
    state["history"] = state["history"][-HISTORY_LIMIT:]
    check_state_schema(state)
    atomic_write(state_file(base, state["run_id"]), json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def check_state_schema(state: Dict[str, Any]) -> None:
    """Состояние обязано соответствовать схеме — иначе схема лишь документ.

    Находка приёмки Ф6: `run-state.schema.json` ехал клиенту, но ничего не
    держал. Правило без носителя — то же, что правило прозой; проверка ставится
    перед записью, чтобы битое состояние не попало на диск.
    """
    if not STATE_SCHEMA_FILE.is_file():
        return
    try:
        spec = json.loads(STATE_SCHEMA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    violations: List[Any] = []
    form.check_schema(state, spec, "", violations)
    if violations:
        raise RunError("state_schema_violation",
                       "внутренняя ошибка: состояние прогона не соответствует run-state.schema.json — {0}".format(
                           "; ".join(v.message for v in violations[:3])),
                       exit_code=2)


def log(state: Dict[str, Any], event: str, step: Optional[str] = None, detail: Optional[str] = None) -> None:
    state["history"].append({"at": now(), "event": event, "step": step, "detail": detail})


def accepted_text(state: Dict[str, Any], step: str) -> str:
    """Читает принятый ТЕКСТОВЫЙ артефакт и сверяет его hash с записанным.

    Без этой сверки существовало окно между `render` и `ack`: подменённый на
    диске текст становился «показанным» — `ack` хешировал уже подменённое, а
    `deliver` сверял с ним же. В канал уходило то, что не проходило ни
    валидации, ни рендера.
    """
    marker = state["steps"][step]
    path = Path(marker["artifact"])
    if not path.is_file():
        raise RunError("accepted_missing", "принятая копия шага «{0}» исчезла: {1}".format(step, path))
    if artifact_hash(path) != marker["artifact_hash"]:
        raise RunError("accepted_tampered", "принятая копия шага «{0}» изменена в обход драйвера".format(step))
    return path.read_text(encoding="utf-8")


def accepted_json(base: Path, state: Dict[str, Any], step: str) -> Dict[str, Any]:
    """Читает ПРИНЯТУЮ копию артефакта и сверяет её hash с записанным.

    Расхождение означает, что копию правили в обход драйвера, — тогда всё, что
    ниже по цепочке, опирается на несуществующую версию.
    """
    path = Path(state["steps"][step]["artifact"])
    if not path.is_file():
        raise RunError("accepted_missing", "принятая копия шага «{0}» исчезла: {1}".format(step, path))
    if artifact_hash(path) != state["steps"][step]["artifact_hash"]:
        raise RunError("accepted_tampered", "принятая копия шага «{0}» изменена в обход драйвера".format(step))
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Цепочка маркеров
# --------------------------------------------------------------------------- #


def input_hash_for(state: Dict[str, Any], step: str) -> str:
    idx = STEP_ORDER.index(step)
    parts = [state["steps"][name].get("artifact_hash") or "" for name in STEP_ORDER[:idx]]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def invalidate_after(state: Dict[str, Any], step: str) -> List[str]:
    idx = STEP_ORDER.index(step)
    dropped: List[str] = []
    for name in STEP_ORDER[idx + 1:]:
        if state["steps"][name]["status"] != "pending":
            dropped.append(name)
        state["steps"][name] = {"status": "pending", "artifact": None, "artifact_hash": None,
                                "input_hash": None, "updated_at": None, "meta": None}
    if dropped:
        state["preview"] = None
    return dropped


def mark_done(base: Path, state: Dict[str, Any], step: str, path: Path, meta: Optional[Dict[str, Any]] = None) -> List[str]:
    dropped = invalidate_after(state, step)
    state["steps"][step] = {
        "status": "done",
        "artifact": str(path),
        "artifact_hash": artifact_hash(path),
        "input_hash": input_hash_for(state, step),
        "updated_at": now(),
        "meta": meta,
    }
    return dropped


def next_step(state: Dict[str, Any]) -> Optional[str]:
    for name in STEP_ORDER:
        if state["steps"][name]["status"] != "done":
            return name
    return None


def require_ready(state: Dict[str, Any], step: str) -> None:
    idx = STEP_ORDER.index(step)
    missing = [n for n in STEP_ORDER[:idx] if state["steps"][n]["status"] != "done"]
    if missing:
        raise RunError(
            "step_out_of_order",
            "шаг «{0}» недоступен: не выполнены {1}".format(step, ", ".join(missing)),
            payload={"missing": missing},
        )


def require_chain_intact(state: Dict[str, Any], step: str) -> None:
    """Вход шага не изменился с момента, когда шаг был выполнен."""
    marker = state["steps"][step]
    if marker["status"] == "done" and marker.get("input_hash") != input_hash_for(state, step):
        raise RunError("chain_broken", "вход шага «{0}» изменился — шаг нужно выполнить заново".format(step))


# --------------------------------------------------------------------------- #
# Команды
# --------------------------------------------------------------------------- #


def cmd_start(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    if active_run(base):
        raise RunError("run_already_active", "для этой базы уже есть активный прогон — `status` или `abandon`")
    run_id = "{0}-{1}".format(datetime.now().strftime("%Y%m%d-%H%M%S"), uuid.uuid4().hex[:6])
    state = new_state(base, run_id, getattr(args, "phrase", None))
    save_state(base, state)
    return ({"ok": True, "run_id": run_id, "run_dir": str(run_dir(base, run_id))},
            ["Прогон начат: {0}".format(run_id), "Дальше — `next`."])


def cmd_next(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    state = load_state(base, resolve_run(args, base))
    step = next_step(state)
    if step is None:
        return {"ok": True, "done": True}, ["Все шаги пройдены."]
    command = {
        "object_resolved": "resolve --object <путь> --kind node|goal|person --date <ГГГГ-ММ-ДД> --type <тип>",
        "sources_collected": "collect",
        "metrics_resolved": "metrics",
        "drafted": "submit drafted --artifact <путь>",
        "validated": "validate",
        "rendered": "render",
        "previewed_ack": "ack",
        "delivered": "deliver",
    }[step]
    payload = {"ok": True, "step": step, "hint": STEP_HINT[step], "command": command}
    return payload, ["Шаг: {0}".format(step), STEP_HINT[step], "Команда: {0}".format(command)]


def cmd_submit(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    """Принимает внешний артефакт: проверяет предметно и КОПИРУЕТ в run-каталог."""
    state = load_state(base, resolve_run(args, base))
    step = args.step
    if step not in SUBMITTABLE:
        raise RunError("step_not_submittable",
                       "шаг «{0}» драйвер выполняет сам — команда `{1}`".format(
                           step, "validate" if step == "validated" else "render" if step == "rendered" else step))
    require_ready(state, step)

    path = Path(args.artifact).resolve()
    if not path.is_file():
        raise RunError("artifact_missing", "артефакта нет: {0}".format(path), exit_code=2)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RunError("artifact_broken", "артефакт не разобран как JSON: {0}".format(exc), exit_code=2)

    # Предметная проверка: маркер ставится за исполнение шага, а не за то,
    # что по указанному пути лежит какой-нибудь файл.
    ARTIFACT_CHECKS[step](payload)

    copy = accepted_path(base, state["run_id"], step)
    atomic_write(copy, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    dropped = mark_done(base, state, step, copy)
    log(state, "submit", step, "dropped: {0}".format(",".join(dropped)) if dropped else None)
    save_state(base, state)

    lines = ["Шаг «{0}» принят.".format(step)]
    if dropped:
        lines.append("Сброшены маркеры ниже по цепочке: {0}.".format(", ".join(dropped)))
    return {"ok": True, "step": step, "accepted": str(copy), "invalidated": dropped}, lines


def cmd_resolve(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    """Принимает ВЫБОР объекта, а не готовый артефакт: выбор валидирует код.

    Раньше сюда подавался json, и «объект» вида `ghost/not-in-base` проходил —
    дальше вся цепочка строилась вокруг места, которого в базе нет.
    """
    state = load_state(base, resolve_run(args, base))
    require_ready(state, "object_resolved")
    problems = resolver.validate_choice(base, args.object, args.kind)
    if problems:
        raise RunError("object_invalid", "; ".join(problems), payload={"problems": problems})

    payload = {"object_ref": args.object, "object_kind": args.kind,
               "date": args.date, "type": args.type}
    path = accepted_path(base, state["run_id"], "object_resolved")
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    dropped = mark_done(base, state, "object_resolved", path)
    state["object"] = {"object_ref": args.object, "object_kind": args.kind, "series_key": None,
                       "meeting_date": args.date, "meeting_type": args.type}
    log(state, "resolve", "object_resolved", args.object)
    save_state(base, state)
    lines = ["Объект встречи: {0} ({1}).".format(args.object, args.kind)]
    if dropped:
        lines.append("Сброшены маркеры ниже по цепочке: {0}.".format(", ".join(dropped)))
    return {"ok": True, "object_ref": args.object, "invalidated": dropped}, lines


def cmd_collect(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    """Драйвер собирает чек-лист САМ — manifest не принимается снаружи.

    Иначе провенанс проверяется по списку, который тот же автор и написал:
    достаточно объявить выдуманный путь прочитанным.
    """
    state = load_state(base, resolve_run(args, base))
    require_ready(state, "sources_collected")
    obj = accepted_json(base, state, "object_resolved")
    try:
        manifest = sources_lib.collect(base, obj["object_ref"], obj["object_kind"], obj.get("type"))
    except sources_lib.CollectError as exc:
        raise RunError(exc.code, exc.message)

    path = accepted_path(base, state["run_id"], "sources_collected")
    atomic_write(path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    mark_done(base, state, "sources_collected", path)
    if state.get("object") is not None:
        state["object"]["series_key"] = manifest.get("series_key")
    log(state, "collect", "sources_collected", None)
    save_state(base, state)
    return ({"ok": True, "sources": len(manifest["sources"]), "missing": len(manifest["missing"]),
             "series_key": manifest["series_key"]},
            ["Источников: {0} (нет или недоступны: {1})".format(len(manifest["sources"]), len(manifest["missing"])),
             "Серия: {0}".format(manifest["series_key"] or "не определена — свежесть по fallback")])


SNAPSHOT_ENV = "SVAIB_SNAPSHOT_DIR"


def snapshot_dir_of(args: argparse.Namespace) -> Optional[Path]:
    """Каталог снимка книг: флаг сильнее окружения, обоих может не быть.

    Через окружение — потому что путь задаёт среда исполнения (в кластере его
    знает манифест, не человек), а флаг оставлен для ручного прогона.
    """
    explicit = getattr(args, "snapshot_dir", None)
    if explicit:
        return Path(explicit)
    from_env = os.environ.get(SNAPSHOT_ENV, "")
    return Path(from_env) if from_env else None


def cmd_metrics(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    """Драйвер получает перечень метрик САМ — отчёт не принимается снаружи."""
    state = load_state(base, resolve_run(args, base))
    require_ready(state, "metrics_resolved")
    obj = accepted_json(base, state, "object_resolved")
    # Снимок книг метрик приходит извне прогона: в облаке его кладёт fetcher, в
    # интерактивной среде — агент. Нет снимка — вертикаль не зовётся, и это
    # штатный режим: перечень метрик строится, значения не выдумываются.
    snapshot_dir = snapshot_dir_of(args)
    try:
        report = gateway.build_report(
            base, obj["object_ref"], obj["object_kind"],
            snapshot_dir=snapshot_dir,
            meeting_date=obj.get("date"),
            # Артефакты обмена с вертикалью живут в run-каталоге прогона: по
            # ним потом разбирают, что именно было запрошено и что прочитано.
            work_dir=run_dir(base, state["run_id"]) / "metrics")
    except gateway.GatewayError as exc:
        raise RunError(exc.code, exc.message)

    path = accepted_path(base, state["run_id"], "metrics_resolved")
    atomic_write(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    mark_done(base, state, "metrics_resolved", path)
    log(state, "metrics", "metrics_resolved", None)
    save_state(base, state)
    return ({"ok": True, "metrics": len(report["metrics"]), "mode": report["mode"]},
            ["Метрик в перечне: {0}. Режим: {1}.".format(len(report["metrics"]), report["mode"])])


def cmd_validate(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    """Драйвер проверяет форму САМ — из принятых копий.

    Подать под видом валидации посторонний «зелёный» файл невозможно: отчёт
    производится здесь и связан с конкретной принятой agenda.
    """
    state = load_state(base, resolve_run(args, base))
    require_ready(state, "validated")
    agenda = accepted_json(base, state, "drafted")
    metrics_report = accepted_json(base, state, "metrics_resolved")
    manifest = accepted_json(base, state, "sources_collected")

    # Отчёт передаётся целиком, а не одним перечнем id: иначе оси и числа в
    # agenda.json не с чем сверить, и подделка «источник прочитан, значение
    # такое-то» проходит как истина.
    violations = form.validate(agenda, metrics_report.get("metric_ids"), manifest, metrics_report)
    report = {
        "ok": not violations,
        "agenda_hash": state["steps"]["drafted"]["artifact_hash"],
        "violations": [v.as_dict() for v in violations],
    }
    path = accepted_path(base, state["run_id"], "validated")
    atomic_write(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    if violations:
        # Маркер не ставится: провал валидации — не состояние драйвера, а повод
        # починить черновик и подать его заново.
        log(state, "validate_failed", "validated", "{0} нарушений".format(len(violations)))
        save_state(base, state)
        return ({"ok": False, "violations": report["violations"], "report": str(path)},
                ["Нарушений формы: {0}".format(len(violations))]
                + ["  · [{0}] {1} — {2}".format(v.code, v.field or "-", v.msg) for v in violations])

    mark_done(base, state, "validated", path)
    log(state, "validated", "validated", None)
    save_state(base, state)
    return {"ok": True, "report": str(path)}, ["Форма цела: нарушений нет."]


def cmd_render(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    """Драйвер рендерит САМ — из той же принятой agenda, что прошла валидацию."""
    state = load_state(base, resolve_run(args, base))
    require_ready(state, "rendered")
    require_chain_intact(state, "validated")
    agenda = accepted_json(base, state, "drafted")

    text = render_lib.render(agenda)
    violations = form.validate_text(text, render_lib.FOCUS_HEADING, args.limit)
    if violations:
        log(state, "render_overflow", "rendered", violations[0].msg)
        save_state(base, state)
        return ({"ok": False, "violations": [v.as_dict() for v in violations]},
                ["❌ {0}".format(violations[0].msg)])

    path = accepted_path(base, state["run_id"], "rendered")
    atomic_write(path, text)
    mark_done(base, state, "rendered", path,
              meta={"chars_visible": form.visible_length(
                  form.screen_head(text, render_lib.FOCUS_HEADING))})
    log(state, "rendered", "rendered", None)
    save_state(base, state)
    return ({"ok": True, "text": text, "path": str(path)}, [text])


def cmd_ack(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    """Маркер показа. Доказывает, что переход выполнен, — не что человек прочитал."""
    state = load_state(base, resolve_run(args, base))
    require_ready(state, "previewed_ack")
    require_chain_intact(state, "rendered")
    text = accepted_text(state, "rendered")
    state["preview"] = {"shown_at": now(), "text_hash": text_hash(text), "skipped": bool(args.skip_preview)}
    state["steps"]["previewed_ack"] = {
        "status": "done", "artifact": None, "artifact_hash": state["preview"]["text_hash"],
        "input_hash": input_hash_for(state, "previewed_ack"), "updated_at": now(),
        "meta": {"skipped": bool(args.skip_preview)},
    }
    log(state, "ack", "previewed_ack", "skipped" if args.skip_preview else "shown")
    save_state(base, state)
    lines = ["Показ зафиксирован." if not args.skip_preview
             else "Показ пропущен по явному указанию — это зафиксированный переход, а не пропуск шага."]
    return {"ok": True, "skipped": bool(args.skip_preview), "text_hash": state["preview"]["text_hash"]}, lines


def telegram_script() -> Path:
    """Путь к каналу доставки. Rich — первым, plain — запасным.

    Повестка структурна по своей норме: таблица метрик, несколько секций,
    чек-лист задач. Плоский канал конвертирует только `**жирный**`, поэтому
    таблица приезжала руководителю сырыми пайпами — читать её глазами нельзя.
    `sendRichMessage` рисует GFM, и повестка выглядит документом, а не логом.

    Plain остаётся запасным на случай пакета без rich-скрипта; сам rich при
    ОТКАЗЕ API тоже уходит в plain — там это аварийная доставка текста, а не
    равноценный путь.

    По два кандидата на каждый режим не для гибкости, а по факту раскладки: в
    собранном пакете канал лежит рядом (`skills/send-telegram/`), в исходном
    дереве продукта — во вложенной `skills/channels/send-telegram/`, которую
    разворачивает сборщик. Без второго скилл не запускается на dogfood — то
    есть ровно там, где его проверяют перед клиентом.
    """
    env = os.environ.get(TELEGRAM_ENV, "")
    if env:
        return Path(env)
    roots = (SKILL_ROOT.parent / "send-telegram" / "scripts",
             SKILL_ROOT.parent / "channels" / "send-telegram" / "scripts")
    candidates = [root / name for name in CHANNEL_PREFERENCE for root in roots]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def channel_reason(stdout: str, stderr: str) -> str:
    """Человеческая причина отказа канала — для ops-чата и его классификатора.

    ❗️ Не «stderr, а если пусто — stdout»: у двух каналов эти потоки устроены
    ЗЕРКАЛЬНО. Прямой канал печатает причину в stdout, а обёртка шлюза — тоже
    в stdout (вторая строка контракта §10.3), но её stderr при этом почти
    никогда не пуст: там служебные `message_id`, `delivery_id`, `X-Request-Id`.
    Прежняя эвристика брала непустой stderr и выдавала в ops-чат один только
    идентификатор запроса, потеряв «не принято (http_401)».

    Порядок здесь: сначала человеческие строки stdout, затем его машинная
    первая строка, затем stderr. Машинная строка остаётся в тексте намеренно —
    по имени отказа в ней классификатор ops-алерта опознаёт словарь шлюза,
    а гадать по человеческой формулировке было бы гаданием по тому, что
    контракт не фиксирует.
    """
    rows = [line.strip() for line in (stdout or "").splitlines() if line.strip()]
    tail = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
    ordered = rows[1:] + rows[:1] + tail
    return (" · ".join(ordered) or (stderr or "").strip())[:400]


def channel_receipt(stdout: str) -> Dict[str, str]:
    """Идентификаторы доставки из ПЕРВОЙ строки stdout канала.

    Первая строка канала — компактный JSON: так его печатает и прямой
    `send_telegram.sh`, и обёртка шлюза. У шлюза там `delivery_id` — адрес
    операции `svaib-gw admin resolve`, без которого неизвестный исход
    неразрешим. Драйвер обязан вынести его наружу: он единственный, кто видит
    вывод канала.

    Разбор мягкий намеренно: канал может печатать что угодно, и доставка не
    должна проваливаться из-за того, что её квитанцию не разобрали. Нет полей —
    нет полей; это прямой маршрут либо чужой канал, а не отказ.
    """
    line = (stdout or "").strip().splitlines()
    if not line:
        return {}
    try:
        parsed = json.loads(line[0])
    except (ValueError, TypeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    # ❗️ Два канала печатают квитанцию по-разному, и второй разбор не роскошь.
    # Обёртка шлюза печатает свою форму (§10.3), а прямой канал — СЫРОЙ ответ
    # Bot API, где идентификатор сообщения лежит внутри `result`. Разбор только
    # верхнего уровня оставлял колонку журнала пустой на прямом маршруте —
    # всегда, при исправном канале.
    result = parsed.get("result")
    nested = result if isinstance(result, dict) else {}
    out: Dict[str, str] = {}
    # `status` — не украшение: «подтверждённый отказ» и «конфликт тела» дают
    # один и тот же код возврата, а решения по ним противоположные (§2.5).
    for field in ("message_id", "delivery_id", "status"):
        value = parsed.get(field, nested.get(field))
        if isinstance(value, str) and value.strip():
            out[field] = value.strip()
        elif isinstance(value, int) and not isinstance(value, bool):
            out[field] = str(value)
    return out


def cmd_deliver(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    """Единственный путь наружу. Прямой вызов канала в обход драйвера запрещён."""
    state = load_state(base, resolve_run(args, base))
    require_ready(state, "delivered")
    require_chain_intact(state, "previewed_ack")

    rendered = Path(state["steps"]["rendered"]["artifact"])
    text = rendered.read_text(encoding="utf-8")
    current = text_hash(text)
    if (state.get("preview") or {}).get("text_hash") != current:
        raise RunError(
            "preview_hash_mismatch",
            "показывали не этот текст: повестка пересобрана после подтверждения — покажи заново и подтверди",
        )

    script = telegram_script()
    if not script.is_file():
        raise RunError("channel_missing", "канал доставки не найден: {0}".format(script), exit_code=2)
    if args.dry_run:
        return {"ok": True, "dry_run": True, "chars": len(text)}, ["Проверка прошла, доставка не выполнялась (--dry-run)."]

    try:
        proc = subprocess.run([str(script), text], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RunError("channel_failed", "канал не отработал: {0}".format(exc), exit_code=2)

    ids = channel_receipt(proc.stdout)

    if proc.returncode != 0:
        # Текст отказа канала — В САМОМ сообщении об ошибке, а не только в
        # блокере state.json: классификатор ops-алерта разбирает именно его, и
        # раньше ему доставалась строка «канал вернул код N», по которой
        # отличить «клиент не нажал Start» от «разъехалась разметка» нельзя.
        detail = channel_reason(proc.stdout, proc.stderr)
        state["blockers"].append({"step": "delivered", "code": "channel_error",
                                  "message": detail, "at": now()})
        log(state, "deliver_failed", "delivered", "rc={0}".format(proc.returncode))
        save_state(base, state)
        raise RunError(
            "channel_error",
            "канал вернул код {0} — доставка не засчитана{1}".format(
                proc.returncode, ": {0}".format(detail) if detail else ""),
            payload=dict(ids, channel_rc=proc.returncode))

    receipt = accepted_path(base, state["run_id"], "delivered")
    atomic_write(receipt, json.dumps(
        dict({"at": now(), "text_hash": current, "channel": str(script), "chars": len(text)}, **ids),
        ensure_ascii=False, indent=2) + "\n")
    mark_done(base, state, "delivered", receipt)
    state["status"] = "done"
    log(state, "delivered", "delivered", None)
    save_state(base, state)
    return dict({"ok": True, "text_hash": current, "channel_rc": 0}, **ids), ["Повестка доставлена."]


def cmd_status(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    state = load_state(base, resolve_run(args, base, require_active=False))
    lines = ["Прогон {0} · {1}".format(state["run_id"], state["status"])]
    if state.get("object"):
        lines.append("Объект: {0} ({1})".format(state["object"]["object_ref"], state["object"]["object_kind"]))
    for name in STEP_ORDER:
        lines.append("  {0} {1}".format("✔" if state["steps"][name]["status"] == "done" else "·", name))
    if state["blockers"]:
        lines.append("Блокеры: {0}".format("; ".join(b["message"] for b in state["blockers"])))
    return {"ok": True, "state": state}, lines


def cmd_list(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    runs = list_runs(base)
    return {"ok": True, "runs": runs}, ["Прогонов: {0}".format(len(runs))] + ["  " + r for r in runs]


def cmd_abandon(args: argparse.Namespace, base: Path) -> Tuple[Dict[str, Any], List[str]]:
    state = load_state(base, resolve_run(args, base))
    state["status"] = "abandoned"
    log(state, "abandon", None, None)
    save_state(base, state)
    return {"ok": True}, ["Прогон остановлен. В базе следов не осталось: скилл в неё не пишет."]


HANDLERS = {
    "start": cmd_start,
    "next": cmd_next,
    "resolve": cmd_resolve,
    "collect": cmd_collect,
    "metrics": cmd_metrics,
    "submit": cmd_submit,
    "validate": cmd_validate,
    "render": cmd_render,
    "ack": cmd_ack,
    "deliver": cmd_deliver,
    "status": cmd_status,
    "list": cmd_list,
    "abandon": cmd_abandon,
}


def resolve_run(args: argparse.Namespace, base: Path, require_active: bool = True) -> str:
    """Активный прогон для команд, меняющих состояние; последний — для чтения."""
    run_id = getattr(args, "run", None)
    if run_id:
        return run_id
    found = active_run(base)
    if found:
        return found
    if not require_active:
        runs = list_runs(base)
        if runs:
            return runs[0]
    raise RunError("no_active_run", "активного прогона нет — начни `start`")


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base", default=argparse.SUPPRESS, help="корень базы (по умолчанию текущий каталог)")
    common.add_argument("--run", default=argparse.SUPPRESS, help="run_id вместо активного прогона")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="машинный вывод")

    parser = argparse.ArgumentParser(description="Драйвер прогона повестки.", parents=[common])
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", parents=[common], help="начать прогон")
    p_start.add_argument("--phrase", default=None, help="исходная фраза человека")

    sub.add_parser("next", parents=[common], help="следующий шаг")

    p_resolve = sub.add_parser("resolve", parents=[common], help="назвать объект встречи (выбор валидирует код)")
    p_resolve.add_argument("--object", required=True, help="путь узла, файл цели или профиль")
    p_resolve.add_argument("--kind", required=True, choices=["node", "goal", "person"])
    p_resolve.add_argument("--date", default=None, help="дата встречи, ГГГГ-ММ-ДД")
    p_resolve.add_argument("--type", default=None, help="тип встречи словом базы")

    sub.add_parser("collect", parents=[common], help="собрать чек-лист источников (драйвер делает сам)")
    p_metrics = sub.add_parser("metrics", parents=[common],
                               help="получить перечень метрик и их значения (драйвер делает сам)")
    p_metrics.add_argument("--snapshot-dir", default=None,
                           help="каталог снимка книг метрик; без него значения не читаются "
                                "(по умолчанию — из {0})".format(SNAPSHOT_ENV))

    p_submit = sub.add_parser("submit", parents=[common], help="принять черновик повестки")
    p_submit.add_argument("step", choices=list(SUBMITTABLE))
    p_submit.add_argument("--artifact", required=True)

    sub.add_parser("validate", parents=[common], help="проверить форму (драйвер делает сам)")

    p_render = sub.add_parser("render", parents=[common], help="отрендерить повестку (драйвер делает сам)")
    p_render.add_argument("--limit", type=int, default=form.SCREEN_LIMIT_CHARS)

    p_ack = sub.add_parser("ack", parents=[common], help="подтвердить показ человеку")
    p_ack.add_argument("--skip-preview", action="store_true",
                       help="доставка без показа: явный флаг, то есть зафиксированный переход")

    p_deliver = sub.add_parser("deliver", parents=[common], help="доставить повестку")
    p_deliver.add_argument("--dry-run", action="store_true", help="проверить гейты, канал не вызывать")

    for name in ("status", "list", "abandon"):
        sub.add_parser(name, parents=[common], help=name)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    as_json = getattr(args, "json", False)
    base = Path(getattr(args, "base", ".")).resolve()

    try:
        payload, lines = HANDLERS[args.command](args, base)
    except RunError as exc:
        out = {"ok": False, "error": exc.code, "message": exc.message}
        out.update(exc.payload)
        if as_json:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print("❌ {0}: {1}".format(exc.code, exc.message), file=sys.stderr)
        return exc.exit_code
    except OSError as exc:
        print(json.dumps({"ok": False, "error": "io_error", "message": str(exc)}, ensure_ascii=False))
        return 2

    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for line in lines:
            print(line)
    return 0 if payload.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
