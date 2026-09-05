#!/usr/bin/env python3
"""Apply Check — кодовая самопроверка вызова «запись» скилла content-update.

Смысловую сохранность держит показ пакета человеку на согласовании;
этот скрипт держит механическую: строки, якоря, счётчики.

Команды:
  snapshot --scope <корень области> --files <файл ...> --out <run>/before [--exclude <путь> ...]
      Снимки всех файлов пакета до записи (откат = восстановить их) и манифест
      хэшей всей области — им ловятся незапланированные правки.
  check --scope <корень области> --before <run>/before --ledger <файл>
        [--extra <путь> ...] [--out <отчёт.md>]
      Дифф записи против снимков и якорного леджера пакета:
      изменённые файлы = согласованные — в обе стороны: лишние краснят,
      несмененные согласованные краснят тоже · каждая удалённая или изменённая
      строка покрыта якорем леджера ТОЧНЫМ совпадением нормализованной строки —
      иначе потеря; якорь с ≥2 совпадениями — спорная правка, красный ·
      смена чекбокса [ ]/[x] — содержание, без якоря это потеря ·
      при «объединена» даты и ссылки прежней записи присутствуют в новом
      состоянии ТОГО ЖЕ файла · счётчики и рост файлов (круг ревью 31.08).
      --extra — правка мимо пакета по явному решению человека: не краснит,
      но всегда считается.

Леджер — плоский файл, строка = тронутая запись пакета:
  <исход>: <дословная первая строка прежней записи>
исход — изменена | удалена | заменена | объединена; строка без исхода — якорь
с любым исходом. Добавленные записи в леджер не пишутся: добавления не потеря.

Красный выход (код 1) чинится модулем, отчёт применения перевыпускается.
Stdlib-only.
"""

import argparse
import hashlib
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

OUTCOMES = ("изменена", "удалена", "заменена", "объединена")
SKIP_DIRS = {".git", "__pycache__"}
MANIFEST = "manifest.tsv"
BULLET = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+|#{1,6}\s+|>\s+)+")  # чекбокс [x]/[ ] — содержание: его смена без якоря = потеря
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}\.\d{2}(?:\.\d{2,4})?\b")
LINK = re.compile(r"\]\(([^)\s]+)\)")


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def norm(line):
    """Нормализация для сверки: маркеры списков/заголовков, эмфаза, пробелы, регистр, ё."""
    s = BULLET.sub("", line.strip())
    s = re.sub(r"[*_`]", "", s)
    return " ".join(s.split()).casefold().replace("ё", "е")


def indent_of(raw):
    raw = raw.expandtabs(4)
    return len(raw) - len(raw.lstrip())


def is_heading(raw):
    return raw.lstrip().startswith("#")


def heading_level(raw):
    s = raw.lstrip()
    return len(s) - len(s.lstrip("#"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel_str(path, scope):
    try:
        return Path(path).resolve().relative_to(scope).as_posix()
    except ValueError:
        fail(f"путь вне области: {path}")


def is_under(rel, exclude):
    return rel == exclude or rel.startswith(exclude + "/")


def scan(scope, excludes):
    """Карта «относительный путь → sha256» всех файлов области."""
    result = {}
    for p in sorted(scope.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(scope).as_posix()
        parts = rel.split("/")
        if any(part in SKIP_DIRS for part in parts):
            continue
        if any(is_under(rel, e) for e in excludes):
            continue
        result[rel] = sha256(p)
    return result


def parse_ledger(text):
    """[(исход | None, дословный якорь, нормализованный якорь)] — пустые строки мимо."""
    anchors = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        outcome = None
        for o in OUTCOMES:
            if line.casefold().startswith(o + ":"):
                outcome, line = o, line[len(o) + 1:].strip()
                break
        n = norm(line)
        if n:
            anchors.append((outcome, line, n))
    return anchors


def ancestors(lines, i):
    """Структурные предки строки: свой абзац вверх до пустой, родители по отступу, заголовки."""
    result = []
    cur = indent_of(lines[i])
    h_level = None
    same_para = True
    seen_heading = False
    for j in range(i - 1, -1, -1):
        raw = lines[j]
        if not raw.strip():
            same_para = False
            continue
        if is_heading(raw):
            lvl = heading_level(raw)
            if h_level is None or lvl < h_level:
                result.append(raw)
                h_level = lvl
            seen_heading = True
            same_para = False
            continue
        if seen_heading:
            continue
        ind = indent_of(raw)
        if ind < cur:
            result.append(raw)
            cur = ind
        elif same_para and ind == cur:
            result.append(raw)
    return result


def covered(lines, i, anchor_set):
    """Строка покрыта якорем: сама, её абзац, родитель по отступу или заголовок записи.
    Совпадение — точное по нормализованной строке: подстрока покрывала бы чужие записи."""
    for raw in [lines[i]] + ancestors(lines, i):
        if norm(raw) in anchor_set:
            return True
    return False


def record_block(lines, i):
    """Запись целиком: первая строка + подстроки по отступу (или секция заголовка)."""
    block = [lines[i]]
    if is_heading(lines[i]):
        base = heading_level(lines[i])
        for j in range(i + 1, len(lines)):
            if is_heading(lines[j]) and heading_level(lines[j]) <= base:
                break
            block.append(lines[j])
    else:
        base = indent_of(lines[i])
        for j in range(i + 1, len(lines)):
            if not lines[j].strip() or indent_of(lines[j]) <= base:
                break
            block.append(lines[j])
    return block


def snapshot(scope, files, out, excludes):
    out.mkdir(parents=True, exist_ok=True)
    excludes = list(excludes)
    if out.is_relative_to(scope):
        excludes.append(out.relative_to(scope).as_posix())
    rels = []
    for f in files:
        p = Path(f) if Path(f).is_absolute() else scope / f
        if not p.is_file():
            fail(f"файла пакета нет: {p} — пакет меняет только существующие файлы")
        rel = rel_str(p, scope)
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
        rels.append(rel)
    manifest = scan(scope, excludes)
    with (out / MANIFEST).open("w", encoding="utf-8") as fh:
        for e in excludes:
            fh.write(f"# exclude\t{e}\n")
        for rel, digest in manifest.items():
            fh.write(f"{digest}\t{rel}\n")
    return rels, manifest


def check(scope, before, ledger_text, extras=(), excludes_extra=()):
    """Возвращает (отчёт md, stats). stats['red'] — список причин красного выхода."""
    manifest_path = before / MANIFEST
    if not manifest_path.is_file():
        fail(f"нет манифеста {manifest_path} — снимки делались не командой snapshot?")
    manifest, excludes = {}, list(excludes_extra)
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        key, _, value = raw.partition("\t")
        if key == "# exclude":
            excludes.append(value)
        elif key:
            manifest[value] = key

    agreed = {p.relative_to(before).as_posix(): p
              for p in sorted(before.rglob("*"))
              if p.is_file() and p.name != MANIFEST}
    now = scan(scope, excludes)
    touched = sorted(
        [r for r in now if r not in manifest or now[r] != manifest[r]]
        + [r for r in manifest if r not in now])
    extras = set(extras)
    unplanned = [r for r in touched if r not in agreed and r not in extras]
    extra_touched = [r for r in touched if r in extras]

    anchors = parse_ledger(ledger_text)
    anchor_set = {a[2] for a in anchors}
    anchor_hits = Counter()          # норм-якорь → точных вхождений в снимках (все файлы)
    anchor_pos = {}                  # норм-якорь → (rel, строки before, индекс) первого вхождения
    losses, per_file, vanished = [], [], []
    added_total = 0
    after_by_rel = {}

    for rel, bpath in agreed.items():
        before_lines = bpath.read_text(encoding="utf-8").splitlines()
        after_path = scope / rel
        if after_path.is_file():
            after_lines = after_path.read_text(encoding="utf-8").splitlines()
        else:
            after_lines = []
            vanished.append(rel)
        after_by_rel[rel] = "\n".join(after_lines)
        per_file.append((rel, len(before_lines), len(after_lines)))

        need, have = Counter(), Counter()
        first_seen = {}
        for i, raw in enumerate(before_lines):
            n = norm(raw)
            if not n:
                continue
            need[n] += 1
            first_seen.setdefault(n, i)
            if n in anchor_set:
                anchor_hits[n] += 1
                anchor_pos.setdefault(n, (rel, before_lines, i))
        for raw in after_lines:
            n = norm(raw)
            if n:
                have[n] += 1
        added_total += sum((have - need).values())
        for n in (need - have):
            i = first_seen[n]
            if not covered(before_lines, i, anchor_set):
                losses.append((rel, i + 1, before_lines[i].strip()))

    anchors_missing = [(o, raw) for o, raw, n in anchors if anchor_hits[n] == 0]
    anchors_ambiguous = [(o, raw) for o, raw, n in anchors if anchor_hits[n] > 1]
    agreed_untouched = [r for r in agreed if r not in set(touched)]
    merge_missing = []
    for o, raw, n in anchors:
        if o != "объединена" or n not in anchor_pos:
            continue
        rel, before_lines, i = anchor_pos[n]
        block = "\n".join(record_block(before_lines, i))
        elements = set(DATE.findall(block)) | set(LINK.findall(block))
        target = after_by_rel.get(rel, "")   # элементы ищутся в том же файле: совпадение в чужом маскирует потерю
        for el in sorted(elements):
            if el not in target:
                merge_missing.append((raw, el))

    outcome_counts = Counter(o for o, _, _ in anchors if o)
    red = []
    if losses:
        red.append(f"потеряно строк без якоря: {len(losses)}")
    if unplanned:
        red.append(f"незапланированных изменений: {len(unplanned)}")
    if anchors_missing:
        red.append(f"якорей без совпадений в снимках: {len(anchors_missing)}")
    if anchors_ambiguous:
        red.append(f"якорей с неоднозначным совпадением (≥2) — правка спорная: {len(anchors_ambiguous)}")
    if agreed_untouched:
        red.append(f"согласованных файлов не изменено: {len(agreed_untouched)}")
    if merge_missing:
        red.append(f"утрачено элементов при объединении: {len(merge_missing)}")
    if vanished:
        red.append(f"файлов пакета исчезло: {len(vanished)}")

    lines = ["# Проверка записи — apply_check", ""]
    lines.append(
        f"Файлов согласовано {len(agreed)} · тронуто в области {len(touched)} · "
        f"незапланированных {len(unplanned)} · правок мимо пакета {len(extra_touched)}")
    lines.append(
        f"Потеряно строк без якоря {len(losses)} · якорей {len(anchors)} · "
        f"без совпадений {len(anchors_missing)} · добавлено строк {added_total}")
    lines.append("Леджер: " + " · ".join(f"{o} {outcome_counts.get(o, 0)}" for o in OUTCOMES))
    lines += ["", "| файл | строк было → стало |", "|---|---|"]
    lines += [f"| {rel} | {b} → {a} |" for rel, b, a in per_file]
    for title, rows in [
        ("Потери — удалённые или изменённые строки без якоря леджера",
         [f"{rel}:{no}: {text}" for rel, no, text in losses]),
        ("Незапланированные изменения — файлы вне пакета",
         unplanned),
        ("Правки мимо пакета — по явному решению человека",
         extra_touched),
        ("Якоря без совпадений в снимках",
         [f"{o or 'без исхода'}: {raw}" for o, raw in anchors_missing]),
        ("Якоря с неоднозначным совпадением — место правки не угадывается",
         [f"{o or 'без исхода'}: {raw}" for o, raw in anchors_ambiguous]),
        ("Согласованные файлы без единой правки",
         agreed_untouched),
        ("Объединение — элементы прежней записи, не найденные в новом состоянии",
         [f"«{raw}» → {el}" for raw, el in merge_missing]),
        ("Файлы пакета, исчезнувшие из области", vanished),
    ]:
        if rows:
            lines += ["", f"## {title}"] + [f"- {r}" for r in rows]
    lines += ["", ("КРАСНЫЙ: " + " · ".join(red)) if red else
              "OK: потерянных строк 0, изменённые файлы совпадают с согласованными"]
    stats = {"agreed": len(agreed), "touched": len(touched), "unplanned": unplanned,
             "extra": extra_touched, "losses": losses, "anchors": len(anchors),
             "anchors_missing": anchors_missing, "anchors_ambiguous": anchors_ambiguous,
             "agreed_untouched": agreed_untouched, "merge_missing": merge_missing,
             "vanished": vanished, "added": added_total,
             "outcomes": dict(outcome_counts), "red": red}
    return "\n".join(lines) + "\n", stats


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--scope", required=True)
    s.add_argument("--files", nargs="+", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--exclude", action="append", default=[])
    c = sub.add_parser("check")
    c.add_argument("--scope", required=True)
    c.add_argument("--before", required=True)
    c.add_argument("--ledger", required=True)
    c.add_argument("--extra", action="append", default=[])
    c.add_argument("--exclude", action="append", default=[])
    c.add_argument("--out")
    args = parser.parse_args(argv)

    scope = Path(args.scope).resolve()
    if not scope.is_dir():
        fail(f"области нет: {scope}")
    if args.cmd == "snapshot":
        excludes = [rel_str(e, scope) for e in args.exclude]
        rels, manifest = snapshot(scope, args.files, Path(args.out).resolve(), excludes)
        print(f"Снимков: {len(rels)} · файлов в манифесте области: {len(manifest)}")
        return 0
    ledger_path = Path(args.ledger)
    if not ledger_path.is_file():
        fail(f"леджера нет: {ledger_path}")
    extras = [rel_str(e, scope) for e in args.extra]
    excludes_extra = [rel_str(e, scope) for e in args.exclude]
    report, stats = check(scope, Path(args.before).resolve(),
                          ledger_path.read_text(encoding="utf-8"), extras, excludes_extra)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    print(report, end="")
    return 1 if stats["red"] else 0


if __name__ == "__main__":
    sys.exit(main())
