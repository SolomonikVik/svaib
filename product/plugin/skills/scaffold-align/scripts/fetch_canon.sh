#!/usr/bin/env bash
# Выгрузка канона scaffold одним вызовом: файлы канона из ветки main публичного репозитория
# (последний релиз) → папка канона на диске. Печатает путь и отпечаток снимка; дальше агент
# читает файлы с диска, а не по сети.
# Шаблоны не качаются: `_templates/` стоят в корне пространства и поставляются вместе с ним.
#
#   cd "<корень пространства>" && bash .claude/skills/scaffold-align/scripts/fetch_canon.sh [--ref main] [--force]
#     # одна форма для любой среды: cwd bash-инструмента не гарантированно совпадает с корнем
#     # пространства (в Cowork это домашний каталог сессии), CLAUDE_SKILL_DIR в Cowork не задана
#
# Как качается: файлы канона забираются пофайлово, параллельными запросами залпом — так
# канон приезжает за ~15 с и укладывается в лимит одного вызова в Cowork (45 с). Архив всего
# репозитория одним потоком не используется: GitHub режет ему скорость до ~14 КБ/с, это ~90 с на
# 1,2 МБ, за лимит вызова.
# Список файлов даёт одна маленькая выдача jsDelivr. Её нет — списка и не нужно: канон объявляет
# себя сам, скрипт берёт README канона и добирает то, на что он ссылается, тем же залпом.
# Кэш: ${TMPDIR:-/tmp}/svaib-canon/<ref> — символическая ссылка на каталог <ref>@<sha>,
# переключается атомарно, поэтому параллельные вызовы и читатели друг другу не мешают;
# свежее суток — не качается, старше — перекачивается (не вышло — отдаёт старый с STALE=).
# Выход: 0 — CANON= (путь к канону), SNAPSHOT= (отпечаток содержимого) и VIA= (каким путём
# приехал) напечатаны; 1 — канон недоступен: без него хранитель не работает, это отказ, не повод
# судить по памяти. Причина отказа названа: сеть, лимит GitHub ограничил запросы, ref не найден,
# нет curl.
# Сеть: raw.githubusercontent.com (файлы) и data.jsdelivr.com (список). В Cowork нужны в allowlist
# оба; закрыт jsDelivr — канон всё равно приедет, закрыт raw — это отказ. Лимит api.github.com не
# тратится: этот домен не используется.
set -euo pipefail

REPO="SolomonikVik/svaib"
REF="main"
FORCE=0
MAX_AGE=86400
BATCH=16           # столько запросов в залпе: весь канон уходит одним; больше — риск упереться в лимит raw
MAX_EXTRA=40       # предохранитель добора по ссылкам
BUDGET=35          # секунд на выгрузку: вызов в Cowork живёт 45, добор в этот потолок не лезет
MAX_WAVES=6        # волн обхода: цепочка ссылок в каноне бывает длиннее двух шагов
# служебные файлы канона: на них никто не ссылается, без списка их берём по именам
SEED="README.md CLAUDE.md AGENTS.md _plan.md"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref) [[ $# -ge 2 ]] || { echo "канон недоступен: --ref без значения" >&2; exit 1; }; REF="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) echo "канон недоступен: неизвестный аргумент $1" >&2; exit 1 ;;
  esac
done
# ref — только простое имя ветки или тега: он попадает в путь кэша и в URL, а «/» в URL raw
# неотличим от границы пути — такой ref разобрать нельзя, и гадать мы не будем
[[ "$REF" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ && "$REF" != *..* ]] || { echo "канон недоступен: недопустимый ref «$REF» (допустимы буквы, цифры, «.», «_», «-»)" >&2; exit 1; }

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANON_REL="product/methodology/scaffold"
ROOT="${TMPDIR:-/tmp}/svaib-canon"
REF_KEY="${REF//\//%2F}"   # биекция: «feature/x» и «feature_x» не делят кэш
LINK="$ROOT/$REF_KEY"
LIST_URL="${SVAIB_CANON_LIST_URL:-https://data.jsdelivr.com/v1/packages/gh}"
RAW_URL="${SVAIB_CANON_RAW_URL:-https://raw.githubusercontent.com}"

fail() { echo "канон недоступен: $*" >&2; exit 1; }
emit() { echo "CANON=$1/$CANON_REL"; echo "SNAPSHOT=$2"; }

# метаданные снимка: пишутся целиком и при первой выгрузке, и при её повторении — «возраст»
# всегда одна строка, поэтому кэш живёт сутки от последней выгрузки, а файл не растёт
write_meta() {
  printf 'ref: %s\nsnapshot: %s\nvia: %s\nfiles: %s\nfetched_epoch: %s\nfetched_at: %s\nsource: https://github.com/%s\n' \
    "$REF" "$sha" "$VIA" "$(find "$1/$CANON_REL" -type f | wc -l | tr -d ' ')" \
    "$(date +%s)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$REPO" > "$1/FETCHED.txt"
}

current_sha() { [[ -L "$LINK" ]] && basename "$(readlink "$LINK")" | sed 's/^.*@//' || true; }
current_age() {
  local f="$LINK/FETCHED.txt" t
  [[ -f "$f" ]] || { echo 999999999; return; }
  t="$(sed -n 's/^fetched_epoch: //p' "$f" | tail -1)"
  [[ "$t" =~ ^[0-9]+$ ]] && echo $(( $(date +%s) - t )) || echo 999999999
}

# общий /tmp: каталог кэша должен быть нашим настоящим каталогом, а не чужой подложкой.
# Проверяется раньше всего: подложенный кэш нельзя отдавать и по короткому пути «свежий кэш»
if [[ -L "$ROOT" ]]; then fail "каталог кэша $ROOT — символическая ссылка, это не наш кэш"; fi
if [[ -e "$ROOT" ]]; then
  [[ -d "$ROOT" && -O "$ROOT" && -w "$ROOT" ]] || fail "каталог кэша $ROOT не наш или не пишется"
  chmod 700 "$ROOT" 2>/dev/null || true
fi
if [[ -L "$LINK" ]]; then
  link_target="$(readlink "$LINK")"
  case "$link_target" in "$ROOT"/*) ;; *) fail "ссылка кэша $LINK ведёт наружу кэша" ;; esac
fi

cache_intact() {  # снимок в кэше цел: README на месте и файлов столько же, сколько записано
  local want have
  [[ -f "$LINK/$CANON_REL/README.md" ]] || return 1
  want="$(sed -n 's/^files: //p' "$LINK/FETCHED.txt" 2>/dev/null | tail -1)"
  [[ "$want" =~ ^[0-9]+$ ]] || return 1   # нет записи о составе — доверять нечему
  have="$(find "$LINK/$CANON_REL" -type f 2>/dev/null | wc -l | tr -d ' ')"
  [[ "$have" == "$want" ]]
}

if [[ $FORCE -eq 0 ]] && cache_intact; then
  age="$(current_age)"
  if [[ "$age" -lt $MAX_AGE ]]; then emit "$LINK" "$(current_sha)"; echo "VIA=cache"; exit 0; fi
fi

command -v curl >/dev/null || fail "нет curl"
command -v python3 >/dev/null || fail "нет python3"
mkdir -p "$ROOT"
chmod 700 "$ROOT" 2>/dev/null || true
work="$(mktemp -d "$ROOT/fetch.XXXXXX")"
trap 'rm -rf "$work"' EXIT
top="$work/tree"
mkdir -p "$top"

stale_or_fail() {
  # сеть не дала свежего — старый кэш лучше отказа, но об этом говорится явно
  if [[ $FORCE -eq 0 ]] && cache_intact; then
    emit "$LINK" "$(current_sha)"; echo "VIA=cache"; echo "STALE=$(current_age)s ($*)"; exit 0
  fi
  fail "$@"
}

# один запрос отдаёт плоский список файлов ветки с размерами; из него берутся только пути канона.
# Разбирает python3: имена приходят снаружи, и путь из них нормализуется, а не склеивается как есть
list_canon_files() {
  local out="$work/listing.json" code
  code="$(curl -sSL --connect-timeout 10 --max-time 15 -w '%{http_code}' \
    "${LIST_URL}/${REPO}@${REF}?structure=flat" -o "$out" 2>/dev/null || true)"
  [[ "$code" == "200" ]] || return 1
  python3 "$SELF_DIR/parse_listing.py" "$out" "$CANON_REL" "$work/files.tsv" || return 1
  cut -f1 "$work/files.tsv" > "$work/files.txt"
  [[ -s "$work/files.txt" ]]
}

# залпами по $BATCH: параллельные запросы внутри одного вызова, каждый со своим таймаутом
download_batch() {
  local list="$1" n=0 f
  while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    mkdir -p "$top/$(dirname "$f")"
    curl -fsS --retry 1 --connect-timeout 10 --max-time 25 -o "$top/$f" "${RAW_URL}/${REPO}/${REF}/${f}" 2>/dev/null &
    n=$((n+1)); (( n % BATCH == 0 )) && wait || true
  done < "$list"
  wait || true
}

# чего не хватает после залпа: файла нет, он пуст или размером не тот, что обещан списком.
# Оборванный ответ curl оставляет обрезанный файл — по одному лишь наличию канон принимать нельзя
missing_into() {
  local list="$1" out="$2" f want have
  : > "$out"
  while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    if [[ ! -s "$top/$f" ]]; then echo "$f" >> "$out"; continue; fi
    want="$(awk -F'\t' -v p="$f" '$1==p{print $2; exit}' "$work/files.tsv" 2>/dev/null || true)"
    [[ -n "$want" && "$want" != "-1" ]] || continue
    have="$(wc -c < "$top/$f" | tr -d ' ')"
    if [[ "$have" != "$want" ]]; then echo "$f" >> "$out"; fi   # обрыв или не тот файл
  done < "$list"
}

# ../ и ./ в ссылке — в нормальный путь
norm_path() {
  local p="$1"
  while [[ "$p" == *"/./"* ]]; do p="${p//\/.\//\/}"; done
  p="${p#./}"
  while [[ "$p" == *"/../"* ]]; do p="$(printf '%s' "$p" | sed 's|[^/][^/]*/\.\./||')"; done
  printf '%s' "$p"
}

# чего канон ждёт, но на диске ещё нет: список мог отстать (у jsDelivr свой кэш) или его не было
# вовсе. Ссылки за пределы канона не берём — область скилла сам канон; пробованное не повторяем
extra_from_links() {
  local out="$1" src rel dir link cand
  : > "$out"; touch "$work/tried.txt"
  while IFS= read -r src; do
    rel="${src#$top/}"; dir="$(dirname "$rel")"
    { grep -oE '\]\([^)[:space:]]+\.md' "$src" 2>/dev/null || true; } | sed 's/^](//' | while IFS= read -r link; do
      case "$link" in http*|/*|\#*|mailto:*) continue ;; esac
      cand="$(norm_path "$dir/$link")"
      [[ "$cand" == "$CANON_REL/"* ]] || continue
      [[ -s "$top/$cand" ]] && continue
      grep -qxF "$cand" "$work/tried.txt" && continue
      echo "$cand"
    done
  done < <(find "$top/$CANON_REL" -type f -name '*.md' 2>/dev/null) | sort -u | head -n "$MAX_EXTRA" > "$out" || true
}

VIA="raw"; LISTED=1
if ! list_canon_files; then
  # списка нет: служебные имена — попытка, а не обещание; обязателен только README
  printf "$CANON_REL/%s\n" $SEED > "$work/files.txt"
  VIA="raw:walk"; LISTED=0
fi
download_batch "$work/files.txt"
# один повтор недостающего: сеть моргнула на части файлов — это не повод терять весь канон
missing_into "$work/files.txt" "$work/missing.txt"
if [[ -s "$work/missing.txt" ]]; then
  while IFS= read -r f; do [[ -n "$f" ]] && rm -f "$top/$f"; done < "$work/missing.txt"
  download_batch "$work/missing.txt"
fi
if [[ ! -s "$top/$CANON_REL/README.md" ]]; then
  # один диагностический запрос — только на отказе: без него причину не назвать
  code="$(curl -sSL --connect-timeout 10 --max-time 20 -w '%{http_code}' -o /dev/null \
    "${RAW_URL}/${REPO}/${REF}/${CANON_REL}/README.md" 2>/dev/null || true)"
  case "$code" in
    404) fail "ref «$REF» в ${REPO} не найден (HTTP 404)" ;;
    403|429) stale_or_fail "GitHub ограничил запросы (HTTP $code) — повторить позже" ;;
    *) stale_or_fail "README канона не отдан (HTTP ${code:-нет ответа}: сеть или allowlist raw.githubusercontent.com)" ;;
  esac
fi

for _ in $(seq 1 "$MAX_WAVES"); do
  # канон по списку уже собран; добор — уточнение, и ради него нельзя проесть лимит вызова
  (( SECONDS < BUDGET )) || break
  extra_from_links "$work/extra.txt"
  [[ -s "$work/extra.txt" ]] || break
  cat "$work/extra.txt" >> "$work/tried.txt"
  download_batch "$work/extra.txt"
done

# пустой файл выглядит как прочитанный, а содержания в нём нет: одна попытка перекачать и отказ
find "$top/$CANON_REL" -type f -empty 2>/dev/null | sed "s|^$top/||" > "$work/empty.txt" || true
if [[ -s "$work/empty.txt" ]]; then
  while IFS= read -r f; do [[ -n "$f" ]] && rm -f "$top/$f"; done < "$work/empty.txt"
  download_batch "$work/empty.txt"
  find "$top/$CANON_REL" -type f -empty 2>/dev/null | sed "s|^$top/$CANON_REL/||" > "$work/empty2.txt" || true
  if [[ -s "$work/empty2.txt" ]]; then
    stale_or_fail "часть канона приехала пустой: $(tr '\n' ' ' < "$work/empty2.txt" | sed 's/ *$//')"
  fi
fi

# список обещал файлы — канон обязан приехать целиком, иначе это не канон, а его огрызок
missing_into "$work/files.txt" "$work/missing.txt"
if ((LISTED)) && [[ -s "$work/missing.txt" ]]; then
  stale_or_fail "канон приехал неполным, не отдано: $(tr '\n' ' ' < "$work/missing.txt" | sed "s|$CANON_REL/||g; s| *$||")"
fi

# --- публикация в кэш -------------------------------------------------------------------------

# источник не сообщает коммит — идентификатор снимка считается по содержимому канона:
# одно содержимое → один каталог кэша, повторная выгрузка того же не плодит копий
sha="$(python3 "$SELF_DIR/snapshot_id.py" "$top/$CANON_REL")" || fail "не посчитать отпечаток снимка"

dest="$ROOT/${REF_KEY}@${sha}"
# снимок с тем же отпечатком мог остаться повреждённым от прежней выгрузки — сверяем состав
if [[ -f "$dest/$CANON_REL/README.md" ]]; then
  have="$(find "$dest/$CANON_REL" -type f | wc -l | tr -d ' ')"
  want="$(find "$top/$CANON_REL" -type f | wc -l | tr -d ' ')"
  if [[ "$have" != "$want" ]]; then mv "$dest" "$dest.broken.$$" 2>/dev/null || rm -rf "$dest"; fi
fi
if [[ ! -f "$dest/$CANON_REL/README.md" ]]; then
  # публикация атомарна: собираем в уникальном каталоге, потом один mv
  staged="$work/staged"
  mkdir -p "$staged/$(dirname "$CANON_REL")"
  mv "$top/$CANON_REL" "$staged/$CANON_REL"
  write_meta "$staged"
  # проиграли гонку — каталог уже положил другой вызов, свой черновик выбрасывается
  python3 "$SELF_DIR/publish_dir.py" "$staged" "$dest" "$CANON_REL/README.md" || fail "снимок не опубликован"
else
  write_meta "$dest"   # тот же снимок: возраст переписывается, а не дописывается строкой
fi
[[ -f "$dest/$CANON_REL/README.md" ]] || fail "кэш не собрался"
# переключение ссылки атомарно (rename), старый каталог не удаляется — читатели его не теряют
python3 "$SELF_DIR/swap_link.py" "$dest" "$LINK" || fail "не переключить ссылку кэша"
# снимки этого ref старше недели никому не нужны: кэш в /tmp не должен расти бесконечно
find "$ROOT" -maxdepth 1 -type d -name "${REF_KEY}@*" ! -name "$(basename "$dest")" -mtime +7 -exec rm -rf {} + 2>/dev/null || true
emit "$LINK" "$sha"
echo "VIA=$VIA"
# без списка состав канона не с чем сверить: файлы целы и непусты, но что их все — не доказано
if ((LISTED == 0)); then echo "UNVERIFIED=состав канона не сверялся: список файлов недоступен"; fi
