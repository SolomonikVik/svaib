#!/bin/bash
# macwhisper_transcript.sh — двухшаговый доступ к MacWhisper SQLite
#
# Шаг 1. Обзор (всегда сначала):
#   ./macwhisper_transcript.sh --list                              # сегодня
#   ./macwhisper_transcript.sh --list 2026-04-23                   # за дату
#   ./macwhisper_transcript.sh --list --search "дивиденды"         # FTS по содержимому
#   ./macwhisper_transcript.sh --list --search "..." --date ...
#   ./macwhisper_transcript.sh --list --speaker Ефим
#
# Шаг 2. Извлечение по id_short (8 hex-символов из --list):
#   ./macwhisper_transcript.sh --extract A6C13203 /path/_transcript.md

DB="$HOME/Library/Application Support/MacWhisper/Database/main.sqlite"

if [ ! -f "$DB" ]; then
    echo "ERROR: MacWhisper database not found at $DB"
    exit 1
fi

sql_escape() { printf '%s' "$1" | sed "s/'/''/g"; }

usage() {
    cat <<EOF
Usage:
  $0 --list [YYYY-MM-DD] [--search "<fts query>"] [--speaker <name>]
  $0 --extract <id_short> <output.md>
EOF
    exit 1
}

# ───────────────────────── режим --list ─────────────────────────
if [ "$1" = "--list" ]; then
    shift
    DATE=""
    SEARCH=""
    SPEAKER=""

    while [ $# -gt 0 ]; do
        case "$1" in
            --search)  SEARCH="$2"; shift 2 ;;
            --speaker) SPEAKER="$2"; shift 2 ;;
            --date)    DATE="$2"; shift 2 ;;
            20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]) DATE="$1"; shift ;;
            *) echo "Unknown argument: $1"; usage ;;
        esac
    done

    # если нет ни даты, ни поиска — дефолт сегодня
    if [ -z "$SEARCH" ] && [ -z "$DATE" ]; then
        DATE=$(date +%Y-%m-%d)
    fi

    WHERE="s.userChosenTitle != '' AND s.dateDeleted IS NULL"
    [ -n "$DATE" ]    && WHERE="$WHERE AND date(s.dateCreated) = '$(sql_escape "$DATE")'"
    [ -n "$SEARCH" ]  && WHERE="$WHERE AND s.rowid IN (SELECT rowid FROM sessionFTS WHERE sessionFTS MATCH '$(sql_escape "$SEARCH")')"
    [ -n "$SPEAKER" ] && WHERE="$WHERE AND s.id IN (SELECT ss.sessionID FROM session_speaker ss JOIN speaker sp ON sp.id=ss.speakerID WHERE sp.name LIKE '%$(sql_escape "$SPEAKER")%')"

    HEADER="=== MacWhisper sessions"
    [ -n "$DATE" ]    && HEADER="$HEADER | date=$DATE"
    [ -n "$SEARCH" ]  && HEADER="$HEADER | search=\"$SEARCH\""
    [ -n "$SPEAKER" ] && HEADER="$HEADER | speaker=$SPEAKER"
    HEADER="$HEADER ==="
    echo "$HEADER"
    echo ""

    COUNT=$(sqlite3 "$DB" "SELECT count(*) FROM session s WHERE $WHERE;")
    if [ "$COUNT" -eq 0 ]; then
        echo "(ничего не найдено)"
        exit 0
    fi

    sqlite3 -separator $'\t' "$DB" "
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
        WHERE $WHERE
        ORDER BY s.dateCreated ASC;
    " | awk -F'\t' '
    {
        printf "─── %s  │  %s  │  %s min  │  %s lines / %s chars\n", $1, $2, $8, $10, $11
        if ($3 != "") printf "    title     : %s\n", $3
        if ($4 != "") printf "    aiTitle   : %s\n", $4
        if ($5 != "") printf "    summary   : %s\n", $5
        app_line = ""
        if ($6 != "") app_line = $6
        if ($7 != "" && $7 != $3) {
            if (app_line != "") app_line = app_line "  (calendar: " $7 ")"
            else app_line = "calendar: " $7
        }
        if (app_line != "") printf "    app       : %s\n", app_line
        if ($9 != "") printf "    speakers  : %s\n", $9
        print ""
    }'

    echo "($COUNT found. Для извлечения: $0 --extract <id_short> <output.md>)"
    exit 0
fi

# ───────────────────────── режим --extract ─────────────────────────
if [ "$1" = "--extract" ]; then
    SESSION_ID_SHORT="$2"
    OUTPUT_FILE="$3"

    [ -z "$SESSION_ID_SHORT" ] || [ -z "$OUTPUT_FILE" ] && usage

    # валидируем формат id_short: 8 hex символов
    if ! echo "$SESSION_ID_SHORT" | grep -qE '^[0-9A-Fa-f]{8}$'; then
        echo "ERROR: id_short должен быть 8 hex-символов (из --list). Получено: $SESSION_ID_SHORT"
        exit 1
    fi
    ID_UPPER=$(echo "$SESSION_ID_SHORT" | tr '[:lower:]' '[:upper:]')

    OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
    if [ ! -d "$OUTPUT_DIR" ]; then
        echo "ERROR: Directory $OUTPUT_DIR does not exist"
        exit 1
    fi

    # находим сессию по префиксу hex(id)
    MATCHES=$(sqlite3 "$DB" "SELECT hex(id) FROM session WHERE substr(hex(id),1,8) = '$ID_UPPER' AND dateDeleted IS NULL;")
    MATCH_COUNT=$(echo "$MATCHES" | grep -c .)

    if [ "$MATCH_COUNT" -eq 0 ]; then
        echo "ERROR: сессия с id_short=$SESSION_ID_SHORT не найдена"
        exit 1
    fi
    if [ "$MATCH_COUNT" -gt 1 ]; then
        echo "ERROR: несколько сессий с префиксом $SESSION_ID_SHORT — коллизия (крайне редкий случай). Полные id:"
        echo "$MATCHES"
        exit 1
    fi
    FULL_ID="$MATCHES"

    # метаданные в stdout
    sqlite3 "$DB" "
        SELECT
            '=== Session: ' || COALESCE(s.userChosenTitle,'(no title)') ||
            CASE WHEN s.aiTitle IS NOT NULL AND s.aiTitle != ''
                 THEN ' / ' || s.aiTitle ELSE '' END || char(10) ||
            'id        : ' || substr(hex(s.id),1,8) || char(10) ||
            'date      : ' || datetime(s.dateCreated) || char(10) ||
            'duration  : ' || COALESCE(printf('%.0f min', rm.duration/60.0), 'unknown') || char(10) ||
            'app       : ' || COALESCE(rm.appName, '—') ||
            CASE WHEN rm.matchedCalendarTitle IS NOT NULL AND rm.matchedCalendarTitle != s.userChosenTitle
                 THEN '  (calendar: ' || rm.matchedCalendarTitle || ')' ELSE '' END || char(10) ||
            'model     : ' || COALESCE(s.modelIdentifer,'—') || char(10) ||
            'language  : ' || COALESCE(s.detectedLanguage,'—') || char(10) ||
            'diarized  : ' || CASE WHEN s.hasBeenDiarized=1 THEN 'yes' ELSE 'no' END || char(10) ||
            'summary   : ' || COALESCE(s.aiSummaryShort, '—')
        FROM session s
        LEFT JOIN recordedmeeting rm ON rm.id = s.recordedMeetingID
        WHERE hex(s.id) = '$FULL_ID';
    "

    echo -n "speakers  : "
    sqlite3 "$DB" "
        SELECT group_concat(sp.name, ', ')
        FROM session_speaker ss
        JOIN speaker sp ON sp.id = ss.speakerID
        WHERE ss.sessionID = (SELECT id FROM session WHERE hex(id) = '$FULL_ID');
    "
    echo ""

    # транскрипт: **Спикер** [MM:SS]: текст, склейка подряд идущих реплик одного спикера
    sqlite3 -separator $'\t' "$DB" "
        SELECT COALESCE(sp.name, 'Unknown'), tl.start, tl.text
        FROM transcriptline tl
        JOIN session s ON tl.sessionId = s.id
        LEFT JOIN speaker sp ON tl.speakerID = sp.id
        WHERE hex(s.id) = '$FULL_ID'
        ORDER BY tl.start ASC;
    " | awk -F'\t' '
    BEGIN { prev_speaker = ""; buffer = "" }
    {
        speaker = $1; start_ms = $2; text = $3
        total_sec = int(start_ms / 1000)
        timestamp = sprintf("%02d:%02d", int(total_sec/60), total_sec%60)
        if (speaker != prev_speaker) {
            if (buffer != "") { print buffer; print "" }
            buffer = "**" speaker "** [" timestamp "]: " text
            prev_speaker = speaker
        } else {
            buffer = buffer " " text
        }
    }
    END { if (buffer != "") { print buffer; print "" } }
    ' > "$OUTPUT_FILE"

    LINES=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
    echo "Transcript written to $OUTPUT_FILE ($LINES lines)"
    exit 0
fi

usage
