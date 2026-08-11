#!/usr/bin/env python3
"""Verifier — сверка объявленного с прочитанным.

Владеет ровно тремя вердиктами (boundary §2, «один владелец на проверку»):
  - координаты сошлись            → verified[]   (значение показывать можно);
  - координаты разошлись          → mapping_mismatch[] (происхождение числа под сомнением);
  - метрика объявлена, строки нет → unmapped_metric[].

Состав разреза (composition_mismatch) verifier НЕ выносит: composition-hash — часть
несогласованного пакета Э0-A, поэтому composition_confirmed остаётся false, а массив
пустым. Это записано ограничением, а не забыто.

schema_mismatch[] — ретрансляция остановки extractor'а, не вторая проверка.
"""
from __future__ import annotations

import extractor
from source_map import normalize_label, normalize_labels


class Resolution:
    """Что verifier решил по одной паре {name, file}."""

    __slots__ = ("verdict", "entry", "expected", "actual")

    def __init__(self, verdict, entry=None, expected=None, actual=None):
        self.verdict = verdict          # verified | mapping_mismatch | unmapped
        self.entry = entry              # запись rows[] раскладки, откуда читать
        self.expected = expected        # {sheet, row_label} — как объявлено картой
        self.actual = actual            # {sheet, row_label} — где нашлось физически


def resolve(pair, binding, layout):
    """Сверить объявленные координаты с теми, откуда extractor фактически читает.

    Строка раскладки выбирается по ИМЕНИ МЕТРИКИ (`rows[].metric`), а не по меткам
    привязки — в этом весь смысл сверки. Выбор по expected-координатам сделал бы actual
    равным expected по построению, и mapping_mismatch стал бы недостижим; выбор «по
    первому совпадению метки» был бы динамической эвристикой, которую канон запрещает.
    """
    name, file = pair
    expected = {"sheet": binding.sheet, "row_label": binding.row_label}

    matches = [
        entry for entry in layout["rows"]
        if entry["metric"]["name"] == name and entry["metric"]["file"] == file
    ]
    if not matches:
        # Метрика привязана картой, но раскладка её не читает: строки в источнике для
        # раннера нет. Натяжка признана в runner-spec §5 — контракт различает «строки
        # нет в книге» и «строки нет в раскладке» одним и тем же unmapped_metric.
        return Resolution("unmapped", expected=expected)
    if len(matches) > 1:
        raise ValueError(
            f"раскладка описывает метрику ({name}, {file}) несколькими строками — "
            "какая верна, код решать не вправе"
        )

    entry = matches[0]
    actual = {"sheet": entry["sheet"], "row_label": " / ".join(entry["labels"])}
    same_sheet = normalize_label(entry["sheet"]) == normalize_label(binding.sheet)
    same_labels = normalize_labels(entry["labels"]) == normalize_labels(binding.row_labels)
    if same_sheet and same_labels:
        return Resolution("verified", entry=entry, expected=expected, actual=actual)
    # Провал R5 вживую: паспорт называет «Sales Team UAE», читается «Sales Team (upd)».
    # Значение всё равно извлекаем — под сомнением его происхождение, и решает это
    # потребитель, но ось verification уже mismatch, и число он не покажет.
    return Resolution("mapping_mismatch", entry=entry, expected=expected, actual=actual)


def bound_coordinates(source_map, source, layout, catalog=None):
    """Что считать «уже привязанным» при поиске сирот — два набора.

    `rows` — конкретные координаты `(лист, строка)`, которые раскладка читает по
    метрикам карты. Именно координаты, а не метки: две строки «MRR / fact» в одном
    блоке (старая таблица и актуальная) при исключении по метке спрятали бы обе, и
    подмена строки не всплыла бы даже сиротой.

    `labels` — метки привязок, для которых раскладка строки НЕ содержит. Такие ряды
    обязаны всплыть сиротой, поэтому сюда они не попадают; набор остаётся для привязок
    к листам, которых нет в раскладке, — их исключаем, чтобы не звать сиротой то, что
    клиент уже объявил.
    """
    rows, labels = set(), set()
    by_metric = {}
    for entry in layout["rows"]:
        by_metric.setdefault((entry["metric"]["name"], entry["metric"]["file"]), entry)
    for key, binding in source_map.all_bindings():
        if binding.source != source:
            continue
        if catalog is not None and key not in catalog:
            # Привязка-призрак: метрики с таким именем в паспортах клиента уже нет
            # (переименовали, удалили). Считать её строку «привязанной» значит спрятать
            # живой ряд, у которого больше нет паспорта, — ровно инверсия дефекта A3.1.
            # Прогон при этом не роняем: устаревшая карта не повод не собрать повестку.
            continue
        entry = by_metric.get(key)
        if entry is not None:
            rows.add((entry["sheet"], entry["row"]))
        elif normalize_label(binding.sheet) not in {
            normalize_label(name) for name in layout["sheets"]
        }:
            labels.add(binding.normalized)
    return rows, labels


def candidate_metrics(row_label, catalog):
    """Кандидаты в метрики для строки-сироты — детерминированно, без догадок.

    Только точное совпадение нормализованной метки с именем метрики либо вхождение
    одного в другое. Семантические пары («предварительный» ↔ «Preliminary vs final P&L
    variance») так не выводятся — это перевод, а не сопоставление строк; ограничение
    названо в runner-spec §9, а не замаскировано пустым массивом «на всякий случай».
    """
    label = normalize_label(row_label)
    if not label:
        return []
    candidates = []
    for (name, file) in catalog:
        norm = normalize_label(name)
        if not norm:
            continue
        if norm == label or norm in label or label in norm:
            candidates.append({"name": name, "file": file})
    return sorted(candidates, key=lambda c: (c["name"], c["file"]))


def collect_orphans(reading, source_map, catalog):
    """orphan_row[] по одному источнику: строки блоков вне привязок карты."""
    if not reading.readable:
        return []
    bound_rows, bound_labels = bound_coordinates(
        source_map, reading.source, reading.layout, catalog)
    rows = extractor.orphan_rows(reading, bound_rows, bound_labels)
    return [
        {
            "source": reading.source,
            "sheet": sheet,
            "row_label": row_label,
            "candidate_metrics": candidate_metrics(row_label, catalog),
        }
        for sheet, row_label in rows
    ]
