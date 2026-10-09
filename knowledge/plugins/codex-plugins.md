---
title: "Плагины Codex — манифесты, компоненты, маркетплейсы, обновление, один пакет для Codex и Claude Code"
source: "https://developers.openai.com/plugins/build/plugins"
source_type: docs
status: processed
added: 2026-09-18
updated: 2026-10-08
review_by: 2026-12-18
tags: [plugins, codex, openai, claude-code, marketplace, hooks, mcp, portability, agent-plugins]
publish: false
---

# Плагины Codex

## Кратко

Codex (CLI, TUI, desktop) ставит плагины из маркетплейсов и читает три формата манифеста: Agent Plugins 1.0 (`plugin.json` в корне), собственный `.codex-plugin/plugin.json` и манифест Claude Code `.claude-plugin/plugin.json`. Полный набор компонентов (скиллы, MCP, хуки, команды) грузится только из legacy-манифестов, а портативный формат Agent Plugins даёт лишь скиллы и MCP. Поэтому пакет в формате Claude Code без второго манифеста работает и в Codex, со своими ограничениями по хукам и MCP.

> **Снимок:** код `openai/codex` тега `rust-v0.154.0` и `main` на 17.09.2026 плюс живая установка тестового плагина в Codex CLI 0.154.0 и Claude Code 2.1.274. Документация OpenAI местами расходится с кодом, расхождения отмечены.

## Какой манифест читается

Порядок поиска в корне плагина:

1. `plugin.json`, если это обычный файл (не симлинк) и его `$schema` начинается с `https://agent-plugins.org/schemas/`. `plugin.json` без такой схемы (например, от npm) пропускается.
2. `.codex-plugin/plugin.json`.
3. `.claude-plugin/plugin.json`.
4. `.cursor-plugin/plugin.json`.

Если на более приоритетном месте лежит симлинк, плагин не грузится совсем.

Документация OpenAI называет формат Agent Plugins основным для новых пакетов, а `.codex-plugin/` — fallback для совместимости. Встроенный скилл `plugin-creator` при этом по-прежнему генерирует `.codex-plugin/`.

## Что грузится в каждом формате

| Компонент | Legacy (`.codex-plugin/`, `.claude-plugin/`) | Agent Plugins (`plugin.json` в корне) |
|---|---|---|
| Скиллы | `skills/`, обход рекурсивный — вложенные каталоги видны без объявления (проверено на двух уровнях), имена остаются плоскими | только прямые подпапки `skills/` |
| MCP | `.mcp.json` или inline `mcpServers` | `mcp.json` |
| Хуки | `hooks/hooks.json` или поле `hooks` | **не грузятся** |
| Apps | `.app.json` | **не активируются** в локальном рантайме |
| Команды | `commands/` при установке превращаются в скиллы `<плагин>:source-command-<имя>`, но только пока файл невелик (см. ниже) | нет |
| Субагенты | загрузчика нет | нет |

🔴 **Расхождение документации с кодом.** Документация предлагает объявлять хуки и apps в корневом `plugin.json` через `extensions.com.openai`. Код для этого формата их не включает (`core-plugins/src/loader.rs`, тест `agent_plugin_overlay_apps_are_not_runtime_active`). Пакет с хуками должен оставаться в legacy-формате.

🟡 **Лимит на длину команды.** Миграция `commands/` в скиллы работает только для небольших файлов: по коду предел около 4 КБ. Проверено — команда на 285 байт мигрировала, команда на 13 КБ была молча пропущена, без предупреждения при установке. Длинные роли поэтому доставляются не командой, а скиллом: `skills/<роль>/SKILL.md` ограничен только длиной `description` и работает в обоих хостах (в Claude Code скилл плагина вызывается как `/<плагин>:<имя>`).

🟡 **«Validation rejects `hooks`».** Эта фраза из встроенной спецификации `plugin-creator` относится к валидатору публикации в каталоге OpenAI, а не к локальному рантайму. `codex plugin add` ставит плагин с хуками, и хук срабатывает.

## MCP в плагине

- **Legacy `.mcp.json`** разбирается в ту же структуру, что `[mcp_servers]` в `config.toml`. Работают `required`, `startup_timeout_sec`, `tool_timeout_sec`, `enabled_tools`/`disabled_tools`, `bearer_token_env_var`, `http_headers`, `oauth`. `type` принимает `http`, `streamable_http`, `stdio`. Относительный `cwd` считается от корня плагина. Подстановки `${CLAUDE_PLUGIN_ROOT}` или `${PLUGIN_ROOT}` в `args` в коде нет.
- **Портативный `mcp.json`** принимает только поля стандарта: `required` и таймауты недопустимы, SSE не поддерживается, удалённый адрес обязан быть HTTPS, заголовок `Authorization` молча удаляется. Зато подставляются `${PLUGIN_ROOT}` и `${PLUGIN_DATA}`.
- Пользователь управляет серверами плагина через `[plugins."<plugin>".mcp_servers.<srv>]` (`enabled`, `enabled_tools`, режим подтверждения). `required` и таймауты так не задаются.

## Маркетплейсы

- **Где ищется файл:** `.agents/plugins/marketplace.json`, `.agents/plugins/api_marketplace.json`, `.claude-plugin/marketplace.json`, `.cursor-plugin/marketplace.json`. Репозиторный маркетплейс находится от git-корня рабочей папки, личный лежит в `~/.agents/plugins/marketplace.json`, оба подхватываются без `marketplace add`.
- **Источники плагина в записи:** локальный путь от корня маркетплейса, `url` (с `ref`/`sha`), `git-subdir`, `npm`. Тип `github`, как у Claude Code, не поддерживается.
- **Подключение:** `codex plugin marketplace add <путь | owner/repo[@ref] | HTTPS/SSH git URL>` с `--ref` и `--sparse <PATH>`. Запись попадает в `[marketplaces.<name>]` пользовательского `config.toml`.
- **Приватный репозиторий:** отдельного механизма нет — используются системные git-учётки (в коде git запускается с `GIT_TERMINAL_PROMPT=0`). Проверено: установка из приватного репозитория по SSH-адресу проходит без дополнительной настройки, если ключ уже работает.
- **Установка:** `codex plugin add PLUGIN@MARKETPLACE`. Клон маркетплейса остаётся в `~/.codex/.tmp/marketplaces/<имя>` — полный, с историей; сам плагин копируется в `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/`. В рабочую папку проекта не попадает ничего.
- **Для проекта:** аналог `enabledPlugins` — `[plugins."plugin@marketplace"] enabled = true` в `.codex/config.toml` проекта. Проектный конфиг читается только для доверенного проекта. Флаг `INSTALLED_BY_DEFAULT` — это метка в UI, логики автоустановки за ним нет.

## Обновление

- **Автоматически при старте** — проверено запуском: после публикации новой версии в git-маркетплейс очередной `codex exec` сам подтянул снимок маркетплейса и переустановил плагин. По коду обход git-маркетплейсов запускает app-server, таймаут git — 30 с, настройки выключения не найдено.
- **Вручную:** `codex plugin marketplace upgrade [NAME]`. Отдельной команды `codex plugin update` нет.
- **Пиннинг:** на уровне маркетплейса — `--ref`, на уровне записи плагина — `ref` или `sha`.
- **Локальные маркетплейсы** `upgrade` не трогает. При разработке меняют версию в манифесте и переустанавливают плагин. Встроенный `plugin-creator` для этого ставит суффикс `+codex.<cachebuster>`.

Отдельная проверка Codex 0.161.0 от 2026-10-08: [удаление старых каталогов и риск запуска хуков по прежнему пути](plugin-update-hook-paths.md#codex). Она дополняет исторический снимок этого обзора.

## Хуки

- Хуки включены по умолчанию (`hooks` stable). Отдельный флаг `plugin_hooks` снят.
- **Где конфиг вне плагина:** `~/.codex/hooks.json`, `~/.codex/config.toml` (`[hooks]`), `<repo>/.codex/hooks.json`, `<repo>/.codex/config.toml`. Проектные хуки грузятся только в доверенном проекте.
- **События:** `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`, `Interrupt`.
- **Обработчики:** в протоколе объявлены `command`, `mcp_tool`, `prompt`, `agent`. `prompt` и `agent` Codex не запускает (документация OpenAI), `mcp_tool` не проверялся. Переносимый вариант — `command`.
- **Доверие:** хук без статуса managed, в том числе из плагина, не запустится, пока пользователь его не проверит. Доверие привязано к хэшу, поэтому изменённый хук требует подтверждения заново. Разовый обход для автоматизации — `--dangerously-bypass-hook-trust`.
- Хукам плагина Codex выставляет `CLAUDE_PLUGIN_ROOT` и `CLAUDE_PLUGIN_DATA` (проверено запуском: корень указывает на кэш версии, data — на `~/.codex/plugins/data/<plugin>-<marketplace>`).

## Как скилл находит свои файлы

Переменной окружения с каталогом скилла нет. Модель получает путь к `SKILL.md` и инструкцию разрешать относительные пути от его каталога. Claude Code даёт то же самое строкой `Base directory for this skill: …`. Путь от корня проекта (`.claude/skills/<имя>/…`) в плагине не работает ни там, ни там: файлы плагина лежат в кэше хоста.

**Переменные в тексте `SKILL.md` переносимыми не являются** (проверено запуском в обоих хостах): Claude Code подставляет прямо в текст и `${CLAUDE_PLUGIN_ROOT}`, и `${CLAUDE_SKILL_DIR}`, Codex оставляет обе литералом, а в Bash-инструменте переменной нет вовсе — `echo $CLAUDE_PLUGIN_ROOT` печатает пустую строку. Переносимая форма одна — **путь от каталога скилла** (`bash scripts/x.sh`): оба хоста сами переходят в каталог скилла. Переменная остаётся рабочей там, где её подставляет хост: в `hooks/hooks.json` и в конфигурации MCP.

## Один пакет для Codex и Claude Code

Проверено установкой в оба хоста. Одно дерево без `.codex-plugin/` обслуживает оба:

```
marketplace-repo/
├── .claude-plugin/marketplace.json     # Codex читает его как legacy-маркетплейс
└── plugins/<name>/
    ├── .claude-plugin/plugin.json
    ├── skills/<skill>/SKILL.md
    ├── .mcp.json
    └── hooks/hooks.json
```

В обоих хостах подхватываются скиллы, MCP и хук `SessionStart`; `commands/` становятся командами в Claude Code и скиллами в Codex. В Codex хук сработал после выдачи доверия. Проверено установкой из приватного репозитория GitHub.

**Ограничения такого пакета в Codex:**

- переносимы только хуки типа `command`, и без выданного пользователем доверия они не запускаются;
- `${CLAUDE_PLUGIN_ROOT}` в `args` у `.mcp.json` не подставляется: stdio-серверу нужен другой способ найти свои файлы, удалённому HTTP-серверу это не важно;
- поле `headers` в Claude Code и `http_headers` в Codex называются по-разному;
- корневой `plugin.json` со `$schema` Agent Plugins добавлять нельзя: он перехватит приоритет и отключит в Codex хуки, apps и команды.

Официального пути «один манифест для двух хостов» OpenAI не описывает. Есть только портал публикации, который конвертирует `.claude-plugin/plugin.json` в `.codex-plugin/plugin.json` и советует переделать `commands/` и `agents/` в скиллы.

## Источники

- [OpenAI — Build plugins](https://developers.openai.com/plugins/build/plugins)
- [OpenAI — Submit a Claude plugin](https://developers.openai.com/plugins/guides/submit-claude-plugin)
- [Codex — Hooks](https://developers.openai.com/codex/hooks)
- [openai/codex, тег rust-v0.154.0](https://github.com/openai/codex/tree/rust-v0.154.0/codex-rs) — `core-plugins/src/loader.rs`, `core-plugins/src/marketplace.rs`, `core-plugins/src/manager.rs`, `utils/plugins/src/plugin_namespace.rs`, `codex-mcp/src/plugin_config.rs`, `codex-mcp/src/agent_plugin_config.rs`, `hooks/src/engine/discovery.rs`
- встроенный скилл Codex `plugin-creator`: `references/plugin-json-spec.md`, `references/installing-and-updating.md`

## Связанные файлы

- [!plugins.md](!plugins.md) — плагины как формат и экосистема, формат Anthropic
- [agent-plugins-standard.md](agent-plugins-standard.md) — Agent Plugins 1.0: портативное ядро, которое Codex поддерживает частично
- [../cases/coman-os.md](../cases/coman-os.md) — живая поставка под Claude Code и Codex: расхождения контракта хуков
- [../agents/mcp.md](../agents/mcp.md) — MCP: протокол и транспорты
- [../coding/third-party-models.md](../coding/third-party-models.md) — Codex как харнесс: сторонние модели через `model_providers` (только Responses API), Codex SDK
