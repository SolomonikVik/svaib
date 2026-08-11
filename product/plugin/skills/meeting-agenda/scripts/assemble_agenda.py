#!/usr/bin/env python3
"""assemble_agenda.py — вливает машинные поля в черновик повестки.

Собирает полный agenda.json из трёх входов: черновика LLM (прозаические поля),
отчёта вертикали metrics (значения и три оси по каждой метрике) и manifest'а
источников (даты, ритм серии, статусы чтения).

Несущее правило (design.md Р1): строки метрик собирает assembler, а не LLM.
Тогда fail-closed «число без пройденной сверки не выводится» и запрет «посчитал
сам» блокируются структурно, а не ловятся регуляркой постфактум.

Выход: agenda.json на диск, отчёт о вливании в stdout.
Коды возврата: 0 — собрано; 1 — вход не удовлетворяет контракту; 2 — usage/IO.

Stdlib-only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
AGENDA_SCHEMA_FILE = SKILL_ROOT / "schema" / "agenda.schema.json"

# --------------------------------------------------------------------------- #
# Оси деградации и деривация пользовательского статуса
# --------------------------------------------------------------------------- #

# Таблица приоритетов design.md Р1: первая сработавшая строка выигрывает.
# Порядок — и есть спека: причина деградации должна называться истинная,
# а не первая попавшаяся. Схлопывание любых двух строк = сообщать руководителю
# то, чего никто не наблюдал (класс ошибки R2).
STATUS_PRIORITY: Tuple[Tuple[str, str, str], ...] = (
    ("availability", "source_unavailable", "source_unavailable"),
    # Guard остановил чтение: структура книги разошлась с раскладкой либо
    # строка задвоена. Стоит рядом с «книга не прочитана», потому что
    # достоверность потеряна одинаково — но причина другая и названа своя.
    ("availability", "blocked", "blocked"),
    ("availability", "value_error", "value_error"),
    # ВЫШЕ, чем `verification not_run`, и это не косметика: при непривязанном
    # источнике сверять нечего, поэтому вертикаль честно ставит not_run — и без
    # этой строки руководителю сообщалось бы «сверка не выполнялась» вместо
    # «источник не назначен». Первое читается как сбой контура, второе — как
    # незакрытый онбординг, и действия у них разные.
    ("availability", "source_unbound", "source_unbound"),
    ("verification", "mismatch", "unverified"),
    ("verification", "not_run", "verification_not_run"),
    ("availability", "no_value", "no_value"),
    ("freshness", "undatable", "as_of_unknown"),
    ("freshness", "before_period", "outdated"),
)
STATUS_FALLBACK = "current"

# Значения осей, которые контракт вертикали объявляет допустимыми, плюс
# `not_attempted` — его ставит сам gateway, когда снимка книг нет и читать было
# нечем. Проверка нужна, потому что `STATUS_FALLBACK` — «всё в порядке»: любое
# незнакомое значение (рассинхрон версий схемы, опечатка производителя,
# частичная деградация) прошло бы таблицу приоритетов насквозь и объявило
# несверенное число актуальным. Это ровно тот fail-open, который весь контур
# запрещает.
KNOWN_AXIS_VALUES: Dict[str, frozenset] = {
    "availability": frozenset({"value", "no_value", "value_error", "source_unavailable",
                               "source_unbound", "blocked", "not_attempted"}),
    "freshness": frozenset({"in_period", "before_period", "undatable"}),
    "verification": frozenset({"verified", "mismatch", "not_run"}),
}

# Статусы, при которых число к руководителю не идёт. Строже матрицы валидатора
# намеренно: непройденная сверка обесценивает не только факт, но и план с
# производными — доверия к источнику в этот момент нет никакого.
STATUS_WITHOUT_NUMBER = frozenset(
    {"no_value", "value_error", "source_unavailable", "unverified", "verification_not_run",
     # Источник не назначен — числа нет по определению; чтение остановлено
     # guard'ом — число в книге есть, но доверять ему нельзя целиком.
     "source_unbound", "blocked",
     # Значение за ДРУГОЙ период. Раньше оно печаталось в колонке факта, и
     # июньское число стояло рядом с июльскими так же уверенно — руководитель
     # читал таблицу как одномоментный срез. Число не потеряно: период назван в
     # статусе, и «за отчётный период данных нет» — это ответ, а не пустота.
     "outdated"}
)
# Статусы, при которых датировка отсутствует. `as_of_unknown` — легальная ветка
# A4.1: число есть, даты нет, и требовать её здесь запрещено.
STATUS_WITHOUT_AS_OF = STATUS_WITHOUT_NUMBER | {"as_of_unknown"}

# Свежесть пункта задач: при неизвестной серии и невычислимом ритме.
FALLBACK_STALE_DAYS = 14
RHYTHM_FACTOR = 1.5
RHYTHM_WINDOW = 4  # последние N встреч серии дают медианный интервал
MIN_COLLAPSE_GROUP = 2


class AssembleError(Exception):
    """Ожидаемое нарушение контракта входа."""

    def __init__(self, code: str, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


def derive_display_status(availability: str, freshness: str, verification: str) -> str:
    """Пользовательский статус из трёх независимых осей — детерминированно.

    Полем суждения статус не является: его выводит код, а LLM решает только,
    стоит ли деградировавшая метрика упоминания в фокус-пунктах.
    """
    for axis, value in (("availability", availability), ("freshness", freshness),
                        ("verification", verification)):
        if value not in KNOWN_AXIS_VALUES[axis]:
            raise AssembleError(
                "unknown_axis_value",
                "ось {0} пришла со значением «{1}», которого нет в контракте вертикали".format(axis, value),
            )
    if availability == "not_attempted" and verification != "not_run":
        # «Источник не исследовался» без «сверка не выполнялась» — состояние,
        # которого не бывает: если чтения не было, сверять было нечего.
        raise AssembleError(
            "impossible_axes",
            "availability=not_attempted допустим только с verification=not_run, получено «{0}»".format(verification),
        )
    axes = {"availability": availability, "freshness": freshness, "verification": verification}
    for axis, value, status in STATUS_PRIORITY:
        if axes[axis] == value:
            return status
    return STATUS_FALLBACK


# --------------------------------------------------------------------------- #
# Метрики
# --------------------------------------------------------------------------- #


def normalize_metric(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Строка метрики из отчёта вертикали: статус выводится, числа гасятся по нему."""
    for axis in ("availability", "freshness", "verification"):
        if axis not in raw:
            raise AssembleError(
                "metric_axis_missing",
                "метрика {0}: нет оси {1} — статус вывести нечем".format(raw.get("metric_id"), axis),
            )

    status = derive_display_status(raw["availability"], raw["freshness"], raw["verification"])
    metric: Dict[str, Any] = {
        "metric_id": raw["metric_id"],
        "name": raw.get("name") or raw["metric_id"],
        "unit": raw.get("unit"),
        "direction": raw.get("direction"),
        "plan": raw.get("plan"),
        "plan_conflict": raw.get("plan_conflict"),
        "fact": raw.get("fact"),
        "as_of": raw.get("as_of"),
        "period": raw.get("period"),
        "granularity": raw.get("granularity"),
        "period_partial": raw.get("period_partial"),
        "delta": raw.get("delta"),
        "trend": raw.get("trend"),
        "availability": raw["availability"],
        "freshness": raw["freshness"],
        "verification": raw["verification"],
        "display_status": status,
        "source_ref": raw.get("source_ref"),
        "composition_confirmed": bool(raw.get("composition_confirmed", False)),
        "collapsed_names": None,
    }

    if status in STATUS_WITHOUT_NUMBER:
        # Fail-closed по R5: непроверяемый guard уже пропустил к руководителю
        # неверное число из неканонического листа. Больше не пропустит.
        metric["fact"] = None
        metric["plan"] = None
        metric["delta"] = None
        metric["trend"] = None
    if status in STATUS_WITHOUT_AS_OF:
        metric["as_of"] = None

    # Правило разреза (design.md Р6): Δ и тренд живут только при подтверждённом
    # составе ОБОИХ сравниваемых периодов. Иначе рост состава метрики уедет
    # к руководителю как органический рост (R3).
    if not raw.get("composition_confirmed", False):
        metric["delta"] = None
        metric["trend"] = None

    if metric["plan_conflict"]:
        # A2.1: три несовпадающих плана. Колонка «План» пуста с пометкой,
        # а не заполнена одним из трёх наугад.
        metric["plan"] = None

    return metric


def has_deviation(metric: Dict[str, Any]) -> bool:
    """Метрика с отклонением от плана — не сворачивается никогда."""
    if metric.get("delta") is not None and metric["delta"] != 0:
        return True
    plan, fact = metric.get("plan"), metric.get("fact")
    return plan is not None and fact is not None and plan != fact


def collapse_metrics(metrics: List[Dict[str, Any]], focus_metric_ids: List[str]) -> List[Dict[str, Any]]:
    """Легальная свёртка: полнота перечня × лимит объёма.

    Группа с одинаковым display_status и без отклонения схлопывается в одну
    строку с collapsed_names. Свёртка идёт по любому однородному статусу, а не
    только по «актуально»: в стартовом режиме все метрики получают «сверка не
    выполнялась», и правило «сворачиваются только зелёные» сделало бы полноту
    перечня недостижимой ровно там, где скилл впервые собирается.
    """
    protected = set(focus_metric_ids)
    groups: Dict[str, List[Dict[str, Any]]] = {}
    expanded: List[Dict[str, Any]] = []

    for metric in metrics:
        # Прочитанное значение не сворачивается никогда. Свёртка — способ
        # уместить ПЕРЕЧЕНЬ в экран, а не спрятать то единственное, ради чего
        # таблица существует: агрегатная строка числа не несёт, и живой прогон
        # 06.08 показал это буквально — три метрики со значениями (в том числе
        # выручка) схлопнулись в «Остальные 3», и руководитель не увидел ни
        # одной цифры при полностью исправном чтении книги.
        if metric.get("fact") is not None:
            expanded.append(metric)
            continue
        if metric["metric_id"] in protected or has_deviation(metric):
            expanded.append(metric)
            continue
        groups.setdefault(metric["display_status"], []).append(metric)

    out = list(expanded)
    for status, group in groups.items():
        if len(group) < MIN_COLLAPSE_GROUP:
            out.extend(group)
            continue
        out.append(
            {
                "metric_id": "collapsed:{0}".format(status),
                "name": "Остальные {0}".format(len(group)),
                "unit": None,
                "direction": None,
                "plan": None,
                "plan_conflict": None,
                "fact": None,
                "as_of": None,
                "delta": None,
                "trend": None,
                "availability": group[0]["availability"],
                "freshness": group[0]["freshness"],
                "verification": group[0]["verification"],
                "display_status": status,
                "source_ref": None,
                "composition_confirmed": all(m.get("composition_confirmed") for m in group),
                "collapsed_names": [m["metric_id"] for m in group],
            }
        )
    return out


# --------------------------------------------------------------------------- #
# Свежесть пунктов
# --------------------------------------------------------------------------- #


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def median_interval(dates: List[date]) -> Optional[float]:
    """Медианный интервал последних встреч серии — база порога протухания."""
    ordered = sorted(set(dates))[-RHYTHM_WINDOW:]
    if len(ordered) < 2:
        return None
    gaps = [(b - a).days for a, b in zip(ordered, ordered[1:])]
    return statistics.median(gaps) if gaps else None


def is_stale(source_date: Optional[date], base: date, series_dates: List[date]) -> bool:
    """Протухание — свойство пункта, не блока.

    Основной критерий: после даты факта прошла встреча той же серии, а пункт
    не подтверждался. Порог-константа как основной отвергнут: для двухнедельного
    1-on-1 он даёт ложную тревогу.
    """
    if source_date is None:
        return False
    later = [d for d in series_dates if d > source_date and d <= base]
    if later:
        return True
    if series_dates:
        rhythm = median_interval(series_dates)
        if rhythm:
            return (base - source_date).days > RHYTHM_FACTOR * rhythm
    return (base - source_date) > timedelta(days=FALLBACK_STALE_DAYS)


def normalize_task(raw: Dict[str, Any], base: date, series_dates: List[date]) -> Dict[str, Any]:
    """Пункт задач: текст от LLM, датность и протухание вливает код."""
    if not raw.get("source_ref"):
        raise AssembleError(
            "task_without_source",
            "пункт «{0}…» без source_ref: пункт без источника не пишется".format(str(raw.get("text", ""))[:40]),
        )
    source_date = parse_date(raw.get("source_date"))
    origin = raw.get("date_origin") or ("undatable" if source_date is None else "protocol")
    if source_date is None:
        # Задача без выводимой даты не вырезается — симметрия с метриками:
        # молчаливое исчезновение это тот же дефект. Пункт идёт со статусом.
        origin = "undatable"
    return {
        "text": raw["text"],
        "owner_source": raw.get("owner_source"),
        "due": raw.get("due"),
        "status": raw.get("status"),
        "source_ref": raw["source_ref"],
        "source_date": source_date.isoformat() if source_date else None,
        "date_origin": origin,
        "stale": is_stale(source_date, base, series_dates),
    }


# --------------------------------------------------------------------------- #
# Сборка
# --------------------------------------------------------------------------- #


METRIC_TOKEN_RE = re.compile(r"\{metric:([^{}:]+)(?::[^{}]*)?\}")


def tokens_referenced(draft: Dict[str, Any]) -> List[str]:
    """metric_id, на которые ссылается проза черновика."""
    texts: List[str] = []
    frame = draft.get("frame") or {}
    texts.extend(str(frame.get(k) or "") for k in ("goal_text", "summary_line"))
    for group in ("tasks", "focus", "questions"):
        texts.extend(str(item.get("text") or "") for item in (draft.get(group) or []))
    out: List[str] = []
    for text in texts:
        out.extend(m.group(1).strip() for m in METRIC_TOKEN_RE.finditer(text))
    return out


def merge_checks_skipped(*sources_of_skips: Dict[str, Any]) -> List[Dict[str, str]]:
    """Объединяет пропущенные проверки ИЗ ВСЕХ источников с дедупликацией.

    Прежняя `or`-цепочка теряла записи: непустой список у одного источника
    прятал списки остальных, а manifest не читался вовсе. Пропуск проверки —
    машинный факт, и переносить его вручную (тем более силами LLM) нельзя:
    именно так деградация ядра ценности проходит молча.
    """
    out: List[Dict[str, str]] = []
    seen: set = set()
    for payload in sources_of_skips:
        for item in (payload.get("checks_skipped") or []):
            key = item.get("check_id")
            if key and key not in seen:
                seen.add(key)
                out.append({"check_id": key, "reason": item.get("reason", "причина не названа")})
    return out


def assemble(draft: Dict[str, Any], metrics_report: Dict[str, Any], sources: Dict[str, Any]) -> Dict[str, Any]:
    meeting = dict(draft.get("meeting") or {})
    if not meeting.get("object_ref"):
        raise AssembleError("meeting_object_missing", "в черновике нет object_ref — собирать повестку не для чего")

    base = parse_date(meeting.get("date")) or date.today()
    series_dates = [d for d in (parse_date(x) for x in sources.get("series_dates", [])) if d]
    if meeting.get("series_key") is None:
        meeting["series_key"] = sources.get("series_key")

    focus_raw = list(draft.get("focus") or [])
    protected_metric_ids: List[str] = []
    for item in focus_raw:
        protected_metric_ids.extend(item.get("metric_ids") or [])
    # Метрика, на которую ссылается токен в прозе, из свёртки исключается.
    # Иначе сверенное значение молча превращается в прочерк: агрегатная строка
    # числа не несёт, и «MRR держится на {metric:MRR}» рендерится как «на —».
    protected_metric_ids.extend(tokens_referenced(draft))

    metrics = [normalize_metric(m) for m in metrics_report.get("metrics", [])]
    focus_metric_ids = protected_metric_ids
    # Счётчик считается ДО свёртки: он про метрики, а не про строки таблицы.
    # После свёртки «три метрики без чисел» превратились бы в «одну» — и
    # руководителю сообщили бы неверный масштаб пробела.
    unverified = sum(1 for m in metrics if m["display_status"] in STATUS_WITHOUT_NUMBER)
    metrics = collapse_metrics(metrics, focus_metric_ids)

    tasks = [normalize_task(t, base, series_dates) for t in (draft.get("tasks") or [])]

    focus = [
        {
            "text": item.get("text", ""),
            "evidence": item.get("evidence") or [],
            "check_id": item.get("check_id", ""),
            "metric_ids": item.get("metric_ids") or None,
        }
        for item in focus_raw
    ]
    questions = [
        {
            "text": q.get("text", ""),
            "decision_owner": q.get("decision_owner"),
            "owner_source_ref": q.get("owner_source_ref"),
        }
        for q in (draft.get("questions") or [])
    ]

    frame = dict(draft.get("frame") or {})
    frame["metrics_ref"] = "metrics"
    frame.setdefault("goal_text", None)
    frame.setdefault("goal_ref", None)
    frame.setdefault("summary_line", None)

    flags = {
        "stale_tasks": [i for i, t in enumerate(tasks) if t["stale"]],
        "unverified_count": unverified,
        "undated_tasks_count": sum(1 for t in tasks if t["date_origin"] == "undatable"),
        "unowned_tasks_count": sum(1 for t in tasks if not t.get("owner_source")),
        "sources_missing": sources.get("missing", []),
        "orphan_rows": metrics_report.get("orphan_rows", []),
        "checks_skipped": merge_checks_skipped(sources, metrics_report, draft),
        "series_key_undefined": meeting.get("series_key") is None,
    }

    return {
        "meeting": {
            "object_ref": meeting["object_ref"],
            "object_kind": meeting.get("object_kind", "node"),
            "date": meeting.get("date") or base.isoformat(),
            "type": meeting.get("type") or "встреча",
            "series_key": meeting.get("series_key"),
            "prev_protocol_ref": meeting.get("prev_protocol_ref"),
            "prev_meeting_date": meeting.get("prev_meeting_date"),
        },
        "frame": frame,
        "metrics": metrics,
        "tasks": tasks,
        "focus": focus,
        "questions": questions,
        "flags": flags,
    }


def read_json(path: Path, what: str) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise AssembleError("input_missing", "нет файла {0}: {1}".format(what, path), exit_code=2)
    except json.JSONDecodeError as exc:
        raise AssembleError("input_broken", "{0} не разобран как JSON: {1}".format(what, exc), exit_code=2)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Вливает машинные поля в черновик повестки.")
    parser.add_argument("--draft", required=True, help="черновик LLM (прозаические поля)")
    parser.add_argument("--metrics", required=True, help="отчёт вертикали metrics")
    parser.add_argument("--sources", required=True, help="manifest источников")
    parser.add_argument("--out", required=True, help="куда записать agenda.json")
    parser.add_argument("--json", action="store_true", help="машинный вывод")
    args = parser.parse_args(argv)

    try:
        agenda = assemble(
            read_json(Path(args.draft), "черновика"),
            read_json(Path(args.metrics), "отчёта метрик"),
            read_json(Path(args.sources), "manifest источников"),
        )
    except AssembleError as exc:
        payload = {"ok": False, "error": exc.code, "message": exc.message}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("❌ {0}: {1}".format(exc.code, exc.message), file=sys.stderr)
        return exc.exit_code

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(agenda, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = {
        "ok": True,
        "out": str(out_path),
        "metrics_rows": len(agenda["metrics"]),
        "tasks": len(agenda["tasks"]),
        "stale_tasks": len(agenda["flags"]["stale_tasks"]),
        "checks_skipped": len(agenda["flags"]["checks_skipped"]),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Собрано: {0}".format(out_path))
        print("  строк метрик: {0} · пунктов: {1} · протухших: {2}".format(
            payload["metrics_rows"], payload["tasks"], payload["stale_tasks"]))
        if payload["checks_skipped"]:
            print("  проверок пропущено: {0}".format(payload["checks_skipped"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
