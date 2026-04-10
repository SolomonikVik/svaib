#!/bin/bash
# macwhisper_transcript.sh — вытащить транскрипт из MacWhisper в _transcript.md
#
# Использование:
#   ./macwhisper_transcript.sh "Название сессии" /path/to/client/meetings/_transcript.md
#   ./macwhisper_transcript.sh --list                # показать сегодняшние сессии
#   ./macwhisper_transcript.sh --list 2026-04-03     # показать сессии за дату
#
# Что делает:
#   1. Находит merged-сессию по названию в MacWhisper SQLite
#   2. Извлекает fullText (транскрипт со спикерами и таймстемпами)
#   3. Записывает в указанный файл
#
# Метаданные (спикеры, AI summary, длительность) выводятся в stdout

DB="$HOME/Library/Application Support/MacWhisper/Database/main.sqlite"

if [ ! -f "$DB" ]; then
    echo "ERROR: MacWhisper database not found at $DB"
    exit 1
fi

# --- Режим --list ---
if [ "$1" = "--list" ]; then
    DATE="${2:-$(date +%Y-%m-%d)}"
    echo "=== MacWhisper sessions for $DATE ==="
    echo ""
    sqlite3 "$DB" "
        SELECT
            s.userChosenTitle,
            COALESCE(s.aiTitle, ''),
            time(s.dateCreated) AS time,
            COALESCE(printf('%.0f min', rm.duration/60.0), '? min'),
            COALESCE(s.aiSummaryShort, '')
        FROM session s
        LEFT JOIN recordedmeeting rm ON rm.id = s.recordedMeetingID
        WHERE date(s.dateCreated) = '$DATE'
          AND s.userChosenTitle != ''
        ORDER BY s.dateCreated DESC;
    " -separator ' | '
    echo ""
    echo "(showing only named/merged sessions)"
    exit 0
fi

# --- Режим извлечения ---
if [ $# -lt 2 ]; then
    echo "Usage: $0 \"Session Name\" /path/to/_transcript.md"
    echo "       $0 --list [YYYY-MM-DD]"
    exit 1
fi

SESSION_NAME="$1"
OUTPUT_FILE="$2"

# Проверяем что output-директория существует
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "ERROR: Directory $OUTPUT_DIR does not exist"
    exit 1
fi

# Находим сессию
SESSION_COUNT=$(sqlite3 "$DB" "SELECT count(*) FROM session WHERE userChosenTitle = '$SESSION_NAME';")

if [ "$SESSION_COUNT" -eq 0 ]; then
    echo "ERROR: Session '$SESSION_NAME' not found"
    echo ""
    echo "Available named sessions:"
    sqlite3 "$DB" "SELECT userChosenTitle, date(dateCreated) FROM session WHERE userChosenTitle != '' ORDER BY dateCreated DESC LIMIT 10;"
    exit 1
fi

if [ "$SESSION_COUNT" -gt 1 ]; then
    echo "WARNING: Multiple sessions named '$SESSION_NAME', using most recent"
fi

# Извлекаем метаданные
echo "=== Session: $SESSION_NAME ==="
sqlite3 "$DB" "
    SELECT
        'Date: ' || datetime(s.dateCreated),
        'Duration: ' || COALESCE(printf('%.0f min', rm.duration/60.0), 'unknown'),
        'Model: ' || s.modelIdentifer,
        'AI Summary: ' || COALESCE(s.aiSummaryShort, 'n/a')
    FROM session s
    LEFT JOIN recordedmeeting rm ON rm.id = s.recordedMeetingID
    WHERE s.userChosenTitle = '$SESSION_NAME'
    ORDER BY s.dateCreated DESC
    LIMIT 1;
"

# Спикеры
echo -n "Speakers: "
sqlite3 "$DB" "
    SELECT group_concat(sp.name, ', ')
    FROM session s
    JOIN session_speaker ss ON ss.sessionID = s.id
    JOIN speaker sp ON sp.id = ss.speakerID
    WHERE s.userChosenTitle = '$SESSION_NAME'
    ORDER BY s.dateCreated DESC
    LIMIT 1;
"

echo ""

# Извлекаем транскрипт из transcriptline (со спикерами и таймкодами)
# fullText — сплошной текст без разметки, поэтому собираем из отдельных строк
SESSION_ID=$(sqlite3 "$DB" "
    SELECT hex(id) FROM session
    WHERE userChosenTitle = '$SESSION_NAME'
    ORDER BY dateCreated DESC
    LIMIT 1;
")

if [ -z "$SESSION_ID" ]; then
    echo "ERROR: Could not get session ID"
    exit 1
fi

# Собираем транскрипт: группируем последовательные реплики одного спикера
# Формат: **Спикер** [MM:SS]: текст
sqlite3 -separator $'\t' "$DB" "
    SELECT
        COALESCE(sp.name, 'Unknown'),
        tl.start,
        tl.text
    FROM transcriptline tl
    JOIN session s ON tl.sessionId = s.id
    LEFT JOIN speaker sp ON tl.speakerID = sp.id
    WHERE hex(s.id) = '$SESSION_ID'
    ORDER BY tl.start ASC;
" | awk -F'\t' '
BEGIN { prev_speaker = ""; buffer = "" }
{
    speaker = $1
    start_ms = $2
    text = $3

    # Convert milliseconds to MM:SS
    total_sec = int(start_ms / 1000)
    mins = int(total_sec / 60)
    secs = total_sec % 60
    timestamp = sprintf("%02d:%02d", mins, secs)

    if (speaker != prev_speaker) {
        # Flush previous speaker buffer
        if (buffer != "") {
            print buffer
            print ""
        }
        buffer = "**" speaker "** [" timestamp "]: " text
        prev_speaker = speaker
    } else {
        # Same speaker — append text
        buffer = buffer " " text
    }
}
END {
    if (buffer != "") {
        print buffer
        print ""
    }
}
' > "$OUTPUT_FILE"

LINES=$(wc -l < "$OUTPUT_FILE")
echo "Transcript written to $OUTPUT_FILE ($LINES lines)"
