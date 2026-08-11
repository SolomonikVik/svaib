#!/bin/bash
# Отправка RICH-сообщения в Telegram через sendRichMessage (Bot API 10.1, июнь 2026).
# Использование: ./send_telegram_rich.sh [--to alias[,alias...]] [--] "MARKDOWN_TEXT"
# Контент — GFM-подобный markdown (заголовки, таблицы, списки, цитаты, формулы, код, картинки по URL).
# Креды: env-переменные → ./.env → git-root/.env (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID).
#
# Исход классифицируется (python по разобранному JSON), bash на нём ветвится:
#   ok        — Telegram принял (ok:true). Готово.
#   apifail   — Telegram ОТВЕТИЛ отказом (ok:false / HTTP-ошибка с телом). Фолбэк на plain send_telegram.sh.
#   transport — timeout/разрыв: НЕИЗВЕСТНО, принял ли Telegram. НЕ фолбэчим (риск двойной доставки), выходим с ошибкой.
# Фолбэк теряет rich-форматирование (таблицы/<details>/код уйдут сырой разметкой) — это аварийная доставка текста.
#
# Коды возврата: 0 — доставлено всем; 1 — подтверждённые отказы (повтор
# безопасен); 2 — НЕИЗВЕСТНЫЕ исходы, повторять нельзя; 3 — не отправлено
# никому (ошибка вызова или предусловия). Двойка важнее единицы.
set -uo pipefail

CHANNEL_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_channel_common.sh
source "$CHANNEL_SCRIPT_DIR/_channel_common.sh"

channel_parse_args "$@" || exit 3
MD="$CHANNEL_TEXT"
# непустой и не только из пробелов/переводов строк
if [ -z "${MD//[[:space:]]/}" ]; then
  echo "ERROR: empty or whitespace-only message" >&2
  exit 3
fi

# Резолв кредов — тем же правилом, что и plain: env → ./.env → git-root/.env.
# Файл .env есть только на машине оператора; в кластере токен и чат приезжают
# k8s-секретом уже переменными окружения, и требование файла делало rich
# недоступным ровно там, где повестку доставляет контур, а не человек.
channel_load_env
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "ERROR: TELEGRAM_BOT_TOKEN not set (checked env, ./.env, git-root/.env)" >&2
  exit 3
fi

# Адресаты разрешаются ОДИН раз, здесь. Ниже по коду ходят уже готовые chat_id:
# фолбэк на plain обязан получить один конкретный чат, а не исходный --to —
# иначе каждый отказавший адресат перезапустил бы весь веер и продублировал
# доставку тем, кому rich уже прошёл.
channel_resolve_recipients "$CHANNEL_TO" || exit $?

# --- Отправка одному адресату -----------------------------------------------
# Печатает тело ответа. Возвращает: 0 — ok, 1 — apifail, 2 — transport.
send_rich_one() {
  local chat="$1" out status
  out=$(TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" TELEGRAM_CHAT_ID="$chat" MD="$MD" python3 - <<'PY'
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
        parsed = json.loads(body)
        ok = parsed.get('ok') is True if isinstance(parsed, dict) else None
    except ValueError:
        # HTTP 200, но тело не разбирается: оборванный ответ, прокси, пустое
        # тело. Это НЕ подтверждённый отказ — Telegram мог сообщение принять.
        # Считать такой исход apifail значило бы уйти в фолбэк и доставить
        # повестку вторым сообщением поверх уже доставленной.
        ok = None
    status = 'ok' if ok is True else ('apifail' if ok is False else 'transport')
    print(body)
except urllib.error.HTTPError as e:
    # Подтверждённым отказом считается только ответ 4xx: Telegram разобрал
    # запрос и отверг его — повтор другим каналом безопасен. 5xx означает сбой
    # на стороне сервера, и был ли запрос применён, неизвестно: фолбэк здесь
    # доставил бы повестку вторым сообщением поверх уже принятой.
    print(e.read().decode())
    status = 'apifail' if 400 <= e.code < 500 else 'transport'
except Exception as e:
    # timeout / разрыв соединения — исход неизвестен, не дублируем.
    print(json.dumps({'ok': False, 'description': f'{type(e).__name__}: {e}'}))
    status = 'transport'
print(f'STATUS={status}')
PY
)
  # Показать тело ответа (без служебной строки STATUS).
  printf '%s\n' "$out" | grep -v '^STATUS='
  status=$(printf '%s\n' "$out" | sed -n 's/^STATUS=//p' | tail -1)
  case "$status" in
    ok) return 0 ;;
    apifail) return 1 ;;
    *) return 2 ;;
  esac
}

# --- Цикл по адресатам ------------------------------------------------------
ANY_FAILED=0
ANY_UNKNOWN=0
SUMMARY=""
FIRST=1

for i in "${!ALIASES[@]}"; do
  alias="${ALIASES[$i]}"
  chat="${CHATS[$i]}"
  [ "$FIRST" -eq 0 ] && sleep 1
  FIRST=0

  send_rich_one "$chat"
  case $? in
    0)
      SUMMARY="${SUMMARY}  ✅ $alias: доставлено rich"$'\n'
      ;;
    1)
      # Фолбэк — на ОДИН уже разрешённый chat_id, без --to и без повторного
      # чтения реестра: рассылка второй раз развернулась бы целиком.
      if [ ! -f "$CHANNEL_SCRIPT_DIR/send_telegram.sh" ]; then
        echo "ERROR: rich rejected by API and plain channel is missing at $CHANNEL_SCRIPT_DIR/send_telegram.sh" >&2
        ANY_FAILED=1
        SUMMARY="${SUMMARY}  ❌ $alias: rich отвергнут, plain-канал отсутствует"$'\n'
      else
        echo "RICH rejected by API -> fallback to plain sendMessage (rich formatting will be lost)" >&2
        TELEGRAM_CHAT_ID="$chat" bash "$CHANNEL_SCRIPT_DIR/send_telegram.sh" -- "$MD"
        plain_rc=$?
        # Код plain разбирается, а не сводится к «получилось / не получилось».
        # Двойка означает «сообщение могло дойти»: записав её как ❌, мы бы
        # выдали наружу exit 1, а инструкция скилла разрешает повторять ❌ —
        # и повтор лёг бы поверх уже доставленного.
        case "$plain_rc" in
          0)
            SUMMARY="${SUMMARY}  ✅ $alias: доставлено plain (rich отвергнут API)"$'\n'
            ;;
          2)
            ANY_UNKNOWN=1
            SUMMARY="${SUMMARY}  ❓ $alias: rich отвергнут, исход plain неизвестен — не повторять вслепую"$'\n'
            ;;
          *)
            ANY_FAILED=1
            SUMMARY="${SUMMARY}  ❌ $alias: rich отвергнут, plain тоже не прошёл (код $plain_rc)"$'\n'
            ;;
        esac
      fi
      ;;
    *)
      echo "ERROR: rich send failed at transport level (timeout/connection); delivery outcome UNKNOWN for $alias." >&2
      echo "NOT falling back to avoid double delivery. Check Telegram and resend manually if needed." >&2
      ANY_UNKNOWN=1
      SUMMARY="${SUMMARY}  ❓ $alias: исход неизвестен — не повторять вслепую"$'\n'
      ;;
  esac
done

# Сводка — в stdout, рядом с телами ответов: потребители канала берут
# «stderr или stdout», и сводка в stderr вытеснила бы диагностику Telegram.
if [ "${#ALIASES[@]}" -gt 1 ] || [ "$ANY_FAILED" -eq 1 ] || [ "$ANY_UNKNOWN" -eq 1 ]; then
  printf 'Доставка:\n%s' "$SUMMARY"
fi

[ "$ANY_UNKNOWN" -eq 1 ] && exit 2
[ "$ANY_FAILED" -eq 1 ] && exit 1
exit 0
