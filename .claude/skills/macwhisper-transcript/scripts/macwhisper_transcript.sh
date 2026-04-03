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

# Извлекаем fullText в файл
sqlite3 "$DB" "
    SELECT fullText FROM session
    WHERE userChosenTitle = '$SESSION_NAME'
    ORDER BY dateCreated DESC
    LIMIT 1;
" > "$OUTPUT_FILE"

LINES=$(wc -l < "$OUTPUT_FILE")
echo "Transcript written to $OUTPUT_FILE ($LINES lines)"
