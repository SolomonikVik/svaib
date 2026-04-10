#!/bin/bash
# Отправка сообщения в Telegram через Bot API
# Использование: ./send_telegram.sh "текст сообщения"
# Требует .env в корне рабочего пространства (pwd при запуске)
# Конвертирует markdown → HTML для Telegram (жирный, чекбоксы, разделители)

ROOT_DIR="$(pwd)"

if [ ! -f "$ROOT_DIR/.env" ]; then
  echo "ERROR: .env not found at $ROOT_DIR/.env"
  exit 1
fi

source "$ROOT_DIR/.env"

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
  echo "ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env"
  exit 1
fi

# Экранирование HTML-символов (до конвертации markdown)
TEXT="$1"
TEXT=$(echo "$TEXT" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')

# Конвертация markdown → HTML для Telegram
TEXT=$(echo "$TEXT" | sed 's/\*\*\([^*]*\)\*\*/<b>\1<\/b>/g')  # **жирный** → <b>жирный</b>
TEXT=$(echo "$TEXT" | sed 's/__\([^_]*\)__/<i>\1<\/i>/g')      # __курсив__ → <i>курсив</i>
TEXT=$(echo "$TEXT" | sed 's/^- \[ \] /- /g')                    # - [ ] → -
TEXT=$(echo "$TEXT" | sed 's/^---$//g')                           # --- → убрать

MAX_LENGTH=4096

send_message() {
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT_ID}" \
    -d parse_mode=HTML \
    -d text="$1"
}

if [ ${#TEXT} -le $MAX_LENGTH ]; then
  RESULT=$(send_message "${TEXT}")
  echo "$RESULT"
else
  PART=1
  while [ ${#TEXT} -gt 0 ]; do
    CHUNK="${TEXT:0:$MAX_LENGTH}"
    TEXT="${TEXT:$MAX_LENGTH}"
    echo "Sending part $PART..."
    RESULT=$(send_message "${CHUNK}")
    echo "$RESULT"
    PART=$((PART + 1))
    [ ${#TEXT} -gt 0 ] && sleep 1
  done
fi
