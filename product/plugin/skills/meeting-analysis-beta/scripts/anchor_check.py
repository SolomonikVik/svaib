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
#: Реплика транскрипта формы `**Спикер** [MM:SS]: текст`.
TURN = re.compile(
    r"^\s*\*\*(?P<who>[^*\n]{1,60}?)\*\*\s*(?:\[(?P<tc>[^\]\n]{1,20})\])?\s*:\s*(?P<text>.*)$")
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


# --- источник --------------------------------------------------------------

def parse_turns(lines: list) -> list:
    """Реплики `**Спикер** [MM:SS]: текст`; строки без разметки продолжают
    предыдущую реплику. Разметки нет вовсе — весь текст одной «репликой»."""
    turns = []
    for raw in lines:
        m = TURN.match(raw)
        if m:
            turns.append({"who": m.group("who").strip(),
                          "tc": (m.group("tc") or "").strip(),
                          "text": m.group("text")})
        elif turns and raw.strip():
            turns[-1]["text"] += "\n" + raw.strip()
    if not turns:
        turns = [{"who": "", "tc": "", "text": "\n".join(lines)}]
    return turns


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

def loc(meta, turns, pos) -> str:
    ti = meta[pos][0]
    turn = turns[ti]
    tc = f" [{turn['tc']}]" if turn["tc"] else ""
    return f"{turn['who'] or 'без спикера'}{tc}, реплика {ti + 1}"


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
            tc = f" [{turn['tc']}]" if turn["tc"] else ""
            out.append(f"**{turn['who'] or 'без спикера'}{tc}** (реплика {tj + 1}): {snippet}")
    return out


STATUS_RU = {"full": "найден", "partial": "найден частично", "miss": "не найден"}


def build_report(draft_text: str, source_text: str, points: list,
                 source_name: str = "", window: int = 400, context: int = 250):
    turns = parse_turns(source_text.splitlines())
    toks, meta, positions = build_index(turns)
    draft_norm = " ".join(tokenize(draft_text))
    has_markup = any(t["who"] for t in turns)
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
        hint = None  # таймкод точки → вхождение якоря ищется рядом, не первым по файлу
        m_tc = TIMECODE.search(QUOTE_SPAN.sub("", point))
        if m_tc:
            ti = turn_by_timecode(turns, seconds(m_tc.group()) or 0)
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
        if (misses or not quotes):  # добор материала по таймкодам самой точки
            for m in TIMECODE.finditer(QUOTE_SPAN.sub("", point)):
                ti = turn_by_timecode(turns, seconds(m.group()) or 0)
                if ti is not None and ti not in anchor_spans:
                    anchor_spans[ti] = None
                    lines.append(f"- фрагмент по таймкоду {m.group()} — реплика {ti + 1}")
        frags = render_fragments(anchor_spans, turns, window, context)
        if frags:
            lines.append("Фрагменты:")
            lines.extend(frags)
        sections.append("\n".join(lines))

    head = [
        "# Контрольный след кода — якоря ключевых точек",
        f"Источник: {source_name or '—'} · реплик {len(turns)} · "
        + ("формат «**Спикер** [MM:SS]: текст»" if has_markup else "без разметки реплик — атрибуции нет"),
        f"Точек {stats['points']} · якорей {stats['anchors']} · найдено {stats['full']} · "
        f"частично {stats['partial']} · не найдено {stats['miss']} · склеек {stats['splice']}",
        "Файл читает судья; исходы по словарю проверки ставит он, не скрипт.",
    ]
    if warnings:
        head.append("⚠️ " + " · ".join(warnings))
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
    print(f"{args.out}: точек {stats['points']} · якорей {stats['anchors']} · "
          f"найдено {stats['full']} · частично {stats['partial']} · "
          f"не найдено {stats['miss']} · склеек {stats['splice']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
