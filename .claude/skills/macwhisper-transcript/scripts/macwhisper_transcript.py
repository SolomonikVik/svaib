#!/usr/bin/env python3
"""macwhisper_transcript.py — двухшаговый доступ к MacWhisper SQLite.

Шаг 1. Обзор (всегда сначала):
  ./macwhisper_transcript.py --list                              # сегодня
  ./macwhisper_transcript.py --list 2026-04-23                   # за дату
  ./macwhisper_transcript.py --list --search "дивиденды"         # FTS по содержимому
  ./macwhisper_transcript.py --list --search "..." --date ...
  ./macwhisper_transcript.py --list --speaker Ефим

Шаг 2. Извлечение по id_short (8 hex-символов из --list):
  ./macwhisper_transcript.py --extract A6C13203 /path/_transcript.md

Только стандартная библиотека python3.
"""

import datetime
import glob
import os
import re
import sqlite3
import sys
from pathlib import Path


def find_db():
    """Найти БД MacWhisper. Mac → ~/Library/..., Cowork → /sessions/*/mnt/..."""
    candidates = [
        Path.home() / "Library/Application Support/MacWhisper/Database/main.sqlite",
    ]
    candidates.extend(Path(p) for p in glob.glob("/sessions/*/mnt/MacWhisper/Database/main.sqlite"))

    for p in candidates:
        if p.exists():
            return p

    sys.stderr.write("ERROR: MacWhisper database not found. Tried:\n")
    for p in candidates:
        sys.stderr.write(f"  - {p}\n")
    sys.exit(1)


def connect_ro(db_path):
    """Read-only коннект. Сначала mode=ro, при отказе — добавляем immutable=1
    (нужно если БД на read-only mount: иначе sqlite не сможет создать -shm/-wal)."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute("SELECT 1").fetchone()
        return conn
    except sqlite3.OperationalError:
        return sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)


def usage():
    sys.stderr.write(
        "Usage:\n"
        f"  {sys.argv[0]} --list [YYYY-MM-DD] [--search \"<fts query>\"] [--speaker <name>]\n"
        f"  {sys.argv[0]} --extract <id_short> <output.md>\n"
    )
    sys.exit(1)


def cmd_list(rest):
    date = None
    search = None
    speaker = None

    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg == "--search":
            if i + 1 >= len(rest):
                usage()
            search = rest[i + 1]
            i += 2
        elif arg == "--speaker":
            if i + 1 >= len(rest):
                usage()
            speaker = rest[i + 1]
            i += 2
        elif arg == "--date":
            if i + 1 >= len(rest):
                usage()
            date = rest[i + 1]
            i += 2
        elif re.match(r"^\d{4}-\d{2}-\d{2}$", arg):
            date = arg
            i += 1
        else:
            sys.stderr.write(f"Unknown argument: {arg}\n")
            usage()

    if not search and not date:
        date = datetime.date.today().isoformat()

    where = "s.userChosenTitle != '' AND s.dateDeleted IS NULL"
    params = []
    if date:
        where += " AND date(s.dateCreated) = ?"
        params.append(date)
    if search:
        where += " AND s.rowid IN (SELECT rowid FROM sessionFTS WHERE sessionFTS MATCH ?)"
        params.append(search)
    if speaker:
        where += (
            " AND s.id IN (SELECT ss.sessionID FROM session_speaker ss "
            "JOIN speaker sp ON sp.id=ss.speakerID WHERE sp.name LIKE ?)"
        )
        params.append(f"%{speaker}%")

    header = "=== MacWhisper sessions"
    if date:
        header += f" | date={date}"
    if search:
        header += f' | search="{search}"'
    if speaker:
        header += f" | speaker={speaker}"
    header += " ==="
    print(header)
    print()

    db = find_db()
    conn = connect_ro(db)

    try:
        count = conn.execute(f"SELECT count(*) FROM session s WHERE {where}", params).fetchone()[0]
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        if "fts5" in msg or "sessionfts" in msg or "no such module" in msg:
            sys.stderr.write(f"ERROR: FTS5 search not available in this SQLite build: {e}\n")
            sys.exit(1)
        raise

    if count == 0:
        print("(ничего не найдено)")
        return

    query = f"""
        SELECT
            substr(hex(s.id),1,8),
            strftime('%Y-%m-%d %H:%M', s.dateCreated),
            COALESCE(s.userChosenTitle,''),
            COALESCE(s.aiTitle,''),
            COALESCE(s.aiSummaryShort,''),
            COALESCE(rm.appName,''),
            COALESCE(rm.matchedCalendarTitle,''),
            COALESCE(printf('%.0f', rm.duration/60.0),'?'),
            COALESCE((SELECT group_concat(sp.name, ', ')
                      FROM session_speaker ss JOIN speaker sp ON sp.id=ss.speakerID
                      WHERE ss.sessionID=s.id), ''),
            (SELECT count(*) FROM transcriptline tl WHERE tl.sessionId=s.id),
            length(COALESCE(s.fullText,''))
        FROM session s
        LEFT JOIN recordedmeeting rm ON rm.id = s.recordedMeetingID
        WHERE {where}
        ORDER BY s.dateCreated ASC
    """

    for row in conn.execute(query, params):
        id_short, dt, title, ai_title, summary, app, cal, dur, speakers, lines, chars = row
        print(f"─── {id_short}  │  {dt}  │  {dur} min  │  {lines} lines / {chars} chars")
        if title:
            print(f"    title     : {title}")
        if ai_title:
            print(f"    aiTitle   : {ai_title}")
        if summary:
            print(f"    summary   : {summary}")
        app_line = ""
        if app:
            app_line = app
        if cal and cal != title:
            app_line = f"{app_line}  (calendar: {cal})" if app_line else f"calendar: {cal}"
        if app_line:
            print(f"    app       : {app_line}")
        if speakers:
            print(f"    speakers  : {speakers}")
        print()

    print(f"({count} found. Для извлечения: {sys.argv[0]} --extract <id_short> <output.md>)")


def cmd_extract(rest):
    if len(rest) < 2:
        usage()
    id_short = rest[0]
    output = rest[1]

    if not re.match(r"^[0-9A-Fa-f]{8}$", id_short):
        sys.stderr.write(
            f"ERROR: id_short должен быть 8 hex-символов (из --list). Получено: {id_short}\n"
        )
        sys.exit(1)
    id_upper = id_short.upper()

    output_path = Path(output)
    if not output_path.parent.is_dir():
        sys.stderr.write(f"ERROR: Directory {output_path.parent} does not exist\n")
        sys.exit(1)

    db = find_db()
    conn = connect_ro(db)

    matches = conn.execute(
        "SELECT hex(id) FROM session WHERE substr(hex(id),1,8) = ? AND dateDeleted IS NULL",
        (id_upper,),
    ).fetchall()

    if not matches:
        sys.stderr.write(f"ERROR: сессия с id_short={id_short} не найдена\n")
        sys.exit(1)
    if len(matches) > 1:
        sys.stderr.write(
            f"ERROR: несколько сессий с префиксом {id_short} — коллизия (крайне редкий случай). Полные id:\n"
        )
        for m in matches:
            sys.stderr.write(f"{m[0]}\n")
        sys.exit(1)
    full_id = matches[0][0]

    meta = conn.execute(
        """
        SELECT
            COALESCE(s.userChosenTitle,'(no title)'),
            COALESCE(s.aiTitle,''),
            substr(hex(s.id),1,8),
            datetime(s.dateCreated),
            rm.duration,
            COALESCE(rm.appName, '—'),
            COALESCE(rm.matchedCalendarTitle, ''),
            COALESCE(s.modelIdentifer,'—'),
            COALESCE(s.detectedLanguage,'—'),
            s.hasBeenDiarized,
            COALESCE(s.aiSummaryShort, '—')
        FROM session s
        LEFT JOIN recordedmeeting rm ON rm.id = s.recordedMeetingID
        WHERE hex(s.id) = ?
        """,
        (full_id,),
    ).fetchone()

    title, ai_title, id_short_out, dt, duration, app, cal, model, lang, diarized, summary = meta

    head = f"=== Session: {title}"
    if ai_title:
        head += f" / {ai_title}"
    print(head)
    print(f"id        : {id_short_out}")
    print(f"date      : {dt}")
    if duration is not None:
        print(f"duration  : {round(duration / 60)} min")
    else:
        print("duration  : unknown")
    app_line = app
    if cal and cal != title:
        app_line = f"{app_line}  (calendar: {cal})"
    print(f"app       : {app_line}")
    print(f"model     : {model}")
    print(f"language  : {lang}")
    print(f"diarized  : {'yes' if diarized == 1 else 'no'}")
    print(f"summary   : {summary}")

    speakers_row = conn.execute(
        """
        SELECT group_concat(sp.name, ', ')
        FROM session_speaker ss
        JOIN speaker sp ON sp.id = ss.speakerID
        WHERE ss.sessionID = (SELECT id FROM session WHERE hex(id) = ?)
        """,
        (full_id,),
    ).fetchone()
    speakers = speakers_row[0] if speakers_row and speakers_row[0] else ""
    print(f"speakers  : {speakers}")
    print()

    rows = conn.execute(
        """
        SELECT COALESCE(sp.name, 'Unknown'), tl.start, tl.text
        FROM transcriptline tl
        JOIN session s ON tl.sessionId = s.id
        LEFT JOIN speaker sp ON tl.speakerID = sp.id
        WHERE hex(s.id) = ?
        ORDER BY tl.start ASC
        """,
        (full_id,),
    ).fetchall()

    lines_out = []
    prev_speaker = None
    buffer = ""
    for speaker, start_ms, text in rows:
        total_sec = int((start_ms or 0) / 1000)
        timestamp = f"{total_sec // 60:02d}:{total_sec % 60:02d}"
        if speaker != prev_speaker:
            if buffer:
                lines_out.append(buffer)
                lines_out.append("")
            buffer = f"**{speaker}** [{timestamp}]: {text}"
            prev_speaker = speaker
        else:
            buffer += " " + text
    if buffer:
        lines_out.append(buffer)
        lines_out.append("")

    content = "\n".join(lines_out) + "\n"
    output_path.write_text(content, encoding="utf-8")

    line_count = content.count("\n")
    print(f"Transcript written to {output} ({line_count} lines)")


def main():
    argv = sys.argv[1:]
    if not argv:
        usage()
    mode = argv[0]
    rest = argv[1:]

    if mode == "--list":
        cmd_list(rest)
    elif mode == "--extract":
        cmd_extract(rest)
    else:
        usage()


if __name__ == "__main__":
    main()
