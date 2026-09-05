"""Тесты формы apply_check.py: снимки / потери / незапланированное / объединение.

Мутационная проверка инварианта «потерянных строк 0»: одна и та же запись,
удалённая с якорем в леджере и без него, обязана дать зелёный и красный —
скрипт, который всё называет сохранённым, здесь краснеет.

Запуск: python3 -m unittest discover -s tests  (из папки скилла)
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import apply_check  # noqa: E402

ACTIVE = """\
# Актив

## Сейчас

- [ ] Первая версия машинного слоя — отв. Эрик, до 05.09
  - стенд собран, детали в [спеке](specs/layer.md)
- [ ] Обновить сайт — отв. Виктор
"""

DECISIONS = """\
# Решения

- Runtime — Claude Code — на 06.08, [основание](notes/runtime.md)
- Адаптеры отложены
"""


class TestApplyCheck(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.scope = Path(self._tmp.name) / "base"
        self.run = Path(self._tmp.name) / "run"
        (self.scope / "kit").mkdir(parents=True)
        self.active = self.scope / "kit" / "02_active.md"
        self.decisions = self.scope / "kit" / "05_decisions.md"
        self.active.write_text(ACTIVE, encoding="utf-8")
        self.decisions.write_text(DECISIONS, encoding="utf-8")
        apply_check.snapshot(self.scope, ["kit/02_active.md", "kit/05_decisions.md"],
                             self.run / "before", [])

    def tearDown(self):
        self._tmp.cleanup()

    def run_check(self, ledger, extras=()):
        return apply_check.check(self.scope, self.run / "before", ledger, extras)

    def resnap(self, files):
        """Переснять снимки только файлов пакета: несмененный согласованный — красный."""
        import shutil
        shutil.rmtree(self.run / "before")
        apply_check.snapshot(self.scope, files, self.run / "before", [])

    def test_mutation_uncovered_deletion_flips_verdict(self):
        """Инвариант: запись удалена — с якорем зелёный, без якоря потеря и красный."""
        self.resnap(["kit/02_active.md"])
        self.active.write_text("# Актив\n\n## Сейчас\n\n- [ ] Обновить сайт — отв. Виктор\n",
                               encoding="utf-8")
        ledger = "удалена: [ ] Первая версия машинного слоя — отв. Эрик, до 05.09\n"
        report, stats = self.run_check(ledger)
        self.assertEqual((stats["losses"], stats["red"]), ([], []))
        self.assertIn("OK: потерянных строк 0", report)
        report2, stats2 = self.run_check("")  # мутация: тот же дифф, якоря нет
        self.assertEqual(len(stats2["losses"]), 2)  # запись и её подстрока
        self.assertTrue(any("потеряно строк" in r for r in stats2["red"]))
        self.assertIn("## Потери", report2)

    def test_sub_line_covered_by_parent_anchor(self):
        """Подстрока записи покрывается якорем первой строки; добавленное — не потеря."""
        self.resnap(["kit/02_active.md"])
        self.active.write_text(
            "# Актив\n\n## Сейчас\n\n"
            "- [x] Первая версия машинного слоя — отв. Эрик, сделано\n"
            "- [ ] Обновить сайт — отв. Виктор\n"
            "- [ ] Собрать стенд прогонов — отв. Эрик\n", encoding="utf-8")
        report, stats = self.run_check(
            "изменена: [ ] Первая версия машинного слоя — отв. Эрик, до 05.09\n")
        self.assertEqual(stats["losses"], [])
        self.assertGreaterEqual(stats["added"], 1)

    def test_unplanned_file_red_extra_counted(self):
        """Файл вне пакета красный; с --extra — счётчик «правка мимо пакета»."""
        self.decisions.write_text(DECISIONS + "- Новое решение человека\n", encoding="utf-8")
        _, stats = apply_check.check(self.scope, self.run / "before", "")
        # мутация манифеста: убираем decisions из согласованных — файл становится вне пакета
        (self.run / "before" / "kit" / "05_decisions.md").unlink()
        _, stats2 = apply_check.check(self.scope, self.run / "before", "")
        self.assertEqual(stats["unplanned"], [])
        self.assertEqual(stats2["unplanned"], ["kit/05_decisions.md"])
        _, stats3 = apply_check.check(self.scope, self.run / "before", "",
                                      extras=["kit/05_decisions.md"])
        self.assertEqual((stats3["unplanned"], stats3["extra"]),
                         ([], ["kit/05_decisions.md"]))

    def test_merge_keeps_dates_and_links(self):
        """При «объединена» дата и ссылка прежней записи обязаны выжить в новом состоянии."""
        merged_ok = ("# Решения\n\n- Runtime — Claude Code, адаптеры отложены — на 06.08, "
                     "[основание](notes/runtime.md)\n")
        merged_lost = "# Решения\n\n- Runtime — Claude Code, адаптеры отложены\n"
        ledger = ("объединена: Runtime — Claude Code — на 06.08, [основание](notes/runtime.md)\n"
                  "удалена: Адаптеры отложены\n")
        self.resnap(["kit/05_decisions.md"])
        self.decisions.write_text(merged_ok, encoding="utf-8")
        _, stats = self.run_check(ledger)
        self.assertEqual((stats["merge_missing"], stats["red"]), ([], []))
        self.decisions.write_text(merged_lost, encoding="utf-8")
        _, stats2 = self.run_check(ledger)
        self.assertEqual({el for _, el in stats2["merge_missing"]},
                         {"06.08", "notes/runtime.md"})
        self.assertTrue(any("объединении" in r for r in stats2["red"]))

    def test_ambiguous_anchor_two_identical_records_red(self):
        """Один якорь на две одинаковые записи: место правки не угадывается — красный (ревью 31.08)."""
        self.active.write_text(ACTIVE + "- [ ] Обновить сайт — отв. Виктор\n", encoding="utf-8")
        self.resnap(["kit/02_active.md"])
        self.active.write_text(ACTIVE.replace("- [ ] Обновить сайт — отв. Виктор\n", ""),
                               encoding="utf-8")
        _, stats = self.run_check("удалена: [ ] Обновить сайт — отв. Виктор\n")
        self.assertTrue(any("неоднозначн" in r for r in stats["red"]), stats["red"])

    def test_same_record_in_two_files_ambiguous_red(self):
        """Одноимённая запись в соседнем файле пакета: якорь не привязан к файлу — красный, не тихое покрытие (ревью 31.08)."""
        self.decisions.write_text(DECISIONS + "- [ ] Обновить сайт — отв. Виктор\n",
                                  encoding="utf-8")
        self.resnap(["kit/02_active.md", "kit/05_decisions.md"])
        self.active.write_text(ACTIVE.replace("- [ ] Обновить сайт — отв. Виктор\n", ""),
                               encoding="utf-8")
        self.decisions.write_text(DECISIONS, encoding="utf-8")
        _, stats = self.run_check("удалена: [ ] Обновить сайт — отв. Виктор\n")
        self.assertTrue(any("неоднозначн" in r for r in stats["red"]), stats["red"])

    def test_checkbox_flip_without_anchor_red(self):
        """Смена [ ] на [x] — закрытие задачи: без якоря это потеря, не косметика (ревью 31.08)."""
        self.resnap(["kit/02_active.md"])
        self.active.write_text(ACTIVE.replace("- [ ] Обновить сайт", "- [x] Обновить сайт"),
                               encoding="utf-8")
        _, stats = self.run_check("")
        self.assertGreaterEqual(len(stats["losses"]), 1)
        self.assertTrue(any("потеряно строк" in r for r in stats["red"]), stats["red"])

    def test_agreed_file_untouched_red(self):
        """Согласованный файл без единой правки: «изменённые = согласованные» в обе стороны (ревью 31.08)."""
        self.active.write_text(ACTIVE + "- [ ] Новая задача — отв. Эрик\n", encoding="utf-8")
        _, stats = self.run_check("")
        self.assertTrue(any("не изменено" in r for r in stats["red"]), stats["red"])

    def test_merge_element_in_other_file_still_red(self):
        """Элемент объединяемой записи ищется в том же файле: совпадение в чужом маскирует потерю (ревью 31.08)."""
        self.resnap(["kit/02_active.md", "kit/05_decisions.md"])
        self.decisions.write_text("# Решения\n\n- Runtime — Claude Code, адаптеры отложены\n",
                                  encoding="utf-8")
        self.active.write_text(ACTIVE + "- [ ] Сверка 06.08 — [основание](notes/runtime.md)\n",
                               encoding="utf-8")
        ledger = ("объединена: Runtime — Claude Code — на 06.08, [основание](notes/runtime.md)\n"
                  "удалена: Адаптеры отложены\n")
        _, stats = self.run_check(ledger)
        self.assertEqual({el for _, el in stats["merge_missing"]},
                         {"06.08", "notes/runtime.md"})
        self.assertTrue(any("объединении" in r for r in stats["red"]), stats["red"])

    def test_header_counters_match_stats(self):
        """Счётчики шапки отчёта равны фактическому содержимому stats."""
        self.active.write_text(ACTIVE + "- [ ] Новая задача — отв. Эрик\n", encoding="utf-8")
        report, stats = self.run_check("")
        m = re.search(r"Файлов согласовано (\d+) · тронуто в области (\d+) · "
                      r"незапланированных (\d+) · правок мимо пакета (\d+)", report)
        self.assertIsNotNone(m)
        self.assertEqual([int(g) for g in m.groups()],
                         [stats["agreed"], stats["touched"],
                          len(stats["unplanned"]), len(stats["extra"])])
        m2 = re.search(r"Потеряно строк без якоря (\d+) · якорей (\d+) · "
                       r"без совпадений (\d+) · добавлено строк (\d+)", report)
        self.assertEqual([int(g) for g in m2.groups()],
                         [len(stats["losses"]), stats["anchors"],
                          len(stats["anchors_missing"]), stats["added"]])


if __name__ == "__main__":
    unittest.main()
