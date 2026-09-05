#!/usr/bin/env python3
"""Отпечаток содержимого каталога: 12 hex-символов, одинаковые на любой платформе.

Считается по парам «относительный путь → sha256 содержимого», отсортированным по пути: одно
содержимое даёт один отпечаток, а имя файла входит в него наравне с телом.

    python3 snapshot_id.py <каталог>
"""
import hashlib
import os
import sys


def main() -> int:
    root = sys.argv[1]
    outer = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            inner = hashlib.sha256()
            with open(full, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    inner.update(chunk)
            outer.update(rel.encode("utf-8") + b"\0" + inner.hexdigest().encode() + b"\n")
    print(outer.hexdigest()[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
