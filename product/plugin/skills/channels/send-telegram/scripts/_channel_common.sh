# Общая часть канала send-telegram: резолв кредов и разрешение адресатов.
# Подключается через source из send_telegram.sh и send_telegram_rich.sh.
#
# ЗАЧЕМ ОТДЕЛЬНЫМ ФАЙЛОМ. Раньше резолв кредов был скопирован в оба скрипта и
# разошёлся: rich научился отдавать приоритет уже заданным переменным, plain —
# нет, и подмена адресата извне в plain молча уходила в чат из .env. Разрешение
# адресатов — та же логика с той же ценой ошибки, поэтому живёт в одном месте.

# Заполняет TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID / TG_CHAT_*: env → ./.env → git-root/.env.
#
# Файл читается ВСЕГДА, даже когда токен и дефолтный чат уже в окружении:
# адресные ключи TG_CHAT_* могут лежать только в .env (штатная раскладка с
# direnv), и ранний выход отсюда ронял бы --to с «ключ не задан» при исправной
# конфигурации. Приоритет окружения защищает от перетирания.
channel_load_env() {
  local env_file="" git_root preset
  if [ -f "$(pwd)/.env" ]; then
    env_file="$(pwd)/.env"
  else
    git_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -n "$git_root" ] && [ -f "$git_root/.env" ]; then
      env_file="$git_root/.env"
    fi
  fi
  [ -z "$env_file" ] && return 0

  # Приоритет окружения — ПОКАЖДОЙ переменной, а не по факту «одной не хватает».
  # Иначе отсутствие chat_id заставляет файл перебить и уже заданный токен:
  # оператор, подставивший чужой чат одной переменной, отправит в свой.
  # TG_CHAT_* здесь наравне с ними — это тоже адреса.
  # Снимок через export -p, а не declare -A: ассоциативных массивов нет в
  # bash 3.2, который стоит на macOS по умолчанию.
  #
  # `declare -x` заменяется на `export`: eval с `declare` ВНУТРИ функции создаёт
  # локальную переменную, которая умирает на выходе, и приоритет окружения
  # молча пропадает. `export` внутри функции меняет глобальную. Ловушка тихая —
  # поймана регрессионным тестом при выносе этой логики из скрипта в функцию.
  preset="$(export -p \
    | grep -E '^declare -x (TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID|TG_CHAT_[A-Z0-9_]+)=' \
    | sed 's/^declare -x /export /' || true)"
  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
  [ -n "$preset" ] && eval "$preset"
  return 0
}

# $1 — список алиасов или пусто. Заполняет глобальные ALIASES и CHATS.
# Разрешает ЦЕЛИКОМ и ДО отправки: половина списка хуже отказа, потому что
# ошибка адресации — это чужие глаза на содержимом встречи.
channel_resolve_recipients() {
  local to="$1" resolver bot_id resolved rc alias ref value
  ALIASES=()
  CHATS=()

  if [ -z "$to" ]; then
    if [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
      echo "ERROR: TELEGRAM_CHAT_ID not set (checked env, ./.env, git-root/.env)" >&2
      return 3
    fi
    ALIASES+=("default")
    CHATS+=("$TELEGRAM_CHAT_ID")
    return 0
  fi

  resolver="${SVAIB_RECIPIENTS_PY:-$CHANNEL_SCRIPT_DIR/recipients.py}"
  if [ ! -f "$resolver" ]; then
    echo "ERROR: --to требует реестра адресатов, но recipients.py не найден рядом со скриптом" >&2
    return 3
  fi

  # id бота — префикс токена до двоеточия, величина публичная: сверка идёт
  # офлайн. chat_id зависит от пары «бот + получатель», поэтому реестр,
  # собранный для другого бота, резолвил бы алиасы в чужие чаты.
  bot_id="${TELEGRAM_BOT_TOKEN%%:*}"
  # stderr НЕ сливается в stdout: предупреждение интерпретатора при rc=0 стало
  # бы строкой данных, а строка без табуляции дала бы пустое имя ключа.
  local errfile
  errfile="$(mktemp 2>/dev/null || echo /tmp/svaib-recipients-err.$$)"
  resolved="$(python3 "$resolver" --resolve "$to" --bot-id "$bot_id" 2>"$errfile")"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "ERROR: адресаты не разрешены, не отправлено никому:" >&2
    cat "$errfile" >&2
    rm -f "$errfile"
    return 3
  fi
  rm -f "$errfile"

  # Дедуп ведётся строкой-аккумулятором, а не вторым массивом. Причина не в
  # красоте: расширение ПУСТОГО массива (`"${!arr[@]}"`) под `set -u` в bash
  # 3.2 — «unbound variable» и мгновенная смерть скрипта. Bash 3.2 стоит на
  # macOS по умолчанию, то есть у клиентов, и --to там падал бы целиком.
  local seen=$'\n'
  while IFS=$'\t' read -r alias ref; do
    [ -z "$alias" ] && continue
    value="${!ref:-}"
    if [ -z "$value" ]; then
      echo "ERROR: у адресата «$alias» ключ $ref не задан в окружении — не отправлено никому" >&2
      return 3
    fi
    # Два разных ключа с одинаковым значением дают дубль при валидном реестре.
    # Пересечение человека и группы, где он состоит, — другое: это два разных
    # чата и две осознанные доставки, схлопывать их нельзя.
    case "$seen" in
      *$'\n'"$value"$'\n'*)
        echo "NOTE: «$alias» указывает на уже добавленный чат — доставка одна" >&2
        continue
        ;;
    esac
    seen="${seen}${value}"$'\n'
    ALIASES+=("$alias")
    CHATS+=("$value")
  done <<< "$resolved"

  if [ "${#ALIASES[@]}" -eq 0 ]; then
    echo "ERROR: список адресатов пуст" >&2
    return 3
  fi
  return 0
}

# --- Диагностика маршрута ----------------------------------------------------
#
# Канал ходит в Bot API напрямую — и это его единственная задача. Доставка через
# шлюз делается инструментом MCP, который зовёт агент; второго пути к шлюзу тут
# намеренно нет (решение Эрика 12.08: один путь, а не «ещё один способ туда же»).
# Скрипты остаются для контуров, где шлюза не существует: клиентские установки и
# аварийная процедура §12.
#
# `--check` ничего не отправляет: печатает, чем канал будет слать и что для этого
# настроено. Нужен там, где раньше приходилось гадать — сообщение ушло не туда
# или не ушло вовсе, а конфигурация видна только чтением .env.
channel_report_route() {
  channel_load_env
  echo "Канал send-telegram — прямая отправка в Bot API"
  echo
  # ❗️ Печатается ФАКТ наличия, никогда значение. `${VAR:+да}${VAR:-нет}`
  # выглядит компактно и выводит сам секрет: первая подстановка даёт «да»,
  # вторая — значение, потому что переменная задана. Поймано живым прогоном
  # 12.08 — в терминал уехал токен бота.
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "  Токен бота: задан"
  else
    echo "  Токен бота: НЕ ЗАДАН"
  fi
  if [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    echo "  Чат по умолчанию: задан"
  else
    echo "  Чат по умолчанию: НЕ ЗАДАН"
  fi
  echo
  if [ -f "${SVAIB_RECIPIENTS_PY:-$CHANNEL_SCRIPT_DIR/recipients.py}" ]; then
    echo "  Известные адресаты (локальный реестр):"
    python3 "${SVAIB_RECIPIENTS_PY:-$CHANNEL_SCRIPT_DIR/recipients.py}" --list 2>&1 | sed 's/^/    /'
  else
    echo "  Реестра адресатов в этой поставке нет: доступен только чат по умолчанию."
  fi
  echo
  echo "  Есть MCP-сервер svaib — отправляй его инструментом, а не этими скриптами:"
  echo "  там журнал доставки, идемпотентность, права по ключу и видимый отправитель."
}

# Разбор общих аргументов: [--to alias[,alias...]] [--] "текст".
# Заполняет CHANNEL_TO и CHANNEL_TEXT. --to допустим только первым аргументом,
# `--` завершает флаги: внешние потребители зовут канал как [script, text],
# и текст, начинающийся с дефиса, не должен быть съеден парсером.
channel_parse_args() {
  CHANNEL_TO=""
  if [ "${1:-}" = "--to" ]; then
    CHANNEL_TO="${2:-}"
    if [ -z "$CHANNEL_TO" ]; then
      echo "ERROR: --to без списка адресатов" >&2
      return 3
    fi
    shift 2
  fi
  [ "${1:-}" = "--" ] && shift
  CHANNEL_TEXT="${1:-}"
  return 0
}
