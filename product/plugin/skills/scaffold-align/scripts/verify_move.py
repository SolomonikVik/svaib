#!/usr/bin/env python3
"""Верификация переноса scaffold-align. Stdlib-only.

Механический нижний уровень, не смысловая полнота: проверяется дословное
присутствие строк и байтовая идентичность файлов. Штатный путь к зелёной
проверке — архивировать исходник (`zz_archive/`) перед трансформацией:
архив даёт дословный дом каждой строке; перефразировка без архива проверку
не проходит — и не должна.

  preserve --source <файлы|каталоги> --target <файлы|каталоги>
      Текстовые источники: каждая непустая строка (кроме чисто декоративных
      разделителей) встречается в приёмниках не реже, чем в источниках —
      кратность учитывается, YAML-шапки и заголовки считаются наравне с
      остальным содержимым. Бинарные источники: файл с тем же содержимым
      (sha256) существует среди приёмников. Каталог обходится целиком,
      все файлы.

  links <файлы|каталоги>
      Относительные markdown-ссылки вида [текст](путь) указывают на
      существующие файлы. Каталог — все .md в нём. Чтобы поймать входящие
      ссылки на перенесённое, передавай каталогами прежний и новый дом.

Выход: 0 — зелёно; 1 — потери или битые ссылки (список в stdout);
2 — ошибка вызова. Перенос не считается выполненным, пока обе проверки
не вернули 0.
"""

import argparse
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

DECOR = re.compile(r"^[\s\-=|:>*`~._#+]*$")  # разделители и рамки без букв и цифр
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:\s+\"[^\"]*\")?(?:#[^)]*)?\)")


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
    return out


def cmd_preserve(args) -> int:
    pool = Counter()
    target_hashes = set()
    for t in collect_files(args.target):
        target_hashes.add(sha256(t))
        text = try_text(t)
        if text is not None:
            pool.update(line for _, line in content_lines(text))

    need = Counter()
    first_seen = {}
    lost_binary = []
    for src in collect_files(args.source):
        text = try_text(src)
        if text is None:
            if sha256(src) not in target_hashes:
                lost_binary.append(src)
            continue
        for n, line in content_lines(text):
            need[line] += 1
            first_seen.setdefault(line, (src, n))

    deficit = need - pool  # Counter: остаются только положительные недостачи
    if deficit or lost_binary:
        total = sum(deficit.values()) + len(lost_binary)
        print(f"ПОТЕРИ: {total} (строк: {sum(deficit.values())}, бинарных файлов: {len(lost_binary)})")
        for line, k in list(deficit.items())[:50]:
            src, n = first_seen[line]
            miss = f" (не хватает вхождений: {k})" if k > 1 else ""
            print(f"  {src}:{n}: {line[:120]}{miss}")
        if sum(deficit.values()) > 50:
            print(f"  … и ещё {sum(deficit.values()) - 50}")
        for b in lost_binary:
            print(f"  бинарный без копии в приёмниках: {b}")
        return 1
    print("OK: все строки источников (с учётом кратности) и все бинарные файлы найдены в приёмниках")
    return 0


def cmd_links(args) -> int:
    broken = []
    for f in collect_files(args.files, suffix=".md"):
        for n, raw in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in MD_LINK.finditer(raw):
                ref = m.group(1)
                if re.match(r"^[a-z][a-z0-9+.-]*:", ref):  # http:, mailto: и т.п.
                    continue
                if not (f.parent / ref).exists():
                    broken.append((f, n, ref))
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
    p2 = sub.add_parser("links", help="битые относительные markdown-ссылки")
    p2.add_argument("files", nargs="+")
    args = parser.parse_args()
    return cmd_preserve(args) if args.cmd == "preserve" else cmd_links(args)


if __name__ == "__main__":
    sys.exit(main())
