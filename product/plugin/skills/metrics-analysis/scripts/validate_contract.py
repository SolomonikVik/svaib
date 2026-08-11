#!/usr/bin/env python3
"""Семантический валидатор контракта границы «вертикаль metrics ↔ потребитель» — часть контракта v1.

Схемы (schema/*.schema.json) ловят локальные связки внутри строки; этот код — межмассивные
и междокументные правила. Принципы:
  - оси достоверности НЕ принимаются на слово: валидатор выводит ожидаемые значения всех трёх
    осей из фактов отчёта по таблицам boundary §4 (первое сработавшее правило сверху вниз)
    и требует точного совпадения с заявленными;
  - дубль имени выводится из ЗАПРОСА, а не из признания производителя: duplicate_name[]
    обязан совпасть с дублями перечня запроса, их строки — not_read + blocked/mismatch;
  - записи verified[]/unmapped_metric[]/mapping_mismatch[]/composition_mismatch[] допустимы
    только для пар с читаемым источником (status = ok) и не-дублей — сверка иначе невозможна;
  - schema_mismatch[] ⇔ sources[].status = schema_mismatch (в обе стороны);
  - composition_mismatch гасит сравнение: composition_confirmed = false обязателен (Δ/тренд
    null принуждает схема);
  - эхо-поля; «ровно запрошенные пары, ровно по одной, в порядке запроса»; уникальность
    бизнес-ключей; манифест — единственный источник title/modified_time (сверка для всех
    статусов, где запись манифеста существует); sha256 snapshot'ов; свежесть по run_id.

Гоняют его обе стороны: тесты трека metrics (contract-тест производителя) и мок облака.
Негативы заморожены суитой dev/metrics/tests/test_contract.py.
Выход: rc 0 — чисто; rc 1 — перечень нарушений в stdout, JSON {error, message} в stderr.
"""
import argparse
import datetime as dt
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def norm_dt(value):
    """Нормализация времени к явному смещению: Z -> +00:00 (норма контракта)."""
    if isinstance(value, str) and value.endswith("Z"):
        return value[:-1] + "+00:00"
    return value


def pair(row):
    return (row["name"], row["file"])


def last_closed_period(granularity, meeting_date):
    """Последний закрытый период в шкале метрики относительно даты встречи."""
    d = dt.date.fromisoformat(meeting_date)
    if granularity == "month":
        prev = d.replace(day=1) - dt.timedelta(days=1)
        return f"{prev.year:04d}-{prev.month:02d}"
    if granularity == "week":
        last_sunday = d - dt.timedelta(days=d.isoweekday())
        y, w, _ = last_sunday.isocalendar()
        return f"{y:04d}-W{w:02d}"
    if granularity == "quarter":
        q = (d.month - 1) // 3  # номер текущего квартала 0..3
        return f"{d.year - 1:04d}-Q4" if q == 0 else f"{d.year:04d}-Q{q}"
    if granularity == "year":
        return f"{d.year - 1:04d}"
    return None


class Deriver:
    """Ожидаемые оси строки метрики из фактов отчёта — таблицы boundary §4, сверху вниз.

    dup_pairs приходит снаружи: дубли выведены из запроса, не из признания производителя.
    """

    def __init__(self, report, dup_pairs, meeting_ok):
        v = report["verification"]
        self.status_by_source = {s["source"]: s["status"] for s in report["sources"]}
        self.verified = {pair(e) for e in v["verified"]}
        self.unmapped = {pair(e) for e in v["unmapped_metric"]}
        self.mapping = {pair(e) for e in v["mapping_mismatch"]}
        self.composition = {pair(e) for e in v["composition_mismatch"]}
        self.dup_pairs = dup_pairs
        self.meeting_date = report["meeting_date"]
        self.basis = report["period_basis"]
        self.meeting_ok = meeting_ok

    def availability(self, row):
        p, src = pair(row), row["source"]
        if src is None:
            return "source_unbound"
        if self.status_by_source.get(src) in ("unavailable", "no_extractor"):
            return "source_unavailable"
        if self.status_by_source.get(src) == "schema_mismatch" or p in self.dup_pairs:
            return "blocked"
        if row["value_status"] in ("div0", "error"):
            return "value_error"
        if row["value_status"] == "missing" or p in self.unmapped:
            return "no_value"
        if row["value_status"] == "ok":
            return "value"
        return None  # unmapped_facts: сочетание не покрыто таблицей

    def freshness(self, row, errors):
        closed = None
        if self.meeting_ok and self.basis == "closed" and row["granularity"] and row["period"]:
            closed = last_closed_period(row["granularity"], self.meeting_date)
            if closed is not None and row["period"] > closed:
                errors.append(
                    f"contract_violation: {pair(row)}: period {row['period']} позже последнего "
                    f"закрытого {closed} при period_basis=closed"
                )
        if row["fact"] is None:
            return "undatable"
        if closed is not None and row["period"] < closed:
            return "before_period"
        return "undatable" if row["as_of"] is None else "in_period"

    def verification(self, row):
        p, src = pair(row), row["source"]
        if src is None or self.status_by_source.get(src) in ("unavailable", "no_extractor"):
            return "not_run"
        if self.status_by_source.get(src) == "schema_mismatch" or p in (self.mapping | self.composition | self.dup_pairs):
            return "mismatch"
        if p in (self.verified | self.unmapped):
            return "verified"
        return None  # пара не упомянута ни в одном массиве


def unique_by(entries, keyfn, label, errors):
    seen = set()
    for e in entries:
        k = keyfn(e)
        if k in seen:
            errors.append(f"contract_violation: {label}: повтор ключа {k}")
        seen.add(k)
    return seen


def check(request, report, manifest=None, snapshot_dir=None):
    errors = []
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema не установлен — валидация невозможна (см. scripts/requirements.txt)"]

    docs = [("metrics-request", request), ("metrics-report", report)]
    if manifest is not None:
        docs.append(("snapshot-manifest", manifest))
    for name, doc in docs:
        schema = load_json(SCHEMA_DIR / f"{name}.schema.json")
        for err in jsonschema.Draft7Validator(schema).iter_errors(doc):
            errors.append(f"{name}: схема: {'/'.join(map(str, err.absolute_path))}: {err.message}")
    if errors:
        return errors  # дальше проверять нечего: структура не гарантирована

    # --- манифест и snapshot-dir обязательны: контракт без них не проверяем
    if manifest is None:
        errors.append("contract_violation: snapshot-manifest обязателен — его пишут обе среды, валидация без него неполна")
    if snapshot_dir is None:
        errors.append("contract_violation: --snapshot-dir обязателен — sha256 snapshot'ов не сверить")

    # --- даты — календарные (regex схемы пропускает 2026-02-31); отчёт проверяется отдельно,
    #     чтобы невозможная дата производителя давала именованный отказ, а не падение
    meeting_ok = True
    for label, code, value in (("запроса", "request_invalid", request["meeting_date"]),
                               ("отчёта", "contract_violation", report["meeting_date"])):
        try:
            dt.date.fromisoformat(value)
        except ValueError:
            meeting_ok = False
            errors.append(f"{code}: meeting_date {label} {value!r} — не календарная дата")

    # --- эхо-поля (report_mismatch)
    for field in ("run_id", "object_ref", "meeting_date", "period_basis"):
        if request[field] != report[field]:
            errors.append(f"report_mismatch: {field}: запрос {request[field]!r} ≠ отчёт {report[field]!r}")

    # --- пары: ровно те же, ровно один раз, в порядке запроса (contract_violation)
    req_pairs = [pair(m) for m in request["metrics"]]
    req_set = unique_by(request["metrics"], pair, "request.metrics", errors)
    unique_by(request["plan_values"], pair, "request.plan_values", errors)
    for e in request["plan_values"]:
        if pair(e) not in req_set:
            errors.append(f"contract_violation: plan_values называет незапрошенную пару {pair(e)}")
    rep_pairs = [pair(m) for m in report["metrics"]]
    if rep_pairs != req_pairs:
        errors.append(
            "contract_violation: строки отчёта не совпадают с перечнем запроса "
            f"(запрошено {req_pairs}, получено {rep_pairs})"
        )

    # --- дубли имени: выводятся из запроса, признание производителя обязано совпасть
    files_by_name = defaultdict(set)
    for n, f in req_pairs:
        files_by_name[n].add(f)
    expected_dup = {n: fs for n, fs in files_by_name.items() if len(fs) > 1}
    ver = report["verification"]
    reported_dup = {e["name"]: set(e["files"]) for e in ver["duplicate_name"]}
    if reported_dup != expected_dup:
        errors.append(
            f"contract_violation: duplicate_name не совпадает с дублями запроса "
            f"(из запроса следует {sorted(expected_dup)}, заявлено {sorted(reported_dup)})"
        )
    dup_pairs = {(n, f) for n, fs in expected_dup.items() for f in fs}

    # --- уникальность бизнес-ключей и принадлежность verification запрошенному перечню
    verified_set = unique_by(ver["verified"], pair, "verified", errors)
    unmapped_set = unique_by(ver["unmapped_metric"], pair, "unmapped_metric", errors)
    mapping_set = unique_by(ver["mapping_mismatch"], pair, "mapping_mismatch", errors)
    unique_by(ver["composition_mismatch"], lambda e: (e["name"], e["file"], e["period"]), "composition_mismatch", errors)
    comp_set = {pair(e) for e in ver["composition_mismatch"]}
    unique_by(ver["duplicate_name"], lambda e: e["name"], "duplicate_name", errors)

    # --- смысловая совместимость массивов: verified + composition законно (координаты сошлись,
    #     состав разошёлся — пример boundary §3); verified + mapping и unmapped + любой вердикт — нет
    for p in verified_set & mapping_set:
        errors.append(f"contract_violation: {p}: verified[] и mapping_mismatch[] взаимоисключающи — координаты либо сошлись, либо нет")
    for p in unmapped_set & (verified_set | mapping_set | comp_set):
        errors.append(f"contract_violation: {p}: unmapped_metric несовместим с verified/mapping/composition — строки в источнике нет")
    if (verified_set or unmapped_set or mapping_set or comp_set or ver["orphan_row"]) and not ver["files_scanned"]:
        errors.append("contract_violation: сверка выполнялась, а files_scanned пуст — доказательство client-scope отсутствует")

    # --- источники строк объявлены в sources[]; статусы против schema_mismatch[] — в обе стороны
    declared = unique_by(report["sources"], lambda s: s["source"], "sources", errors)
    status_by_source = {s["source"]: s["status"] for s in report["sources"]}
    for row in report["metrics"]:
        if row["source"] is not None and row["source"] not in declared:
            errors.append(f"contract_violation: {pair(row)}: source не объявлен в sources[]")
    schema_set = {e["source"] for e in ver["schema_mismatch"]}
    for src in schema_set:
        if status_by_source.get(src) != "schema_mismatch":
            errors.append(f"contract_violation: schema_mismatch[] называет {src}, но sources[].status = {status_by_source.get(src)!r}")
    for s in report["sources"]:
        if s["status"] == "schema_mismatch" and s["source"] not in schema_set:
            errors.append(f"contract_violation: источник {s['source']} со status=schema_mismatch не назван в schema_mismatch[]")

    # --- записи сверки допустимы только для пар с читаемым источником и не-дублей
    rows_by_pair = {pair(m): m for m in report["metrics"]}
    for arr, label in (
        (ver["verified"], "verified"),
        (ver["unmapped_metric"], "unmapped_metric"),
        (ver["mapping_mismatch"], "mapping_mismatch"),
        (ver["composition_mismatch"], "composition_mismatch"),
    ):
        for e in arr:
            p = pair(e)
            if p not in req_set:
                errors.append(f"contract_violation: {label} называет незапрошенную пару {p}")
                continue
            row = rows_by_pair.get(p)
            if row is None:
                continue  # расхождение перечня уже зафиксировано
            if row["source"] is None or status_by_source.get(row["source"]) != "ok" or p in dup_pairs:
                errors.append(
                    f"contract_violation: {label} называет пару {p}, чей источник не читаем "
                    f"или имя-дубль — сверка для неё невозможна"
                )

    # --- composition_mismatch гасит сравнение
    comp_pairs = {pair(e) for e in ver["composition_mismatch"]}
    for row in report["metrics"]:
        if pair(row) in comp_pairs and row["composition_confirmed"]:
            errors.append(
                f"contract_violation: {pair(row)}: composition_mismatch требует "
                f"composition_confirmed=false — Δ и тренд обязаны гаситься"
            )

    # --- оси: вывод из фактов по таблицам §4 и точное совпадение с заявленными
    deriver = Deriver(report, dup_pairs, meeting_ok)
    for row in report["metrics"]:
        p = pair(row)
        expected_av = deriver.availability(row)
        if expected_av is None:
            errors.append(f"unmapped_facts: {p}: сочетание фактов не покрыто таблицей availability")
        elif row["axes"]["availability"] != expected_av:
            errors.append(
                f"contract_violation: {p}: availability заявлена {row['axes']['availability']!r}, "
                f"из фактов следует {expected_av!r}"
            )
        expected_fr = deriver.freshness(row, errors)
        if row["axes"]["freshness"] != expected_fr:
            errors.append(
                f"contract_violation: {p}: freshness заявлена {row['axes']['freshness']!r}, "
                f"из фактов следует {expected_fr!r}"
            )
        expected_ve = deriver.verification(row)
        if expected_ve is None:
            errors.append(f"contract_violation: {p}: пара не упомянута ни в одном массиве verification")
        elif row["axes"]["verification"] != expected_ve:
            errors.append(
                f"contract_violation: {p}: verification заявлена {row['axes']['verification']!r}, "
                f"из фактов следует {expected_ve!r}"
            )
        if p in dup_pairs and row["value_status"] != "not_read":
            errors.append(f"contract_violation: {p}: строка дубля обязана быть not_read")

    # --- манифест: единственный источник title / modified_time; свежесть; sha256
    if manifest is not None:
        unique_by(manifest["sources"], lambda s: s["source"], "manifest.sources.source", errors)
        unique_by(manifest["sources"], lambda s: s["path"], "manifest.sources.path", errors)
        if manifest["run_id"] != request["run_id"]:
            errors.append(f"stale_snapshot: manifest.run_id {manifest['run_id']!r} ≠ run_id прогона {request['run_id']!r}")
        by_source = {s["source"]: s for s in manifest["sources"]}
        for s in report["sources"]:
            entry = by_source.get(s["source"])
            code = s["error"]["code"] if s["error"] else None
            if s["status"] == "unavailable" and entry is None:
                if code != "snapshot_missing":
                    errors.append(f"contract_violation: {s['source']}: файла нет в манифесте — error.code обязан быть snapshot_missing")
                if s["title"] is not None or s["snapshot_modified_time"] is not None:
                    errors.append(f"contract_violation: {s['source']}: при snapshot_missing title и snapshot_modified_time обязаны быть null")
                continue
            if entry is None:
                errors.append(f"contract_violation: источник {s['source']} со status={s['status']} отсутствует в манифесте")
                continue
            if s["status"] == "unavailable" and code != "snapshot_unreadable":
                errors.append(f"contract_violation: {s['source']}: файл в манифесте есть — unavailable допустим только как snapshot_unreadable")
            if s["title"] != entry["title"]:
                errors.append(f"contract_violation: {s['source']}: title отчёта ≠ title манифеста (title берётся из манифеста)")
            if s["snapshot_modified_time"] != norm_dt(entry["modified_time"]):
                errors.append(f"contract_violation: {s['source']}: snapshot_modified_time ≠ нормализованный modified_time манифеста")

        if snapshot_dir is not None:
            for entry in manifest["sources"]:
                f = Path(snapshot_dir) / entry["path"]
                if not f.is_file():
                    errors.append(f"snapshot_manifest_mismatch: файла {entry['path']} нет в --snapshot-dir")
                elif hashlib.sha256(f.read_bytes()).hexdigest() != entry["sha256"]:
                    errors.append(f"snapshot_manifest_mismatch: sha256 файла {entry['path']} разошёлся с манифестом")

    return errors


def main():
    ap = argparse.ArgumentParser(description="Семантический валидатор контракта metrics-report v1")
    ap.add_argument("--request", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--snapshot-dir", required=True)
    args = ap.parse_args()

    errors = check(
        load_json(args.request),
        load_json(args.report),
        load_json(args.manifest),
        args.snapshot_dir,
    )
    if errors:
        print("\n".join(errors))
        json.dump({"error": "contract_violation", "message": f"{len(errors)} нарушений контракта"}, sys.stderr, ensure_ascii=False)
        return 1
    print("contract OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
