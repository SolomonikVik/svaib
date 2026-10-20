---
title: "Плагин svaib в OMP и вход в MCP"
created: 2026-10-14
updated: 2026-10-14
status: draft
type: reference
audience: client
publish: false
---

# Плагин svaib в OMP и вход в MCP

Две настройки превращают OMP в рабочее место партнёра. Плагин приносит методологию: скиллы, агента-поисковика и требования к файлам. Вход в MCP открывает инструменты компании: кто ты и где твоё, кто в компании, отправка в Telegram и на почту, управление людьми.

Команды — для Bash на Linux/macOS. Предполагается, что OMP уже установлен; если нет — начните с [инструкции установки BB Desktop, Codex CLI и OMP](bb-and-omp.md). Плагин ставится в харнес, а не в BB: интерфейс BB и пакет svaib настраиваются независимо.

Проверено на OMP 18.10.4 под Ubuntu 22.04.5, 2026-10-14.

## 🔹 Что нужно до начала

| Что | Зачем | Проверка |
| --- | --- | --- |
| OMP | сам харнес | `omp --version` |
| Bun | установщик плагинов OMP вызывает `bun install`; без него установка падает | `command -v bun` |
| Браузер на том же компьютере | вход в MCP проходит через экран согласия в браузере | — |

## 🔹 Шаг 1. Плагин

### 1.1 Bun, если его нет

Официальный установщик:

```bash
curl -fsSL https://bun.sh/install | bash
```

Открой новый терминал и проверь `bun --version`. Установщик Bun добавляет свой каталог в конфигурацию shell; если править конфигурацию не хочется, положи бинарник `bun` в `~/.local/bin` — этот каталог обычно уже в PATH. На проверке мы поставили готовый бинарник в `~/.bun/bin` и симлинк в `~/.local/bin`.

### 1.2 Маркетплейс плагина

```bash
omp plugin marketplace add https://github.com/SolomonikVik/svaib-plugin.git
omp plugin marketplace list
```

Повторный запуск ничего не ломает: ответ `Marketplace "svaib" already exists`. Убедись, что OMP видит плагин:

```bash
omp plugin discover
```

В списке — `svaib@0.7.0`.

### 1.3 Установка

```bash
omp plugin install svaib@svaib
omp plugin list
omp plugin doctor
```

Ожидаемое: `✔ Installed svaib from svaib (0.7.0)`; в списке `svaib@svaib (0.7.0) (user)`; доктор — `3 ok, 0 errors`.

Имя плагина указывается с источником. Команда `omp plugin install svaib` без источника ищет одноимённый пакет в npm и падает: `error: GET https://registry.npmjs.org/svaib - 404`.

### 1.4 Что приезжает и как проверить

В пакете 19 скиллов: `onboarding`, `space-align`, `space-scaffold`, `space-toolbox`, `roles-*`, `metrics-*`, `rhythm-*`, `content-update`, `projects-review`, `send-telegram`, `team-*-review`, `transcript-extract`; плюс агент `svaib-scout` — он ищет место и факт в пространстве, не забивая разговор прочитанным.

Свежая сессия подхватывает состав сама. Уже открытая — нет: дай `/reload-plugins` или перезапусти OMP. Проверка: спроси в сессии «какие скиллы для онбординга и работы с пространством тебе доступны» — в ответ должны прийти имена `onboarding`, `space-align`, `space-scaffold`, `space-toolbox`.

Честная граница: хуки плагина в формате Claude (`hooks/hooks.json`) OMP пока не исполняет. Карта пространства и требования к файлам приходят через скиллы и инструкцию партнёра, а не отдельным событием хода. Мост — работа в треке поддержки харнесов, клиентская поддержка не обещана.

## 🔹 Шаг 2. Вход в MCP

### 2.1 Первый запуск

Открой терминал в папке пространства:

```bash
omp
```

До входа OMP напишет `MCP server "svaib:svaib" failed to connect … HTTP 401 … ключ не принят`. Это ожидаемо: сервер платформы требует входа, а его ещё не было.

### 2.2 Авторизация

Внутри сессии:

```text
/mcp list
/mcp reauth svaib:svaib
```

`/mcp list` покажет `svaib:svaib ○ not connected`.

Имя сервера — тоже с источником. `/mcp reauth svaib` отвечает `Error: Server "svaib" not found`.

Дальше OMP поднимает локальный слушатель `http://localhost:3000` и открывает браузер. Если браузер не открылся, на экране есть ссылка на экран согласия и локальный ярлык `http://localhost:3000/launch` — он ведёт туда же. На экране согласия — восемь областей доступа, среди них `offline_access`: без него вход придётся проходить заново, с ним OMP продлевает токен сам.

Признаки успеха:

```text
✓ Authorization completed in browser
● Connected to "svaib:svaib"
✓ Reauthorized "svaib:svaib"
```

Вместе с подключением приходят 16 инструментов: `whoami`, `get_user`, `update_me`, `list_users`, `invite_user`, `update_user`, `disable_user`, `get_tenant`, `update_tenant`, `list_contacts`, `check_chat`, `confirm_chat`, `register_chat`, `list_chat_requests`, `send_telegram_message`, `send_email_message`. Что каждый делает — [серверная часть svaib](../mcp-platform.md).

### 2.3 Проверка

Один запрос без интерфейса:

```bash
omp -p "вызови whoami и назови имя, компанию и зону"
```

Ответ с именем и компанией — вход работает. Кто ты по имени в Telegram и что тебе доступно, определяет роль в компании и права, выданные на экране согласия.

### 2.4 Где живёт вход

Вход хранится в локальном хранилище OMP — `~/.omp/agent/agent.db`, таблица `auth_credentials`, запись с именем `mcp_oauth:profile:<профиль>:<url>`. Файлы настроек при этом не меняются: `~/.omp/agent/mcp.json` не создаётся, `.mcp.json` из пакета плагина остаётся как есть.

Привязка идёт к профилю по адресу сервера, поэтому в другой папке или другом проекте вход подхватывается сам — повторно согласие проходить не нужно. Сменить аккаунт — `/mcp reauth svaib:svaib`, отвязать — `/mcp unauth svaib:svaib`.

### 2.5 Это штатный функционал

Marketplace, установку плагинов и OAuth для MCP OMP умеет сам: команды `/mcp`, локальный слушатель обратного вызова, хранение токена и его продление, хранилище вида `auth`/`oauth` в конфиге — всё встроено. Сверх OMP и Bun ставить нечего, скрипты и правки кода не нужны. Источники: [плагины и marketplace](https://github.com/can1357/oh-my-pi/blob/main/docs/marketplace.md), [MCP и OAuth](https://github.com/can1357/oh-my-pi/blob/main/docs/mcp-config.md).

## 🔹 Если не получилось

| Что видно | Причина | Что делать |
| --- | --- | --- |
| `Executable not found in $PATH: "bun"` | Bun не установлен | Шаг 1.1 |
| `bun install failed … registry.npmjs.org/svaib - 404` | Установка без источника | `omp plugin install svaib@svaib` |
| `Error: Server "svaib" not found` | Имя сервера без источника | `/mcp reauth svaib:svaib` |
| `HTTP 401 … ключ не принят` | Вход не пройден | `/mcp reauth svaib:svaib` |
| В открытой сессии нет скиллов `space-*` | Состав читается при входе в сессию | `/reload-plugins` или перезапуск |
| Согласие ждёт, браузера на машине нет | Вход задуман браузерным | Подсказка самого OMP: `Headless? Paste the redirect URL or code with /login <value>` |

## 🔹 Признак готовности

Плагин стоит, когда `omp plugin list` показывает `svaib@svaib`, доктор не находит ошибок, а свежая сессия называет скиллы `space-*`. Вход пройден, когда `omp -p` больше не пишет 401, а `whoami` возвращает имя и компанию.

До входа скиллы уже работают, а инструменты платформы — нет: партнёр ведёт разговор о компании, но не видит, кто в ней, и не может отправить сообщение. Рабочим местом харнес считается только после обоих шагов.
