"""Тесты формы anchor_check.py: найдено / не найдено / склейка / счётчики.

Мутационная проверка инварианта «пропавшая опора видна»: одна и та же точка
на источнике с опорой и без неё обязана дать разные статусы — скрипт,
который всё называет найденным, здесь краснеет.

Запуск: python3 -m unittest discover -s tests  (из папки скилла)
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import anchor_check  # noqa: E402

SOURCE = """\
**Виктор** [00:10]: Так, мы запускаем проект — решено, стартуем в понедельник.
Ещё успеем обсудить бюджет.

**Эрик** [00:20]: Хорошо, принял. Я подготовлю стенд к среде.

**Виктор** [00:30]: Отлично. Про бюджет вернёмся позже.
"""

DRAFT = """\
- Запускаем проект · решение — «Мы запускаем проект – решено, стартуем в понедельник» [00:10]
- Эрик готовит стенд · обязательство — «еще успеем обсудить бюджет… я подготовлю стенд к среде» [00:20]
- Согласован бюджет · решение — «бюджет утверждаем полностью» [00:30]
"""


def run(draft, source, points):
    return anchor_check.build_report(draft, source, points, source_name="test")


class TestAnchorCheck(unittest.TestCase):
    points = [line[2:] for line in DRAFT.splitlines()]

    def test_normalized_match_and_attribution(self):
        """Разнобой (регистр, тире, ё→е, перенос строки) находке не мешает."""
        report, stats = run(DRAFT, SOURCE, [self.points[0]])
        self.assertEqual((stats["full"], stats["miss"]), (1, 0))
        self.assertIn("найден · Виктор [00:10]", report)

    def test_splice_across_speakers(self):
        """Цитата, склеенная из реплик двух спикеров, помечается склейкой."""
        report, stats = run(DRAFT, SOURCE, [self.points[1]])
        self.assertEqual(stats["splice"], 1)
        self.assertIn("склейка из разных мест", report)
        self.assertIn("Виктор", report)
        self.assertIn("Эрик", report)

    def test_splice_inside_one_turn(self):
        """Цитата, собранная из далёких кусков ОДНОЙ реплики, — тоже склейка.
        Счёт реплик её не видит: спикер один, а места разные (находка Codex)."""
        source = ("**Виктор** [01:00]: Начнём с бюджета, там всё понятно и "
                  "давно посчитано, потом обсудим сроки поставки и людей, "
                  "а в самом конце вернёмся к найму подрядчика.\n")
        point = "Найм подрядчика · решение — «начнём с бюджета вернёмся к найму подрядчика» [01:00]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual(stats["splice"], 1)
        self.assertIn("куски одной реплики стоят не подряд", report)

    def test_continuous_quote_with_noise_is_not_splice(self):
        """Обратная сторона: непрерывная цитата с одним неузнанным словом
        внутри склейкой не объявляется — иначе метка обесценится."""
        source = "**Эрик** [02:00]: Я подготовлю рабочий стенд к среде.\n"
        point = "Эрик готовит стенд — «я подготовлю рабоч стенд к среде» [02:00]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual(stats["splice"], 0)
        self.assertNotIn("склейка", report)

    def test_ellipsis_inside_one_turn_is_not_splice(self):
        """Цитата с «…» — объявленный пропуск: куски одной реплики по порядку
        склейкой не считаются (ночь 01.09: 16 из 16 таких «склеек» были ложными)."""
        source = ("**Виктор** [01:00]: Начнём с бюджета, там всё понятно и "
                  "давно посчитано, потом обсудим сроки поставки и людей, "
                  "а в самом конце вернёмся к найму подрядчика.\n")
        point = "Найм · решение — «начнём с бюджета, там всё понятно… вернёмся к найму подрядчика» [01:00]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual(stats["splice"], 0)
        self.assertNotIn("склейка", report)

    def test_ellipsis_out_of_order_is_splice(self):
        """Те же куски, но в цитате переставлены — это уже склейка."""
        source = ("**Виктор** [01:00]: Начнём с бюджета, там всё понятно и "
                  "давно посчитано, потом обсудим сроки поставки и людей, "
                  "а в самом конце вернёмся к найму подрядчика.\n")
        point = "Найм · решение — «вернёмся к найму подрядчика… начнём с бюджета, там всё понятно» [01:00]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual(stats["splice"], 1)

    def test_ellipsis_across_adjacent_turns_same_speaker_is_not_splice(self):
        """Соседние реплики одного спикера по порядку — законное цитирование через «…»."""
        source = ("**Эрик** [34:22]: Надо понять, нужна она или нет, прежде чем строить.\n"
                  "**Эрик** [34:28]: Ну, это с тестом проверим на следующей неделе.\n")
        point = "Проверка · задача — «надо понять, нужна она или нет… ну, это с тестом проверим» [34:22]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual(stats["splice"], 0)

    def test_ellipsis_across_speakers_stays_splice(self):
        """Многоточие не легализует склейку из реплик разных людей."""
        source = ("**Эрик** [34:22]: Надо понять, нужна она или нет, прежде чем строить.\n"
                  "**Виктор** [34:28]: Ну, это с тестом проверим на следующей неделе.\n")
        point = "Проверка · задача — «надо понять, нужна она или нет… ну, это с тестом проверим» [34:22]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual(stats["splice"], 1)

    def test_mutation_missing_anchor_flips_status(self):
        """Инвариант: опоры нет в источнике → якорь «не найден», не «найден»."""
        _, stats = run(DRAFT, SOURCE, [self.points[2]])
        self.assertEqual((stats["miss"], stats["full"]), (1, 0))
        mutated = SOURCE.replace("Про бюджет вернёмся позже",
                                 "Так, бюджет утверждаем полностью")
        _, stats2 = run(DRAFT, mutated, [self.points[2]])
        self.assertEqual((stats2["miss"], stats2["full"]), (0, 1))

    def test_anchor_picks_occurrence_near_point_timecode(self):
        """Короткий якорь при таймкоде в точке привязывается к вхождению рядом
        с ним, а не к первому в файле (ложное обвинение серии r1-3, точка 4)."""
        source = ("**Виктор** [00:10]: Окей. Начнём с бюджета.\n\n"
                  "**Эрик** [05:00]: Окей. Статусы документов сверим завтра.\n")
        point = "Статусы документов · решение — «Окей» [05:00]"
        report, _ = run(f"- {point}\n", source, [point])
        self.assertIn("найден · Эрик [05:00]", report)

    def test_header_counters_match_body(self):
        """Счётчики шапки равны фактическому содержимому отчёта."""
        report, stats = run(DRAFT, SOURCE, self.points)
        m = re.search(r"якорей (\d+) · найдено (\d+) · частично (\d+) · "
                      r"не найдено (\d+) · склеек (\d+)", report)
        self.assertIsNotNone(m)
        self.assertEqual([int(g) for g in m.groups()],
                         [stats["anchors"], stats["full"], stats["partial"],
                          stats["miss"], stats["splice"]])
        self.assertEqual(stats["anchors"], stats["full"] + stats["partial"] + stats["miss"])


if __name__ == "__main__":
    unittest.main()
