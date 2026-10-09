---
title: "Plugins — система расширения AI-агентов: формат, экосистема, best practices"
status: processed
added: 2026-02-13
updated: 2026-10-08
review_by: 2026-12-08
tags: [plugins, claude-code, cowork, marketplace, ecosystem, svaib-product, skill-graph]
publish: false
---

# Plugins — система расширения AI-агентов

## Кратко

Плагин — пакет для распространения AI-расширений: Skills + Commands + Agents + Hooks + MCP + LSP. Всё файловое (Markdown + JSON), zero code, zero build steps. Единый формат для Claude Code (CLI, разработчики) и Cowork (GUI, knowledge workers). Public beta с октября 2025. Экосистема: official marketplace (dev-плагины + LSP + интеграции), knowledge-work плагины для Cowork (отраслевые), растущие community-маркетплейсы. Cross-platform: Codex ставит пакет в формате Claude Code без трансляции — скиллы, MCP и command-хуки ([codex-plugins.md](codex-plugins.md)), остальные хосты совместимы через Agent Skills стандарт; с августа 2026 обёртку описывает вендор-нейтральный [Agent Plugins 1.0](agent-plugins-standard.md), но только для скиллов и MCP. Для SVAIB: плагин — готовый delivery mechanism для модели подписки "Skills + Agents + Онтология".

---

## Что такое плагин

Плагин объединяет 6 компонентов в один распространяемый пакет:

| Компонент | Файлы | Что делает |
|-----------|-------|-----------|
| **Skills** | `skills/name/SKILL.md` | AI-инструкции, авто-активация по триггеру |
| **Commands** | `commands/*.md` | Слэш-команды, вызов пользователем |
| **Agents** | `agents/*.md` | Субагенты для изолированных подзадач |
| **Hooks** | `hooks/hooks.json` | Обработчики событий жизненного цикла |
| **MCP** | `.mcp.json` | Коннекторы к внешним сервисам |
| **LSP** | `.lsp.json` | Code intelligence (Language Server Protocol) |

Каждый компонент можно использовать отдельно в `.claude/` проекта — без создания плагина. Плагин нужен когда хочешь **распространять**: команде, сообществу, через маркетплейс.

**Ключевое различие:** без плагина — Skills имеют короткие имена (`/hello`). В плагине — namespace (`/plugin-name:hello`). Namespace предотвращает конфликты между плагинами.

Подробнее о компонентах: Skills → [skills/!skills.md](../skills/!skills.md), Agents → [agents/!agents.md](../agents/!agents.md), MCP → [agents/mcp.md](../agents/mcp.md).

---

## Структура плагина

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json           # Манифест (ТОЛЬКО он здесь)
├── skills/                   # Agent Skills (папки с SKILL.md)
│   └── code-review/
│       ├── SKILL.md
│       ├── scripts/          # Исполняемый код
│       └── references/       # Документация по необходимости
├── commands/                 # Слэш-команды (legacy; для новых — skills/)
├── agents/                   # Субагенты
├── hooks/
│   └── hooks.json            # Конфигурация хуков
├── .mcp.json                 # MCP-серверы
├── .lsp.json                 # LSP-серверы
├── scripts/                  # Утилиты для хуков
├── README.md
├── CHANGELOG.md
└── LICENSE
```

**Критическое правило:** Все компоненты в КОРНЕ плагина. Внутри `.claude-plugin/` — только `plugin.json`. Самая частая ошибка.

**`commands/` — legacy.** Для новых плагинов рекомендуется `skills/`. Commands остаётся для обратной совместимости.

---

## Манифест (plugin.json)

Манифест опционален. Если его нет — Claude Code auto-discover компонентов по дефолтным путям, имя берётся из названия директории.

### Обязательное поле — только `name`

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Brief plugin description",
  "author": { "name": "...", "email": "...", "url": "..." },
  "homepage": "https://...",
  "repository": "https://...",
  "license": "MIT",
  "keywords": ["tag1", "tag2"]
}
```

### Кастомные пути к компонентам

```json
{
  "commands": ["./custom/cmd.md"],
  "agents": "./custom/agents/",
  "skills": "./custom/skills/",
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "outputStyles": "./styles/",
  "lspServers": "./.lsp.json"
}
```

Кастомные пути **дополняют** дефолтные директории, не заменяют. Все пути относительные, начинаются с `./`.

**Этим же полем скиллы раскладываются по каталогам.** По умолчанию видны только прямые потомки `skills/`: `skills/roles/keeper/SKILL.md` не подхватывается. Объявление `"skills": ["./skills/roles/", "./skills/utils/"]` его находит, но вглубь не раскрывается — `./skills/expertise/` не увидит `expertise/deep/<скилл>`, каждый каталог с каталогами скиллов объявляется явно. Имена при этом остаются плоскими: каталог в имя скилла не входит. Codex, для сравнения, обходит `skills/` рекурсивно и объявлений не требует.

### Переменные окружения

`${CLAUDE_PLUGIN_ROOT}` — абсолютный путь к директории плагина. Использовать в хуках, MCP, скриптах — пути корректны независимо от места установки.

`${CLAUDE_PLUGIN_DATA}` — персистентный каталог плагина (`~/.claude/plugins/data/{id}/`), создаётся при первом обращении и переживает обновления. Сюда — состояние и кэш, которые не должны сбрасываться новой версией.

Скилл плагина адресует свои файлы от каталога `SKILL.md`: при запуске скилла агент получает строку `Base directory for this skill: …`. Путь от корня проекта (`.claude/skills/<имя>/…`) в плагине не работает — файлы лежат в кэше.

Claude Code подставляет в тексте `SKILL.md` и `${CLAUDE_PLUGIN_ROOT}`, и `${CLAUDE_SKILL_DIR}` (каталог самого скилла — форма, которую советует документация). Но в Bash-инструменте этих переменных нет (`echo $CLAUDE_PLUGIN_ROOT` пуст), а Codex оставляет обе литералом. Для пакета, который едет в оба хоста, переносим только путь от каталога скилла — оба хоста в него переходят.

---

## Hooks — 13 событий, 3 типа

### События

| Событие | Когда | Применение |
|---------|-------|-----------|
| **PreToolUse** | Перед действием AI | Блокировать опасные операции |
| **PostToolUse** | После действия AI | Линтер, форматирование |
| **PostToolUseFailure** | После провала действия | Обработка ошибок |
| **PermissionRequest** | При запросе разрешения | Кастомная логика доступа |
| **UserPromptSubmit** | При отправке сообщения | Напомнить про скиллы (~84% активация) |
| **Notification** | При нотификации | Интеграции |
| **Stop** | AI завершает ответ | Проверка: тесты? CLAUDE.md? |
| **SubagentStart** | Запуск субагента | Логирование, контекст |
| **SubagentStop** | Остановка субагента | Валидация результата |
| **SessionStart** | Начало сессии | Инициализация, загрузка состояния |
| **SessionEnd** | Конец сессии | Сохранение прогресса |
| **TeammateIdle** | Teammate засыпает (Agent Teams) | Координация команды |
| **TaskCompleted** | Задача завершена | Верификация |
| **PreCompact** | Перед compact истории | Сохранение критичного контекста |

### Типы хуков

| Тип | Что делает | Когда использовать |
|-----|-----------|-------------------|
| **command** | Shell-команда/скрипт | Линтеры, форматирование, простые проверки |
| **prompt** | LLM-оценка (через `$ARGUMENTS`) | Сложная валидация, не формализуемая скриптом |
| **agent** | Агентный верификатор с инструментами | Комплексные проверки (code review, compliance) |

### Конфигурация

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh",
        "timeout": 10
      }]
    }]
  }
}

```

Расположение: `hooks/hooks.json` в плагине, или inline в `plugin.json`, или `settings.json` (standalone).

---

## Маркетплейсы и дистрибуция

### Как работает

Маркетплейс = каталог плагинов (Git-репо с `.claude-plugin/marketplace.json`). Два шага: подключить маркетплейс → установить плагины из него.

Дистрибуция Git-based, не NPM. Децентрализованная — любой Git-репо может быть маркетплейсом.

### Источники плагинов

| Тип | Описание |
|-----|---------|
| **Relative path** | Копируется рекурсивно |
| **GitHub** | `owner/repo` shorthand |
| **Git URL** | Любой https/ssh, включая GitLab, Bitbucket, self-hosted |
| **npm** | npm-пакет |
| **pip** | pip-пакет |
| **URL** | Прямая ссылка на `marketplace.json` |

Поддержка веток/тегов: `owner/repo#branch`, SHA-пиннинг.

### Установка

```bash
# CLI
claude plugin install <name>@<marketplace>
claude plugin install <name> --scope project

# Интерактивно
/plugin                            # менеджер плагинов
/plugin marketplace add owner/repo  # подключить маркетплейс
```

### Scopes установки

| Scope | Файл | Для чего |
|-------|------|---------|
| `user` (default) | `~/.claude/settings.json` | Все проекты пользователя |
| `project` | `.claude/settings.json` | Команда (коммитится в git) |
| `local` | `.claude/settings.local.json` | Проект, в .gitignore |
| `managed` | `managed-settings.json` | Read-only, admin-controlled |

**Auto-updates.** Официальные маркетплейсы Anthropic — включены по умолчанию; **сторонние и локальные — выключены по умолчанию**. Включаются у каждого пользователя в `/plugin` → Marketplaces → Enable auto-update либо записью `"autoUpdate": true` в `extraKnownMarketplaces`. Документация называет для этой записи managed settings, но проверено: в пользовательских настройках флаг тоже работает — плагин обновился фоном через ~7 минут после старта сессии. Проверка идёт в фоне после старта сессии со случайной задержкой до 10 минут; текущая сессия остаётся на загруженной версии, новая подхватывается через `/reload-plugins` или при следующем запуске. Отключение: `DISABLE_AUTOUPDATER`; оставить обновление плагинов при выключенном обновлении Claude Code — `FORCE_AUTOUPDATE_PLUGINS=1`.

**Версия решает, будет ли обновление.** Если в `plugin.json` задан `version`, пользователи получают обновление только после его повышения; без `version` версия берётся из следующего источника (запись маркетплейса, коммит).

**Командный маркетплейс.** `extraKnownMarketplaces` в `.claude/settings.json` проекта добавляет маркетплейс после доверия к папке. Плагины из внешних источников (GitHub, npm), включённые только через `enabledPlugins` проекта, сами не ставятся: Claude Code показывает команду `claude plugin install`, и человек выполняет её сам.

### Синхронизация с claude.ai

Второй канал дистрибуции, без маркетплейса. Плагины, включённые для аккаунта claude.ai, в том числе организацией для своих участников, Claude Code скачивает в `~/.claude/plugins/synced/` и грузит как `<name>@synced`: скиллы, агенты, хуки, MCP и LSP. В Cowork и облачных сессиях — при старте сессии; в терминале — фоновой проверкой при каждом запуске (нужна недавняя версия Claude Code и вход через claude.ai). Обновления приезжают при следующей синхронизации. Организация может пометить плагин обязательным — пользователь не сможет его отключить. Одноимённый плагин из другого источника имеет приоритет над синхронизированным. Отключить синхронизацию на машине — `syncClaudeAiPlugins: false`. Источник — [Plugins reference: synced plugins](https://code.claude.com/docs/en/plugins-reference#synced-plugins).

---

## Официальные маркетплейсы

### anthropics/claude-plugins-official

Встроен по умолчанию. Актуальный каталог: [GitHub](https://github.com/anthropics/claude-plugins-official). Категории:

- **Code intelligence (LSP):** языковые серверы (pyright, gopls, rust-analyzer, typescript и др.) — real-time диагностика + навигация
- **Внешние интеграции (MCP):** GitHub, GitLab, Atlassian, Asana, Linear, Notion, Figma, Vercel, Firebase, Supabase, Slack, Sentry и др.
- **Dev workflows:** code-review, pr-review-toolkit, plugin-dev, feature-dev, security-guidance, hookify и др.
- **Другое:** playground (интерактивные HTML-интерфейсы), output styles

### anthropics/knowledge-work-plugins

Для knowledge workers (Cowork + Claude Code). Все Apache-2.0. Покрывают отрасли: productivity, sales, customer support, product management, marketing, legal, finance, data, enterprise search, bio-research, design, engineering, HR, operations + partner-built плагины. Актуальный каталог: [GitHub](https://github.com/anthropics/knowledge-work-plugins).

Примечательные:
- **productivity** — задачи, календари, workflows (Slack, Notion, Asana, Linear, Jira, Microsoft 365)
- **sales** — prospect research, pipeline (HubSpot, Close, Clay, ZoomInfo)
- **data** — SQL, визуализация (Snowflake, Databricks, BigQuery, Hex)
- **enterprise-search** — поиск по email, chat, docs, wikis
- **cowork-plugin-management** — создание плагинов изнутри Cowork

### Сторонние маркетплейсы и community

Растущая экосистема — community-каталоги, курированные списки, веб-агрегаторы:

- [awesome-claude-plugins](https://github.com/quemsah/awesome-claude-plugins) — автоматический сбор метрик adoption
- [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) — курированный список расширений
- [claudemarketplaces.com](https://claudemarketplaces.com) — веб-каталог маркетплейсов

---

## Портабельность и конвергенция форматов

> **Быстро устаревает.** Ситуация с совместимостью меняется ежемесячно. Перед принятием продуктовых решений — перепроверять актуальное состояние. Снимок: сентябрь 2026.

### Тренд: от фрагментации к стандартам

Экосистема AI-агентов движется к конвергенции, но неравномерно. Четыре волны стандартизации:

1. **LSP** (Language Server Protocol) — стандартизирован давно (Microsoft), универсален. Закрытый вопрос.
2. **MCP** (Model Context Protocol) — стандартизирован (Anthropic, 2024-2025), принят повсеместно. Фактически закрытый вопрос.
3. **Skills** (Agent Skills, SKILL.md) — стандарт опубликован (Anthropic, декабрь 2025), быстро набирает adoption. Процесс идёт.
4. **Обёртка** (папка плагина + манифест) — [Agent Plugins 1.0](agent-plugins-standard.md), август 2026: Amazon/AWS, Cursor, Microsoft и GitHub, OpenAI, Vercel. Стандартизирует ровно упаковку и discovery двух компонентов — скиллов и MCP.

**Hooks, commands, agents** — по-прежнему зона фрагментации, и Agent Plugins 1.0 её закрепляет: они явно оставлены вне scope как клиентские. Все крупные инструменты (Cursor, Copilot, Cline, Windsurf) внедрили свои lifecycle hooks, но форматы несовместимы. Концепция одна, реализации разные.

**Обёртка перестала быть спецификой Claude Code, но формат Anthropic в стандарт не вошёл.** Agent Plugins кладёт `plugin.json` в корень с закрытой схемой, Anthropic — в `.claude-plugin/`: одно имя файла, разные схемы. Anthropic не участвует в стандарте, хотя оба его компонента — MCP и Agent Skills — созданы ею. Плагины ставятся в Claude Code через CLI-трансляцию (`npx plugins add`), при которой хуки и субагенты отбрасываются, а переживают перенос только скиллы и MCP. Детали и таблица расхождений — [agent-plugins-standard.md](agent-plugins-standard.md).

**Обратное направление работает лучше.** Codex читает `.claude-plugin/plugin.json` и `.claude-plugin/marketplace.json` как legacy-формат и грузит из них больше, чем из формата стандарта: скиллы, `.mcp.json`, `hooks/hooks.json` (только `command`, после доверия пользователя), команды — как скиллы. Один пакет в формате Claude Code обслуживает оба хоста; проверено установкой. Ограничения и детали — [codex-plugins.md](codex-plugins.md).

### Что это значит для продукта

Ядро контента (Skills + MCP-коннекторы) — на открытых стандартах, портабельно. Автоматика (hooks, commands) — переписывается, потому что это обёртка, а не экспертиза. Клиент не залочен на одну платформу: ценность в содержании Skills, не в формате доставки.

### Claude Code ↔ Cowork ↔ Desktop

Формат плагинов **идентичен**. "Built for Cowork, also compatible with Claude Code" (Anthropic). Хуки работают во всех трёх средах — с оговорками ниже.

**Хуки плагина работают. Замер 09.09.2026** — зонд на все 10 событий, стенд [runtime-probe](https://github.com/JazzShapka/runtime-probe).

| Событие | Cowork cloud | Desktop, режим Code |
|---|---|---|
| `SessionStart` | 🔴 не эмитится | ✅ |
| `UserPromptSubmit` | ✅ | ✅ |
| `PreToolUse` / `PostToolUse` (Bash и Agent) | ✅ | ✅ |
| `Stop`, `SubagentStart`, `SubagentStop` | ✅ | ✅ |
| `SessionEnd` | ⚪️ | ✅ |
| `Notification` | ✅ | ⚪️ |
| `PreCompact` | ⚪️ | ⚪️ |
| `deny` / `ask` | ✅ блокирует / показывает диалог | ✅ блокирует / показывает диалог |

⚪️ — в прогоне не наблюдалось за отсутствием повода, не отказ.

**Особенности, которые меняют проектирование:**

- **Источник хуков зависит от среды.** Desktop читает и плагин, и `.claude/settings.json` открытой папки — одновременно, оба срабатывают на одно событие. В Cowork сессия живёт в песочнице (`/root`), проектная `.claude/`-обвязка туда не попадает: доехать может только плагин.
- **`SessionStart` в облачном Cowork мёртв** (в «Only on this computer» эмитится на каждом ходе: процесс Claude Code перезапускается с `--resume`, замер 19.09.2026). Доставка контекста впрыском строится на `UserPromptSubmit` — он срабатывает на каждый промпт в обоих режимах и `additionalContext` доходит до модели.
- **У Cowork два режима исполнения; контекст пространства хук доставляет только в одном (замер 19.09.2026).** В облачном плагин, хуки и скрипты исполняются в контейнере Anthropic, подключённая папка — на машине пользователя за MCP-мостом, который зовёт только модель: хук, решающий по входу вызова, работает, хук, читающий файлы пространства, выходит вхолостую, скрипт скилла работает над данными только копией в папке. В «Only on this computer» плагин и папка в одной VM, скрипты работают напрямую, а хуки исполняются на машине пользователя с `cwd` и `CLAUDE_PROJECT_DIR` на служебной папке сессии; корень надо брать из `CLAUDE_CODE_WORKSPACE_HOST_PATHS` (признак среды — `CLAUDE_CODE_IS_COWORK=1`), а bash — это `mcp__workspace__bash` с путями VM. Так сделано и проверено в svaib 0.14.5; облачный режим плагином не чинится. Среда меняется за недели — детали и дата замера в [../tools/cowork.md](../tools/cowork.md#архитектура-исполнения-два-режима-замер-19092026).
- **Модель не видит слой разрешений.** Диалог подтверждения по `ask` показывается пользователю, но в контекст агента не попадает: он сообщает «подтверждения не запрашивали» и достраивает объяснение. UI-эффекты проверяются только человеком.

**Для продукта:** enforcement на хуках переносится в клиентскую поставку, если едет плагином, не опирается на `SessionStart` и — для облачного Cowork — не читает файлы пространства: там такая логика переезжает в инструкцию агента. Гвард «блокировать опасную операцию» — это `PreToolUse` + `deny`, работает везде. Цена ставки на `SessionStart` в живом примере — [../cases/coman-os.md](../cases/coman-os.md).

---

## Enterprise-фичи

| Фича | Статус (февраль 2026) |
|------|----------------------|
| **Managed scope** | Работает. Admin устанавливает плагины read-only |
| **Project scope** | Работает. Плагины коммитятся в `.claude/settings.json` |
| **Auto-updates** | Работает. Для official — по умолчанию; для сторонних — включение пользователем или `autoUpdate` в managed settings (проверено по документации, сентябрь 2026) |
| **Internal catalogs** | Анонсировано, в разработке. Корпоративные каталоги |
| **Private marketplaces** | Анонсировано, "coming in the weeks ahead" |
| **Org-wide sharing** | Работает: синхронизация плагинов организации с claude.ai, с пометкой «обязательный» (документация, сентябрь 2026) |

---

## Best practices разработки

### Из документации Anthropic

- **Начинай standalone** — в `.claude/` для быстрой итерации. Конвертируй в плагин когда готов делиться
- **`--plugin-dir`** — для тестирования. Загружает плагин без установки
- Все пути относительные, начинаются с `./`
- `${CLAUDE_PLUGIN_ROOT}` для всех путей в скриптах и MCP
- Тестируй компоненты по одному: commands, agents, hooks отдельно
- README.md с инструкциями для пользователей
- Semantic versioning в `plugin.json`

### Из практического опыта (Pierce Lamb, community)

**Context management критичен.** Для long-horizon задач плагин должен управлять заполнением context window. Claude теряет фокус когда окно переполнено.

**State management через файлы.** Де-факто стандарт — плагин записывает файлы в key points для recovery между сессиями.

**Setup validation.** "Setup session" скрипт, который валидирует окружение перед работой. Снижает вероятность сбоя.

**CLAUDE.md — не больше 150 строк.** Выносить экспертизу в subagents (контекст) и skills (progressive disclosure), а не в монолитный CLAUDE.md.

**Стратегический human-in-the-loop.** Автоматизируй рутину, сохраняй решения за человеком. Полная автономия даёт худший результат.

---

## Кеширование и безопасность

**Кеширование:** клон маркетплейса остаётся в `~/.claude/plugins/marketplaces/<имя>` (git clone `--depth 1`, рабочее дерево целиком), а сам плагин копируется в `~/.claude/plugins/cache/<маркетплейс>/<плагин>/<версия>/`. В рабочую папку проекта не попадает ничего. Исключение — плагин с относительным путём в локальном маркетплейсе-папке и `command`-источник в режиме link: они грузятся на месте. Path traversal (`../`) не работает — внешние файлы не копируются.

**Жизненный цикл версии:** удержание старых каталогов и переключение хуков определяет хост. Совместимый формат пакета не обещает одинаковой безопасности обновления открытой сессии — [сравнение Codex и Claude Code](plugin-update-hook-paths.md).

**Обход ограничения:** Симлинки внутри плагина (`ln -s /path/to/shared ./shared`) — копируются при установке. Или: указать parent-директорию как source в marketplace.

**Sandboxing:** Отдельного sandboxing для плагинов нет — работают в рамках общей модели разрешений Claude Code. MCP-серверы, хуки и скрипты исполняются с правами пользователя.

---

## Известные issues

1. **Inline `mcpServers` в plugin.json** — документация описывает как рабочий вариант, но ранее молча игнорировался (GitHub #16143), текущее поведение не перепроверялось; надёжнее `.mcp.json` — его к тому же читает Codex
2. **Strict schema validation** молча дропает плагины с неизвестными полями (GitHub #20409) — нет ошибки, плагин просто не загружается
3. **Конфликт зарезервированных имён** с официальным маркетплейсом (GitHub #18329)
4. **LSP `Executable not found in $PATH`** — нужно установить бинарник language server отдельно

---

## Хронология

| Дата | Событие |
|------|---------|
| Октябрь 2025 | Public beta плагинов Claude Code |
| Октябрь-декабрь 2025 | SHA-пиннинг, авто-обновление, output styles, ветки/теги |
| Декабрь 2025 | Agent Skills как открытый стандарт. v4.0 Superpowers. LSP в плагинах |
| Январь 2026 | Cowork launch (12 янв). Cowork Plugins (30 янв) |
| Февраль 2026 | Agent Teams (experimental). Factory Droid совместим. Enterprise: private marketplaces, отраслевые шаблоны, новые коннекторы |
| Август 2026 | Agent Plugins 1.0 — вендор-нейтральный стандарт обёртки (Amazon/AWS, Cursor, Microsoft и GitHub, OpenAI, Vercel), без участия Anthropic |

---

## Связь с продуктом SVAIB

Product vision описывает модель подписки: клиент получает данные, мы поставляем "интеллектуальный слой". Плагин — техническая реализация:

| SVAIB продаёт | В плагине |
|--------------|----------|
| Skills (методология) | `skills/` |
| Agents (автоматизация) | `agents/` + `hooks/` |
| Онтология (структура) | CLAUDE.md + `commands/` |
| Коннекторы к данным | `.mcp.json` |

Наша `.claude/` уже plugin-compatible. Шаг до плагина: `plugin.json` + реорганизация файлов.

Подробнее о связи с продуктом: [tools/cowork.md](../tools/cowork.md) (секция "Связь с продуктом SVAIB"), [product/01_overview.md](../../product/01_overview.md).

---

## Примечательные плагины

### Playground — интерактивные HTML-интерфейсы

Из `anthropics/claude-plugins-official`. Генерирует self-contained HTML с контролами + live preview + Copy prompt. 6 шаблонов: design-playground, data-explorer, concept-map, document-critique, diff-review, code-map. Гипотеза для SVAIB: кастомные шаблоны (ревью протокола встречи, карта проекта) как часть клиентского плагина.

### Superpowers — эталонный плагин

Крупнейшая авторская библиотека. 14 скиллов: TDD, debugging, planning, code review, субагенты, git workflow. Использует все 4 механизма (Skills + Commands + Agents + Hooks). Подробнее: [skills/superpowers.md](../skills/superpowers.md).

### arscontexta — персональный Second Brain

От Heinrich (@arscontexta). Через conversational derivation engine генерирует персональную knowledge system (skill graph) из разговора. 249 связанных markdown-файлов, three-space model (self/notes/ops), 6Rs processing pipeline, 10 skills, subagent orchestration. Первая публичная реализация паттерна [Skill Graphs](../context/skill-graphs/skill-graphs.md). 6.7K лайков, 2.3M просмотров. MIT. Подробный разбор: [cases/arscontexta.md](../cases/arscontexta.md).

### Claude-mem — постоянная память

От thedotmack. Lifecycle hooks захватывают наблюдения, сжимают через AI, инжектят в будущие сессии. SQLite + Chroma vector DB. 3-слойный progressive disclosure. ~10x экономия токенов. AGPL-3.0.

---

## Источники

- [Create Plugins — Claude Code Docs](https://code.claude.com/docs/ru/plugins)
- [Plugins Reference](https://code.claude.com/docs/en/plugins-reference)
- [Discover and Install Plugins](https://code.claude.com/docs/en/discover-plugins)
- [Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [anthropics/claude-plugins-official (GitHub)](https://github.com/anthropics/claude-plugins-official)
- [anthropics/knowledge-work-plugins (GitHub)](https://github.com/anthropics/knowledge-work-plugins)
- [Cowork Plugins — Anthropic Blog](https://claude.com/blog/cowork-plugins)
- [Plugin Development Learnings — Pierce Lamb](https://pierce-lamb.medium.com/what-i-learned-while-building-a-trilogy-of-claude-code-plugins-72121823172b)

## Связанные файлы

- [codex-plugins.md](codex-plugins.md) — плагины Codex: форматы манифеста, маркетплейсы, обновление, хуки с доверием, один пакет для Codex и Claude Code
- [agent-plugins-standard.md](agent-plugins-standard.md) — Agent Plugins 1.0: спецификация вендор-нейтральной обёртки, расхождения с форматом Anthropic, механика CLI-трансляции
- [skills/!skills.md](../skills/!skills.md) — Skills как компонент плагина: формат SKILL.md, проектирование, экосистема
- [skills/superpowers.md](../skills/superpowers.md) — Superpowers: эталонный плагин, все 4 механизма
- [agents/!agents.md](../agents/!agents.md) — Агенты как компонент плагина
- [agents/mcp.md](../agents/mcp.md) — MCP как компонент плагина
- [coding/claude-code.md](../coding/claude-code.md) — Claude Code: рабочая среда, в которой плагины работают
- [tools/cowork.md](../tools/cowork.md) — Cowork: GUI-платформа с той же plugin-архитектурой
- [tools/ai-workspaces.md](../tools/ai-workspaces.md) — Обзор AI-рабочих сред
- [cases/arscontexta.md](../cases/arscontexta.md) — arscontexta: кейс Second Brain как Claude Code плагин
