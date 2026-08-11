#!/usr/bin/env python3
"""validate_agenda.py — валидатор формы повестки (контракт `strict`).

Две фазы (design.md, «Валидатор формы»):
  json  — по agenda.json, до рендера: схема, каркас, лимиты, полнота перечня
          метрик, сверка статуса с осями, матрица «статус → число / датировка»,
          обязательства пунктов, провенанс, токены;
  text  — по отрендеренному тексту, после рендера: объём «одного экрана».

Проверяет форму, а не качество выбора: остроту сигналов кодом не измерить.

ТРИ ПРАВИЛА, БЕЗ КОТОРЫХ FAIL-CLOSED ОБХОДИТСЯ ВХОДЯЩИМ JSON (ревью 31.07):
  · `display_status` ПЕРЕСЧИТЫВАЕТСЯ из трёх осей и обязан совпасть — иначе
    подложный «актуально» при расхождении сверки выводит число;
  · значения осей и статуса проверяются по закрытому enum схемы — иначе
    неизвестный статус проходит мимо всех матриц;
  · провенанс сверяется с manifest прочитанных источников — иначе достаточно
    сочинить путь, чтобы пункт «с опорой» прошёл механический гейт.

Библиотека инвариантов: `validate(agenda, expected_metric_ids, manifest)`.
Коды возврата: 0 — форма цела; 1 — есть нарушения; 2 — вход не разобран.

Stdlib-only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import assemble_agenda as asm  # noqa: E402  — владелец деривации статуса

AGENDA_SCHEMA_FILE = SKILL_ROOT / "schema" / "agenda.schema.json"

LEVEL_FORM = "form"
LEVEL_NOTE = "note"

MAX_FOCUS = 3
MAX_QUESTIONS = 3
SCREEN_LIMIT_CHARS = 1200

# Закрытые списки берутся ИЗ СХЕМЫ, а не дублируются константами: вторая норма
# — это ровно тот класс дефекта, которым болел Ф4 («правка не доехала до
# второго файла»).
_schema_cache: Optional[Dict[str, Any]] = None


def schema() -> Dict[str, Any]:
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = json.loads(AGENDA_SCHEMA_FILE.read_text(encoding="utf-8"))
    return _schema_cache


def metric_enum(field: str) -> List[str]:
    return schema()["properties"]["metrics"]["items"]["properties"][field]["enum"]


STATUS_WITHOUT_NUMBER = asm.STATUS_WITHOUT_NUMBER
STATUS_WITHOUT_AS_OF = asm.STATUS_WITHOUT_AS_OF
STATUS_REQUIRING_NUMBER = frozenset({"current", "outdated", "as_of_unknown"})
STATUS_REQUIRING_AS_OF = frozenset({"current", "outdated"})
# Числовые поля целиком: непройденная сверка обесценивает не только факт, но и
# план с производными — «900 | число не показываю» это противоречие в строке.
NUMERIC_FIELDS = ("fact", "plan", "delta")

TOKEN_RE = re.compile(r"\{(metric|count):([A-Za-zА-Яа-я0-9 _.:%-]+?)\}")
METRIC_TOKEN_PARTS = 2
ALLOWED_NUMERIC = (
    re.compile(r"\d{4}-\d{2}-\d{2}"),
    # Период значения в шкале метрики: месяц, неделя, квартал. Это датировка, а
    # не измерение — тот же класс, что ISO-дата. С появлением чисел в повестке
    # период стоит в таблице («данные за 2026-06»), и ссылка на него в прозе
    # неизбежна: живой прогон 06.08 срезал на этом верный фокус-пункт, приняв
    # датировку за литеральное число.
    re.compile(r"\b\d{4}-(?:\d{2}|W\d{2}|Q\d)\b"),
    # Кириллические О, К, Р, В — намеренно: «О2» набирается в русской раскладке
    # чаще, чем латинское «O2», и ложное срабатывание на идентификаторе цели
    # выглядит как придирка к автору, а не как защита от числа.
    re.compile(r"\b[OKRWQОКРВ]{1,2}\d+\b"),
)
DIGIT_RE = re.compile(r"\d")
FLAG_NAMES = frozenset(schema()["properties"]["flags"]["required"]) if AGENDA_SCHEMA_FILE.is_file() else frozenset()

FORBIDDEN_PHRASES = (
    "не замеряется", "не измеряется", "не замеряют", "не измеряют",
    "не замеряете", "не измеряете", "клиент не замеряет",
)


class Violation:
    """Нарушение формы."""

    __slots__ = ("code", "level", "field", "msg")

    def __init__(self, code: str, msg: str, field: Optional[str] = None, level: str = LEVEL_FORM) -> None:
        self.code = code
        self.msg = msg
        self.field = field
        self.level = level

    def as_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "level": self.level, "field": self.field, "msg": self.msg}

    def __repr__(self) -> str:
        return "Violation({0}, {1})".format(self.code, self.msg)


# --------------------------------------------------------------------------- #
# Мини-проверка по схеме: required, type, enum
# --------------------------------------------------------------------------- #

JSON_TYPES = {
    "object": dict, "array": list, "string": str, "integer": int,
    "number": (int, float), "boolean": bool, "null": type(None),
}


def type_ok(value: Any, expected: Any) -> bool:
    names = expected if isinstance(expected, list) else [expected]
    for name in names:
        py = JSON_TYPES.get(name)
        if py is None:
            return True
        if name == "integer" and isinstance(value, bool):
            continue
        if isinstance(value, py):
            return True
    return False


def check_schema(node: Any, spec: Dict[str, Any], path: str, out: List[Violation]) -> None:
    """Поднабор JSON Schema: required, type, enum, pattern, additionalProperties,
    minLength, minItems, maxItems, minimum.

    Полноценной библиотеки нет и быть не может — пакет stdlib-only. Схема
    объявлена нормативом каркаса, поэтому исполняется всё, чем этот норматив
    выражен: без `pattern` дата «not-an-iso-date» проходит, без
    `additionalProperties` в повестку приезжают поля, которых контракт не знает.
    """
    if "type" in spec and not type_ok(node, spec["type"]):
        out.append(Violation("schema_type", "{0}: ожидался тип {1}".format(path or "корень", spec["type"]), field=path))
        return
    if "enum" in spec and node not in spec["enum"]:
        out.append(Violation("schema_enum", "{0}: значение «{1}» вне закрытого списка".format(path, node), field=path))
        return
    if isinstance(node, str):
        pattern = spec.get("pattern")
        if pattern and not re.match(pattern, node):
            out.append(Violation("schema_pattern", "{0}: «{1}» не соответствует формату".format(path, node), field=path))
        if "minLength" in spec and len(node) < spec["minLength"]:
            out.append(Violation("schema_min_length", "{0}: строка короче допустимого".format(path), field=path))
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        if "minimum" in spec and node < spec["minimum"]:
            out.append(Violation("schema_minimum", "{0}: значение меньше допустимого".format(path), field=path))
    if isinstance(node, dict):
        for key in spec.get("required", []):
            if key not in node:
                out.append(Violation("schema_required", "{0}: нет обязательного поля «{1}»".format(path or "корень", key), field=path))
        props = spec.get("properties") or {}
        if spec.get("additionalProperties") is False:
            for key in node:
                if key not in props:
                    out.append(Violation("schema_unknown_field",
                                         "{0}: поле «{1}» контрактом не предусмотрено".format(path or "корень", key),
                                         field=path))
        for key, sub in props.items():
            if key in node:
                check_schema(node[key], sub, "{0}.{1}".format(path, key) if path else key, out)
    elif isinstance(node, list):
        if "minItems" in spec and len(node) < spec["minItems"]:
            out.append(Violation("schema_min_items", "{0}: элементов меньше допустимого".format(path), field=path))
        if "maxItems" in spec and len(node) > spec["maxItems"]:
            out.append(Violation("schema_max_items", "{0}: элементов больше допустимого".format(path), field=path))
        if "items" in spec:
            for i, item in enumerate(node):
                check_schema(item, spec["items"], "{0}[{1}]".format(path, i), out)


# --------------------------------------------------------------------------- #
# Проза и токены
# --------------------------------------------------------------------------- #


def prose_fields(agenda: Dict[str, Any]) -> List[Sequence[str]]:
    out: List[Sequence[str]] = []
    frame = agenda.get("frame") or {}
    for key in ("goal_text", "summary_line"):
        if frame.get(key):
            out.append(("frame.{0}".format(key), frame[key]))
    for i, task in enumerate(agenda.get("tasks") or []):
        if task.get("text"):
            out.append(("tasks[{0}].text".format(i), task["text"]))
    for i, item in enumerate(agenda.get("focus") or []):
        if item.get("text"):
            out.append(("focus[{0}].text".format(i), item["text"]))
    for i, q in enumerate(agenda.get("questions") or []):
        if q.get("text"):
            out.append(("questions[{0}].text".format(i), q["text"]))
    return out


def check_tokens(text: str,
                 field: str,
                 known_metric_ids: Iterable[str],
                 hidden_metric_ids: Optional[Iterable[str]] = None) -> List[Violation]:
    out: List[Violation] = []
    known = set(known_metric_ids)
    hidden = set(hidden_metric_ids or ())
    for match in TOKEN_RE.finditer(text):
        kind, body = match.group(1), match.group(2).strip()
        if kind == "metric":
            metric_id = body.split(":")[0].strip()
            if metric_id not in known:
                out.append(Violation("token_unknown_metric",
                                     "токен ссылается на метрику «{0}», которой нет в повестке".format(metric_id),
                                     field=field))
            elif metric_id in hidden:
                # Рендер такой токен гасит в «—» (fail-closed), и фраза теряет
                # смысл: «цель года по —». Ловим на валидации, а не глазами
                # после render — иначе бессмыслица доезжает до доставки.
                out.append(Violation("token_on_hidden_metric",
                                     "токен метрики «{0}»: её число скрыто статусом, "
                                     "рендер подставит прочерк — переформулируй без токена".format(metric_id),
                                     field=field))
            if len(body.split(":")) > METRIC_TOKEN_PARTS:
                out.append(Violation("token_malformed", "токен метрики разобран как {0}".format(body), field=field))
        elif body not in FLAG_NAMES:
            out.append(Violation("token_unknown_flag",
                                 "токен счётчика ссылается на «{0}» — такого флага нет".format(body), field=field))
    residue = TOKEN_RE.sub(" ", text)
    if "{" in residue or "}" in residue:
        out.append(Violation("token_malformed", "в поле есть фигурная скобка вне токена", field=field))
    return out


def strip_allowed(text: str) -> str:
    out = TOKEN_RE.sub(" ", text)
    for pattern in ALLOWED_NUMERIC:
        out = pattern.sub(" ", out)
    return out


def readable_sources(manifest: Optional[Dict[str, Any]]) -> Optional[set]:
    """Пути, которые чек-лист отметил прочитанными.

    None — manifest не передан: провенанс проверить нечем, и это само по себе
    нарушение, а не повод пропустить проверку.
    """
    if manifest is None:
        return None
    return {s["path"] for s in (manifest.get("sources") or []) if s.get("status") == "read"}


# --------------------------------------------------------------------------- #
# Основная проверка
# --------------------------------------------------------------------------- #


def check_against_report(agenda: Dict[str, Any], metrics_report: Dict[str, Any]) -> List[Violation]:
    """Сверяет строки метрик с ПРИНЯТЫМ отчётом вертикали.

    Пересчёт статуса из осей ловит враньё в `display_status`, но самим осям
    верит на слово. Без этой сверки достаточно прописать в `agenda.json`
    самосогласованные `value / in_period / verified` и число — и оно доедет до
    руководителя со штампом «в норме», хотя источник не читался вовсе. Тот же
    класс, что R2, только на уровень глубже.
    """
    v: List[Violation] = []
    truth: Dict[str, Dict[str, Any]] = {}
    for raw in metrics_report.get("metrics", []):
        try:
            row = asm.normalize_metric(raw)
        except asm.AssembleError as exc:
            v.append(Violation("report_broken", exc.message, field="metrics"))
            continue
        truth[row["metric_id"]] = row

    for i, m in enumerate(agenda.get("metrics") or []):
        field = "metrics[{0}]".format(i)
        names = m.get("collapsed_names") or []
        if names:
            for name in names:
                reference = truth.get(name)
                if reference and reference["display_status"] != m.get("display_status"):
                    v.append(Violation(
                        "collapse_status_mismatch",
                        "метрика «{0}» свёрнута под статус «{1}», а по отчёту у неё «{2}»".format(
                            name, m.get("display_status"), reference["display_status"]),
                        field=field))
            # Имя агрегата генерирует код; произвольная подпись здесь — такой же
            # канал для числа, как и прозаическое поле.
            if m.get("name") != "Остальные {0}".format(len(names)):
                v.append(Violation("aggregate_name_forged",
                                   "подпись агрегатной строки не соответствует её составу", field=field))
            continue
        reference = truth.get(m.get("metric_id"))
        if reference is None:
            v.append(Violation("metric_not_in_report",
                               "метрики «{0}» нет в отчёте вертикали".format(m.get("metric_id")), field=field))
            continue
        # `name`, `unit`, `source_ref` рендерятся в таблицу и потому проверяются
        # наравне с числами: иначе значение непройденной метрики доезжает до
        # руководителя внутри её же подписи — `name = "MRR 921"`.
        for key in ("name", "unit", "source_ref", "direction"):
            if m.get(key) != reference.get(key):
                v.append(Violation(
                    "field_mismatch",
                    "поле «{0}» расходится с отчётом: в повестке «{1}», в отчёте «{2}»".format(
                        key, m.get(key), reference.get(key)),
                    field=field))
        for key in ("availability", "freshness", "verification", "composition_confirmed"):
            if m.get(key) != reference.get(key):
                v.append(Violation(
                    "axis_mismatch",
                    "поле «{0}» расходится с отчётом: в повестке «{1}», в отчёте «{2}»".format(
                        key, m.get(key), reference.get(key)),
                    field=field))
        # `period` попал сюда не для полноты: рендер печатает его датировкой
        # («данные за 2026-07»), поэтому несверенное поле было бы вторым каналом
        # для числа — модель написала бы «данные за 921», и валидатор молчал.
        for key in ("fact", "plan", "delta", "as_of", "trend",
                    "period", "granularity", "period_partial"):
            if m.get(key) != reference.get(key):
                v.append(Violation(
                    "value_mismatch",
                    "значение «{0}» расходится с отчётом: в повестке «{1}», в отчёте «{2}»".format(
                        key, m.get(key), reference.get(key)),
                    field=field))
    return v


def validate(agenda: Dict[str, Any],
             expected_metric_ids: Optional[Iterable[str]] = None,
             manifest: Optional[Dict[str, Any]] = None,
             metrics_report: Optional[Dict[str, Any]] = None) -> List[Violation]:
    """Фаза 1 — по agenda.json. Пустой список = форма цела."""
    v: List[Violation] = []
    if metrics_report is not None:
        v.extend(check_against_report(agenda, metrics_report))

    check_schema(agenda, schema(), "", v)
    for block in ("meeting", "frame", "metrics", "tasks", "focus", "questions", "flags"):
        if block not in agenda:
            v.append(Violation("block_missing", "нет блока каркаса: {0}".format(block), field=block))
    if any(x.code == "block_missing" for x in v):
        return v

    if len(agenda["focus"]) > MAX_FOCUS:
        v.append(Violation("focus_limit", "фокус-пунктов {0}, максимум {1}".format(len(agenda["focus"]), MAX_FOCUS), field="focus"))
    if len(agenda["questions"]) > MAX_QUESTIONS:
        v.append(Violation("questions_limit", "вопросов {0}, максимум {1}".format(len(agenda["questions"]), MAX_QUESTIONS), field="questions"))

    metrics = agenda["metrics"]
    focus_metric_ids = set()
    for item in agenda["focus"]:
        focus_metric_ids.update(item.get("metric_ids") or [])

    # Полнота перечня — на ней стоит весь strict.
    if expected_metric_ids is None:
        v.append(Violation("expected_list_missing",
                           "перечень метрик объекта не передан — полноту проверить нечем", field="metrics"))
    else:
        expected = set(expected_metric_ids)
        covered = set()
        for m in metrics:
            covered.update(m.get("collapsed_names") or [m.get("metric_id")])
        missing = expected - covered
        if missing:
            v.append(Violation("metric_list_incomplete",
                               "метрики объекта исчезли из повестки: {0}".format(", ".join(sorted(missing))),
                               field="metrics"))

    for i, m in enumerate(metrics):
        field = "metrics[{0}]".format(i)
        names = m.get("collapsed_names") or []
        if names:
            if len(names) < 2:
                v.append(Violation("collapse_singleton", "свёртка из одной метрики — это не агрегат", field=field))
            hidden = focus_metric_ids.intersection(names)
            if hidden:
                v.append(Violation("collapse_hides_focus",
                                   "в свёртку попали метрики из фокус-пунктов: {0}".format(", ".join(sorted(hidden))),
                                   field=field))
            if any(m.get(k) is not None for k in NUMERIC_FIELDS):
                v.append(Violation("collapse_carries_number", "агрегатная строка несёт число", field=field))

        status = m.get("display_status")
        axes = (m.get("availability"), m.get("freshness"), m.get("verification"))
        if not status:
            v.append(Violation("status_missing", "у метрики нет display_status", field=field))
            continue

        # Статус ПЕРЕСЧИТЫВАЕТСЯ: подложный «актуально» при расхождении сверки
        # иначе выводит несверённое число, и вся матрица ниже бесполезна.
        if all(axes):
            try:
                expected_status = asm.derive_display_status(*axes)
            except asm.AssembleError as exc:
                v.append(Violation("impossible_axes", exc.message, field=field))
                expected_status = None
            if expected_status and expected_status != status:
                v.append(Violation(
                    "status_not_derived",
                    "статус «{0}» не выводится из осей ({1}) — по таблице приоритетов должен быть «{2}»".format(
                        status, ", ".join(axes), expected_status),
                    field=field,
                ))
                status = expected_status  # дальше судим по истинному статусу

        has_number = any(m.get(k) is not None for k in NUMERIC_FIELDS)
        has_as_of = bool(m.get("as_of"))
        if status in STATUS_WITHOUT_NUMBER:
            if has_number:
                v.append(Violation("number_without_verification",
                                   "статус «{0}», а число выводится".format(status), field=field))
            if m.get("trend"):
                v.append(Violation("derived_without_verification",
                                   "статус «{0}», а тренд выводится".format(status), field=field))
        elif status in STATUS_REQUIRING_NUMBER and m.get("fact") is None and not names:
            v.append(Violation("number_required", "статус «{0}» требует числа".format(status), field=field))
        if status in STATUS_WITHOUT_AS_OF:
            if has_as_of:
                v.append(Violation("as_of_forbidden", "статус «{0}» не может нести датировку".format(status), field=field))
        elif status in STATUS_REQUIRING_AS_OF and not has_as_of and not m.get("period") and not names:
            # Период — законная датировка наравне с датой среза: вертикаль знает
            # его всегда, а `as_of` не выдаёт до пакета Э0-B. Требовать здесь
            # именно дату среза значило бы резать исправную строку: значение за
            # закрытый июль датировано июлем, даже если книга не сообщает, когда
            # её последний раз пересчитывали.
            v.append(Violation("as_of_required",
                               "статус «{0}» требует датировки: ни даты среза, ни периода".format(status),
                               field=field))

        if (m.get("delta") is not None or m.get("trend")) and not m.get("composition_confirmed"):
            v.append(Violation("derived_without_composition",
                               "Δ или тренд при неподтверждённом составе разреза: сравнение периодов невалидно",
                               field=field))

    v.extend(check_tasks(agenda, manifest))
    v.extend(check_focus_and_questions(agenda, manifest))

    known_metric_ids: List[str] = []
    hidden_metric_ids: List[str] = []
    for m in metrics:
        names = m.get("collapsed_names") or [m.get("metric_id")]
        known_metric_ids.extend(names)
        if m.get("display_status") in STATUS_WITHOUT_NUMBER:
            hidden_metric_ids.extend(names)
    for field, text in prose_fields(agenda):
        v.extend(check_tokens(text, field, known_metric_ids, hidden_metric_ids))
        rest = strip_allowed(text)
        hit = DIGIT_RE.search(rest)
        if hit:
            v.append(Violation("literal_number_in_prose",
                               "литеральная цифра в прозе («…{0}…»): значение пишется токеном".format(
                                   rest[max(0, hit.start() - 15):hit.start() + 15].strip()),
                               field=field))
        low = text.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in low:
                v.append(Violation("forbidden_claim",
                                   "запрещённая формулировка «{0}»: статус говорит об источнике".format(phrase),
                                   field=field))
                break

    if "checks_skipped" not in agenda["flags"]:
        v.append(Violation("checks_skipped_missing", "нет flags.checks_skipped", field="flags"))
    return v


def check_tasks(agenda: Dict[str, Any], manifest: Optional[Dict[str, Any]]) -> List[Violation]:
    v: List[Violation] = []
    readable = readable_sources(manifest)
    if readable is None:
        v.append(Violation("manifest_missing",
                           "чек-лист источников не передан — провенанс пунктов проверить нечем",
                           field="tasks"))
    undated = 0
    unowned = 0
    for i, t in enumerate(agenda["tasks"]):
        field = "tasks[{0}]".format(i)
        ref = t.get("source_ref")
        if not ref:
            v.append(Violation("task_without_source", "пункт без источника: нет источника — нет пункта", field=field))
        elif readable is not None and ref not in readable:
            # Сочинённый путь — не опора. Правдивость прочтения судит judge,
            # но непрочитанный источник обязан резаться кодом.
            v.append(Violation("source_not_in_manifest",
                               "источник «{0}» не значится прочитанным в чек-листе".format(ref), field=field))
        origin = t.get("date_origin")
        if t.get("source_date"):
            if not origin or origin == "undatable":
                v.append(Violation("date_origin_missing", "дата есть, а её происхождение не названо", field=field))
        else:
            undated += 1
            if origin != "undatable":
                v.append(Violation("undated_task_unmarked", "пункт без даты не помечен как недатируемый", field=field))
        if not t.get("owner_source"):
            unowned += 1

    flags = agenda["flags"]
    if undated != (flags.get("undated_tasks_count") or 0):
        v.append(Violation("undated_count_mismatch",
                           "пунктов без даты {0}, во flags {1}".format(undated, flags.get("undated_tasks_count")),
                           field="flags.undated_tasks_count"))
    # Владелец обязателен так же, как дата: неизвестен — пункт остаётся, но
    # факт учтён и виден, а не растворён в тексте.
    if unowned != (flags.get("unowned_tasks_count") or 0):
        v.append(Violation("unowned_count_mismatch",
                           "пунктов без владельца {0}, во flags {1}".format(unowned, flags.get("unowned_tasks_count")),
                           field="flags.unowned_tasks_count"))
    stale_actual = [i for i, t in enumerate(agenda["tasks"]) if t.get("stale")]
    if stale_actual != list(flags.get("stale_tasks") or []):
        v.append(Violation("stale_flags_mismatch", "flags.stale_tasks расходится с пометками пунктов",
                           field="flags.stale_tasks"))
    return v


def check_focus_and_questions(agenda: Dict[str, Any], manifest: Optional[Dict[str, Any]]) -> List[Violation]:
    v: List[Violation] = []
    readable = readable_sources(manifest)
    for i, q in enumerate(agenda["questions"]):
        if q.get("decision_owner") and not q.get("owner_source_ref"):
            v.append(Violation("owner_without_source",
                               "владелец решения назван без источника", field="questions[{0}]".format(i)))
    for i, item in enumerate(agenda["focus"]):
        field = "focus[{0}]".format(i)
        evidence = item.get("evidence") or []
        if not evidence:
            v.append(Violation("focus_without_evidence", "фокус-пункт без опоры на факт", field=field))
        for j, ev in enumerate(evidence):
            sub = "{0}.evidence[{1}]".format(field, j)
            if not ev.get("path") or not ev.get("date"):
                v.append(Violation("evidence_incomplete", "опора без пути или без даты", field=sub))
            elif readable is not None and ev["path"] not in readable:
                v.append(Violation("evidence_not_in_manifest",
                                   "опора «{0}» не значится прочитанной в чек-листе".format(ev["path"]), field=sub))
        if not item.get("check_id"):
            v.append(Violation("focus_without_check", "не названа проверка, давшая сигнал", field=field))
    return v


# --------------------------------------------------------------------------- #
# Фаза 2
# --------------------------------------------------------------------------- #


def visible_length(text: str) -> int:
    """Длина текста ровно в том виде, в каком его увидит руководитель.

    Считается по факту канала (rich, `sendRichMessage`): разметка, которую он
    рисует, места на экране не занимает — решётки заголовка, звёздочки жирного,
    подчёркивания курсива, скобки чекбокса, горизонтальный разделитель и
    строка-разделитель таблицы. Markdown-ссылка занимает место ТЕКСТОМ: rich
    отдаёт её блоком `{type: url, text, url}` и печатает подпись, а адрес
    показывает при открытии. Плоский канал слал ссылку целиком вместе с URL, и
    счёт по прежнему правилу резал бы законную повестку за чужую длину.

    Пайпы строк таблицы намеренно ОСТАЮТСЯ в счёте: сами они не видны, но
    таблица рисуется колонками и занимает на экране больше, чем её текст
    подряд. Дешёвая аппроксимация ширины лучше, чем счёт, который врёт в
    меньшую сторону, — гейт объёма защищает первый экран телефона.
    """
    out = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    out = re.sub(r"\*\*([^*]*)\*\*", r"\1", out)
    out = re.sub(r"__([^_]*)__", r"\1", out)
    out = re.sub(r"`([^`]*)`", r"\1", out)
    out = re.sub(r"^- \[ \] ", "- ", out, flags=re.M)
    out = re.sub(r"^#{1,6} ", "", out, flags=re.M)
    out = re.sub(r"^---$", "", out, flags=re.M)
    # Строка-разделитель GFM-таблицы (`|---|:--:|`) в рендере не появляется
    # вовсе — она разметка формата, а не содержание строки. Поэтому снимается
    # вместе с переводом строки: за ней не остаётся даже пустой строки.
    # Класс без `\s`: перевод строки в нём позволил бы матчу перескочить на
    # следующую строку таблицы и съесть её начало. Дефис или двоеточие
    # обязательны — иначе строка данных из пустых ячеек (`| | | |`) сошла бы за
    # разметку и выпала из счёта.
    out = re.sub(r"^\|[ \t:|-]*[:-][ \t:|-]*\|[ \t]*\n?", "", out, flags=re.M)
    return len(out.strip())


def screen_head(rendered: str, boundary: str) -> str:
    """Часть повестки до блока фокуса.

    Граница ищется ТОЛЬКО как начало строки: заголовок — структурный элемент, и
    та же фраза внутри задачи или рамки границей не является. Прежний поиск по
    подстроке обрезал текст на первом попавшемся вхождении, из-за чего объём
    мерился по укороченному куску и переполнение проходило незамеченным.
    """
    if not boundary:
        return rendered
    # Строка обязана СОВПАДАТЬ с заголовком целиком, а не начинаться с него:
    # «## ⚡ На чём сфокусироваться — это цитата, не блок» иначе принимается за
    # настоящий заголовок, и всё, что ниже, из подсчёта выпадает.
    match = re.search(r"^" + re.escape(boundary) + r"[ \t]*$", rendered, flags=re.M)
    return rendered[:match.start()] if match else rendered


def validate_text(rendered: str, boundary: str, limit: int = SCREEN_LIMIT_CHARS) -> List[Violation]:
    """Фаза 2: объём до блока фокуса. Границу задаёт рендер — он её владелец."""
    length = visible_length(screen_head(rendered, boundary))
    if length > limit:
        return [Violation("screen_overflow",
                          "до блока фокуса {0} видимых символов при лимите {1}".format(length, limit),
                          field="rendered")]
    return []


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Валидатор формы повестки.")
    parser.add_argument("--agenda", help="путь к agenda.json (по умолчанию stdin)")
    parser.add_argument("--expected", help="JSON со списком metric_id объекта")
    parser.add_argument("--sources", help="manifest источников — включает проверку провенанса")
    parser.add_argument("--rendered", help="отрендеренный текст — включает фазу 2")
    parser.add_argument("--boundary", default="", help="заголовок блока фокуса")
    parser.add_argument("--limit", type=int, default=SCREEN_LIMIT_CHARS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    def read(path: Optional[str], what: str) -> Any:
        if not path:
            return None
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"ok": False, "error": "{0}_broken".format(what), "message": str(exc)}, ensure_ascii=False))
            raise SystemExit(2)

    try:
        raw = Path(args.agenda).read_text(encoding="utf-8") if args.agenda else sys.stdin.read()
        agenda = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": "input_broken", "message": str(exc)}, ensure_ascii=False))
        return 2

    payload_expected = read(args.expected, "expected")
    expected = payload_expected if isinstance(payload_expected, list) else (
        payload_expected.get("metric_ids") if payload_expected else None)
    manifest = read(args.sources, "sources")

    violations = validate(agenda, expected, manifest)
    if args.rendered:
        try:
            violations += validate_text(Path(args.rendered).read_text(encoding="utf-8"), args.boundary, args.limit)
        except OSError as exc:
            print(json.dumps({"ok": False, "error": "rendered_unreadable", "message": str(exc)}, ensure_ascii=False))
            return 2

    payload = {"ok": not violations, "violations": [x.as_dict() for x in violations]}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif not violations:
        print("Форма цела: нарушений нет.")
    else:
        print("Нарушений формы: {0}".format(len(violations)))
        for x in violations:
            print("  · [{0}] {1} — {2}".format(x.code, x.field or "-", x.msg))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
