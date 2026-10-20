#!/usr/bin/env python3
"""Проверка markdown-ссылок изменённых файлов: цель ссылки существует на диске.

Вход — пути файлов; читает готовое состояние базы, ничего не пишет.
Выход: список битых ссылок, exit 1 при находках, 0 — чисто.

    python3 check_links.py file1.md file2.md ...
"""
import sys
from pathlib import Path

from markdown_links import broken_links as find_broken_links


def broken_links(md: Path):
    try:
        for lineno, target in find_broken_links(md):
            yield f"{md}:{lineno}  {target}"
    except (OSError, UnicodeError) as e:
        yield f"{md}: не читается ({e})"


def main(argv):
    if not argv:
        print("usage: check_links.py <file.md> [file.md ...]", file=sys.stderr)
        return 3
    found = 0
    for arg in argv:
        for row in broken_links(Path(arg)):
            print("BROKEN", row)
            found += 1
    print(f"битых ссылок: {found}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
