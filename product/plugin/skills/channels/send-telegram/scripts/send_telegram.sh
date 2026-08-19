#!/bin/bash
# Отправка сообщения в Telegram через Bot API (plain, parse_mode=HTML).
# Использование: ./send_telegram.sh [--to alias[,alias...]] [--] "текст сообщения"
#
# Без --to адресат берётся из TELEGRAM_CHAT_ID — прежнее поведение, реестр не нужен.
# С --to алиасы разрешаются реестром (recipients.py) в ИМЕНА ключей окружения,
# а значения подставляются здесь: логика поиска .env живёт только в shell и не
# раздваивается на python.
#
# Хардёнинг (3 дефекта, аудит Codex 2026-06-15):
#   1. Нарезка по СТРОКАМ до конвертации — чанки не рвут <b>…</b> / HTML-entity.
#   2. Проверяет ok в ответе Telegram — ненулевой exit при недоставке любого чанка.
#   3. .env: сначала уже заданные env-переменные, затем .env в pwd, затем в git-root.
#
# Коды возврата:
#   0 — доставлено всем
#   1 — есть подтверждённые отказы доставки (повтор безопасен)
#   2 — есть НЕИЗВЕСТНЫЕ исходы: обрыв, 5xx, неразборное тело. Повторять нельзя,
#       сообщение могло дойти. Двойка важнее единицы.
#   3 — НЕ ОТПРАВЛЕНО НИКОМУ: ошибка вызова или предусловия (нет токена, пустой
#       текст, неизвестный алиас, незаданный ключ, чужой бот). Разведено с 1 и 2
#       намеренно: headless-потребителю нужно отличать «почини конфиг» от
#       «проверь чат глазами до любого повтора».
set -uo pipefail

MAX_LENGTH=4096
CHANNEL_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_channel_common.sh
source "$CHANNEL_SCRIPT_DIR/_channel_common.sh"

# --- 0. Диагностика маршрута ------------------------------------------------
# `--check` ничего не отправляет: печатает, чем канал будет слать и что для
# этого настроено. Нужен ровно там, где раньше приходилось гадать: сообщение
# ушло не туда или не ушло вовсе, а конфигурация видна только чтением .env.
if [ "${1:-}" = "--check" ]; then
  channel_report_route
  exit 0
fi

# --- 1. Разбор аргументов ---------------------------------------------------
channel_parse_args "$@" || exit 3
INPUT="$CHANNEL_TEXT"
if [ -z "${INPUT//[[:space:]]/}" ]; then
  echo "ERROR: empty or whitespace-only message" >&2
  exit 3
fi

# --- 2. Креды и адресаты ----------------------------------------------------
channel_load_env
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "ERROR: TELEGRAM_BOT_TOKEN not set (checked env, ./.env, git-root/.env)" >&2
  exit 3
fi

channel_resolve_recipients "$CHANNEL_TO" || exit $?

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

# --- 4. Подготовка чанков: один раз на все адресаты -------------------------
# Раньше конвертация жила внутри отправки и повторялась на каждый чанк. При
# нескольких адресатах это означало бы прогон sed на каждого — и, что важнее,
# риск, что адресаты получат по-разному нарезанный текст.
CHUNKS=()
BUFFER=""

while IFS= read -r line || [ -n "$line" ]; do
  if [ -z "$BUFFER" ]; then
    cand="$line"
  else
    cand="$BUFFER"$'\n'"$line"
  fi
  cand_html=$(printf '%s' "$cand" | convert)
  if [ "${#cand_html}" -gt "$MAX_LENGTH" ] && [ -n "$BUFFER" ]; then
    CHUNKS+=("$(printf '%s' "$BUFFER" | convert)")   # буфер помещался, новая строка — уже нет
    BUFFER="$line"
  else
    BUFFER="$cand"       # (одиночная строка длиннее MAX уйдёт как есть — best effort)
  fi
done <<< "$INPUT"

[ -n "$BUFFER" ] && CHUNKS+=("$(printf '%s' "$BUFFER" | convert)")

# --- 5. Отправка одного чанка -----------------------------------------------
# Печатает тело ответа. Коды: 0 — ok:true, 1 — подтверждённый отказ,
# 2 — исход НЕИЗВЕСТЕН (curl не смог получить ответ).
send_chunk() {
  local chat="$1" html="$2" raw curl_rc http body
  # -w выносит HTTP-код последней строкой: без него 5xx и HTML-страница прокси
  # неотличимы от честного отказа Telegram, и «исход неизвестен» превращался бы
  # в «не доставлено» — то есть в разрешение повторить уже принятое.
  # -m: без потолка зависшее соединение вешает CronJob бессрочно.
  raw=$(curl -s -m 30 -w '\n%{http_code}' \
    -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="$chat" \
    -d parse_mode=HTML \
    --data-urlencode text="$html")
  curl_rc=$?
  http="${raw##*$'\n'}"
  body="${raw%$'\n'*}"
  echo "$body"

  # Обрыв связи: ответа нет вовсе — принял ли Telegram, неизвестно.
  if [ "$curl_rc" -ne 0 ] || [ -z "$body" ]; then
    return 2
  fi
  # 5xx — сбой на стороне сервера: запрос мог быть применён. 4xx Telegram
  # разобрал и отверг — это подтверждённый отказ, повтор безопасен.
  case "$http" in
    5*) return 2 ;;
  esac

  RESP="$body" python3 - <<'PY'
import os, json, sys
try:
    parsed = json.loads(os.environ["RESP"])
except Exception:
    # Тело не разбирается: прокси, обрыв, HTML-заглушка. Telegram мог принять
    # сообщение — считать это отказом значило бы разрешить повтор поверх него.
    sys.exit(2)
if not isinstance(parsed, dict):
    sys.exit(2)
sys.exit(0 if parsed.get("ok") is True else 1)
PY
}

# --- 6. Цикл по адресатам ---------------------------------------------------
# Частичный отказ не откатывается: в Telegram отозвать доставленное нельзя.
# Сводка различает ТРИ исхода, а не два — «не доставлено» можно повторить,
# «исход неизвестен» повторять опасно.
SENT=0
ANY_FAILED=0
ANY_UNKNOWN=0
SUMMARY=""

for i in "${!ALIASES[@]}"; do
  alias="${ALIASES[$i]}"
  chat="${CHATS[$i]}"
  ok_parts=0
  bad_parts=0
  unknown_parts=0

  for c in "${CHUNKS[@]}"; do
    [ "$SENT" -gt 0 ] && sleep 1   # анти-throttle: между чанками и между адресатами
    SENT=$((SENT + 1))
    send_chunk "$chat" "$c"
    case $? in
      0) ok_parts=$((ok_parts + 1)) ;;
      2) unknown_parts=$((unknown_parts + 1)) ;;
      *) bad_parts=$((bad_parts + 1)) ;;
    esac
  done

  total="${#CHUNKS[@]}"
  if [ "$unknown_parts" -gt 0 ]; then
    ANY_UNKNOWN=1
    SUMMARY="${SUMMARY}  ❓ $alias: исход неизвестен ($ok_parts/$total доставлено, $unknown_parts без ответа) — не повторять вслепую"$'\n'
  elif [ "$bad_parts" -gt 0 ]; then
    ANY_FAILED=1
    SUMMARY="${SUMMARY}  ❌ $alias: $ok_parts/$total доставлено"$'\n'
  else
    SUMMARY="${SUMMARY}  ✅ $alias: $ok_parts/$total доставлено"$'\n'
  fi
done

# Сводка — в stdout, рядом с телами ответов. НЕ в stderr: потребители канала
# (dev/infra/runner/alerts.py, скилл meeting-agenda) берут «stderr или stdout»,
# и сводка в stderr вытеснила бы тело ответа Telegram — вместе с ним пропала бы
# диагностика вида «bot is not a member», по которой классифицируется отказ.
if [ "${#ALIASES[@]}" -gt 1 ] || [ "$ANY_FAILED" -eq 1 ] || [ "$ANY_UNKNOWN" -eq 1 ]; then
  printf 'Доставка:\n%s' "$SUMMARY"
fi

[ "$ANY_UNKNOWN" -eq 1 ] && exit 2
[ "$ANY_FAILED" -eq 1 ] && exit 1
exit 0
