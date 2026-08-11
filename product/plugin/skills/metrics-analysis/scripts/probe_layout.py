#!/usr/bin/env python3
"""probe_layout.py — помощник онбординга источника: черновик раскладки по книге.

Раскладку и карту источников пишет человек (писатель extractor'а и онбординг), но
рутину — перечень листов, распознанные оси периодов, метки строк, эталонный хэш —
считает код. Скрипт НИЧЕГО не решает за человека: он показывает, что видит в книге,
и печатает заготовку, которую нужно вычитать и дополнить.

Два режима:

    # 1. Разведка: какие листы в книге, где похоже на ось периодов, какие метки строк
    python3 probe_layout.py --snapshot <книга>.xlsx --source gsheet:<fileId>

    # 2. Хэш: пересчитать эталон структуры под готовую раскладку (осознанное действие
    #    после легитимной правки книги — автоподстройки в раннере нет и не будет)
    python3 probe_layout.py --snapshot <книга>.xlsx --layout <раскладка>.json --rehash

Probe-вывод может содержать фрагменты клиентских данных: это рабочая диагностика на
время сборки, её не коммитят и не оставляют документацией (extractor.md, «Probe-артефакты
временные»).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import extractor  # noqa: E402


def guess_sheet_layout(sheet):
    """Догадка о раскладке листа — предложение человеку, а не вывод.

    Ищем первую строку, где больше двух ячеек распознаются как периоды хоть в одной
    шкале; служебными считаем колонки левее первой такой ячейки.
    """
    for row in range(1, min(sheet.max_row, 12) + 1):
        for granularity in ("month", "week", "quarter", "year"):
            columns = []
            for col in range(1, sheet.max_col + 1):
                period = extractor.parse_period(sheet.cell(row, col), granularity, 2026)
                if period is not None:
                    columns.append(col)
            if len(columns) >= 3:
                return {
                    "label_columns": list(range(1, columns[0])) or [1],
                    "period_row": row,
                    "value_columns_from": columns[0],
                    "period_year": None if granularity == "year" else 2026,
                    "granularity": granularity,
                    "block_rows": [row + 1, sheet.max_row],
                }
    return None


def describe(sheet, layout_sheet, limit):
    """Метки строк после forward-fill — по ним человек пишет row_labels и координаты."""
    if layout_sheet is None:
        return []
    rows = []
    first, last = layout_sheet["block_rows"]
    for row in range(first, min(last, sheet.max_row, first + limit - 1) + 1):
        labels = extractor._labels_at(sheet, layout_sheet, row)
        text = [str(x) for x in labels if x is not None]
        if text:
            rows.append({"row": row, "labels": text})
    return rows


def cmd_probe(sheets, source, limit):
    draft = {
        "contract": {"name": "extractor-layout", "version": "1.0.0"},
        # Адрес канонизируется уже в заготовке: раскладку пишет человек, а голый fileId,
        # вставленный из адресной строки Drive, разошёлся бы с картой источников молча.
        "source": extractor.canonical_source(source) if source else "gsheet:<fileId>",
        "schema_hash": "sha256:<пересчитать через --rehash после вычитки>",
        "sheets": {},
        "rows": [],
    }
    for name, sheet in sheets.items():
        guess = guess_sheet_layout(sheet)
        print(f"\n=== лист «{name}» — {sheet.max_row}×{sheet.max_col} ===")
        if guess is None:
            print("  ось периодов не распознана — раскладку писать вручную")
            continue
        print(f"  ось периодов: строка {guess['period_row']}, значения с колонки "
              f"{guess['value_columns_from']}, шкала {guess['granularity']}")
        print(f"  служебные колонки: {guess['label_columns']}")
        draft["sheets"][name] = guess
        for entry in describe(sheet, guess, limit):
            print(f"    {entry['row']:>4}: {' / '.join(entry['labels'])}")
    print("\n=== заготовка раскладки (вычитать, добавить metric/value_scale/percent_mode) ===")
    print(json.dumps(draft, ensure_ascii=False, indent=2))
    return 0


def cmd_rehash(sheets, layout_path):
    layout = json.loads(Path(layout_path).read_text(encoding="utf-8"))
    written = layout.get("source")
    canonical = extractor.canonical_source(written) if written else None
    if canonical and canonical != written:
        # Раннер сравнивает адреса канонизированными и такую раскладку прочитает верно,
        # но в базе клиента одна и та же книга обязана быть записана одинаково везде —
        # иначе следующий читатель этих файлов снова разойдётся с добытчиком.
        print(f"адрес книги записан без схемы: {written!r} → канонически {canonical!r} — "
              "поправить в раскладке и карте источников")
    digest = extractor.schema_hash(sheets, layout)
    print(f"старый: {layout.get('schema_hash')}")
    print(f"новый:  {digest}")
    if digest == layout.get("schema_hash"):
        print("структура не изменилась — правка не нужна")
        return 0
    layout["schema_hash"] = digest
    Path(layout_path).write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    print(f"записано в {layout_path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Помощник онбординга источника вертикали metrics")
    parser.add_argument("--snapshot", required=True, help="книга-снимок (.xlsx или json-слепок)")
    parser.add_argument("--source", help="адрес книги для заготовки раскладки")
    parser.add_argument("--layout", help="готовая раскладка для --rehash")
    parser.add_argument("--rehash", action="store_true", help="пересчитать эталонный schema_hash")
    parser.add_argument("--rows", type=int, default=40, help="сколько строк блока показать")
    args = parser.parse_args(argv)

    try:
        sheets = extractor.load_snapshot(args.snapshot)
    except extractor.SnapshotUnreadable as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    if args.rehash:
        if not args.layout:
            print("FAIL: --rehash требует --layout", file=sys.stderr)
            return 2
        return cmd_rehash(sheets, args.layout)
    return cmd_probe(sheets, args.source, args.rows)


if __name__ == "__main__":
    sys.exit(main())
