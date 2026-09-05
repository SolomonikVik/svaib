#!/usr/bin/env python3
"""Разбор списка файлов ветки (плоская выдача jsDelivr) в «путь<TAB>размер».

Имена приходят из внешнего источника, поэтому путь нормализуется и обязан лежать строго внутри
канона: всё остальное отбрасывается. Нет README канона — выдача бесполезна, код возврата 1.

    python3 parse_listing.py <listing.json> <префикс канона> <файл результата>
"""
import json
import posixpath
import sys


def main() -> int:
    src, prefix, dst = sys.argv[1:4]
    try:
        with open(src, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return 1

    rows = []
    for entry in data.get("files", []):
        name = str(entry.get("name", "")).lstrip("/")
        norm = posixpath.normpath(name)
        if norm != name or not norm.startswith(prefix + "/") or ".." in norm.split("/"):
            continue
        size = entry.get("size")
        rows.append("%s\t%s" % (norm, size if isinstance(size, int) and size >= 0 else -1))

    rows = sorted(set(rows))
    if not any(r.split("\t")[0] == prefix + "/README.md" for r in rows):
        return 1
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write("\n".join(rows) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
