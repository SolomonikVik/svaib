#!/usr/bin/env python3
"""Верификация переноса scaffold-align. Stdlib-only.

Механический нижний уровень, не смысловая полнота: проверяется дословное
присутствие строк и байтовая идентичность файлов. Штатный путь к зелёной
проверке — архивировать исходник (`zz_archive/`) перед трансформацией:
архив дословно сохраняет каждую строку. Согласованные точные замены можно
передать отдельно; без них перефразировка без архива проверку не проходит.

  preserve --source <файлы|каталоги> --target <файлы|каталоги>
      Текстовые источники: каждая непустая строка (кроме чисто декоративных
      разделителей) встречается в приёмниках не реже, чем в источниках —
      кратность учитывается, YAML-шапки и заголовки считаются наравне с
      остальным содержимым. Бинарные источники: файл с тем же содержимым
      (sha256) существует среди приёмников. Каталог обходится целиком,
      все файлы.

      --approved-changes <JSON> — список согласованных замен строк:
      [{"source": "before.md", "target": "after.md", "before": "title: Старое",
        "after": "title: Новое", "count": 1}]. Пути от cwd (скилл запускает
      сверку из корня пространства); count обязателен.
      До сравнения заменяет ожидаемые строки только в указанном количестве,
      проверив before в источнике и after в приёмнике. Не подтверждает
      согласие пользователя или сохранение смысла — это задача вызывающего.

  links <файлы|каталоги>
      Относительные Markdown-ссылки, inline и reference-style, указывают на
      существующие файлы. Скобки в пути балансируются, URL-кодирование
      декодируется; якоря не проверяются. Каталог — все .md в нём. Чтобы поймать входящие
      ссылки на перенесённое, передавай прежний и новый каталог.

Выход: 0 — зелёно; 1 — непроверенные расхождения или битые ссылки (список в stdout);
2 — ошибка вызова. Перенос не считается выполненным, пока обе проверки
не вернули 0.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from markdown_links import broken_links

DECOR = re.compile(r"^[\s\-=|:>*`~._#+]*$")  # разделители и рамки без букв и цифр
def fail_usage(msg: str):
    print(msg, file=sys.stderr)
    sys.exit(2)


def normalize(line: str) -> str:
    return " ".join(line.split())


def try_text(path: Path):
    data = path.read_bytes()
    if b"\x00" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_lines(text: str):
    for n, raw in enumerate(text.splitlines(), 1):
        line = normalize(raw)
        if line and not DECOR.match(line):
            yield n, line


def collect_files(paths, suffix=None):
    out = []
    for p in map(Path, paths):
        if p.is_dir():
            out.extend(sorted(q for q in p.rglob("*") if q.is_file() and (suffix is None or q.suffix == suffix)))
        elif p.is_file():
            out.append(p)
        else:
            fail_usage(f"нет такого пути: {p}")
    # Один и тот же файл при передаче каталога и вложенного пути считаем один раз.
    return list({p.resolve(): p for p in out}.values())


def approved_replacements(path, sources, targets):
    """Точные замены; объём согласования не может превышать фактический текст."""
    if not path:
        return []
    try:
        entries = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail_usage(f"не удалось прочитать --approved-changes: {exc}")
    if not isinstance(entries, list):
        fail_usage("--approved-changes: нужен JSON-массив замен")

    def counts(files):
        result = {}
        for f in files:
            text = try_text(f)
            if text is not None:
                result[f.resolve()] = Counter(line for _, line in content_lines(text))
        return result

    source_counts, target_counts = counts(sources), counts(targets)
    used_source, used_target = Counter(), Counter()
    replacements = []
    fields = {"source", "target", "before", "after", "count"}
    for i, entry in enumerate(entries, 1):
        label = f"--approved-changes, замена {i}"
        if not isinstance(entry, dict) or set(entry) != fields:
            fail_usage(f"{label}: нужны ровно source, target, before, after, count")
        if any(not isinstance(entry[k], str) or not entry[k].strip()
               for k in ("source", "target", "before", "after")):
            fail_usage(f"{label}: пути и строки должны быть непустым текстом")
        count = entry["count"]
        if type(count) is not int or count < 1:
            fail_usage(f"{label}: count должен быть положительным целым")
        if any(len(entry[k].splitlines()) != 1 for k in ("before", "after")):
            fail_usage(f"{label}: before и after должны быть одной строкой")
        before, after = normalize(entry["before"]), normalize(entry["after"])
        if before == after or DECOR.match(before) or DECOR.match(after):
            fail_usage(f"{label}: нужны разные содержательные строки")
        src, dst = Path(entry["source"]).resolve(), Path(entry["target"]).resolve()
        if src not in source_counts or dst not in target_counts:
            fail_usage(f"{label}: source и target должны входить в текстовые файлы сверки")
        used_source[src, before] += count
        used_target[dst, after] += count
        if used_source[src, before] > source_counts[src][before]:
            fail_usage(f"{label}: before отсутствует в source в указанном количестве")
        if used_target[dst, after] > target_counts[dst][after]:
            fail_usage(f"{label}: after отсутствует в target в указанном количестве")
        replacements.append((src, before, after, count))
    return replacements


def cmd_preserve(args) -> int:
    sources, targets = collect_files(args.source), collect_files(args.target)
    replacements = approved_replacements(args.approved_changes, sources, targets)
    pool = Counter()
    target_hashes = set()
    for t in targets:
        target_hashes.add(sha256(t))
        text = try_text(t)
        if text is not None:
            pool.update(line for _, line in content_lines(text))

    need = Counter()
    first_seen = {}
    locations = {}
    lost_binary = []
    for src in sources:
        text = try_text(src)
        if text is None:
            if sha256(src) not in target_hashes:
                lost_binary.append(src)
            continue
        for n, line in content_lines(text):
            need[line] += 1
            first_seen.setdefault(line, (src, n))
            locations.setdefault((src.resolve(), line), (src, n))

    for src, before, after, count in replacements:
        need[before] -= count
        need[after] += count
        first_seen.setdefault(after, locations[src, before])
    approved_count = sum(count for _, _, _, count in replacements)
    if approved_count:
        print(f"СОГЛАСОВАННЫЕ ЗАМЕНЫ: {approved_count} строк; before и after проверены в указанных файлах")

    deficit = need - pool  # Counter: остаются только положительные недостачи
    if deficit or lost_binary:
        total = sum(deficit.values()) + len(lost_binary)
        print(f"НЕПРОВЕРЕННЫЕ РАСХОЖДЕНИЯ: {total} (строк: {sum(deficit.values())}, бинарных файлов: {len(lost_binary)})")
        print("Отсутствие исходной строки не доказывает потерю факта: проверьте перенос, архив или согласованную замену.")
        missing_lines = list(deficit.items())
        for line, k in missing_lines[:50]:
            src, n = first_seen[line]
            miss = f" (не хватает вхождений: {k})" if k > 1 else ""
            print(f"  {src}:{n}: {line[:120]}{miss}")
        hidden = missing_lines[50:]
        if hidden:
            print(f"  … и ещё {len(hidden)} разных строк (вхождений: {sum(k for _, k in hidden)})")
        for b in lost_binary:
            print(f"  бинарный без копии в приёмниках: {b}")
        return 1
    print("OK: все ожидаемые строки (с учётом согласованных замен и кратности) и бинарные файлы найдены в приёмниках")
    return 0


def cmd_links(args) -> int:
    broken = []
    for f in collect_files(args.files, suffix=".md"):
        try:
            broken.extend((f, n, ref) for n, ref in broken_links(f))
        except (OSError, UnicodeError) as exc:
            print(f"Не удалось проверить {f}: {exc}", file=sys.stderr)
            return 1
    if broken:
        print(f"БИТЫЕ ССЫЛКИ: {len(broken)}")
        for f, n, ref in broken[:50]:
            print(f"  {f}:{n}: {ref}")
        if len(broken) > 50:
            print(f"  … и ещё {len(broken) - 50}")
        return 1
    print("OK: битых относительных ссылок нет")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("preserve", help="сохранность источников в приёмниках (строки + sha256 бинарных)")
    p1.add_argument("--source", nargs="+", required=True)
    p1.add_argument("--target", nargs="+", required=True)
    p1.add_argument("--approved-changes", help="JSON-список согласованных точных замен строк")
    p2 = sub.add_parser("links", help="битые относительные markdown-ссылки")
    p2.add_argument("files", nargs="+")
    args = parser.parse_args()
    return cmd_preserve(args) if args.cmd == "preserve" else cmd_links(args)


if __name__ == "__main__":
    sys.exit(main())
