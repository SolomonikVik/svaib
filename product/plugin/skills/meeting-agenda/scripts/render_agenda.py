#!/usr/bin/env python3
"""render_agenda.py — agenda.json → текст повестки + пост-проверка объёма.

Владеет тремя вещами, которых нет ни в схеме, ни в валидаторе:
  1. НОРМАТИВНЫМ ПОРЯДКОМ БЛОКОВ — константа BLOCK_ORDER, покрытая тестом.
     Схема порядок полей не проверяет и источником нормы быть не может.
  2. человеческими формулировками статусов деградации;
  3. раскрытием токенов `{metric:…}` / `{count:…}` из машинных полей.

Токен метрики, чьё число скрыто статусом, НЕ раскрывается — иначе ложное число
доедет до руководителя тем каналом, который токены и закрывали.

Коды возврата: 0 — отрендерено и объём в норме; 1 — объём превышен; 2 — usage/IO.

Stdlib-only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import assemble_agenda as asm  # noqa: E402  — владелец правил отклонения и статусов
import validate_agenda as form  # noqa: E402  — лежит рядом, путь добавлен выше

# Нормативный порядок блоков. Повестка ВСЕГДА открывается рамкой объекта
# управления — даже когда встреча операционная и «все всё помнят»: всё ниже
# читается как ответ на вопрос «двигает ли это к цели». Перестановка = дефект
# продукта, поэтому константа покрыта тестом.
BLOCK_ORDER = ("header", "frame", "tasks", "focus", "questions")

# Заголовки — markdown-заголовками, а не жирной строкой: повестка уходит
# rich-каналом (`sendRichMessage`), который рисует GFM. Жирная строка в нём
# остаётся абзацем и в оглавлении сообщения не участвует.
FOCUS_HEADING = "## ⚡ На чём сфокусироваться"
QUESTIONS_HEADING = "## Что должно быть решено"
TASKS_HEADING = "## Задачи и прогресс"

# Зазор между секциями — разделителем, а не пустой строкой: rich схлопывает
# пустые блоки рядом с заголовками, и секции слипаются (правило канала,
# проверено на живом рендере).
BLOCK_SEPARATOR = "---"

# Человеческие формулировки закрытого списка статусов (level.md). Машинные
# идентификаторы живут в схеме; здесь — то, что видит руководитель.
STATUS_TEXT = {
    "current": "",
    "outdated": "данные на {as_of}",
    "as_of_unknown": "на какую дату актуально — источник не сообщает",
    "no_value": "значений в источнике нет",
    "value_error": "значение в источнике посчитано с ошибкой",
    "source_unavailable": "источник недоступен на момент сборки",
    # Две формулировки, которые руководитель должен различать: первая —
    # незакрытый онбординг (метрике не назначен источник, это его решение),
    # вторая — расхождение книги с раскладкой (это наша работа).
    "source_unbound": "источник этой метрике не назначен",
    "blocked": "чтение остановлено: книга разошлась с раскладкой",
    "unverified": "сверка не сошлась — число не показываю",
    "verification_not_run": "сверить с источником не удалось",
}

TOKEN_RE = form.TOKEN_RE
DASH = "—"


#: Сколько знаков после запятой показывать. Ключ — единица метрики из паспорта.
#: Правило нужно потому, что источник отдаёт то, что посчитала формула:
#: `12.83018868` в колонке роста читается как точность, которой нет, и занимает
#: место, которое в узкой таблице стоит дорого.
DECIMALS_BY_UNIT = (
    (("%", "процент"), 1),          # доли процента руководителю не нужны
    (("шт", "клиент", "чел", "штук"), 0),   # счётчики целые по природе
)
#: Деньги и всё прочее — без дробной части: копейки в управленческой таблице
#: не решают ничего, а разряд решает.
DEFAULT_DECIMALS = 0


def decimals_for(unit: Optional[str]) -> int:
    text = (unit or "").strip().lower()
    for markers, decimals in DECIMALS_BY_UNIT:
        if any(marker in text for marker in markers):
            return decimals
    return DEFAULT_DECIMALS


def format_number(value: Optional[float], unit: Optional[str] = None) -> str:
    """Число для таблицы: округление по единице метрики, без хвостов формулы."""
    if value is None:
        return DASH
    if isinstance(value, bool):  # pragma: no cover — защита от подмены типа
        return DASH
    decimals = decimals_for(unit)
    rounded = round(float(value), decimals)
    if decimals == 0 or float(rounded).is_integer():
        return "{0}".format(int(round(rounded)))
    return "{0:.{1}f}".format(rounded, decimals)


def metric_value_text(metric: Dict[str, Any]) -> str:
    """Значение метрики строкой. Скрытое статусом число не появляется никогда."""
    status = metric.get("display_status")
    if status in form.STATUS_WITHOUT_NUMBER:
        return DASH
    return format_number(metric.get("fact"), metric.get("unit"))


def status_note(metric: Dict[str, Any]) -> str:
    status = metric.get("display_status", "")
    if status == "outdated":
        # Не «данные за 2026-06», а прямой ответ на вопрос, который читатель
        # задаёт таблице: за отчётный период данных нет. Период последнего
        # известного значения называется тут же — он и есть содержание ответа.
        period = metric.get("period")
        if period:
            return "за отчётный период данных нет; последнее значение — {0}".format(period)
        return "за отчётный период данных нет"
    template = STATUS_TEXT.get(status, "")
    if not template:
        return ""
    # Датировка: дата среза, если источник её сообщает, иначе период значения.
    # «Данные за 2026-07» — то, что вертикаль знает точно; «на какую дату
    # актуально — источник не сообщает» при известном периоде звучит как
    # неисправность, хотя число датировано и полностью пригодно.
    if metric.get("as_of"):
        return template.format(as_of=metric["as_of"])
    if metric.get("period"):
        return "данные за {0}".format(metric["period"])
    return template.format(as_of="неизвестную дату")


def metric_index(agenda: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Метрики по id, включая свёрнутые.

    Свёрнутая метрика доступна токену намеренно: свёртка — способ уместить
    перечень в экран, а не причина потерять сверенное значение в прозе. Число
    гасится статусом, а не тем, попала строка в агрегат или нет.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for row in agenda.get("metrics", []):
        for name in (row.get("collapsed_names") or []):
            out.setdefault(name, row)
        if not row.get("collapsed_names"):
            out[row.get("metric_id")] = row
    return out


def expand_tokens(text: str, agenda: Dict[str, Any]) -> str:
    """Подставляет числа из машинных полей. Скрытая метрика остаётся скрытой."""
    metrics = metric_index(agenda)
    flags = agenda.get("flags", {})

    def replace(match: "re.Match[str]") -> str:
        kind, body = match.group(1), match.group(2).strip()
        if kind == "count":
            value = flags.get(body)
            if isinstance(value, list):
                return str(len(value))
            return str(value) if value is not None else DASH
        metric_id = body.split(":")[0].strip()
        metric = metrics.get(metric_id)
        if not metric:
            return DASH
        if metric.get("display_status") in form.STATUS_WITHOUT_NUMBER:
            # Токен скрытой метрики не раскрывается — это часть fail-closed,
            # а не косметика рендера.
            return DASH
        return format_number(metric.get("fact"), metric.get("unit"))

    return TOKEN_RE.sub(replace, text)


# --------------------------------------------------------------------------- #
# Блоки
# --------------------------------------------------------------------------- #


def path_ref(value: str) -> str:
    """Путь в базе — inline-кодом.

    Rich распознаёт `sales/README.md` как адрес и превращает в кликабельную
    ссылку в никуда: руководитель видит подчёркнутый текст, который никуда не
    ведёт. Inline-код снимает распознавание и заодно читается как путь.
    """
    return "`{0}`".format(value)


def render_header(agenda: Dict[str, Any]) -> List[str]:
    meeting = agenda["meeting"]
    lines = ["# {0} · {1}".format(meeting.get("type", "встреча"), meeting.get("date", ""))]
    if meeting.get("prev_meeting_date"):
        prev = "Прошлая встреча — {0}".format(meeting["prev_meeting_date"])
        if meeting.get("prev_protocol_ref"):
            prev += ", протокол: {0}".format(path_ref(meeting["prev_protocol_ref"]))
        lines.append(prev + ".")
    return lines


def sort_metrics(metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Красное и развернувшееся вверху, свёртки — вниз одной строкой."""
    def key(m: Dict[str, Any]) -> tuple:
        collapsed = 1 if m.get("collapsed_names") else 0
        # Отклонение считается тем же правилом, что и у свёртки: строка с
        # разошедшимися планом и фактом обязана быть вверху, даже когда Δ не
        # выводится (состав не подтверждён).
        deviation = 0 if asm.has_deviation(m) else 1
        return (collapsed, deviation, m.get("name", ""))

    return sorted(metrics, key=key)


def render_frame(agenda: Dict[str, Any]) -> List[str]:
    frame = agenda["frame"]
    lines: List[str] = []
    if frame.get("goal_text"):
        lines.append(expand_tokens(frame["goal_text"], agenda))
    if frame.get("goal_ref"):
        # Пустая строка обязательна: соседние строки без маркера rich склеивает
        # в один абзац (мягкий разрыв GFM), и адрес цели прилипал к её тексту.
        if lines:
            lines.append("")
        lines.append("Цель: {0}".format(path_ref(frame["goal_ref"])))
    elif not frame.get("goal_text"):
        lines.append("У объекта встречи нет привязанной цели в базе.")

    metrics = agenda.get("metrics") or []
    if metrics:
        lines.append("")
        # Δ и тренд — нормативные колонки каркаса. Их отсутствие в таблице
        # означало бы, что сигнал R3 («состав метрики изменился») исчезает без
        # следа даже тогда, когда состав подтверждён и сравнение законно.
        lines.append("| Метрика | План | Факт | Δ | Тренд | Статус |")
        lines.append("|---|---|---|---|---|---|")
        for m in sort_metrics(metrics):
            note = status_note(m)
            plan = DASH if m.get("plan") is None else format_number(m["plan"], m.get("unit"))
            if m.get("plan_conflict"):
                plan = "{0} (планов несколько)".format(DASH)
            delta = DASH if m.get("delta") is None else format_number(m["delta"], m.get("unit"))
            trend = m.get("trend") or DASH
            lines.append("| {0} | {1} | {2} | {3} | {4} | {5} |".format(
                m.get("name", m.get("metric_id", "")), plan, metric_value_text(m), delta, trend, note or "в норме"))
    if frame.get("summary_line"):
        lines.append("")
        lines.append(expand_tokens(frame["summary_line"], agenda))
    return lines


def stale_line(stale: int, total: int) -> str:
    """Агрегат протухания. Формулировка меняется по числу — «1 из 1» не пишем."""
    if stale == 1 and total == 1:
        return "Единственный пункт не подтверждался с прошлой встречи — по нему вопрос на сверку, а не прогресс."
    if stale == total:
        return "Все пункты не подтверждались с прошлой встречи — по ним вопросы на сверку, а не прогресс."
    return "{0} из {1} пунктов не подтверждались с прошлой встречи — по ним вопросы на сверку, а не прогресс.".format(
        stale, total)


def render_tasks(agenda: Dict[str, Any]) -> List[str]:
    tasks = agenda.get("tasks") or []
    if not tasks:
        return []
    lines = [TASKS_HEADING]
    for task in tasks:
        marks = []
        if task.get("stale"):
            marks.append("статус не подтверждался")
        if task.get("date_origin") == "undatable":
            marks.append("дата не выводится")
        if not task.get("owner_source"):
            # Норма требует «дата и владелец, иначе пункт не пишется». Резать
            # пункт значило бы терять содержание, поэтому он остаётся — но
            # молча остаться не может: неизвестный владелец назван вслух.
            marks.append("владелец не назначен")
        suffix = " ({0})".format("; ".join(marks)) if marks else ""
        owner = " — {0}".format(task["owner_source"]) if task.get("owner_source") else ""
        date = " · {0}".format(task["source_date"]) if task.get("source_date") else ""
        lines.append("- {0}{1}{2}{3}".format(expand_tokens(task["text"], agenda), owner, date, suffix))

    stale_count = len(agenda["flags"].get("stale_tasks") or [])
    if stale_count:
        # Агрегат считается ПО ПУНКТАМ: «база не обновлялась с {дата}» при одном
        # пункте от июня и девяти вчерашних объявила бы устаревшей всю базу.
        lines.append("")
        lines.append(stale_line(stale_count, len(tasks)))
    return lines


def render_focus(agenda: Dict[str, Any]) -> List[str]:
    """Блок фокуса. Недостача данных называется по-человечески, без внутренних id.

    Перечень пропущенных проверок раньше печатался целиком — с нашими
    идентификаторами (`attention-skew`, `blind-spot`) и формулировками вроде
    «покрытие шапками 0%». Руководителю это не значит ничего: инженерный отчёт
    в управленческом документе. Молчать тоже нельзя — иначе повестка выглядит
    полной, когда половина проверок не отработала.

    Поэтому наружу идёт одна строка на понятном языке, и только когда недостача
    управленчески значима: нечем измерить движение к цели или нечем свериться с
    прошлой встречей. Полный перечень остаётся в артефакте прогона — он для нас.
    """
    focus = agenda.get("focus") or []
    skipped = agenda["flags"].get("checks_skipped") or []
    note = skipped_note(skipped, has_metrics=bool(agenda.get("metrics")))
    if not focus and not note:
        return []
    lines = [FOCUS_HEADING]
    for item in focus:
        lines.append("- {0}".format(expand_tokens(item["text"], agenda)))
    if not focus:
        lines.append("- Острых сигналов не выделено.")
    if note:
        lines.append("")
        lines.append(note)
    return lines


#: Что означает пропущенная проверка на человеческом языке. Ключ — наш
#: идентификатор, значение — недостача, которую видит руководитель. Проверки, у
#: которых значения нет, наружу не выходят вовсе: `attention-skew` и
#: `blind-spot` отключаются на любой клиентской базе (покрытие шапками считается
#: по строке, которой в клиентских протоколах нет), и сообщать о них каждый
#: день — приучать не читать.
SKIPPED_MEANING: Dict[str, str] = {
    # Формулировки описывают недостачу С ТОЧКИ ЗРЕНИЯ ЧИТАТЕЛЯ, а не наш код.
    # «Значений метрик нет» было неточно: значения приходят, не хватает плана и
    # прошлого периода — то есть сравнивать не с чем.
    "metric-agenda": "метрики не с чем сравнить — нет плана и прошлого периода",
    "figure-mismatch": "одну метрику не с чем сверить между источниками",
    "tasks-goals": "активные задачи объекта не найдены",
    "owner-due": "активные задачи объекта не найдены",
    "goal-metric": "у целей не назначены метрики",
    "repeat-slip": "протоколы прошлых встреч не прочитаны",
}


#: Причины, которые осмысленны только при непустом перечне метрик. Когда метрик
#: у объекта нет вовсе, «метрики не с чем сравнить» — не недостача данных, а
#: пересказ того, что и так сказано блоком фокуса.
METRIC_DEPENDENT = frozenset({"metric-agenda", "figure-mismatch"})


def skipped_note(skipped: List[Dict[str, Any]], has_metrics: bool = True) -> str:
    """Одна строка про недостачу данных — или пусто, если сказать нечего."""
    reasons = []
    for item in skipped:
        check_id = item.get("check_id")
        if not has_metrics and check_id in METRIC_DEPENDENT:
            continue
        meaning = SKIPPED_MEANING.get(check_id)
        if meaning and meaning not in reasons:
            reasons.append(meaning)
    if not reasons:
        return ""
    return "Часть повестки собрать не удалось: {0}.".format("; ".join(reasons))


def render_questions(agenda: Dict[str, Any]) -> List[str]:
    questions = agenda.get("questions") or []
    if not questions:
        return []
    lines = [QUESTIONS_HEADING]
    for i, q in enumerate(questions, 1):
        owner = " (решает {0})".format(q["decision_owner"]) if q.get("decision_owner") else ""
        lines.append("{0}. {1}{2}".format(i, expand_tokens(q["text"], agenda), owner))
    return lines


RENDERERS = {
    "header": render_header,
    "frame": render_frame,
    "tasks": render_tasks,
    "focus": render_focus,
    "questions": render_questions,
}


def render(agenda: Dict[str, Any]) -> str:
    """Собирает текст строго в нормативном порядке блоков."""
    chunks: List[str] = []
    for block in BLOCK_ORDER:
        lines = RENDERERS[block](agenda)
        if lines:
            chunks.append("\n".join(lines))
    joiner = "\n\n{0}\n\n".format(BLOCK_SEPARATOR)
    return joiner.join(chunks) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Рендер повестки из agenda.json.")
    parser.add_argument("--agenda", required=True, help="путь к agenda.json")
    parser.add_argument("--out", help="куда записать текст (по умолчанию stdout)")
    parser.add_argument("--limit", type=int, default=form.SCREEN_LIMIT_CHARS, help="лимит видимых символов до блока фокуса")
    parser.add_argument("--json", action="store_true", help="машинный вывод")
    args = parser.parse_args(argv)

    try:
        agenda = json.loads(Path(args.agenda).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": "input_broken", "message": str(exc)}, ensure_ascii=False))
        return 2

    text = render(agenda)
    # Фаза 2 валидатора: границу участка задаёт рендер — он владелец заголовка.
    violations = form.validate_text(text, FOCUS_HEADING, args.limit)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")

    payload = {
        "ok": not violations,
        "chars_visible": form.visible_length(form.screen_head(text, FOCUS_HEADING)),
        "limit": args.limit,
        "violations": [x.as_dict() for x in violations],
        "out": args.out,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif not args.out:
        print(text)
    if violations:
        for x in violations:
            print("❌ {0}: {1}".format(x.code, x.msg), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
