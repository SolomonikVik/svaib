#!/usr/bin/env python3
"""snapshot.py — кэш снимка книги, переживающий сессию.

Книгу качает агент (Drive MCP отдаёт xlsx), код только решает, нужно ли качать, и хранит
снимок между прогонами:

    python3 snapshot.py check <fileId> --modified <modifiedTime>   # качать или нет
    python3 snapshot.py put   <fileId> --file <скачанный>.xlsx --modified <modifiedTime> [--title T]
    python3 snapshot.py path  <fileId>

Свежесть — по `modifiedTime` книги: он меняется от любой правки, поэтому ошибается только
в безопасную сторону. Метаданные недоступны — снимок годен 24 часа и помечается как
неподтверждённый; старше — отказ. `modifiedTime` это дата ФАЙЛА, не дата бизнес-среза:
подставлять её как дату значения запрещено.
"""
from __future__ import annotations

import argparse, datetime as dt, hashlib, json, os, shutil, sys
from pathlib import Path

TTL_UNVERIFIED_HOURS = 24


def state_dir():
    base = os.environ.get("SVAIB_STATE_DIR")
    if base:
        return Path(base) / "metrics"
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "svaib" / "metrics"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "svaib" / "metrics"


def paths(file_id):
    d = state_dir()
    return d / f"{file_id}.xlsx", d / f"{file_id}.json"


def load_mark(file_id):
    _, mark = paths(file_id)
    if not mark.exists():
        return None
    try:
        return json.loads(mark.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def age_hours(iso):
    try:
        t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (dt.datetime.now(dt.timezone.utc) - t).total_seconds() / 3600


def cmd_check(a):
    book, _ = paths(a.file_id)
    mark = load_mark(a.file_id)
    if not book.exists() or not mark:
        return out({"action": "download", "reason": "снимка нет"})
    if a.modified:
        if mark.get("modifiedTime") == a.modified:
            return out({"action": "reuse", "book": str(book), "modifiedTime": mark["modifiedTime"],
                        "note": f"данные книги от {mark['modifiedTime'][:10]}"})
        return out({"action": "download", "reason": f"книга изменилась: снимок {mark.get('modifiedTime')}, сейчас {a.modified}"})
    age = age_hours(mark.get("downloaded_at", ""))
    if age is None or age > TTL_UNVERIFIED_HOURS:
        return out({"action": "refuse",
                    "reason": f"свежесть не подтверждена, снимку {'?' if age is None else round(age)} ч (предел {TTL_UNVERIFIED_HOURS})"}, rc=1)
    return out({"action": "reuse_unverified", "book": str(book),
                "note": f"свежесть не подтверждена, снимок от {mark.get('downloaded_at','')[:10]}"})


def cmd_put(a):
    book, mark = paths(a.file_id)
    book.parent.mkdir(parents=True, exist_ok=True)
    src = Path(a.file)
    if not src.exists():
        return out({"error": f"нет файла {src}"}, rc=2)
    shutil.copy(src, book)
    doc = {"fileId": a.file_id, "title": a.title, "modifiedTime": a.modified,
           "downloaded_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "sha256": hashlib.sha256(book.read_bytes()).hexdigest(),
           "size": book.stat().st_size}
    mark.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return out({"action": "stored", "book": str(book), "size": doc["size"]})


def cmd_path(a):
    book, _ = paths(a.file_id)
    return out({"book": str(book), "exists": book.exists(), "mark": load_mark(a.file_id)})


def out(doc, rc=0):
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return rc


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("file_id"); c.add_argument("--modified"); c.set_defaults(fn=cmd_check)
    p = sub.add_parser("put"); p.add_argument("file_id"); p.add_argument("--file", required=True)
    p.add_argument("--modified", required=True); p.add_argument("--title", default=""); p.set_defaults(fn=cmd_put)
    g = sub.add_parser("path"); g.add_argument("file_id"); g.set_defaults(fn=cmd_path)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
