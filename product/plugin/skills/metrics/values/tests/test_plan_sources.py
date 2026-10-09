"""Чтение и расчёт плана из другого листа/книги на синтетических источниках."""

import contextlib
import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
import sys

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import calculator
import read_metrics
import snapshot


def write_book(path, sheets):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for row in rows:
            ws.append(row)
    wb.save(path)
    wb.close()


class PlanSources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.book = Path(self.tmp.name) / "fact.xlsx"
        self.plan_book = Path(self.tmp.name) / "plan.xlsx"
        write_book(self.book, {
            "Fact": [["Metric", "Jan", "Feb", "Mar"], ["Revenue", 123, 100, 200],
                     ["Revenue plan", 999, 999, 999]],
            "Plan": [["Metric", "Mar", "Jan", "Feb"], ["Revenue plan", 180, 150, 120]],
        })
        write_book(self.plan_book, {
            "Budget": [["Metric", "Mar", "Jan", "Feb"], ["Revenue plan", .18, .15, .12]],
        })

    def read(self, source=None, **extra):
        item = {"name": "Revenue", "unit": "AED", "scale": 1,
                "sheet": "Fact", "labels": ["Revenue"]}
        if source is not None:
            item["plan_source"] = source
        item.update(extra)
        return read_metrics.read(self.book, {"year": 2026, "strict_labels": True, "metrics": [item]},
                                 upto="2026-01")[0]

    def test_plan_on_other_sheet_uses_own_axis_and_keeps_future(self):
        row = self.read({"sheet": "Plan", "labels": ["Revenue plan"]})
        self.assertEqual(row["values"], {"2026-01": 123})
        self.assertEqual(row["plan"], {"2026-01": 150, "2026-02": 120, "2026-03": 180})
        result = calculator.derive([row], "2026-01")[0]
        self.assertEqual(result["plan"], 150)
        self.assertEqual(result["derived"]["выполнение плана, %"], 82)
        self.assertEqual(result["derived"]["отклонение от плана"], -27)

    def test_plan_in_other_book_has_own_scale_and_provenance(self):
        row = self.read({"book": str(self.plan_book), "sheet": "Budget",
                         "labels": ["Revenue plan"], "scale": 1000,
                         "source_note": "данные книги от 2026-01-03"})
        self.assertEqual(row["plan"]["2026-01"], 150)
        self.assertEqual(row["plan_source"]["book"], str(self.plan_book))
        self.assertIn("план: данные книги от 2026-01-03", row["notes"])
        self.assertEqual(calculator.derive([row], "2026-01")[0]["derived"]["выполнение плана, %"], 82)

    def test_plan_default_scale_is_one_independent_of_fact_scale(self):
        row = self.read({"sheet": "Plan", "labels": ["Revenue plan"]}, scale=1000)
        self.assertEqual(row["values"]["2026-01"], 123000)
        self.assertEqual(row["plan"]["2026-01"], 150)

    def test_legacy_same_sheet_plan_still_works(self):
        row = self.read(plan_labels=["Revenue plan"])
        self.assertEqual(row["plan"]["2026-01"], 999)
        self.assertEqual(row["plan"]["2026-03"], 999)

    def test_unavailable_plan_does_not_use_legacy_fallback_or_drop_fact(self):
        row = self.read({"book": str(Path(self.tmp.name) / "missing.xlsx"),
                         "sheet": "Plan", "labels": ["Revenue plan"]},
                        plan_labels=["Revenue plan"])
        self.assertEqual(row["values"], {"2026-01": 123})
        self.assertEqual(row["plan"], {})
        self.assertEqual(row["plan_status"], "refused")
        self.assertNotIn("выполнение плана, %", calculator.derive([row])[0]["derived"])

    def test_missing_sheet_labels_or_mismatched_unit_refuse_only_plan(self):
        for source in [
            {"sheet": "Missing", "labels": ["Revenue plan"]},
            {"sheet": "Plan", "labels": ["Unknown"]},
            {"sheet": "Plan", "labels": ["Revenue plan"], "unit": "EUR"},
            {"sheet": "Plan", "labels": []},
            {"sheet": "Plan", "labels": ["Revenue plan"], "scale": 0},
        ]:
            with self.subTest(source=source):
                row = self.read(source)
                self.assertEqual(row["values"], {"2026-01": 123})
                self.assertEqual(row["plan"], {})
                self.assertEqual(row["plan_status"], "refused")

    def test_plan_year_is_independent(self):
        row = self.read({"sheet": "Plan", "labels": ["Revenue plan"], "year": 2027})
        self.assertEqual(row["plan"]["2027-01"], 150)
        self.assertNotIn("выполнение плана, %", calculator.derive([row], "2026-01")[0]["derived"])

    def test_missing_plan_sheet_does_not_substitute_similar_old_sheet(self):
        write_book(self.plan_book, {"Budget old": [["Metric", "Jan", "Feb", "Mar"],
                                                  ["Revenue plan", 2000, 2000, 2000]]})
        row = self.read({"book": str(self.plan_book), "sheet": "Budget", "labels": ["Revenue plan"]})
        self.assertEqual(row["values"], {"2026-01": 123})
        self.assertEqual(row["plan"], {})
        self.assertEqual(row["plan_status"], "refused")
        self.assertNotIn("plan_source", row)
        self.assertNotIn("выполнение плана, %", calculator.derive([row], "2026-01")[0]["derived"])

    def test_plan_source_is_strict_even_for_a_legacy_fact_card(self):
        write_book(self.plan_book, {"Budget old": [["Metric", "Jan", "Feb", "Mar"],
                                                  ["Revenue plan", 2000, 2000, 2000]]})
        item = {"name": "Revenue", "unit": "AED", "scale": 1, "sheet": "Fact", "labels": ["Revenue"],
                "plan_source": {"book": str(self.plan_book), "sheet": "Budget", "labels": ["Revenue plan"],
                                "strict_labels": False}}
        row = read_metrics.read(self.book, {"year": 2026, "metrics": [item]}, upto="2026-01")[0]
        self.assertEqual(row["plan_status"], "refused")
        self.assertEqual(row["plan"], {})

    def test_strict_fact_sheet_does_not_substitute_similar_sheet(self):
        write_book(self.book, {"Fact old": [["Metric", "Jan", "Feb", "Mar"], ["Revenue", 2000, 2000, 2000]]})
        row = self.read()
        self.assertEqual(row["status"], "refused")
        self.assertEqual(row["values"], {})

    def test_zero_plan_is_kept_without_division(self):
        write_book(self.plan_book, {"Budget": [["Metric", "Jan", "Feb", "Mar"],
                                              ["Revenue plan", 0, 150, 150]]})
        row = self.read({"book": str(self.plan_book), "sheet": "Budget", "labels": ["Revenue plan"]})
        self.assertEqual(row["plan"]["2026-01"], 0)
        result = calculator.derive([row], "2026-01")[0]
        self.assertNotIn("выполнение плана, %", result["derived"])
        self.assertIn("план равен нулю — выполнение не считается", result["notes"])

    def test_strict_plan_cannot_read_similar_label(self):
        row = self.read({"sheet": "Plan", "labels": ["Revenue"]})
        self.assertEqual(row["plan"], {})
        self.assertEqual(row["plan_status"], "refused")

    def test_strict_card_cannot_be_disabled_by_plan_or_metric(self):
        row = self.read({"sheet": "Plan", "labels": ["Revenue"], "strict_labels": False},
                        strict_labels=False)
        self.assertEqual(row["plan"], {})
        self.assertEqual(row["plan_status"], "refused")

    def test_strict_fact_does_not_normalize_case_or_use_substring(self):
        for label in ["revenue", " Revenue", "Reven"]:
            with self.subTest(label=label):
                row = self.read(labels=[label])
                self.assertEqual(row["status"], "refused")
                self.assertEqual(row["values"], {})

    def test_strict_operational_column_does_not_use_substring(self):
        write_book(self.plan_book, {"Daily": [["Metric", "Month"], ["Revenue forecast", 150]]})
        card = {"strict_labels": True, "metrics": [{"name": "Revenue", "unit": "AED", "scale": 1,
                "sheet": "Daily", "labels": ["Revenue"], "column_label": "Month", "period": "2026-01"}]}
        row = read_metrics.read(self.plan_book, card, year=2026, upto="2026-01")[0]
        self.assertEqual(row["status"], "refused")

    def test_legacy_reader_can_still_use_its_old_matching_mode(self):
        card = {"year": 2026, "metrics": [{"name": "Revenue", "unit": "AED", "scale": 1,
                "sheet": "Plan", "labels": ["Revenue"]}]}
        row = read_metrics.read(self.book, card, upto="2026-01")[0]
        self.assertEqual(row["values"]["2026-01"], 150)
        self.assertIn("факт: метка найдена неточно", row["notes"])

    def test_operational_fact_can_have_monthly_external_plan(self):
        write_book(self.book, {"Daily": [["Metric", "Month"], ["Revenue", 123]]})
        row = self.read({"book": str(self.plan_book), "sheet": "Budget",
                         "labels": ["Revenue plan"], "scale": 1000},
                        sheet="Daily", column_label="Month", period="2026-01")
        self.assertEqual(calculator.derive([row], "2026-01")[0]["derived"]["выполнение плана, %"], 82)


class LocalBook(unittest.TestCase):
    def test_local_book_uses_real_file_and_its_modification_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = Path(tmp) / "local.xlsx"
            write_book(book, {"Fact": [["Metric", "Jan", "Feb", "Mar"], ["Revenue", 123, 150, 180]]})
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                rc = snapshot.cmd_local(Namespace(file=str(book)))
            doc = json.loads(output.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(doc["action"], "read")
            self.assertEqual(doc["book"], str(book.resolve()))
            expected = snapshot.dt.datetime.fromtimestamp(book.stat().st_mtime, snapshot.dt.timezone.utc).isoformat(timespec="seconds")
            self.assertEqual(doc["modifiedTime"], expected)
            rows = read_metrics.read(doc["book"], {"year": 2026, "strict_labels": True,
                "metrics": [{"name": "Revenue", "sheet": "Fact", "unit": "шт", "labels": ["Revenue"]}]},
                upto="2026-01")
            self.assertEqual(rows[0]["values"], {"2026-01": 123})

    def test_missing_local_book_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                rc = snapshot.cmd_local(Namespace(file=str(Path(tmp) / "missing.xlsx")))
            self.assertEqual(rc, 1)
            self.assertEqual(json.loads(output.getvalue())["action"], "refuse")


if __name__ == "__main__":
    unittest.main()
