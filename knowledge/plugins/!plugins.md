---
title: "Plugins — система расширения AI-агентов: формат, экосистема, best practices"
status: processed
added: 2026-02-13
updated: 2026-02-13
review_by: 2026-05-13
tags: [plugins, claude-code, cowork, marketplace, ecosystem, svaib-product]
publish: false
version: 1
---

# Plugins — система расширения AI-агентов

## Кратко

Плагин — пакет для распространения AI-расширений: Skills + Commands + Agents + Hooks + MCP + LSP. Всё файловое (Markdown + JSON), zero code, zero build steps. Единый формат для Claude Code (CLI, разработчики) и Cowork (GUI, knowledge workers). Public beta с октября 2025. Экосистема: 28 плагинов в official marketplace, 11 knowledge-work плагинов для Cowork, community-маркетплейсы. Cross-platform: совместим с Factory Droid, OpenAI Codex, 40+ агентов через Agent Skills стандарт. Для SVAIB: плагин — готовый delivery mechanism для модели подписки "Skills + Agents + Онтология".

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

### Переменные окружения

`${CLAUDE_PLUGIN_ROOT}` — абсолютный путь к директории плагина. Использовать в хуках, MCP, скриптах — пути корректны независимо от места установки.

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

**Auto-updates:** Для official marketplace — по умолчанию включены. При обновлении — нотификация о рестарте. Отключение: `DISABLE_AUTOUPDATER=true`.

---

## Официальные маркетплейсы

### anthropics/claude-plugins-official (28 плагинов)

Встроен по умолчанию. Категории:

**Code intelligence (11 LSP):** clangd, csharp, gopls, jdtls, kotlin, lua, php, pyright, rust-analyzer, swift, typescript. Дают Claude real-time диагностику + навигацию по коду. Требуют бинарник language server на машине.

**Внешние интеграции (MCP):** github, gitlab, atlassian (Jira/Confluence), asana, linear, notion, figma, vercel, firebase, supabase, slack, sentry.

**Dev workflows:** commit-commands, pr-review-toolkit, agent-sdk-dev, plugin-dev, feature-dev, code-review, code-simplifier, claude-code-setup, claude-md-management, security-guidance, hookify.

**Другое:** playground (интерактивные HTML-интерфейсы), ralph-loop, output styles (explanatory, learning).

### anthropics/knowledge-work-plugins (11 плагинов для Cowork)

Все Apache-2.0. Для knowledge workers.

| Плагин | Назначение | Коннекторы |
|--------|-----------|------------|
| **productivity** | Задачи, календари, workflows | Slack, Notion, Asana, Linear, Jira, Monday, ClickUp, Microsoft 365 |
| **sales** | Prospect research, call prep, pipeline | Slack, HubSpot, Close, Clay, ZoomInfo, Fireflies |
| **customer-support** | Тикеты, эскалации, KB | Slack, Intercom, HubSpot, Guru, Jira |
| **product-management** | Спеки, roadmaps, research | Slack, Linear, Asana, Figma, Amplitude, Pendo |
| **marketing** | Контент, кампании, brand voice | Slack, Canva, Figma, HubSpot, Ahrefs, Klaviyo |
| **legal** | Контракты, NDA, compliance | Slack, Box, Egnyte, Jira |
| **finance** | Journal entries, reconciliation | Snowflake, Databricks, BigQuery |
| **data** | SQL, визуализация, дашборды | Snowflake, Databricks, BigQuery, Hex, Amplitude |
| **enterprise-search** | Поиск по email, chat, docs, wikis | Slack, Notion, Guru, Jira, Asana |
| **bio-research** | Литература, геномика | PubMed, bioRxiv, ClinicalTrials.gov, ChEMBL |
| **cowork-plugin-management** | Создание и кастомизация плагинов | — |

### Сторонние маркетплейсы и community

| Ресурс | Что это |
|--------|---------|
| **[awesome-claude-plugins](https://github.com/quemsah/awesome-claude-plugins)** | Автоматический сбор метрик adoption с GitHub |
| **[awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)** | Курированный список: skills, hooks, commands, agents, plugins |
| **[claudemarketplaces.com](https://claudemarketplaces.com)** | Веб-каталог маркетплейсов |
| **[claude-tools](https://paddo.dev/blog/claude-tools-plugin-marketplace/)** | Маркетплейс специализированных external capabilities |
| **Community marketplaces** | 87+ плагинов в community-built каталогах |

---

## Портабельность и конвергенция форматов

> **Быстро устаревает.** Ситуация с совместимостью меняется ежемесячно. Перед принятием продуктовых решений — перепроверять актуальное состояние. Снимок: февраль 2026.

### Тренд: от фрагментации к стандартам

Экосистема AI-агентов движется к конвергенции, но неравномерно. Три волны стандартизации:

1. **LSP** (Language Server Protocol) — стандартизирован давно (Microsoft), универсален. Закрытый вопрос.
2. **MCP** (Model Context Protocol) — стандартизирован (Anthropic, 2024-2025), принят повсеместно. Фактически закрытый вопрос.
3. **Skills** (Agent Skills, SKILL.md) — стандарт опубликован (Anthropic, декабрь 2025), быстро набирает adoption. Процесс идёт.

**Hooks, commands, agents** — пока зона фрагментации. Все крупные инструменты (Cursor, Copilot, Cline, Windsurf) внедрили свои lifecycle hooks, но форматы несовместимы. Концепция одна, реализации разные. Стандарта нет. Конвергенция возможна, но не произошла.

**Обёртка** (plugin.json, маркетплейсы, namespace) — специфика Claude Code. Другие инструменты начинают копировать подход (Factory Droid полностью совместим), но это пока не стандарт.

### Что это значит для продукта

Ядро контента (Skills + MCP-коннекторы) — на открытых стандартах, портабельно. Автоматика (hooks, commands) — переписывается, потому что это обёртка, а не экспертиза. Клиент не залочен на одну платформу: ценность в содержании Skills, не в формате доставки.

### Claude Code ↔ Cowork

Формат плагинов **идентичен**. "Built for Cowork, also compatible with Claude Code" (Anthropic). Один плагин — работает в обоих.

---

## Enterprise-фичи

| Фича | Статус (февраль 2026) |
|------|----------------------|
| **Managed scope** | Работает. Admin устанавливает плагины read-only |
| **Project scope** | Работает. Плагины коммитятся в `.claude/settings.json` |
| **Auto-updates** | Работает. Для official — по умолчанию |
| **Internal catalogs** | Анонсировано, в разработке. Корпоративные каталоги |
| **Private marketplaces** | Анонсировано, "coming in the weeks ahead" |
| **Org-wide sharing** | Анонсировано, в разработке |

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

**Кеширование:** Claude Code копирует файлы плагина в кеш-директорию, не запускает in-place. Path traversal (`../`) не работает — внешние файлы не копируются.

**Обход ограничения:** Симлинки внутри плагина (`ln -s /path/to/shared ./shared`) — копируются при установке. Или: указать parent-директорию как source в marketplace.

**Sandboxing:** Отдельного sandboxing для плагинов нет — работают в рамках общей модели разрешений Claude Code. MCP-серверы, хуки и скрипты исполняются с правами пользователя.

---

## Известные issues

1. **Inline `mcpServers` в plugin.json** молча игнорируются (GitHub #16143) — обходить через `.mcp.json` файл
2. **Strict schema validation** молча дропает плагины с неизвестными полями (GitHub #20409) — нет ошибки, плагин просто не загружается
3. **Конфликт зарезервированных имён** с официальным маркетплейсом (GitHub #18329)
4. **LSP `Executable not found in $PATH`** — нужно установить бинарник language server отдельно

---

## Хронология

| Дата | Событие |
|------|---------|
| Октябрь 2025 | Public beta плагинов Claude Code, 36+ плагинов |
| Октябрь-декабрь 2025 | SHA-пиннинг, авто-обновление, output styles, ветки/теги |
| Декабрь 2025 | Agent Skills как открытый стандарт. v4.0 Superpowers. LSP в плагинах |
| Январь 2026 | Cowork launch (12 янв). Cowork Plugins (30 янв). 28 плагинов в official |
| Февраль 2026 | Agent Teams (experimental). Community 87+ плагинов. Factory Droid совместим |

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

Подробнее о связи с продуктом: [tools/cowork.md](../tools/cowork.md) (секция "Связь с продуктом SVAIB"), [meta/meta_context/product_vision.md](../../meta/meta_context/product_vision.md).

---

## Примечательные плагины

### Playground — интерактивные HTML-интерфейсы

Из `anthropics/claude-plugins-official`. Генерирует self-contained HTML с контролами + live preview + Copy prompt. 6 шаблонов: design-playground, data-explorer, concept-map, document-critique, diff-review, code-map. Гипотеза для SVAIB: кастомные шаблоны (ревью протокола встречи, карта проекта) как часть клиентского плагина.

### Superpowers — эталонный плагин

Крупнейшая авторская библиотека. 14 скиллов: TDD, debugging, planning, code review, субагенты, git workflow. Использует все 4 механизма (Skills + Commands + Agents + Hooks). Подробнее: [skills/superpowers.md](../skills/superpowers.md).

### Claude-mem — постоянная память

От thedotmack. Lifecycle hooks захватывают наблюдения, сжимают через AI, инжектят в будущие сессии. SQLite + Chroma vector DB. 3-слойный progressive disclosure. ~10x экономия токенов. AGPL-3.0.

---

## Источники

- [Create Plugins — Claude Code Docs](https://code.claude.com/docs/en/plugins)
- [Plugins Reference](https://code.claude.com/docs/en/plugins-reference)
- [Discover and Install Plugins](https://code.claude.com/docs/en/discover-plugins)
- [Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [anthropics/claude-plugins-official (GitHub)](https://github.com/anthropics/claude-plugins-official)
- [anthropics/knowledge-work-plugins (GitHub)](https://github.com/anthropics/knowledge-work-plugins)
- [Cowork Plugins — Anthropic Blog](https://claude.com/blog/cowork-plugins)
- [Plugin Development Learnings — Pierce Lamb](https://pierce-lamb.medium.com/what-i-learned-while-building-a-trilogy-of-claude-code-plugins-72121823172b)

## Связанные файлы

- [skills/!skills.md](../skills/!skills.md) — Skills как компонент плагина: формат SKILL.md, проектирование, экосистема
- [skills/superpowers.md](../skills/superpowers.md) — Superpowers: эталонный плагин, все 4 механизма
- [agents/!agents.md](../agents/!agents.md) — Агенты как компонент плагина
- [agents/mcp.md](../agents/mcp.md) — MCP как компонент плагина
- [coding/claude-code.md](../coding/claude-code.md) — Claude Code: рабочая среда, в которой плагины работают
- [tools/cowork.md](../tools/cowork.md) — Cowork: GUI-платформа с той же plugin-архитектурой
- [tools/ai-workspaces.md](../tools/ai-workspaces.md) — Обзор AI-рабочих сред
