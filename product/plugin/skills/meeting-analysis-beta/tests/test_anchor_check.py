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


class TestSourceIntegrity(unittest.TestCase):
    """Разбор источника ничего в нём не портит и ничего не теряет.

    Все случаи — находки ревью 10.09 (Codex `gpt-6-astra`), воспроизведённые
    до починки: время и числа вырезались из речи, текст до первой реплики
    пропадал, одна безымянная реплика отключала атрибуцию по всему файлу.
    """

    def test_time_inside_speech_is_not_cut(self):
        """`В 12:30 обсудим бюджет` — речь, а не метка. Срок из неё не вырезается."""
        source = ("**Анна** [00:01]: Встречаемся завтра.\n"
                  "В 12:30 обсудим бюджет.\n"
                  "**Борис** [00:02]: Принял.\n")
        point = "Бюджет · задача — «в 12:30 обсудим бюджет» [00:01]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual((stats["full"], stats["miss"]), (1, 0))
        self.assertIn("найден · Анна", report)

    def test_money_is_not_read_as_timecode(self):
        """`12.5 млн рублей` — сумма. Дробное число внутри речи меткой не считается."""
        source = ("**Анна**: Какой бюджет?\n"
                  "12.5 млн рублей на первый квартал.\n"
                  "**Борис**: Принял.\n"
                  "**Анна**: Тогда решено.\n")
        point = "Бюджет · решение — «12.5 млн рублей на первый квартал» [строка 2]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual((stats["full"], stats["miss"]), (1, 0))

    def test_bare_number_line_survives_without_cues(self):
        """Строка-число выбрасывается только там, где есть блоки субтитров."""
        source = ("**Анна**: Сколько клиентов?\n"
                  "100000\n"
                  "**Борис**: Принял.\n"
                  "**Анна**: Хорошо.\n")
        turns, _ = anchor_check.parse_source(source.splitlines())
        self.assertIn("100000", " ".join(t["text"] for t in turns))

    def test_speech_before_first_turn_is_kept(self):
        """Текст до первой подписанной реплики не теряется."""
        source = ("Начало разговора без подписи, обсуждаем запуск проекта.\n\n"
                  "**Анна** [00:10]: А это уже я сказала.\n")
        point = "Запуск · решение — «обсуждаем запуск проекта» [строка 1]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual((stats["full"], stats["miss"]), (1, 0))

    def test_partial_attribution_is_not_global_off(self):
        """Одна безымянная реплика не отключает проверку голоса по всему файлу."""
        source = ("Реплика без подписи в начале записи.\n\n"
                  "**Анна** [00:10]: Запускаем проект.\n"
                  "**Борис** [00:20]: Принял.\n")
        point = "Запуск · решение — «запускаем проект» [00:10]"
        report, _ = run(f"- {point}\n", source, [point])
        self.assertIn("атрибуция: частично", report)
        self.assertNotIn("не устанавливается в принципе", report)


class TestSpeakerRecognition(unittest.TestCase):
    """Кого считать голосом. Все случаи — находки круга ревью 10.09
    (Codex `gpt-6-astra`, grok-4.6, hy4-preview): три голоса независимо
    назвали однократного спикера и разметку без двоеточия."""

    def test_single_utterance_speaker_is_recognized(self):
        """Участник, прозвучавший один раз, — голос, а не хвост предыдущего."""
        source = ("Виктор:\n\nМы запускаем проект.\n\n"
                  "Эрик:\n\nПринял, готовлю стенд к среде.\n\n"
                  "Виктор:\n\nЗначит решено.\n")
        point = "Стенд · задача — «принял, готовлю стенд к среде» [строка 5]"
        report, _ = run(f"- {point}\n", source, [point])
        self.assertIn("найден · Эрик", report)

    def test_four_speakers_once_each(self):
        """Круг статусов: четверо, каждый по одной реплике — все голоса."""
        source = ("**Анна** [00:01]: Раз.\n**Борис** [00:02]: Два.\n"
                  "**Вера** [00:03]: Три.\n**Глеб** [00:04]: Четыре.\n")
        turns, fmt = anchor_check.parse_source(source.splitlines())
        self.assertEqual(fmt["speaker"], "есть")
        self.assertEqual([t["who"] for t in turns], ["Анна", "Борис", "Вера", "Глеб"])

    def test_role_in_parentheses_is_not_part_of_name(self):
        """`Иван (PM):` — подпись Zoom: приписка не мешает узнать имя."""
        source = ("Иван (PM): Запускаем проект.\n"
                  "Анна (QA): Принял.\n"
                  "Иван (PM): Решено.\n")
        point = "Запуск · решение — «запускаем проект» [строка 1]"
        report, _ = run(f"- {point}\n", source, [point])
        self.assertIn("найден · Иван", report)

    def test_dash_separator_with_timecode(self):
        """Имя, время в скобках, тире — форма, которой в коде нет поимённо."""
        source = ("Анна (12:30) — Запускаем проект.\n"
                  "Борис (12:45) — Подготовлю стенд.\n")
        point = "Запуск · решение — «запускаем проект» [12:30]"
        report, _ = run(f"- {point}\n", source, [point])
        self.assertIn("найден · Анна [12:30]", report)

    def test_whole_seconds_range_is_a_timecode(self):
        """`[5 -> 10]` — тайминг целыми секундами, не текст."""
        source = ("[5 -> 10] Запускаем проект.\n[10 -> 15] Принял.\n[15 -> 20] Решено.\n")
        turns, fmt = anchor_check.parse_source(source.splitlines())
        self.assertEqual(fmt["time"], "timecode")
        self.assertEqual(turns[0]["tc"], "00:05")


class TestAddressAndFrontmatter(unittest.TestCase):
    """Адрес якоря и служебная шапка. Находки qwen3.8-max, круг 10.09."""

    def test_line_address_points_at_the_quote_not_the_name(self):
        """Имя строкой, речь абзацем ниже: адрес — строка речи, не строка имени."""
        source = ("Виктор:\n\nТак, мы запускаем проект.\n\n"
                  "Эрик:\n\nПринял, готовлю стенд.\n")
        point = "Стенд · задача — «принял, готовлю стенд» [строка 7]"
        report, _ = run(f"- {point}\n", source, [point])
        self.assertIn("найден · Эрик [строка 7]", report)

    def test_horizontal_rule_is_not_frontmatter(self):
        """`---` вокруг текста — разделитель. Речь между ними не вырезается."""
        source = ("---\nВступление: тут прозвучало решение о запуске.\n---\n"
                  "Дальше обычный текст разговора.\n")
        point = "Запуск · решение — «тут прозвучало решение о запуске» [строка 2]"
        _, stats = run(f"- {point}\n", source, [point])
        self.assertEqual((stats["full"], stats["miss"]), (1, 0))

    def test_yaml_header_is_still_stripped(self):
        """Обратная сторона: настоящая YAML-шапка голосами не становится."""
        source = ("---\ntitle: Дейли\ntype: transcript\n---\n\n"
                  "**Анна** [00:10]: Запускаем.\n**Борис** [00:20]: Принял.\n")
        turns, _ = anchor_check.parse_source(source.splitlines())
        self.assertEqual([t["who"] for t in turns], ["Анна", "Борис"])

    def test_markdown_doc_with_empty_labels_is_not_a_dialogue(self):
        """Документ, где подписи стоят строкой без значения, разговором не
        становится: жанр файла перевешивает форму строки (регресс 10.09)."""
        source = ("# Работа с файлом\n\n"
                  "**Что читать:**\n\nСначала README узла, потом миссии файлов.\n\n"
                  "**Куда писать:**\n\nВходящее — в `_inbox`, решения — в `05_decisions`.\n")
        turns, fmt = anchor_check.parse_source(source.splitlines())
        self.assertEqual(fmt["speaker"], "нет")

    def test_speaker_case_variants_are_one_voice(self):
        """`ВИКТОР` и `Виктор` — один голос при счёте повторяемости."""
        source = "ВИКТОР: Запускаем.\nВиктор: Решено.\nЭрик: Принял.\n"
        _, fmt = anchor_check.parse_source(source.splitlines())
        self.assertEqual(fmt["speaker"], "есть")

    def test_unicode_arrow_range(self):
        """Диапазон со стрелкой `→` — тоже тайминг."""
        source = "00:01 → 00:04 Запускаем проект.\n00:05 → 00:08 Принял.\n"
        turns, fmt = anchor_check.parse_source(source.splitlines())
        self.assertEqual(fmt["time"], "timecode")
        self.assertNotIn("00:04", turns[0]["text"])


class TestSourceForms(unittest.TestCase):
    """Оси источника: атрибуция есть или нет, адрес якоря — таймкод или строка.

    Разбор не знает вендоров: со строки снимается метка времени в любом
    написании, остаток делится на имя и текст, а кто здесь имя — выводится из
    повторяемости и разметки самого файла. Записи ниже — живые формы разных
    транскрибаторов, и ни одна из них не зашита в код.
    """

    def test_zoom_plain_speaker_lines(self):
        source = ("SPEAKER_01: Так, мы запускаем проект, стартуем в понедельник.\n"
                  "SPEAKER_02: Принял, готовлю стенд.\n"
                  "SPEAKER_01: Отлично, тогда решено.\n")
        point = "Запуск проекта · решение — «мы запускаем проект, стартуем в понедельник» [строка 1]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual((stats["full"], stats["miss"]), (1, 0))
        self.assertIn("атрибуция: есть", report)
        self.assertIn("найден · SPEAKER_01", report)

    def test_tldv_name_line_then_paragraph(self):
        source = ("Виктор:\n\nТак, мы запускаем проект, стартуем в понедельник.\n\n"
                  "Эрик:\n\nПринял, готовлю стенд к среде.\n\n"
                  "Виктор:\n\nОтлично, тогда решено.\n")
        point = "Стенд · задача — «принял, готовлю стенд к среде» [строка 5]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual((stats["full"], stats["miss"]), (1, 0))
        self.assertIn("атрибуция: есть", report)
        self.assertIn("найден · Эрик", report)

    def test_zoom_segments_with_seconds(self):
        """Сырой Zoom: голос строкой, тайминги в секундах отдельными скобками.
        Числа таймингов не должны попадать в текст — иначе они рвут цитату."""
        source = ("SPEAKER_01:\n"
                  "[    3.86 ->     7.86] Так, мы запускаем проект.\n"
                  "[    7.86 ->    11.86] Стартуем в понедельник.\n\n"
                  "SPEAKER_02:\n"
                  "[   12.00 ->    15.00] Принял, готовлю стенд.\n")
        point = "Запуск · решение — «так, мы запускаем проект» [00:03]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual((stats["full"], stats["miss"]), (1, 0))
        self.assertIn("найден · SPEAKER_01 [00:03]", report)
        self.assertIn("адрес якоря: таймкоды", report)

    def test_webvtt_cues_with_voice(self):
        source = ("WEBVTT\n\n"
                  "00:00:01.000 --> 00:00:04.000\n<v Виктор>Мы запускаем проект.\n\n"
                  "00:00:05.000 --> 00:00:08.000\n<v Эрик>Принял, готовлю стенд.\n\n"
                  "00:00:09.000 --> 00:00:12.000\n<v Виктор>Значит решено.\n")
        point = "Запуск · решение — «мы запускаем проект» [00:01]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual((stats["full"], stats["miss"]), (1, 0))
        self.assertIn("найден · Виктор", report)

    def test_no_markup_declares_missing_attribution(self):
        """Разметки нет — след говорит об этом прямо, а не оставляет поле пустым."""
        source = ("Мы запускаем проект, стартуем в понедельник.\n\n"
                  "Стенд готовит вторая сторона, к среде.\n")
        point = "Запуск · решение — «мы запускаем проект, стартуем в понедельник» [строка 1]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual(stats["full"], 1)
        self.assertIn("атрибуция: нет", report)
        self.assertIn("не устанавливается в принципе", report)
        self.assertIn("[строка 1]", report)

    def test_line_address_picks_right_occurrence(self):
        """Без таймкодов адресом служит строка: короткий якорь привязывается
        к вхождению рядом с ней, а не к первому в файле."""
        source = ("SPEAKER_01: Окей. Начнём с бюджета.\n"
                  "SPEAKER_02: Потом сроки.\n"
                  "SPEAKER_01: Окей. Статусы документов сверим завтра.\n")
        point = "Статусы документов · решение — «Окей» [строка 3]"
        report, _ = run(f"- {point}\n", source, [point])
        self.assertIn("найден · SPEAKER_01 [строка 3]", report)

    def test_unfamiliar_markup_still_parses(self):
        """Форма, которой в коде нет: имя, время в круглых скобках, тире."""
        source = ("Виктор (12:30) — Так, мы запускаем проект.\n"
                  "Эрик (12:45) — Принял, готовлю стенд.\n"
                  "Виктор (13:02) — Значит решено.\n")
        point = "Запуск · решение — «так, мы запускаем проект» [12:30]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual((stats["full"], stats["miss"]), (1, 0))
        self.assertIn("найден · Виктор", report)

    def test_yaml_frontmatter_is_not_speech(self):
        """Шапка файла — служебное поле: `title:` голосом не становится."""
        source = ("---\ntitle: \"Дейли\"\ntype: transcript\n---\n\n"
                  "**Виктор** [00:10]: Мы запускаем проект.\n"
                  "**Эрик** [00:20]: Принял.\n")
        point = "Запуск · решение — «мы запускаем проект» [00:10]"
        report, stats = run(f"- {point}\n", source, [point])
        self.assertEqual(stats["full"], 1)
        self.assertNotIn("title", report)
        self.assertIn("Виктор [00:10]", report)

    def test_markdown_document_is_not_a_dialogue(self):
        """Документ с жирными заголовками и ссылками разговором не считается:
        `**Пять частей продукта:**` — не говорящий."""
        source = ("# Продукт\n\n"
                  "**Пять частей продукта:** vision, methodology, scaffold.\n\n"
                  "- [02_active.md](02_active.md) — что горит сейчас: список задач.\n"
                  "- [glossary.md](glossary.md) — словарь: одно имя на понятие.\n\n"
                  "**Соло / малый бизнес:** ядро продукта и управленческий контекст.\n")
        point = "Проверка формы — «ядро продукта и управленческий контекст» [строка 9]"
        report, _ = run(f"- {point}\n", source, [point])
        self.assertIn("без разметки говорящих", report)

    def test_document_header_is_not_a_dialogue(self):
        """`Объект: X`, `Дата: Y` формой реплик не считаются — это шапка."""
        source = ("Объект: Клиент D\n"
                  "Дата: 2026-09-07\n"
                  "Тип встречи: okr-2\n"
                  "Участники: семеро\n\n"
                  "Дальше идёт сплошной текст разговора без разметки.\n")
        point = "Проверка формы — «дальше идёт сплошной текст разговора» [строка 6]"
        report, _ = run(f"- {point}\n", source, [point])
        self.assertIn("без разметки говорящих", report)


if __name__ == "__main__":
    unittest.main()
