#!/usr/bin/env python3
"""metrics_gateway.py — единственный шов между повесткой и вертикалью metrics.

Отдаёт по каждой метрике объекта три оси деградации и отчёт сверки в форме,
которую понимает assemble_agenda.py. Никто, кроме этого файла, о существовании
вертикали не знает: при появлении реального интерфейса меняется он один.

СЕГОДНЯ ИНТЕРФЕЙСА ВЕРТИКАЛИ НЕ СУЩЕСТВУЕТ (блокер №1 design.md): нет вызываемых
extractor'а, verifier'а и calculator'а. Поэтому режим один — `not_attempted`:

    availability = not_attempted   источник не исследовался вовсе
    freshness    = undatable       датировать нечего
    verification = not_run         сервиса сверки нет

Почему не `no_value`: этот код значит «подключённый источник прочитан, значения
в нём не найдено». Записать его там, где чтения не было, — машинно утверждать
об отсутствии данных у руководителя. Ровно так и случился провал R2.
Почему не `source_unavailable`: он говорит о базе клиента («книга не прочитана»),
а причина — на нашей стороне, коннектора нет. Статус обязан называть истинную
причину.

Перечень метрик объекта строится ЗДЕСЬ ЖЕ, потому что от источника значений он
не зависит: это чтение metrics-файлов базы.

Коды возврата: 0 — отчёт построен; 1 — перечень метрик построить не удалось;
2 — usage/IO.

Stdlib-only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import collect_sources as sources_lib  # noqa: E402  — владелец списка служебных деревьев

MODE_NO_VERTICAL = "no_vertical"
MODE_FULL = "full"

# Паспорт метрики живёт в РАКУРСЕ метрик узла и называется `*-metrics.md`.
# Маска «любой файл со словом metrics в любом месте поддерева» затягивала
# протоколы встреч: `meetings/zz_archive/2026-03-27_weekly_metrics.md` отдавал
# свои заголовки `###` как метрики, и перечень раздувался чужими строками.
# Живой прогон 06.08 упёрся в это первым же запросом к вертикали: она честно
# отвергла пары, которых нет ни в одном паспорте.
METRICS_ASPECT = "03_metrics"
METRICS_FILE_SUFFIX = "-metrics.md"

SNAPSHOT_MANIFEST = "snapshot-manifest.json"
REQUEST_CONTRACT = {"name": "metrics-request", "version": "1.0.0"}
# Раннер вертикали лежит соседним скиллом: и в исходном дереве продукта, и в
# собранном пакете клиента `skills/` — общий родитель.
VERTICAL_RUNNER = (Path(__file__).resolve().parent.parent.parent
                   / "metrics-analysis" / "scripts" / "run_vertical.py")
# Потолок одного вызова вертикали. Живой прогон на книге в 19 листов —
# 2.6 с при бюджете самой вертикали 60 с; запас здесь на холодный старт.
VERTICAL_TIMEOUT = 180

# Каноническое имя метрики — заголовок третьего уровня в metrics-файле
# (metrics-spec: `### {имя}` = ID метрики).
METRIC_HEADING = re.compile(r"^###\s+(.+?)\s*$", re.M)
SECTION_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.M)
# Секция источников: её подразделы `### {source_id}` — адреса книг, а не метрики
# (metrics-spec, «Контракт привязки к источнику»). Без этого отсева запрос к
# вертикали уезжал с парами `source_crm`, `source_erp`, и она законно отвергала
# его целиком: таких метрик в паспорте нет.
SOURCES_SECTION = re.compile(r"^источник", re.I)
# Плейсхолдер незаполненного шаблона: `### {Каноническое имя метрики}`.
PLACEHOLDER_NAME = re.compile(r"^\{.*\}$")
# Ссылка «цель → метрика»: markdown-ссылка на metrics-файл с якорем.
# Сопоставление по совпадению имён текстом ЗАПРЕЩЕНО — оно даёт ложные
# «у цели нет метрик», R2-класс в миниатюре.
GOAL_METRIC_LINK = re.compile(r"\[[^\]]*\]\(([^)#]*metrics[^)#]*\.md)#([^)]+)\)")


class GatewayError(Exception):
    def __init__(self, code: str, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


def anchor_to_name(anchor: str) -> str:
    """Якорь markdown → каноническое имя метрики (обратное преобразование)."""
    return anchor.replace("-", " ").strip().lower()


def metrics_of_file(path: Path) -> List[str]:
    """Канонические имена метрик паспорта — заголовки `### {имя}`.

    Не всякий заголовок третьего уровня — метрика. Внутри секции `## Источники`
    такие же заголовки называют ИСТОЧНИКИ (`### source_crm`), а незаполненный
    шаблон держит плейсхолдер `### {Каноническое имя метрики}`. И то и другое,
    попав в запрос, заставляет вертикаль отвергнуть его целиком — «таких метрик
    в паспортах нет», — и повестка остаётся без чисел вообще.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    names: List[str] = []
    in_sources = False
    for line in text.splitlines():
        section = SECTION_HEADING.match(line)
        if section:
            in_sources = bool(SOURCES_SECTION.match(section.group(1).strip()))
            continue
        heading = METRIC_HEADING.match(line)
        if not heading or in_sources:
            continue
        name = heading.group(1).strip()
        if name and not PLACEHOLDER_NAME.match(name):
            names.append(name)
    return names


def metrics_files_under(root: Path, base: Optional[Path] = None) -> List[Path]:
    """Паспорта метрик под каталогом: только ракурс метрик, только `*-metrics.md`.

    Служебные деревья не паспорта. Прогон 06.08 по базе компании показал цену
    отсутствия отсева: объектом встречи стал корень базы, обход затянул
    `scaffold/template/01_company/03_metrics/business-metrics.md`, и
    незаполненный шаблон был принят за паспорт метрик компании — сперва он
    отдавал в вертикаль плейсхолдеры `{Каноническое имя метрики}`, потом, когда
    плейсхолдеры перестали считаться метриками, ронял прогон целиком.

    Служебность считается ОТ БАЗЫ, а не от `root`: объект встречи, сам лежащий
    внутри шаблона, иначе снова притащил бы шаблонные паспорта — путь внутри
    него служебных частей уже не содержит.
    """
    if not root.is_dir():
        return []
    origin = Path(base) if base is not None else root
    return sorted(p for p in root.rglob("*" + METRICS_FILE_SUFFIX)
                  if p.is_file() and METRICS_ASPECT in p.parts
                  and not sources_lib.is_service_path(p, origin))


def metrics_files_of_client(base: Path) -> List[Path]:
    """Все metrics-файлы КЛИЕНТА, а не объекта встречи.

    Область сверки — клиент: одна книга питает файлы разных узлов, и сверка в
    границах объекта объявит чужую заведённую строку сиротой, воспроизведя R2
    внутри собственного контракта.
    """
    return metrics_files_under(base)


def metric_pairs_for_object(base: Path, object_ref: str, object_kind: str) -> List[Dict[str, str]]:
    """Пары «метрика + файл, где она заведена» — то, чем оперирует вертикаль.

    Имени мало: одно и то же имя живёт в metrics-файлах разных узлов, и ключом
    контракта границы служит пара `{name, file}`. Путь — base-relative POSIX.
    """
    collected: List[Tuple[str, Path]] = []
    target = (base / object_ref).resolve()
    if object_kind == "goal":
        # Цель — файл внутри ракурса strategic, а не узел: перечень строится
        # ПО ЕЁ ССЫЛКАМ, а не обходом потомков владельца цели.
        if not target.is_file():
            raise GatewayError("goal_file_missing", "файла цели нет: {0}".format(object_ref))
        text = target.read_text(encoding="utf-8")
        for match in GOAL_METRIC_LINK.finditer(text):
            rel, anchor = match.group(1), match.group(2)
            candidate = (target.parent / rel).resolve()
            # Ссылка из цели — тоже вход в базу, и вести она может куда угодно:
            # в шаблон поставки, в архив, во входящее. Паспортом это не делает.
            if sources_lib.is_service_path(candidate, base):
                continue
            wanted = anchor_to_name(anchor)
            for name in metrics_of_file(candidate):
                if name.lower() == wanted:
                    collected.append((name, candidate))
        return _as_pairs(base, collected)

    if object_kind == "person":
        # Зона ответственности — из профиля, строкой `**Зона:** [узел](путь)`.
        # Записать эту строку скилл не может: write-path отсутствует.
        if not target.is_file():
            raise GatewayError("profile_missing", "профиля нет: {0}".format(object_ref))
        zones = re.findall(r"\*\*Зона:\*\*\s*\[[^\]]*\]\(([^)]+)\)", target.read_text(encoding="utf-8"))
        if not zones:
            raise GatewayError(
                "zone_link_missing",
                "в профиле нет строки `**Зона:**` — зону ответственности нужно спросить у человека "
                "и отдать ему готовую строку для внесения: скилл в базу не пишет",
            )
        for zone in zones:
            node = (target.parent / zone).resolve()
            # Каноническая ссылка на узел ведёт на его `01_overview.md`, а не на
            # папку. Обход по файлу молча отдаёт пусто — и повестка собирается
            # без метрик вообще при исправной базе (живой прогон 31.07, №2).
            if node.is_file():
                node = node.parent
            for path in metrics_files_under(node, base.resolve()):
                collected.extend((name, path) for name in metrics_of_file(path))
        return _as_pairs(base, collected)

    # Объект-узел: метрики всех metrics-файлов ракурса metrics/ узла и потомков.
    if not target.is_dir():
        raise GatewayError("node_missing", "узла нет: {0}".format(object_ref))
    for path in metrics_files_under(target, base.resolve()):
        collected.extend((name, path) for name in metrics_of_file(path))
    return _as_pairs(base, collected)


def metric_list_for_object(base: Path, object_ref: str, object_kind: str) -> List[str]:
    """Перечень имён метрик объекта — форма для тех, кому файл не нужен."""
    return sorted({p["name"] for p in metric_pairs_for_object(base, object_ref, object_kind)})


def _as_pairs(base: Path, collected: List[Tuple[str, Path]]) -> List[Dict[str, str]]:
    """(имя, путь) → пары контракта границы, без дублей и без путей вне базы."""
    pairs: List[Dict[str, str]] = []
    seen = set()
    root = Path(base).resolve()
    for name, path in collected:
        try:
            rel = path.resolve().relative_to(root).as_posix()
        except ValueError:
            # Файл вне базы адресовать вертикали нечем, а подставить путь
            # наугад — соврать о происхождении метрики.
            continue
        key = (name, rel)
        if key in seen:
            continue
        seen.add(key)
        pairs.append({"name": name, "file": rel})
    return sorted(pairs, key=lambda p: (p["name"], p["file"]))


def build_no_vertical(names: List[str]) -> Dict[str, Any]:
    """Отчёт без обращения к вертикали: перечень есть, значений нет."""
    metrics = [
        {
            "metric_id": name,
            "name": name,
            "availability": "not_attempted",
            "freshness": "undatable",
            "verification": "not_run",
            "composition_confirmed": False,
        }
        for name in names
    ]
    checks_skipped = []
    if metrics:
        # Проверки, которым нужны значения, без вертикали неисполнимы. Молча
        # пропасть они не имеют права: это деградация ядра ценности.
        checks_skipped = [
            {"check_id": "metric-agenda", "reason": "значения метрик не читаются: интерфейса вертикали нет"},
            {"check_id": "figure-mismatch", "reason": "сравнивать нечего: значения не читаются"},
        ]
    return {
        "mode": MODE_NO_VERTICAL,
        "metric_ids": names,
        "metrics": metrics,
        "orphan_rows": [],
        "unmapped_metric": [],
        "checks_skipped": checks_skipped,
        "note": "интерфейс вертикали metrics не подключён — все метрики идут со статусом «сверка не выполнялась»",
    }


def build_report(base: Path, object_ref: str, object_kind: str,
                 snapshot_dir: Optional[Path] = None,
                 meeting_date: Optional[str] = None,
                 work_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Перечень метрик объекта и — если есть снимок книг — их значения.

    Снимка нет (интерактивный прогон без выгрузки) → прежний режим
    `no_vertical`: перечень строится, значения не выдумываются. Снимок есть →
    зовём раннер вертикали и отдаём то, что он прочитал.
    """
    pairs = metric_pairs_for_object(base, object_ref, object_kind)
    names = [p["name"] for p in pairs]
    if snapshot_dir is None or not Path(snapshot_dir).is_dir():
        return build_no_vertical(names)
    manifest_path = Path(snapshot_dir) / SNAPSHOT_MANIFEST
    if not manifest_path.is_file():
        return build_no_vertical(names)
    if not pairs:
        # Пустой перечень при живом снимке — не повод звать раннер: запрос без
        # метрик он законно отвергнет, а причина не в нём. Но «метрик нет» и
        # «паспорта есть, а разобрать их не вышло» — разные вещи, и вторая
        # означала бы, что существующая метрика с верным числом молча исчезла
        # из повестки. Различаем по факту наличия файлов-паспортов.
        if object_kind == "node":
            passports = list(metrics_files_under((base / object_ref).resolve(), base.resolve()))
            if passports:
                raise GatewayError(
                    "metrics_unparsed",
                    "паспорта метрик есть ({0} шт.), а перечень пуст — разбор не нашёл ни одной "
                    "метрики: {1}".format(len(passports),
                                          ", ".join(sorted(p.name for p in passports[:5]))))
        return build_no_vertical(names)
    return run_vertical(base, object_ref, pairs, Path(snapshot_dir), manifest_path,
                        meeting_date, work_dir)


def run_vertical(base: Path, object_ref: str, pairs: List[Dict[str, str]], snapshot_dir: Path,
                 manifest_path: Path, meeting_date: Optional[str],
                 work_dir: Optional[Path]) -> Dict[str, Any]:
    """Зовёт раннер вертикали и переводит его отчёт в форму повестки.

    Раннер запускается ОТДЕЛЬНЫМ ПРОЦЕССОМ, а не импортом: так граница между
    повесткой и вертикалью остаётся границей — у повестки нет доступа к
    внутренностям чтения книг, и подменить прочитанное значение ей нечем.
    """
    if not VERTICAL_RUNNER.is_file():
        # Тихо деградировать здесь нельзя: снимок книг есть, значит числа
        # ждали. «Пакета вертикали нет» — отказ прогона, а не пустая таблица.
        raise GatewayError("vertical_missing",
                           "снимок книг есть, а раннера вертикали нет: {0}".format(VERTICAL_RUNNER))
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GatewayError("manifest_unreadable", "манифест снимка не прочитан: {0}".format(exc))
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise GatewayError("manifest_unreadable", "в манифесте снимка нет run_id")

    request = {
        "contract": dict(REQUEST_CONTRACT),
        # run_id берётся ИЗ МАНИФЕСТА, а не у прогона повестки: контракт
        # границы требует, чтобы запрос относился к тому прогону, которым
        # добыт снимок. Чужой снимок раннер отвергает — и правильно делает.
        "run_id": run_id,
        # Объект встречи — тот, что назвал прогон, а не первый компонент пути
        # первой метрики. Совпадали они только у узла верхнего уровня: у
        # `back-office/finance` прежнее правило давало `back-office`, и отчёт
        # заявлял бы, что относится к другому объекту. Поле эхо-возвращается в
        # отчёт, поэтому цена ошибки — неверная трассировка, а не пустая таблица.
        "object_ref": object_ref,
        "meeting_date": meeting_date or date.today().isoformat(),
        "period_basis": "closed",
        "metrics": pairs,
        # Плановые значения приходят параметром от потребителя; до согласования
        # пакета Э0-A их не передаёт никто, и раннер их игнорирует.
        "plan_values": [],
    }

    holder = Path(work_dir) if work_dir else None
    tmp = None
    if holder is None:
        tmp = tempfile.mkdtemp(prefix="agenda-metrics-")
        holder = Path(tmp)
    holder.mkdir(parents=True, exist_ok=True)
    request_path = holder / "metrics-request.json"
    report_path = holder / "metrics-report.json"
    try:
        request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
        argv = [sys.executable, str(VERTICAL_RUNNER),
                "--base", str(base), "--request", str(request_path),
                "--snapshot-dir", str(snapshot_dir), "--out", str(report_path)]
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=VERTICAL_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise GatewayError("vertical_timeout",
                               "вертикаль не уложилась в {0} с".format(VERTICAL_TIMEOUT))
        except (OSError, subprocess.SubprocessError) as exc:
            raise GatewayError("vertical_failed", "раннер вертикали не запустился: {0}".format(exc))

        if proc.returncode != 0:
            # Код отказа принадлежит вертикали и назван в её реестре ошибок;
            # пересказывать его своими словами значило бы завести вторую
            # правду о том, что случилось.
            code, message = _refusal_of(proc.stderr, proc.returncode)
            raise GatewayError(code, message, exit_code=2 if proc.returncode == 2 else 1)
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise GatewayError("vertical_report_broken",
                               "отчёт вертикали не прочитан: {0}".format(exc))
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)

    return translate_report(report, pairs)


def _refusal_of(stderr: str, returncode: int) -> "tuple":
    """Отказ вертикали: её код и сообщение, если она их назвала."""
    for line in reversed((stderr or "").strip().splitlines()):
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        if isinstance(payload, dict) and payload.get("error"):
            return str(payload["error"]), str(payload.get("message") or "")[:600]
    return ("vertical_failed",
            (stderr or "").strip()[:600] or "вертикаль вернула код {0}".format(returncode))


def orphan_lines(rows: Any) -> List[str]:
    """Непривязанные строки источника — человеческой строкой на каждую.

    Контракт вертикали называет поле `orphan_row` (в единственном числе) и
    отдаёт объекты `{source, sheet, row_label, candidate_metrics}`; повестка
    держит перечень строк. Перевод — работа шва: раньше поле читалось по
    множественному числу, всегда выходило пустым, и разрыв форм никак себя не
    проявлял — ремонтный сигнал «в книге есть строка, метрики под неё нет»
    просто терялся.
    """
    out: List[str] = []
    for row in rows or []:
        if isinstance(row, str):
            out.append(row)
            continue
        if not isinstance(row, dict):
            continue
        label = str(row.get("row_label") or "").strip() or "строка без подписи"
        sheet = str(row.get("sheet") or "").strip()
        line = "{0} — лист «{1}»".format(label, sheet) if sheet else label
        candidates = [c.get("name") for c in (row.get("candidate_metrics") or [])
                      if isinstance(c, dict) and c.get("name")]
        if candidates:
            line += " (похоже на: {0})".format(", ".join(candidates))
        out.append(line)
    return out


def translate_report(report: Dict[str, Any], pairs: List[Dict[str, str]]) -> Dict[str, Any]:
    """Отчёт вертикали → форма, которую понимает assemble_agenda.

    Оси РАЗВОРАЧИВАЮТСЯ, но не вычисляются: `display_status` выводит сборщик по
    своей таблице приоритетов, и второго владельца у этого правила быть не
    должно.
    """
    rows = report.get("metrics")
    if not isinstance(rows, list):
        raise GatewayError("vertical_report_broken", "в отчёте вертикали нет перечня метрик")
    metrics: List[Dict[str, Any]] = []
    for row in rows:
        # Имя — ключ строки на всём пути до экрана. Пустое или нестроковое
        # превратило бы `metric_id` в None, а дальше молча разошлись бы токены,
        # свёртка и сверка повестки с отчётом.
        if not isinstance(row.get("name"), str) or not row["name"].strip():
            raise GatewayError("vertical_report_broken",
                               "в отчёте вертикали есть метрика без имени")
        axes = row.get("axes") or {}
        for axis in ("availability", "freshness", "verification"):
            if axis not in axes:
                raise GatewayError("vertical_report_broken",
                                   "метрика «{0}»: в отчёте нет оси {1}".format(row.get("name"), axis))
        metrics.append({
            # Идентификатор строки в повестке — имя метрики: пара «имя + файл»
            # живёт в контракте границы, а на экране руководителя файла нет.
            "metric_id": row.get("name"),
            "name": row.get("name"),
            "unit": row.get("unit"),
            "direction": row.get("direction"),
            "plan": row.get("plan"),
            "plan_conflict": row.get("plan_conflict"),
            "fact": row.get("fact"),
            "as_of": row.get("as_of"),
            # Период вертикаль знает всегда, дату среза (`as_of`) — пока нет.
            # Без него «устарело» нечем датировать, и валидатор режет строку.
            "period": row.get("period"),
            "granularity": row.get("granularity"),
            "period_partial": row.get("period_partial"),
            "delta": row.get("delta"),
            "trend": row.get("trend"),
            "availability": axes["availability"],
            "freshness": axes["freshness"],
            "verification": axes["verification"],
            "composition_confirmed": bool(row.get("composition_confirmed", False)),
            "source_ref": row.get("source_ref"),
        })

    verification = report.get("verification") or {}
    checks_skipped: List[Dict[str, str]] = []
    if not any(m["availability"] == "value" for m in metrics):
        # Ни одного прочитанного значения — проверки на числах неисполнимы, и
        # молчать об этом нельзя: пустая таблица не объясняет себя сама.
        checks_skipped = [
            {"check_id": "metric-agenda", "reason": "ни одно значение метрики не прочитано"},
            {"check_id": "figure-mismatch", "reason": "сравнивать нечего: значений нет"},
        ]
    return {
        "mode": MODE_FULL,
        "metric_ids": [m["metric_id"] for m in metrics],
        "metrics": metrics,
        "orphan_rows": orphan_lines(verification.get("orphan_row")),
        "unmapped_metric": verification.get("unmapped_metric") or [],
        "checks_skipped": checks_skipped,
        "requested": len(pairs),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Отчёт вертикали metrics для повестки.")
    parser.add_argument("--base", required=True, help="корень базы клиента")
    parser.add_argument("--object", required=True, help="object_ref: путь узла, файл цели или профиль")
    parser.add_argument("--kind", required=True, choices=["node", "goal", "person"])
    parser.add_argument("--out", help="куда записать отчёт (по умолчанию stdout)")
    parser.add_argument("--snapshot-dir", default=None,
                        help="каталог снимка книг метрик; без него вертикаль не зовётся "
                             "и перечень идёт без значений")
    parser.add_argument("--meeting-date", default=None, help="дата встречи, ГГГГ-ММ-ДД")
    parser.add_argument("--json", action="store_true", help="машинный вывод")
    args = parser.parse_args(argv)

    try:
        report = build_report(Path(args.base).resolve(), args.object, args.kind,
                              snapshot_dir=Path(args.snapshot_dir) if args.snapshot_dir else None,
                              meeting_date=args.meeting_date)
    except GatewayError as exc:
        payload = {"ok": False, "error": exc.code, "message": exc.message}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else "❌ {0}: {1}".format(exc.code, exc.message),
              file=sys.stdout if args.json else sys.stderr)
        return exc.exit_code
    except OSError as exc:
        print(json.dumps({"ok": False, "error": "io_error", "message": str(exc)}, ensure_ascii=False))
        return 2

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps({"ok": True, "metrics": len(report["metrics"]), "mode": report["mode"], "out": args.out},
                         ensure_ascii=False, indent=2))
    elif not args.out:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Метрик в перечне: {0}. Режим: {1}.".format(len(report["metrics"]), report["mode"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
