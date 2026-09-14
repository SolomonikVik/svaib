#!/usr/bin/env python3
"""Кодовый ярус дефолтной проверки выжимки в оркестраторе meeting-analysis-beta.

Вход: черновик выжимки, список ключевых точек (строки черновика), источник.
Выход: markdown-файл контрольного следа — по каждой точке её якоря-цитаты:
найдены ли в источнике, кто произнёс, склейки из разных мест; фрагменты
разговора вокруг найденного. Скрипт ищет и режет, но не судит: исходы по
словарю проверки ставит модель, читающая этот файл.

Поиск нормализованный: NFC, нижний регистр, ё→е, только слова — разнобой
расшифровки (тире, кавычки, регистр, перенос строки внутри цитаты) совпадению
не мешает. Цитата с «…» ищется по частям. Только stdlib.

Форма источника не задана списком вендоров: реплика разбирается на три
необязательных элемента — кто · когда · текст, — и скрипт объявляет в следе,
что из них в записи есть. Атрибуции нет — «кто произнёс» не проверяется, и это
сказано судье прямым текстом, а не оставлено пустым полем. Таймкодов нет —
адресом якоря становится номер строки источника.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

TOKEN = re.compile(r"\w+", re.UNICODE)
QUOTE_SPAN = re.compile(r"«([^«»\n]+)»|„([^„“”\n]+)[“”]|“([^“”\n]+)”|\"([^\"\n]+)\"")
ELLIPSIS = re.compile(r"…|\.\.\.")
#: Ведущая обёртка строки: `[…]` или `(…)` — в ней часто стоит метка времени.
LEAD_BRACKET = re.compile(r"^\[\s*(?P<in>[^\]\n]{1,60}?)\s*\]\s*|"
                          r"^\(\s*(?P<in2>[^)\n]{1,60}?)\s*\)\s*")
#: Время в любом написании: `1:02`, `01:02:03`, `00:00:01.000`.
TIME_HEAD = re.compile(r"^(?P<h>\d{1,3}):(?P<m>[0-5]\d)(?::(?P<s>[0-5]\d))?(?:[.,]\d+)?")
#: Время секундами: `3.86`, `12,5`, `5` — только внутри обёртки или перед стрелкой.
SEC_HEAD = re.compile(r"^\d+(?:[.,]\d+)?")
#: Диапазон: `начало --> конец`, `начало -> конец`.
RANGE = re.compile(r"^\s*(?:-+>|—>|–>|→|⟶)\s*")
#: Явная разметка голоса WebVTT: `<v Имя>текст`.
VOICE = re.compile(r"^<v\s+(?P<who>[^>]{1,60})>\s*(?P<text>.*)$")
#: Метка времени внутри головы реплики: `**Имя** [00:10]:`, `Имя (12:30) —`.
HEAD_TIME = re.compile(r"[\[(]\s*\d{1,3}[:.,]\d[^\])\n]{0,20}\s*[\])]|"
                       r"\b\d{1,3}:[0-5]\d(?::[0-5]\d)?\b")
#: Тире как разделитель имени и речи: `Имя — текст`. Двоеточие — первый кандидат.
DASH_SEP = re.compile(r"\s+[—–-]\s+")
#: Блок субтитров: строка-номер имеет смысл только рядом с `-->`.
CUE_MARK = re.compile(r"\d\s*(?:-+>|—>|–>|→|⟶)\s*\d")
#: Скобочная приписка к имени: `Иван (PM)`, `Виктор (Клиент D)`, `Speaker [2]`.
NAME_PAREN = re.compile(r"\s*[\[(][^\])\n]{0,40}[\])]\s*")
#: Разметка документа, которой не бывает в записи разговора: заголовки и таблицы.
DOC_MARK = re.compile(r"^\s{0,3}#{1,6}\s|^\s*\|.*\|\s*$")
#: Адрес якоря в источнике без таймкодов — `[строка 76]`.
LINEREF = re.compile(r"строк[аиеу]\s+(\d+)", re.IGNORECASE)
#: Обрамление имени в разметке: `**Имя**`, `__Имя__`, «Имя».
TRIM = " \t*_#>«»\"'"
#: Разметка документа: ссылки, код, таблицы, стрелки схем. В имени их не бывает.
NOT_IN_NAME = set("[]()`|→←↑↓•#=~")
#: Докуда ищем голову реплики: дальше начала строки говорящий не прячется.
HEAD_LIMIT = 80
#: Таймкод в тексте точки — по нему ищется опорная реплика.
TIMECODE = re.compile(r"(?<![\d:])(\d{1,3}):([0-5]\d)(?::([0-5]\d))?(?![\d:])")

#: Кусок цитаты короче трёх слов отдельно не ищется: совпадёт где угодно.
MIN_SEG = 3


def norm_token(tok: str) -> str:
    return unicodedata.normalize("NFC", tok).lower().replace("ё", "е")


def tokenize(text: str) -> list:
    return [norm_token(m.group()) for m in TOKEN.finditer(text)]


def seconds(tc: str):
    m = TIMECODE.search(tc or "")
    if not m:
        return None
    a, b, c = m.group(1), m.group(2), m.group(3)
    return int(a) * 3600 + int(b) * 60 + int(c) if c else int(a) * 60 + int(b)


def _mmss(total: float) -> str:
    total = int(total)
    return f"{total // 60:02d}:{total % 60:02d}"


def _read_time(text: str, with_len: bool = False):
    """Время в начале строки: `MM:SS`, `H:MM:SS` или секунды с дробью."""
    t = (text or "").lstrip()
    pad = len(text or "") - len(t)
    m = TIME_HEAD.match(t)
    if m:
        total = int(m.group("h")) * 60 + int(m.group("m"))
        if m.group("s"):
            total = int(m.group("h")) * 3600 + int(m.group("m")) * 60 + int(m.group("s"))
        return (_mmss(total), pad + m.end()) if with_len else _mmss(total)
    m = SEC_HEAD.match(t)
    if m:
        val = _mmss(float(m.group().replace(",", ".")))
        return (val, pad + m.end()) if with_len else val
    return (None, 0) if with_len else None


def lead_time(line: str):
    """Снимает со строки **ведущую** метку времени в любом её написании.

    Отличать транскрибаторов не нужно: метка времени — это время в самом
    начале строки, само по себе, в скобках или как начало диапазона. Время
    в середине строки не трогается никогда: `В 12:30 обсудим бюджет` — речь,
    и вырезать из неё срок значит испортить то, что проверяем.
    """
    rest, tc = line.strip(), None
    for _ in range(3):  # `[00:01 --> 00:04]`, `1` + `00:01 --> 00:04` — не глубже
        m = LEAD_BRACKET.match(rest)
        inner = (m.group("in") or m.group("in2")) if m else None
        if inner is not None:
            got = _read_time(inner)
            if got is None:
                break
            tc = tc or got
            rest = rest[m.end():]
            continue
        got, used = _read_time(rest, with_len=True)
        if got is None:
            break
        bare_seconds = not TIME_HEAD.match(rest.lstrip())
        if bare_seconds and not re.match(r"^\d+[.,]\d", rest.lstrip()):
            got = None if not RANGE.match(rest.lstrip()[used:].lstrip()) else got
            if got is None:
                break  # голое целое в начале строки — номер пункта, не тайминг
        after = rest[used:].lstrip()
        if bare_seconds and not RANGE.match(after):
            break  # `12.5 млн рублей` — сумма, а не тайминг: секунды меткой
                   # считаются только в скобках или как начало диапазона
        tc = tc or got
        rest = after
        mr = RANGE.match(rest)
        if mr:  # правая граница диапазона нам не нужна
            rest = rest[mr.end():].lstrip()
            _, used2 = _read_time(rest, with_len=True)
            rest = rest[used2:].lstrip() if used2 else rest
        break
    return tc, rest


def norm_name(name: str) -> str:
    """Ключ повторяемости: `Виктор` и `ВИКТОР` — один и тот же голос."""
    return norm_token(" ".join(name.split()))


def plausible_speaker(name: str) -> bool:
    """Имя говорящего коротко, содержит буквы, не кончается точкой и не несёт
    разметки документа — этим оно и отличается от строки текста с двоеточием."""
    n = (name or "").strip(TRIM)
    if not n or len(n) > 60 or n[-1] in ".,!?;":
        return False
    if NOT_IN_NAME & set(n) or not any(ch.isalpha() for ch in n):
        return False
    return 1 <= len(n.split()) <= 5


def split_speaker(rest: str):
    """Делит строку на голову — объявление говорящего — и речь.

    Голова ищется только до разделителя (`:` или тире) в начале строки, и
    метка времени снимается **только из головы**: `**Имя** [00:10]: текст`,
    `Имя (12:30) — текст`. Головы нет — вся строка речь, и в ней ничего не
    вырезается.

    Возвращает `(имя, метка времени, речь, размечено)`; `размечено` — рядом с
    именем стояла метка времени, то есть строка сама объявила себя репликой.
    """
    m = VOICE.match(rest)
    if m:
        return m.group("who").strip(TRIM), None, m.group("text"), True
    zone = rest[:HEAD_LIMIT]
    # двоеточие внутри таймкода разделителем не считается
    masked = HEAD_TIME.sub(lambda mm: "·" * len(mm.group()), zone)
    cut, sep_len = masked.find(":"), 1
    if cut < 0:
        md = DASH_SEP.search(masked)
        if md:
            cut, sep_len = md.start(), md.end() - md.start()
    if cut < 0:
        return None, None, rest, False
    head = zone[:cut]
    tc = None
    times = HEAD_TIME.findall(head)
    if times:
        got = _read_time(HEAD_TIME.search(head).group().strip("[]() "))
        tc = got
        head = HEAD_TIME.sub(" ", head)
    if not plausible_speaker(head):
        # приписка в скобках — часть подписи, а не часть имени: `Иван (PM):`
        stripped = NAME_PAREN.sub(" ", head).strip()
        if stripped == head.strip() or not plausible_speaker(stripped):
            return None, None, rest, False
        head = stripped
    text = rest[cut + sep_len:].lstrip()
    return head.strip(TRIM), tc, text, tc is not None


def detect_speakers(lines: list):
    """Кто в этом файле говорящий — выводится из самого файла, а не из списка
    известных форматов.

    Кандидат — короткое имя в голове строки или короткая самостоятельная
    строка. Кандидаты становятся голосами при одном из двух признаков записи:

    - в записи есть ведущие метки времени или подпись без текста (`Имя:` и
      речь абзацем ниже) — так пишет транскрибатор, но не документ: у поля
      документа значение стоит той же строкой;
    - имя повторяется, собеседник у него есть, а сам файл не размечен как
      документ — ни заголовков, ни таблиц.

    Второе условие и отделяет разговор от документа: `**Цель**: …` рядом с
    `**Срок**: …` статистически выглядит так же, как двое собеседников, и
    различает их только жанр файла. Ни одного признака — у записи нет
    разметки говорящих, и это нормальный исход.
    """
    named, solo, timed, layout = {}, {}, False, False
    for raw in lines:
        tc, rest = lead_time(raw)
        timed = timed or tc is not None  # ведущая метка времени — почерк записи
        if not rest.strip():
            continue
        who, head_tc, text, strong = split_speaker(rest)
        if who:
            named.setdefault(norm_name(who), []).append(who)
            # `Имя:` без текста, речь абзацем ниже — так пишет транскрибатор,
            # а не документ: у поля документа значение стоит той же строкой
            timed = timed or strong
            layout = layout or not text.strip()
            continue
        bare = rest.strip()
        if plausible_speaker(bare) and ":" not in bare:
            solo.setdefault(norm_name(bare), []).append(bare)
    def spelled(d, minimum=1):
        return {w for forms in d.values() if len(forms) >= minimum for w in forms}

    voices = spelled(named) | spelled(solo, 2)
    if timed:
        return voices  # метки времени перевешивают всё: это запись разговора
    if any(DOC_MARK.match(l) for l in lines):
        return set()  # заголовки и таблицы — жанр документа, а не разговора
    repeated = spelled(named, 2) | spelled(solo, 2)
    if (layout or repeated) and len(voices) > 1:
        return voices
    return set()


def _by_paragraphs(lines: list) -> list:
    """Разметки нет вовсе: единица — абзац. Адрес якоря остаётся — номер строки."""
    turns, buf, start = [], [], 1
    for i, raw in enumerate(lines, 1):
        if raw.strip():
            if not buf:
                start = i
            buf.append(raw.strip())
        elif buf:
            turns.append(_turn("", "", "\n".join(buf), start))
            buf = []
    if buf:
        turns.append(_turn("", "", "\n".join(buf), start))
    return turns or [_turn("", "", "\n".join(lines), 1)]


def _turn(who: str, tc: str, text: str, line: int) -> dict:
    """Реплика помнит, с какой строки источника начинается каждый её кусок:
    адрес якоря — строка самой цитаты, а не строка, где стояло имя."""
    return {"who": who, "tc": tc, "text": text, "line": line,
            "map": [(0, line)] if text else []}


def _extend(turn: dict, text: str, line: int) -> None:
    if not text:
        return
    if turn["text"]:
        turn["map"].append((len(turn["text"]) + 1, line))
        turn["text"] += "\n" + text
    else:
        turn["text"] = text
        turn["map"] = [(0, line)]
        turn["line"] = line  # текст пришёл ниже имени — адрес считаем по тексту


def line_at(turn: dict, offset=None) -> int:
    """Строка источника, которой принадлежит символ `offset` внутри реплики."""
    spans = turn.get("map") or [(0, turn.get("line", 0))]
    if offset is None:
        return spans[0][1]
    line = spans[0][1]
    for start, num in spans:
        if start <= offset:
            line = num
        else:
            break
    return line


def strip_frontmatter(lines: list) -> list:
    """YAML-шапка файла — служебное поле, а не реплики: `title:` не говорящий."""
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or lines[i].strip() != "---":
        return lines
    for j in range(i + 1, min(len(lines), i + 40)):
        if lines[j].strip() != "---":
            continue
        body = [l for l in lines[i + 1:j] if l.strip()]
        # шапка — это поля `ключ: значение`. Иначе `---` просто разделитель,
        # и текст между ними принадлежит разговору: вырезать его значит потерять
        fields = sum(1 for l in body if re.match(r"^[A-Za-z_][\w-]{0,29}:", l))
        if len(body) > 1 and fields == len(body):
            return lines[:i] + [""] * (j + 1 - i) + lines[j + 1:]
        return lines
    return lines


def parse_source(lines: list):
    """Источник разбирается на три необязательных элемента: кто · когда · текст.

    Формат не опознаётся по транскрибатору и не нормализуется руками. Со
    строки снимается ведущая метка времени, голова строки делится на имя и
    речь, а кто здесь имя — выводится из повторяемости и разметки самого
    файла. Новая реплика начинается там, где сменился голос или появилась
    новая метка времени; строка без того и другого продолжает предыдущую.
    Речь до первой реплики не теряется — она становится безымянной репликой.

    Возвращает реплики и оси источника: `speaker` — `есть`, `частично` или
    `нет`, `time` — чем адресуется якорь: `timecode` или `line`.
    """
    lines = strip_frontmatter(lines)
    speakers = detect_speakers(lines)
    has_cues = any(CUE_MARK.search(l) for l in lines)
    turns, current = [], ""
    for i, raw in enumerate(lines, 1):
        tc, rest = lead_time(raw)
        if not rest.strip():
            continue
        who, head_tc, text, _ = split_speaker(rest)
        if who not in speakers:
            who, text = None, rest
        else:
            tc = tc or head_tc
        if who is None and rest.strip() in speakers:
            who, text = rest.strip(), ""
        if who is None and has_cues and text.strip().isdigit() and tc is None:
            continue  # номер блока субтитров — только там, где блоки есть
        if who is not None:
            current = who
        elif tc is None:
            if turns:
                _extend(turns[-1], text.strip(), i)
            else:  # речь до первой реплики: безымянная, но не потерянная
                turns.append(_turn("", "", text.strip(), i))
            continue
        if turns and not turns[-1]["text"].strip() and turns[-1]["who"] == (current or ""):
            turns[-1]["tc"] = turns[-1]["tc"] or (tc or "")
            _extend(turns[-1], text.strip(), i)
            continue
        turns.append(_turn(current if who is not None else "", tc or "", text.strip(), i))
    turns = [t for t in turns if t["text"].strip()]
    if not any(t["who"] or t["tc"] for t in turns):
        # ни голосов, ни меток: единицей становится абзац — иначе весь файл
        # окажется одной репликой, и фрагмент вокруг якоря вырастет до неё
        turns = _by_paragraphs(lines)
    with_who = sum(1 for t in turns if t["who"])
    with_tc = sum(1 for t in turns if t["tc"])
    if not with_who:
        speaker = "нет"
    elif with_who == len(turns):
        speaker = "есть"
    else:
        speaker = "частично"
    if not with_tc:
        time_axis = "line"
    elif with_tc == len(turns):
        time_axis = "timecode"
    else:
        time_axis = "mixed"
    fmt = {"turns": len(turns), "speaker": speaker, "time": time_axis}
    fmt["form"] = {"есть": "реплики с именами",
                   "частично": "реплики с именами, часть без голоса",
                   "нет": "без разметки говорящих"}[speaker] + \
                  {"timecode": ", таймкоды",
                   "mixed": ", таймкоды не у всех реплик",
                   "line": ", адрес по строкам"}[time_axis]
    return turns, fmt


# --- источник --------------------------------------------------------------

def build_index(turns: list):
    """Сквозной поток токенов: цитата через перенос строки находится."""
    toks, meta, positions = [], [], {}
    for ti, turn in enumerate(turns):
        for m in TOKEN.finditer(turn["text"]):
            tok = norm_token(m.group())
            positions.setdefault(tok, []).append(len(toks))
            toks.append(tok)
            meta.append((ti, m.start(), m.end()))
    return toks, meta, positions


def find_all_seq(needle: list, toks: list, positions: dict, cap: int = 50) -> list:
    hits = []
    if not needle:
        return hits
    for start in positions.get(needle[0], ()):
        if toks[start:start + len(needle)] == needle:
            hits.append(start)
            if len(hits) >= cap:
                break
    return hits


def find_seq(needle: list, toks: list, positions: dict, near=None):
    """Первое вхождение; при `near` — ближайшее к нему: короткая часть цитаты
    ищется рядом с её длинной частью, а не по первому совпадению в файле."""
    hits = find_all_seq(needle, toks, positions)
    if not hits:
        return None
    if near is None:
        return hits[0]
    return min(hits, key=lambda h: abs(h - near))


def greedy_segments(needle: list, toks: list, positions: dict) -> list:
    """Максимальные найденные куски слева направо; ненайденные слова пропускаются.
    Возвращает `(позиция в источнике, длина, индекс в цитате)`."""
    segs, i = [], 0
    while i < len(needle):
        hit = None
        for ln in range(len(needle) - i, MIN_SEG - 1, -1):
            pos = find_seq(needle[i:i + ln], toks, positions)
            if pos is not None:
                hit = (ln, pos)
                break
        if hit:
            segs.append((hit[1], hit[0], i))
            i += hit[0]
        else:
            i += 1
    return segs


def gap_splice(ordered: list, part_starts=frozenset()) -> bool:
    """Куски, идущие подряд в самой цитате, стоят в источнике не подряд.

    Ловит склейку внутри одной реплики, которую счёт реплик не видит: цитата
    собрана из далёких кусков одного длинного высказывания. Разрыв в источнике
    сравнивается с разрывом в цитате — пропущенные при поиске слова разрывом не
    считаются; допуск `MIN_SEG` оставлен на разнобой расшифровки.

    Граница «…» (`part_starts` — начала частей цитаты после многоточия) —
    объявленный пропуск: разрыв там законен, лишь бы части шли по порядку
    (ночь 01.09: 16 из 16 «склеек» были цитатами с многоточием).
    """
    ordered = sorted(ordered)
    for (i1, p1, l1), (i2, p2, l2) in zip(ordered, ordered[1:]):
        src_gap = p2 - (p1 + l1)
        quote_gap = i2 - (i1 + l1)
        if src_gap < 0:
            return True
        if i2 in part_starts:
            continue
        if src_gap > quote_gap + MIN_SEG:
            return True
    return False


def check_anchor(quote: str, toks: list, meta: list, positions: dict, near=None,
                 who=None) -> dict:
    """`near` — стартовая опора (позиция токена у таймкода точки): короткий якорь
    привязывается к вхождению рядом с ней, а не к первому в файле.
    `who` — спикер по номеру реплики: цитата с «…» через соседние реплики одного
    спикера, идущие по порядку, склейкой не считается."""
    parts = [p for p in (s.strip() for s in ELLIPSIS.split(quote)) if tokenize(p)]
    if len(parts) > 1:  # кусок между «…» короче MIN_SEG совпадёт где угодно — не ищется
        parts = [p for p in parts if len(tokenize(p)) >= MIN_SEG] or parts
    part_toks = [tokenize(p) for p in parts]
    offsets, acc = [], 0  # начало части в цитате целиком — для счёта разрывов
    for ptoks in part_toks:
        offsets.append(acc)
        acc += len(ptoks)
    order = sorted(range(len(parts)),
                   key=lambda i: -len(part_toks[i]))  # длинная часть — опора для коротких
    segs, ordered, total, matched, exact, anchored = [], [], 0, 0, True, False
    for i in order:
        ptoks = part_toks[i]
        total += len(ptoks)
        pos = find_seq(ptoks, toks, positions, near=near)
        if pos is not None:
            segs.append((pos, len(ptoks)))
            ordered.append((offsets[i], pos, len(ptoks)))
            matched += len(ptoks)
            if not anchored:  # найденная длинная часть — опора точнее таймкода
                near, anchored = pos, True
        else:
            exact = False
            for pos2, ln, idx in greedy_segments(ptoks, toks, positions):
                segs.append((pos2, ln))
                ordered.append((offsets[i] + idx, pos2, ln))
                matched += ln
    segs.sort(key=lambda s: s[0])
    turn_ids = sorted({meta[pos][0] for pos, _ in segs})
    status = "full" if exact and total and matched == total else ("partial" if segs else "miss")
    part_starts = frozenset(offsets[1:]) if len(parts) > 1 else frozenset()
    turn_splice = len(turn_ids) > 1
    if turn_splice and part_starts and who is not None:
        adjacent = turn_ids[-1] - turn_ids[0] + 1 == len(turn_ids)
        one_voice = len({who[t] for t in turn_ids}) == 1
        in_order = all(p1 <= p2 for (_, p1, _), (_, p2, _) in
                       zip(sorted(ordered), sorted(ordered)[1:]))
        turn_splice = not (adjacent and one_voice and in_order)
    return {"quote": quote, "status": status, "matched": matched, "total": total,
            "segs": segs, "turns": turn_ids,
            "splice": turn_splice or gap_splice(ordered, part_starts)}


def turn_by_line(turns: list, target: int):
    """Реплика, которой принадлежит строка источника: адрес якоря без таймкодов.

    Смотрит на все строки реплики, а не только на первую: у записи, где имя
    стоит отдельной строкой, текст начинается ниже, и точка ссылается на него.
    """
    best = None
    for ti, turn in enumerate(turns):
        nums = [n for _, n in (turn.get("map") or [(0, turn.get("line", 0))])]
        if not nums:
            continue
        if nums[0] <= target <= nums[-1]:
            return ti
        if nums[0] <= target:
            best = ti
        else:
            break
    return best


def turn_by_timecode(turns: list, target: int):
    best = None
    for ti, turn in enumerate(turns):
        sec = seconds(turn["tc"])
        if sec is None:
            continue
        if sec <= target:
            best = ti
        elif best is None:
            return ti
    return best


# --- отчёт -----------------------------------------------------------------

def addr(turn, offset=None) -> str:
    """Адрес места в источнике: таймкод реплики, если он есть, иначе номер
    строки — той самой, где стоит цитата, а не той, где стояло имя."""
    return f" [{turn['tc']}]" if turn["tc"] else f" [строка {line_at(turn, offset)}]"


def loc(meta, turns, pos) -> str:
    ti, start, _ = meta[pos]
    turn = turns[ti]
    return f"{turn['who'] or 'без спикера'}{addr(turn, start)}, реплика {ti + 1}"


def render_fragments(anchor_spans: dict, turns: list, window: int, context: int) -> list:
    out, printed = [], set()
    for ti in sorted(anchor_spans):
        for tj in (ti - 1, ti, ti + 1):
            if tj < 0 or tj >= len(turns) or tj in printed:
                continue
            if tj != ti and tj in anchor_spans:
                continue  # сам якорная реплика — напечатается со своим срезом
            printed.add(tj)
            text = turns[tj]["text"]
            if tj == ti and anchor_spans[ti] is not None:
                s, e = anchor_spans[ti]
                lo, hi = max(0, s - window), min(len(text), e + window)
            elif tj == ti:  # фрагмент по таймкоду — начало реплики
                lo, hi = 0, min(len(text), window * 2)
            elif tj < ti:
                lo, hi = max(0, len(text) - context), len(text)
            else:
                lo, hi = 0, min(len(text), context)
            snippet = (("⟨…⟩ " if lo else "") + text[lo:hi].strip()
                       + (" ⟨…⟩" if hi < len(text) else "")).replace("\n", " ")
            turn = turns[tj]
            out.append(f"**{turn['who'] or 'без спикера'}{addr(turn, lo)}** "
                       f"(реплика {tj + 1}): {snippet}")
    return out


STATUS_RU = {"full": "найден", "partial": "найден частично", "miss": "не найден"}
#: Чем адресуется якорь. Адрес выбирается у каждой реплики свой: есть у неё
#: таймкод — таймкод, нет — номер строки. Ось описывает запись, а не решает.
ADDR_RU = {"timecode": "таймкоды", "line": "строки источника",
           "mixed": "таймкоды у части реплик, у остальных строки"}


def build_report(draft_text: str, source_text: str, points: list,
                 source_name: str = "", window: int = 400, context: int = 250):
    turns, fmt = parse_source(source_text.splitlines())
    toks, meta, positions = build_index(turns)
    draft_norm = " ".join(tokenize(draft_text))
    first_tok = {}  # реплика → позиция её первого токена: опора поиска по таймкоду точки
    for idx, (ti, _, _) in enumerate(meta):
        first_tok.setdefault(ti, idx)

    stats = {"points": len(points), "anchors": 0, "full": 0, "partial": 0,
             "miss": 0, "splice": 0}
    sections, warnings = [], []

    for n, point in enumerate(points, 1):
        if " ".join(tokenize(point)) not in draft_norm:
            warnings.append(f"точка {n} не является строкой черновика — проверь вход")
        quotes = ["".join(g for g in m.groups() if g) for m in QUOTE_SPAN.finditer(point)]
        lines = [f"## Точка {n}", f"> {point}"]
        hint = None  # адрес точки → вхождение якоря ищется рядом, не первым по файлу
        bare = QUOTE_SPAN.sub("", point)
        m_tc = TIMECODE.search(bare)
        m_ln = LINEREF.search(bare)
        ti = None
        if m_tc:
            ti = turn_by_timecode(turns, seconds(m_tc.group()) or 0)
        elif m_ln:
            ti = turn_by_line(turns, int(m_ln.group(1)))
        if ti is not None:
            hint = first_tok.get(ti)
        anchor_spans = {}
        misses = False
        if not quotes:
            lines.append("- в точке нет дословного якоря (цитаты в кавычках)")
        for quote in quotes:
            stats["anchors"] += 1
            res = check_anchor(quote, toks, meta, positions, near=hint,
                               who=[t["who"] for t in turns])
            stats[res["status"]] += 1
            short = quote if len(quote) <= 70 else quote[:70] + "…"
            if res["status"] == "miss":
                misses = True
                lines.append(f"- «{short}» — не найден")
                continue
            spots = []
            for pos, ln in res["segs"]:
                ti, s, _ = meta[pos]
                _, _, e = meta[pos + ln - 1]
                prev = anchor_spans.get(ti)
                anchor_spans[ti] = (min(prev[0], s), max(prev[1], e)) if prev else (s, e)
                spots.append(loc(meta, turns, pos))
            where = " · ".join(dict.fromkeys(spots))
            note = ""
            if res["splice"]:
                stats["splice"] += 1
                if len(res["turns"]) > 1:
                    whos = sorted({turns[t]["who"] for t in res["turns"]})
                    note = (" · склейка из разных мест "
                            f"({', '.join(w or 'без спикера' for w in whos)})")
                else:
                    note = " · склейка из разных мест: куски одной реплики стоят не подряд"
            if res["status"] == "partial":
                note = f" ({res['matched']}/{res['total']} слов)" + note
            lines.append(f"- «{short}» — {STATUS_RU[res['status']]} · {where}{note}")
        if (misses or not quotes):  # добор материала по адресу самой точки
            for m in TIMECODE.finditer(bare):
                tj = turn_by_timecode(turns, seconds(m.group()) or 0)
                if tj is not None and tj not in anchor_spans:
                    anchor_spans[tj] = None
                    lines.append(f"- фрагмент по таймкоду {m.group()} — реплика {tj + 1}")
            for m in LINEREF.finditer(bare):
                tj = turn_by_line(turns, int(m.group(1)))
                if tj is not None and tj not in anchor_spans:
                    anchor_spans[tj] = None
                    lines.append(f"- фрагмент по строке {m.group(1)} — реплика {tj + 1}")
        frags = render_fragments(anchor_spans, turns, window, context)
        if frags:
            lines.append("Фрагменты:")
            lines.extend(frags)
        sections.append("\n".join(lines))

    head = [
        "# Контрольный след кода — якоря ключевых точек",
        f"Источник: {source_name or '—'} · реплик {fmt['turns']} · форма «{fmt['form']}» · "
        f"атрибуция: {fmt['speaker']} · "
        f"адрес якоря: {ADDR_RU[fmt['time']]}",
        f"Точек {stats['points']} · якорей {stats['anchors']} · найдено {stats['full']} · "
        f"частично {stats['partial']} · не найдено {stats['miss']} · склеек {stats['splice']}",
        "Файл читает судья; исходы по словарю проверки ставит он, не скрипт.",
    ]
    if fmt["speaker"] == "нет":
        head.append(
            "❗️ В источнике нет разметки говорящих — ни у одной реплики. «Кто произнёс» "
            "по этой записи не устанавливается в принципе: это свойство записи, а не "
            "дефект отдельной точки. Такие точки собираются в один общий пункт "
            "«атрибуция недоступна», а не размножаются одинаковыми сомнениями.")
    elif fmt["speaker"] == "частично":
        head.append(
            "⚠️ Разметка говорящих есть, но не у всех реплик: у части источника голос "
            "не указан. Точка, чья опора попала в безымянную реплику, атрибуции не "
            "имеет — это сигнал по самой точке, а не свойство записи.")
    if warnings:
        head.append("⚠️ " + " · ".join(warnings))
    stats["format"] = fmt
    return "\n\n".join(["\n".join(head)] + sections) + "\n", stats


def read_points(path: Path) -> list:
    pts = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        pts.append(re.sub(r"^[-*+]\s+", "", s))
    return pts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--draft", required=True, help="черновик выжимки")
    ap.add_argument("--source", required=True, help="источник (транскрипт)")
    ap.add_argument("--points", required=True, help="файл ключевых точек: строка = точка")
    ap.add_argument("--out", required=True, help="куда писать контрольный след")
    ap.add_argument("--window", type=int, default=400, help="символов вокруг якоря в его реплике")
    ap.add_argument("--context", type=int, default=250, help="символов из соседних реплик")
    args = ap.parse_args(argv)

    try:
        draft = Path(args.draft).read_text(encoding="utf-8")
        source = Path(args.source).read_text(encoding="utf-8")
        points = read_points(Path(args.points))
    except OSError as exc:
        print(f"вход не читается: {exc}", file=sys.stderr)
        return 2
    if not points:
        print("список ключевых точек пуст", file=sys.stderr)
        return 2

    report, stats = build_report(draft, source, points,
                                 source_name=Path(args.source).name,
                                 window=args.window, context=args.context)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(report, encoding="utf-8")
    fmt = stats["format"]
    print(f"{args.out}: форма «{fmt['form']}» · реплик {fmt['turns']} · "
          f"атрибуция {fmt['speaker']} · "
          f"адрес {ADDR_RU[fmt['time']]} · "
          f"точек {stats['points']} · якорей {stats['anchors']} · "
          f"найдено {stats['full']} · частично {stats['partial']} · "
          f"не найдено {stats['miss']} · склеек {stats['splice']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
