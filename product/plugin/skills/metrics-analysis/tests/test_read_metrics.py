"""Тесты `read_metrics.py`: разбор шапки периодов.

Месяц узнаётся из `YYYY-MM` / `YYYY/MM` / `MM.YYYY` и названий месяцев, но не из
даты с днём и не из настоящей даты ячейки — дневной лист не должен читаться
как месячный.

Запуск: python3 -m unittest discover -s tests  (из папки скилла)
"""

import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import read_metrics  # noqa: E402


class ParseMonth(unittest.TestCase):
    CASES = [
        ("2026-09", 9), ("2026/09", 9), ("09.2026", 9), ("2026-1", 1), ("Jan", 1), ("янв", 1),
        ("Sep 2026", 9), ("сентябрь 2026", 9),
        ("07.09.2026", None), ("2026-13", None), ("2026-09-01", None),
        ("2026-09-01 00:00:00", None),
        (dt.datetime(2026, 9, 1), None), (dt.date(2026, 9, 1), None), ("итого", None),
        (None, None),
    ]

    def test_machine_headers_and_names_but_not_days(self) -> None:
        for header, month in self.CASES:
            with self.subTest(header=header):
                self.assertEqual(read_metrics.parse_month(header), month)


if __name__ == "__main__":
    unittest.main()
