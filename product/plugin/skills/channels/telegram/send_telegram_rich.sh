#!/bin/bash
# Отправка RICH-сообщения Виктору в Telegram через sendRichMessage (Bot API 10.1, июнь 2026).
# Использование: ./send_telegram_rich.sh "MARKDOWN_TEXT"
# Контент — GFM-подобный markdown (заголовки, таблицы, списки, цитаты, формулы, код, картинки по URL).
# Требует .env в pwd (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID).
#
# Исход классифицируется (python по разобранному JSON), bash на нём ветвится:
#   ok        — Telegram принял (ok:true). Готово.
#   apifail   — Telegram ОТВЕТИЛ отказом (ok:false / HTTP-ошибка с телом). Фолбэк на plain send_telegram.sh.
#   transport — timeout/разрыв: НЕИЗВЕСТНО, принял ли Telegram. НЕ фолбэчим (риск двойной доставки), выходим с ошибкой.
# Фолбэк теряет rich-форматирование (таблицы/<details>/код уйдут сырой разметкой) — это аварийная доставка текста.

ROOT_DIR="$(pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$ROOT_DIR/.env" ]; then
  echo "ERROR: .env not found at $ROOT_DIR/.env"
  exit 1
fi

source "$ROOT_DIR/.env"

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
  echo "ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env"
  exit 1
fi

MD="$1"
# непустой и не только из пробелов/переводов строк
if [ -z "${MD//[[:space:]]/}" ]; then
  echo "ERROR: empty or whitespace-only message"
  exit 1
fi

# Отправка через sendRichMessage. python3: безопасная JSON-сериализация + классификация исхода.
# Печатает тело ответа, последней строкой — STATUS=ok|apifail|transport.
OUT=$(TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" TELEGRAM_CHAT_ID="$TELEGRAM_CHAT_ID" MD="$MD" python3 - <<'PY'
import os, json, urllib.parse, urllib.request, urllib.error
token=os.environ['TELEGRAM_BOT_TOKEN']; chat=os.environ['TELEGRAM_CHAT_ID']; md=os.environ['MD']
payload=urllib.parse.urlencode({
    'chat_id': chat,
    'rich_message': json.dumps({'markdown': md}, ensure_ascii=False),
}).encode('utf-8')
req=urllib.request.Request(f'https://api.telegram.org/bot{token}/sendRichMessage', data=payload)
status='transport'
try:
    r=urllib.request.urlopen(req, timeout=30)
    body=r.read().decode()
    try:
        ok = json.loads(body).get('ok') is True
    except Exception:
        ok = False
    status = 'ok' if ok else 'apifail'
    print(body)
except urllib.error.HTTPError as e:
    # Telegram ответил с телом — подтверждённый отказ API.
    print(e.read().decode())
    status = 'apifail'
except Exception as e:
    # timeout / разрыв соединения — исход неизвестен, не дублируем.
    print(json.dumps({'ok': False, 'description': f'{type(e).__name__}: {e}'}))
    status = 'transport'
print(f'STATUS={status}')
PY
)

# Показать тело ответа (без служебной строки STATUS).
printf '%s\n' "$OUT" | grep -v '^STATUS='
STATUS=$(printf '%s\n' "$OUT" | sed -n 's/^STATUS=//p' | tail -1)

case "$STATUS" in
  ok)
    : # доставлено rich-сообщением
    ;;
  apifail)
    echo "RICH rejected by API -> fallback to plain sendMessage (rich formatting will be lost)"
    bash "$SCRIPT_DIR/send_telegram.sh" "$MD"
    ;;
  *)
    echo "ERROR: rich send failed at transport level (timeout/connection); delivery outcome UNKNOWN." >&2
    echo "NOT falling back to avoid double delivery. Check Telegram and resend manually if needed." >&2
    exit 2
    ;;
esac
