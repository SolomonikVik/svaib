#!/usr/bin/env python3
"""run_vertical.py — раннер линии данных вертикали metrics.

Единый вход обеих сред (интерактивный gateway повестки и облачный Job):

    python3 run_vertical.py --base <база клиента> --request <run>/metrics-request.json \\
        --snapshot-dir <run>/snapshots/ --out <run>/metrics-report.json

Производит отчёт `metrics-report` v1 — контракт границы «вертикаль ↔ потребитель»
(dev/metrics/boundary.md §3, схема schema/metrics-report.schema.json). Дизайн реализации —
dev/metrics/runner-spec.md.

Коды возврата (schema/error-codes.json): 0 — отчёт построен, в том числе сплошь
деградированный; 1 — отчёт построить нельзя, JSON {error, message} в stderr; 2 — usage/IO.

Раннер не ходит в сеть, ничего не пишет кроме --out и читает только внутри --base и
--snapshot-dir.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import extractor  # noqa: E402
import metrics_catalog as catalog_mod  # noqa: E402
import verifier  # noqa: E402
from source_map import normalize_label  # noqa: E402
from source_map import BaseConfigError, canonical_source, load_source_map  # noqa: E402

CONTRACT_VERSION = "1.0.0"
SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"
MANIFEST_FILENAME = "snapshot-manifest.json"
REPORT_SIZE_LIMIT = 1024 * 1024  # sanity-лимит облака, принят при заморозке 04.08


class Refusal(Exception):
    """Именованный отказ прогона: отчёт построить нельзя."""

    def __init__(self, code, message, rc=1):
        super().__init__(message)
        self.code = code
        self.message = message
        self.rc = rc


# --------------------------------------------------------------------------------------
# Периоды. ВНИМАНИЕ: это ВТОРАЯ, намеренно независимая реализация — validate_contract.py
# считает то же самое своим кодом и сверяет результат. Дедупликация этих двух реализаций
# ЗАПРЕЩЕНА: общий код превратил бы проверку контракта в сравнение величины с самой собой
# (runner-spec §7). Расхождение — сигнал, его ловят общие фикстуры.
# --------------------------------------------------------------------------------------

def current_period(granularity, meeting_date):
    """Период, в который попадает дата встречи (он же — незакрытый)."""
    d = dt.date.fromisoformat(meeting_date)
    if granularity == "month":
        return f"{d.year:04d}-{d.month:02d}"
    if granularity == "week":
        y, w, _ = d.isocalendar()
        return f"{y:04d}-W{w:02d}"
    if granularity == "quarter":
        return f"{d.year:04d}-Q{(d.month - 1) // 3 + 1}"
    return f"{d.year:04d}"


def last_closed_period(granularity, meeting_date):
    """Последний ЗАКРЫТЫЙ период в шкале метрики относительно даты встречи."""
    d = dt.date.fromisoformat(meeting_date)
    if granularity == "month":
        prev = d.replace(day=1) - dt.timedelta(days=1)
        return f"{prev.year:04d}-{prev.month:02d}"
    if granularity == "week":
        last_sunday = d - dt.timedelta(days=d.isoweekday())
        y, w, _ = last_sunday.isocalendar()
        return f"{y:04d}-W{w:02d}"
    if granularity == "quarter":
        q = (d.month - 1) // 3
        return f"{d.year - 1:04d}-Q4" if q == 0 else f"{d.year:04d}-Q{q}"
    return f"{d.year - 1:04d}"


def previous_period(period, granularity):
    """Период, предшествующий заданному, в той же шкале."""
    if granularity == "month":
        year, month = int(period[:4]), int(period[5:7])
        return f"{year - 1:04d}-12" if month == 1 else f"{year:04d}-{month - 1:02d}"
    if granularity == "quarter":
        year, q = int(period[:4]), int(period[6])
        return f"{year - 1:04d}-Q4" if q == 1 else f"{year:04d}-Q{q - 1}"
    if granularity == "year":
        return f"{int(period) - 1:04d}"
    year, week = int(period[:4]), int(period[6:8])
    if week > 1:
        return f"{year:04d}-W{week - 1:02d}"
    # Неделя 1 предыдущего года: 52 или 53 — спрашиваем календарь, а не угадываем.
    last_week = dt.date(year - 1, 12, 28).isocalendar()[1]
    return f"{year - 1:04d}-W{last_week:02d}"


# --------------------------------------------------------------------------------------
# Оси достоверности — вторая независимая реализация таблиц boundary §4 (см. комментарий
# выше про запрет дедупликации). Правила применяются строго сверху вниз.
# --------------------------------------------------------------------------------------

def derive_availability(row, source_status, is_duplicate, unmapped):
    if row["source"] is None:
        return "source_unbound"
    if source_status in ("unavailable", "no_extractor"):
        return "source_unavailable"
    if source_status == "schema_mismatch" or is_duplicate:
        return "blocked"
    if row["value_status"] in ("div0", "error"):
        return "value_error"
    if row["value_status"] == "missing" or unmapped:
        return "no_value"
    if row["value_status"] == "ok":
        return "value"
    return None  # unmapped_facts: сочетание не покрыто таблицей — отказ прогона


def derive_freshness(row, period_basis, meeting_date):
    if row["fact"] is None:
        return "undatable"
    # Граница закрытого периода существует только при period_basis = closed: при current
    # валидатор её не вычисляет и before_period не ждёт.
    if period_basis == "closed" and row["granularity"] and row["period"]:
        closed = last_closed_period(row["granularity"], meeting_date)
        if row["period"] < closed:
            return "before_period"
    return "undatable" if row["as_of"] is None else "in_period"


def derive_verification(row, source_status, is_duplicate, in_verified, in_unmapped, in_mapping):
    if row["source"] is None or source_status in ("unavailable", "no_extractor"):
        return "not_run"
    if source_status == "schema_mismatch" or is_duplicate or in_mapping:
        return "mismatch"
    if in_verified or in_unmapped:
        return "verified"
    return None  # пара не упомянута ни в одном массиве — нарушение контракта


# --------------------------------------------------------------------------------------
# Вход
# --------------------------------------------------------------------------------------

def load_json_or_refuse(path, code):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise Refusal("usage_error", f"{path} не читается: {exc}", rc=2) from exc
    except (ValueError, RecursionError) as exc:
        # RecursionError — не ValueError: документ с тысячами уровней вложенности иначе
        # уронил бы Job с traceback вместо именованного отказа.
        raise Refusal(code, f"{path}: не является пригодным JSON: {exc}") from exc


def validate_schema(doc, schema_name, code, label):
    import jsonschema

    schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    errors = sorted(
        jsonschema.Draft7Validator(schema).iter_errors(doc), key=lambda e: list(e.absolute_path)
    )
    if errors:
        first = errors[0]
        where = "/".join(map(str, first.absolute_path)) or "<корень>"
        raise Refusal(code, f"{label} не проходит схему: {where}: {first.message}")


def check_paths(args):
    """Границы записи и чтения — до любой работы с данными."""
    base = Path(args.base)
    snapshot_dir = Path(args.snapshot_dir)
    if not base.is_dir():
        raise Refusal("usage_error", f"--base не является каталогом: {args.base}", rc=2)
    if not snapshot_dir.is_dir():
        raise Refusal("usage_error", f"--snapshot-dir не является каталогом: {args.snapshot_dir}", rc=2)
    out = Path(args.out).resolve()
    for other, name in ((args.request, "--request"), (args.manifest, "--manifest")):
        if other and out == Path(other).resolve():
            raise Refusal(
                "usage_error", f"--out совпадает с {name}: отчёт затёр бы вход прогона", rc=2
            )
    for guarded, name in ((base, "--base"), (snapshot_dir, "--snapshot-dir")):
        try:
            out.relative_to(guarded.resolve())
        except ValueError:
            continue
        raise Refusal(
            "usage_error",
            f"--out лежит внутри {name}: запись отчёта изменила бы то, что раннер обязан только читать",
            rc=2,
        )
    if not out.parent.is_dir():
        raise Refusal("usage_error", f"каталог для --out не существует: {out.parent}", rc=2)


def load_manifest(args):
    path = Path(args.manifest) if args.manifest else Path(args.snapshot_dir) / MANIFEST_FILENAME
    if not path.is_file():
        raise Refusal("manifest_invalid", f"манифест не найден: {path}")
    doc = load_json_or_refuse(path, "manifest_invalid")
    validate_schema(doc, "snapshot-manifest.schema.json", "manifest_invalid", "snapshot-manifest")
    return doc


def verify_snapshots(manifest, snapshot_dir):
    """sha256 каждого файла манифеста; {адрес: (путь, запись)}."""
    by_source = {}
    seen_paths = set()
    for entry in manifest["sources"]:
        # Ключ канонизируется той же функцией, что карта и раскладка: добытчик и база —
        # разные авторы, и форма записи адреса у них разъезжается (проверено живьём).
        source = canonical_source(entry["source"])
        if source in by_source:
            raise Refusal("manifest_invalid", f"книга {entry['source']} объявлена в манифесте дважды")
        if entry["path"] in seen_paths:
            # Один файл под двумя адресами: какая книга где — добытчик решать не вправе.
            raise Refusal("manifest_invalid", f"файл {entry['path']} объявлен в манифесте дважды")
        seen_paths.add(entry["path"])
        path = Path(snapshot_dir) / entry["path"]
        # Defense in depth: схема манифеста запрещает подкаталоги в path, но деление
        # Path с абсолютным правым операндом заместило бы каталог целиком, и раннер
        # прочитал бы файл вне контура снимков.
        try:
            path.resolve().relative_to(Path(snapshot_dir).resolve())
        except ValueError as exc:
            raise Refusal(
                "manifest_invalid",
                f"путь {entry['path']!r} уводит за пределы --snapshot-dir",
            ) from exc
        if not path.is_file():
            raise Refusal("snapshot_manifest_mismatch", f"файла {entry['path']} нет в --snapshot-dir")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            raise Refusal(
                "snapshot_manifest_mismatch", f"sha256 файла {entry['path']} разошёлся с манифестом"
            )
        by_source[source] = (path, entry)
    return by_source


def normalize_datetime(value):
    """Манифест фиксирует Z дословно; схема отчёта требует явное смещение."""
    if isinstance(value, str) and value.endswith("Z"):
        return value[:-1] + "+00:00"
    return value


# --------------------------------------------------------------------------------------
# Сборка отчёта
# --------------------------------------------------------------------------------------

def read_pair_value(reading, resolution, requested_period, period_basis, binding=None):
    """Значение пары с fallback на ближайший более ранний заполненный период."""
    entry = resolution.entry
    layout_sheet = reading.layout["sheets"][entry["sheet"]]
    granularity = layout_sheet["granularity"]

    column_problem = column_contract_problem(layout_sheet, binding)
    if column_problem is not None:
        # Читать можно было бы, но нечем сверить выбор колонки — а именно в этом
        # выборе и живёт ошибка, ради которой сверка существует. Число без сверки
        # здесь опаснее его отсутствия.
        #
        # Статус — `missing`, а не `not_read`: «чтения не было при живом
        # источнике» замороженная таблица осей выразить не может, и такой отчёт
        # отвергает валидатор контракта. Причина при этом не теряется — она
        # уходит в `source_ref`, который для «нет значения» как раз и оставлен
        # заполненным.
        return {
            "value_status": "missing",
            "fact": None,
            "period": requested_period,
            "granularity": granularity,
            "baseline": None,
            "source_ref": build_source_ref(entry, None, column_problem),
            "column_label": None,
            "detail": column_problem,
        }

    read = extractor.read_value(reading, entry, requested_period)
    # Причина недостачи факта («период есть, а колонки факта нет») снимается ДО
    # fallback: после подмены периода она уже необъяснима, а человеку нужна
    # именно она — иначе он видит «устарело» и не знает, что за запрошенный месяц
    # в книге стоит прогноз.
    detail = read.detail
    if read.status == "missing":
        earlier = [p for p in extractor.available_periods(reading, entry) if p < requested_period]
        if earlier:
            read = extractor.read_value(reading, entry, max(earlier), strict_guard=False)
    period = read.period if read.period is not None else requested_period

    baseline = None
    if read.value is not None:
        prev = previous_period(period, granularity)
        previous = extractor.read_value(reading, entry, prev, strict_guard=False)
        if previous.status == "ok":
            baseline = {"period": prev, "fact": previous.value, "composition_confirmed": False}
    return {
        "value_status": read.status,
        "fact": read.value,
        "period": period,
        "granularity": granularity,
        "baseline": baseline,
        "source_ref": build_source_ref(entry, read.column_label, detail),
        "column_label": read.column_label,
        "detail": detail,
        # План читается за ТОТ ЖЕ период, что и отданный факт: план текущего
        # месяца рядом с фактом позапрошлого — не отклонение, а два разных
        # разговора в одной строке.
        "plan": extractor.read_plan(reading, entry, period),
    }


def column_contract_problem(layout_sheet, binding):
    """Согласованность сторон по КОЛОНКЕ; None — читать можно.

    Две стороны обязаны говорить об одном: раскладка объявляет роли колонок,
    карта источников называет колонку факта словами книги. Одна сторона без
    другой — не режим, а незаконченный онбординг, и молчать о нём нельзя:
    именно выбор колонки отличает факт от прогноза.
    """
    declares_roles = bool(layout_sheet.get("role_row"))
    expected = getattr(binding, "fact_column_label", None) if binding is not None else None
    if declares_roles and not expected:
        return ("раскладка листа объявляет роли колонок, а карта источников не называет "
                "колонку факта — сверить выбор колонки нечем")
    if expected and not declares_roles:
        return ("карта источников называет колонку факта, а раскладка листа ролей не "
                "объявляет — на этом листе колонка периода одна, сверять нечего")
    return None


def column_mismatch(expected, actual):
    """Разошлись ли объявленная и фактическая колонки. Сравнение нормализованное."""
    if not expected:
        return False
    return normalize_label(expected) != normalize_label(actual)


def build_source_ref(entry, column_label, detail):
    """След прочитанного: лист, строка, колонка и причина недостачи.

    Поле контракта — свободная строка («лист + строка/ячейка текстом»), поэтому
    колонка и причина помещаются в него без диффа границы. Без колонки человек
    не может проверить выбор вообще ничем: у книги в разрезе «период × роль»
    строка одна, а колонок под периодом несколько.
    """
    parts = ["лист «{0}»".format(entry["sheet"]),
             "строка «{0}»".format(" / ".join(entry["labels"]))]
    if column_label:
        parts.append("колонка «{0}»".format(column_label))
    if detail:
        parts.append(detail)
    return ", ".join(parts)


def build_report(args):
    request = load_json_or_refuse(args.request, "request_invalid")
    validate_schema(request, "metrics-request.schema.json", "request_invalid", "metrics-request")
    try:
        dt.date.fromisoformat(request["meeting_date"])
    except ValueError as exc:
        raise Refusal("request_invalid", f"meeting_date {request['meeting_date']!r} — не календарная дата") from exc

    manifest = load_manifest(args)
    if manifest["run_id"] != request["run_id"]:
        raise Refusal(
            "manifest_invalid",
            f"манифест добыт прогоном {manifest['run_id']!r}, запрошен {request['run_id']!r}",
        )
    snapshots = verify_snapshots(manifest, args.snapshot_dir)

    try:
        catalog, files_scanned = catalog_mod.build_catalog(args.base)
    except catalog_mod.CatalogError as exc:
        raise Refusal("base_unreadable", str(exc)) from exc

    # Вход проверяется раньше конфигурации базы: при двух дефектах сразу наружу должна
    # выйти причина, которая ближе к вызывающему, а не «база сломана».
    pairs = [(m["name"], m["file"]) for m in request["metrics"]]
    unknown = [p for p in pairs if p not in catalog]
    if unknown:
        raise Refusal(
            "request_invalid",
            "запрошены пары, которых нет в паспортах базы: "
            + ", ".join(f"{n} ({f})" for n, f in unknown),
        )

    try:
        source_map = load_source_map(args.base)
        layouts = extractor.load_layouts(args.base)
    except BaseConfigError as exc:
        raise Refusal("base_unreadable", str(exc)) from exc

    basis = request["period_basis"]
    duplicates = catalog_mod.duplicate_names(pairs)
    duplicate_pairs = {(name, file) for name, files in duplicates.items() for file in files}

    # Как адрес книги показывается в отчёте. Канонизация — только для сопоставления трёх
    # артефактов между собой; наружу отчёт отдаёт форму, в которой книгу объявил добытчик,
    # а если снимка нет — форму, которой её объявила карта клиента. Иначе отчёт разошёлся бы
    # с манифестом, против которого его судит валидатор контракта: починка одного шва открыла
    # бы соседний.
    #
    # Честное ограничение: пока авторы пишут адрес по-разному, форма в отчёте НЕ инвариант —
    # книга без снимка названа формой карты, а с ним формой добытчика. Снимает это только
    # завершённая миграция (все три автора пишут канон), а не ещё одно правило здесь: любое
    # из них разошлось бы с замороженным валидатором. Ограничение закреплено тестом.
    display_by_source = dict(source_map.written_sources)
    display_by_source.update({canonical_source(e["source"]): e["source"]
                              for e in manifest["sources"]})

    def display_source(source):
        return display_by_source.get(source, source)

    # --- источники запрошенных пар: карта объявляет, манифест приносит, раскладка читает
    bindings = {}
    for pair in pairs:
        bindings[pair] = source_map.binding(pair[0], pair[1], basis)
    needed_sources = sorted({b.source for b in bindings.values() if b is not None})

    # Есть непривязанные пары — читаем и остальные добытые книги клиента, у которых есть
    # раскладка. Иначе повестка направления, где карта источников ещё не заведена (живой
    # дефект A3.5: карта у одного файла из восьми), не увидела бы ни одной сироты, и
    # ремонтный кандидат «ряд найден в книге, привязки в паспорте нет» не появился бы —
    # то есть провал R2 воспроизвёлся бы внутри собственного контракта.
    if any(binding is None for binding in bindings.values()):
        extra = sorted(set(snapshots) & set(layouts) - set(needed_sources))
        needed_sources = sorted(needed_sources + extra)

    readings = {}
    for source in needed_sources:
        snapshot_path = snapshots[source][0] if source in snapshots else None
        try:
            layout = layouts.get(source)
        except BaseConfigError as exc:
            # Конфликт раскладок отложен до этого момента: он срывает прогон только там,
            # где книгу действительно надо прочитать.
            raise Refusal("base_unreadable", str(exc)) from exc
        if layout is None:
            note = getattr(layouts, "unsupported", {}).get(source)
            if note:
                # Источник уйдёт в отчёт штатным `no_extractor` — код ошибки
                # источника в контракте закрытый, и «раскладка новее движка» в
                # него не помещается. Но оператор обязан различать «раскладки
                # нет» и «раскладка есть, движок старый»: первое чинится
                # онбордингом, второе — выкатом образа.
                print("warning: {0}".format(note), file=sys.stderr)
        readings[source] = extractor.read_source(source, layout, snapshot_path)

    # --- сироты сканируются ПЕРВЫМИ: guard, впервые сработавший на скане (лист, который
    #     не читает ни одна запрошенная метрика), обязан заблокировать источник ДО того,
    #     как в отчёт попадут значения и записи verified[] с этого же источника.
    orphan_row = []
    for source in needed_sources:
        reading = readings[source]
        try:
            orphan_row.extend(verifier.collect_orphans(reading, source_map, catalog))
        except extractor.GuardStop as stop:
            reading.status = "schema_mismatch"
            reading.error = ("schema_mismatch", "guard extractor'а остановил чтение")
            reading.detail = stop.detail

    # --- сверка координат и чтение значений; guard роняет источник целиком
    resolutions, values = {}, {}
    for pair, binding in bindings.items():
        if binding is None or pair in duplicate_pairs:
            continue
        reading = readings[binding.source]
        if not reading.readable:
            continue
        try:
            resolutions[pair] = verifier.resolve(pair, binding, reading.layout)
        except ValueError as exc:
            raise Refusal("base_unreadable", str(exc)) from exc

    for source in needed_sources:
        reading = readings[source]
        if not reading.readable:
            continue
        source_pairs = [p for p, b in bindings.items() if b is not None and b.source == source]
        collected = {}
        try:
            for pair in source_pairs:
                resolution = resolutions.get(pair)
                if resolution is None or resolution.verdict == "unmapped":
                    continue
                requested = (
                    current_period if basis == "current" else last_closed_period
                )(reading.layout["sheets"][resolution.entry["sheet"]]["granularity"],
                  request["meeting_date"])
                collected[pair] = read_pair_value(reading, resolution, requested, basis,
                                                  bindings[pair])
                # Сверяем только фактически прочитанную колонку. Без значения
                # сверять нечего: «периода нет» и «за период нет факта» — это
                # недостача данных, и объявлять её расхождением маппинга значит
                # показать «не сверено» там, где верный ответ — «значения нет».
                if collected[pair]["column_label"] and column_mismatch(
                        bindings[pair].fact_column_label, collected[pair]["column_label"]):
                    # Раскладка прочитала не ту колонку, которую объявила карта:
                    # происхождение числа под сомнением ровно так же, как при
                    # съехавшей строке, и решает это потребитель — но со статусом.
                    resolution.verdict = "mapping_mismatch"
                    resolution.actual = dict(
                        resolution.actual,
                        row_label="{0} | колонка «{1}»".format(
                            resolution.actual["row_label"],
                            collected[pair]["column_label"] or "—"),
                    )
                    resolution.expected = dict(
                        resolution.expected,
                        row_label="{0} | колонка «{1}»".format(
                            resolution.expected["row_label"],
                            bindings[pair].fact_column_label),
                    )
        except extractor.GuardStop as stop:
            # Строка съехала или сменился формат числа — перестроена таблица, а не ячейка:
            # источник блокируется целиком, значения не берутся ни по одной его метрике.
            reading.status = "schema_mismatch"
            reading.error = ("schema_mismatch", "guard extractor'а остановил чтение")
            reading.detail = stop.detail
            # И сироты этого источника тоже снимаются: структура книги объявлена
            # перестроенной, значит «ремонтные кандидаты» из неё ничего не доказывают.
            orphan_row = [o for o in orphan_row if o["source"] != source]
            # (о["source"] здесь ещё канонический — форма отчёта проставляется ниже, разом)
            continue
        values.update(collected)

    # --- verification
    verified, unmapped_metric, mapping_mismatch = [], [], []
    for pair, resolution in sorted(resolutions.items()):
        name, file = pair
        if not readings[bindings[pair].source].readable:
            continue
        if resolution.verdict == "verified":
            verified.append({
                "name": name, "file": file,
                "sheet": resolution.actual["sheet"], "row_label": resolution.actual["row_label"],
            })
        elif resolution.verdict == "mapping_mismatch":
            mapping_mismatch.append({
                "name": name, "file": file,
                "expected": resolution.expected, "actual": resolution.actual,
            })
        else:
            unmapped_metric.append({"name": name, "file": file})


    schema_mismatch = [
        {"source": display_source(r.source), "detail": r.detail}
        for r in (readings[s] for s in needed_sources)
        if r.status == "schema_mismatch"
    ]

    verified_keys = {(e["name"], e["file"]) for e in verified}
    unmapped_keys = {(e["name"], e["file"]) for e in unmapped_metric}
    mapping_keys = {(e["name"], e["file"]) for e in mapping_mismatch}

    # --- строки метрик
    rows = []
    for pair in pairs:
        name, file = pair
        passport = catalog[pair]
        binding = bindings[pair]
        source = binding.source if binding else None
        status = readings[source].status if source else None
        source_shown = display_source(source) if source else None
        read = values.get(pair)

        row = {
            "name": name,
            "file": file,
            "source": source_shown,
            "unit": passport.unit,
            "direction": passport.direction,
            # `plan_values` ЗАПРОСА по-прежнему игнорируются: плановое значение из
            # цели — вторая роль с другим периодом, и молчаливый выбор между ней
            # и планом книги канон запрещает. Заполняется только план ИЗ КНИГИ,
            # и только там, где онбординг объявил его сопоставимым с фактом
            # (координата `plan_row` раскладки).
            "plan": None, "plan_source": None, "plan_conflict": None,
            "as_of": None, "delta": None, "trend": None,
            "composition_confirmed": False,
            "fact": None,
            "value_status": "not_read",
            "period": None,
            "granularity": None,
            "period_partial": False,
            "baseline": None,
            "source_ref": None,
        }
        if read is not None and read.get("plan") is not None:
            # `source` — план операционки из книги. Плановое значение цели имеет
            # другую роль и период; какое из двух показывать при расхождении,
            # решает дифф Э0-A-б, и до него второе не подставляется вовсе.
            row["plan"] = read["plan"]
            row["plan_source"] = "source"
        if read is not None:
            row.update({
                "value_status": read["value_status"],
                "fact": read["fact"] if read["value_status"] == "ok" else None,
                "period": read["period"],
                "granularity": read["granularity"],
                "baseline": read["baseline"] if read["value_status"] == "ok" else None,
                # При `missing` координаты обычно не показываются: читать было
                # нечего. Но если недостача объяснима («период есть, колонки
                # факта нет»), причина обязана доехать — без неё человек видит
                # пустоту там, где в книге стоит прогноз.
                "source_ref": read["source_ref"]
                if (read["value_status"] != "missing" or read.get("detail")) else None,
                "period_partial": read["period"] == current_period(read["granularity"], request["meeting_date"]),
            })
        elif pair in unmapped_keys:
            # Метрика объявлена картой, строки в раскладке нет: «нет значения», а не «не читалось».
            granularity = None
            row.update({"value_status": "missing", "period": None, "granularity": granularity})

        is_dup = pair in duplicate_pairs
        availability = derive_availability(row, status, is_dup, pair in unmapped_keys)
        if availability is None:
            raise Refusal(
                "unmapped_facts",
                f"сочетание фактов пары ({name}, {file}) не покрыто таблицей availability",
            )
        verification = derive_verification(
            row, status, is_dup, pair in verified_keys, pair in unmapped_keys, pair in mapping_keys
        )
        if verification is None:
            raise Refusal(
                "unmapped_facts",
                f"пара ({name}, {file}) не попала ни в один массив verification",
            )
        row["axes"] = {
            "availability": availability,
            "freshness": derive_freshness(row, basis, request["meeting_date"]),
            "verification": verification,
        }
        rows.append(row)

    # --- источники
    sources = []
    for source in needed_sources:
        reading = readings[source]
        entry = snapshots.get(source, (None, None))[1]
        error = None
        if reading.error:
            error = {"code": reading.error[0], "message": reading.error[1]}
        sources.append({
            "source": display_source(source),
            "title": entry["title"] if entry else None,
            "schema_hash": reading.schema_hash if reading.status in ("ok", "schema_mismatch") else None,
            "snapshot_modified_time": normalize_datetime(entry["modified_time"]) if entry else None,
            "status": reading.status,
            "error": error,
        })

    generated = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return {
        "contract": {"name": "metrics-report", "version": CONTRACT_VERSION},
        "run_id": request["run_id"],
        "object_ref": request["object_ref"],
        "meeting_date": request["meeting_date"],
        "period_basis": basis,
        "generated_at": generated,
        "sources": sorted(sources, key=lambda s: s["source"]),
        "metrics": rows,
        "verification": {
            "scope": "client",
            "files_scanned": files_scanned,
            "verified": sorted(verified, key=lambda e: (e["name"], e["file"])),
            "unmapped_metric": sorted(unmapped_metric, key=lambda e: (e["name"], e["file"])),
            "mapping_mismatch": sorted(mapping_mismatch, key=lambda e: (e["name"], e["file"])),
            "orphan_row": sorted((dict(o, source=display_source(o["source"])) for o in orphan_row),
                                 key=lambda e: (e["source"], e["sheet"], e["row_label"])),
            "schema_mismatch": sorted(schema_mismatch, key=lambda e: e["source"]),
            # Состав разреза выносит verifier по composition-hash, а он — часть
            # несогласованного пакета Э0-A. До согласования массив пуст, а
            # composition_confirmed = false: гашение Δ и тренда схема делает сама.
            "composition_mismatch": [],
            "duplicate_name": [
                {"name": name, "files": files} for name, files in sorted(duplicates.items())
            ],
        },
    }


def tidy_numbers(node):
    """Целые float → int: 921.0 и 921 — одно и то же число, но разные байты.

    Норма «повторный вызов даёт байт-в-байт тот же отчёт» держится и без этого, но
    сравнение с эталонными фикстурами и читаемость отчёта — нет.
    """
    if isinstance(node, dict):
        return {k: tidy_numbers(v) for k, v in node.items()}
    if isinstance(node, list):
        return [tidy_numbers(v) for v in node]
    if isinstance(node, float) and node.is_integer():
        return int(node)
    return node


def serialize(report):
    """Каноническая сериализация — норма из scripts/requirements.txt."""
    # allow_nan=False — страховка: NaN/Infinity отсекаются раньше, но если бы они
    # просочились, отчёт стал бы нестрогим JSON, который валидатор пропускает.
    return json.dumps(tidy_numbers(report), ensure_ascii=False, indent=2,
                      sort_keys=True, allow_nan=False) + "\n"


def main(argv=None):
    class JsonArgumentParser(argparse.ArgumentParser):
        """Ошибку аргументов печатает JSON-ом: stderr контура читается машиной."""

        def error(self, message):  # noqa: D401 — переопределение argparse
            json.dump({"error": "usage_error", "message": message},
                      sys.stderr, ensure_ascii=False)
            sys.stderr.write("\n")
            raise SystemExit(2)

    parser = JsonArgumentParser(description="Раннер линии данных вертикали metrics")
    parser.add_argument("--base", required=True, help="корень базы клиента (read-only)")
    parser.add_argument("--request", required=True, help="metrics-request.json прогона")
    parser.add_argument("--snapshot-dir", required=True, help="каталог снимков книг (read-only)")
    parser.add_argument("--out", required=True, help="путь отчёта — единственный write-path")
    parser.add_argument("--manifest", help="манифест снимков; по умолчанию <snapshot-dir>/" + MANIFEST_FILENAME)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_code:
        # JSON уже напечатан обработчиком error(); --help выходит с нулём и печатает
        # справку — это единственный человеческий вывод, и он законен.
        if exit_code.code == 0:
            raise
        return 2

    try:
        check_paths(args)
        report = build_report(args)
        payload = serialize(report)
        if len(payload.encode("utf-8")) > REPORT_SIZE_LIMIT:
            raise Refusal("usage_error", "отчёт превысил sanity-лимит 1 МБ", rc=2)
        Path(args.out).write_text(payload, encoding="utf-8")
    except Refusal as refusal:
        json.dump({"error": refusal.code, "message": refusal.message}, sys.stderr, ensure_ascii=False)
        sys.stderr.write("\n")
        return refusal.rc
    except OSError as exc:
        json.dump({"error": "usage_error", "message": str(exc)}, sys.stderr, ensure_ascii=False)
        sys.stderr.write("\n")
        return 2
    except Exception as exc:  # noqa: BLE001 — стоп-кран, а не глушитель
        # Обещание контура: stderr всегда JSON, rc всегда из {0, 1, 2}. Неучтённый
        # класс ошибки не должен превращаться в traceback, по которому ops гадает;
        # текст исключения едет в message, чтобы причина не потерялась.
        json.dump({"error": "usage_error", "message": f"{type(exc).__name__}: {exc}"},
                  sys.stderr, ensure_ascii=False)
        sys.stderr.write("\n")
        return 2
    print(f"OK: {len(report['metrics'])} метрик → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
