#!/bin/bash
# Отправка сообщения в Telegram через Bot API (plain, parse_mode=HTML).
# Использование: ./send_telegram.sh "текст сообщения"
#
# Хардёнинг (3 дефекта, аудит Codex 2026-06-15):
#   1. Нарезка по СТРОКАМ до конвертации — чанки не рвут <b>…</b> / HTML-entity.
#   2. Проверяет ok в ответе Telegram — ненулевой exit при недоставке любого чанка.
#   3. .env: сначала уже заданные env-переменные, затем .env в pwd, затем в git-root.
set -uo pipefail

MAX_LENGTH=4096

# --- 1. Резолв токена/чата: env → ./.env → git-root/.env --------------------
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  ENV_FILE=""
  if [ -f "$(pwd)/.env" ]; then
    ENV_FILE="$(pwd)/.env"
  else
    GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -n "$GIT_ROOT" ] && [ -f "$GIT_ROOT/.env" ]; then
      ENV_FILE="$GIT_ROOT/.env"
    fi
  fi
  if [ -n "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
fi

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  echo "ERROR: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set (checked env, ./.env, git-root/.env)" >&2
  exit 1
fi

# --- 2. Валидация входа -----------------------------------------------------
INPUT="${1:-}"
if [ -z "${INPUT//[[:space:]]/}" ]; then
  echo "ERROR: empty or whitespace-only message" >&2
  exit 1
fi

# --- 3. Конвертация markdown → HTML (построчно) -----------------------------
# sed обрабатывает строку за строкой, поэтому <b>/<i> никогда не пересекают
# границу строки — а значит и границу чанка (чанки режутся ТОЛЬКО по строкам).
convert() {
  sed -e 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g' \
      -e 's/\*\*\([^*]*\)\*\*/<b>\1<\/b>/g' \
      -e 's/__\([^_]*\)__/<i>\1<\/i>/g' \
      -e 's/^- \[ \] /- /g' \
      -e 's/^---$//'
}

# --- 4. Отправка одного (уже сконвертированного) чанка -----------------------
# Печатает тело ответа. Возвращает 0 при ok:true, иначе 1.
send_chunk() {
  local resp
  resp=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT_ID}" \
    -d parse_mode=HTML \
    --data-urlencode text="$1")
  echo "$resp"
  RESP="$resp" python3 - <<'PY'
import os, json, sys
try:
    sys.exit(0 if json.loads(os.environ["RESP"]).get("ok") is True else 1)
except Exception:
    sys.exit(1)
PY
}

# --- 5. Нарезка по строкам с учётом длины КОНВЕРТИРОВАННОГО чанка ------------
FAILED=0
PART=0
BUFFER=""

flush() {
  [ -z "$BUFFER" ] && return 0
  PART=$((PART + 1))
  [ "$PART" -gt 1 ] && sleep 1   # анти-throttle между чанками
  local html
  html=$(printf '%s' "$BUFFER" | convert)
  send_chunk "$html" || FAILED=1
  BUFFER=""
}

while IFS= read -r line || [ -n "$line" ]; do
  if [ -z "$BUFFER" ]; then
    cand="$line"
  else
    cand="$BUFFER"$'\n'"$line"
  fi
  cand_html=$(printf '%s' "$cand" | convert)
  if [ "${#cand_html}" -gt "$MAX_LENGTH" ] && [ -n "$BUFFER" ]; then
    flush                # текущий буфер помещается, новая строка — уже нет
    BUFFER="$line"
  else
    BUFFER="$cand"       # (одиночная строка длиннее MAX уйдёт как есть — best effort)
  fi
done <<< "$INPUT"

flush

exit "$FAILED"
