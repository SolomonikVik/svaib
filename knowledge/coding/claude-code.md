---
title: "Claude Code — AI-ассистент для разработки (CLI)"
source: "https://code.claude.com/docs"
source_type: docs
status: processed
added: 2026-01-30
updated: 2026-02-11
review_by: 2026-04-30
tags: [claude-code, tools, plugins, mcp, hooks, agents, anthropic]
publish: false
version: 7
---

# Claude Code — AI-ассистент для разработки

## Кратко

Claude Code — CLI-инструмент Anthropic для AI-assisted разработки. Работает в терминале и IDE (VS Code, JetBrains). Расширяется через систему плагинов (Skills + Commands + Agents + Hooks + MCP + LSP). Ключевой инструмент проекта SVAIB — мы работаем внутри него каждый день. Public beta плагинов — с октября 2025. Текущая версия: v2.1.x (январь 2026).

## Система расширения Claude Code

Claude Code расширяется через 6 механизмов. Они могут использоваться отдельно или объединяться в плагины.

### Механизмы расширения

| Механизм | Что делает | Файлы | Расположение |
|----------|-----------|-------|-------------|
| **Skills** | AI-инструкции, активируемые по триггеру | `SKILL.md` в папках | `skills/` |
| **Commands** | Слэш-команды, вызываемые пользователем | `.md` файлы | `commands/` или `.claude/commands/` |
| **Agents** | Субагенты для изолированных подзадач | `.md` файлы | `agents/` или `.claude/agents/` |
| **Hooks** | Обработчики событий жизненного цикла | `hooks.json` + скрипты | `hooks/` |
| **MCP Servers** | Подключение к внешним сервисам (Model Context Protocol) | `.mcp.json` | корень проекта |
| **LSP Servers** | Code intelligence (Language Server Protocol) | `.lsp.json` | корень проекта |

**Связь:** Skills — подробнее в [knowledge/skills/!skills.md](../skills/!skills.md). Agents — в [knowledge/agents/!agents.md](../agents/!agents.md).

### Без плагина (встроенные в проект)

Можно использовать все механизмы без создания плагина — просто положить файлы в `.claude/` проекта:
- `.claude/commands/` — слэш-команды
- `.claude/agents/` — субагенты
- `.claude/settings.json` — настройки проекта (включая ссылки на плагины)
- `CLAUDE.md` — системные инструкции для AI

Это то, как мы работаем в SVAIB сейчас: `/svaib-knowledge`, `/svaib-dev` и т.д. — это commands без плагина.

### Плагин (пакет для распространения)

Плагин = пакет, объединяющий несколько механизмов для распространения.

**Структура плагина:**
```
my-plugin/
├── .claude-plugin/
│   └── plugin.json           # ОБЯЗАТЕЛЬНО: манифест
├── skills/                    # Skills (папки с SKILL.md)
├── commands/                  # Слэш-команды
├── agents/                    # Субагенты
├── hooks/
│   └── hooks.json             # Конфигурация хуков
├── .mcp.json                  # MCP серверы
├── .lsp.json                  # LSP серверы
├── README.md
└── LICENSE
```

**Критическое правило:** Все компоненты ДОЛЖНЫ быть в корне плагина, НЕ внутри `.claude-plugin/`. Внутри `.claude-plugin/` — только `plugin.json`.

**Манифест (`plugin.json`):**
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What this plugin does",
  "author": { "name": "...", "email": "..." },
  "keywords": ["tag1", "tag2"]
}
```

Обязательное поле — только `name`. Всё остальное опционально. Кастомные пути к компонентам через поля `commands`, `agents`, `skills`, `hooks`, `mcpServers`, `lspServers` — дополняют дефолтные директории, не заменяют.

**Переменные окружения:** `${CLAUDE_PLUGIN_ROOT}` — абсолютный путь к директории плагина (для скриптов, хуков, MCP).

## Установка и распространение плагинов

### Установка

```bash
# Через CLI
claude plugin install <plugin-name>@<marketplace>
claude plugin install <plugin> --scope project   # для проекта
claude plugin uninstall <plugin>
claude plugin update <plugin>

# Через UI
/plugin   # внутри Claude Code — менеджер плагинов
```

### Маркетплейсы

| Маркетплейс | Описание |
|------------|----------|
| **anthropics/claude-plugins-official** | Официальный, 53 плагина (январь 2026). Встроен по умолчанию |
| **anthropics/skills** | Skills-маркетплейс. Reference implementation стандарта Agent Skills (декабрь 2025). Скиллы для документов, creative, enterprise. Детали: [!skills.md](../skills/!skills.md) |
| **anthropics/life-sciences** | Плагины для life sciences |
| Сторонние | Любой Git-репо с `.claude-plugin/marketplace.json` |

Подключить сторонний: `/plugin marketplace add user-or-org/repo-name`

**Распространение** — Git-based, не NPM. Децентрализованные маркетплейсы (любой Git-репо). Поддержка веток/тегов (`owner/repo#branch`), пиннинг по SHA коммита.

### Scope установки

| Scope | Файл | Когда |
|-------|------|-------|
| `user` (default) | `~/.claude/settings.json` | Личные, для всех проектов |
| `project` | `.claude/settings.json` | Для команды, коммитится в git |
| `local` | `.claude/settings.local.json` | Для проекта, в .gitignore |
| `managed` | `managed-settings.json` | Только чтение |

**Для команды:** добавить плагины в `.claude/settings.json` → коммитнуть → коллеги доверяют папке → плагины устанавливаются автоматически.

## Hooks — обработчики событий

Hooks — автоматические перехватчики событий жизненного цикла Claude Code. Запускают скрипты (Python/Bash) при наступлении событий. Скрипт может разрешить, заблокировать действие или показать предупреждение.

### События

| Событие | Когда срабатывает | Пример применения |
|---------|------------------|-------------------|
| **PreToolUse** | Перед каждым действием AI (запись файла, bash и т.д.) | Блокировать удаление файлов, проверить опасные команды |
| **PostToolUse** | После каждого действия AI | Проверить линтером созданный файл |
| **UserPromptSubmit** | При отправке сообщения пользователем | Напомнить AI про список скиллов (повышает активацию с ~20% до ~84%, см. [skill-activation.md](../skills/skill-activation.md)) |
| **Stop** | Когда AI заканчивает ответ | Проверить: обновлены ли тесты? Не сломан ли CLAUDE.md? |
| **SessionStart** | При запуске сессии | Загрузить состояние проекта, инициализация |
| **SessionEnd** | При завершении сессии | Сохранить прогресс |

### Где конфигурировать

| Расположение | Для чего |
|-------------|----------|
| `.claude/settings.json` (проект) | Хуки проекта, коммитятся в git |
| `~/.claude/settings.json` (глобально) | Хуки для всех проектов |
| `hooks/hooks.json` (в плагине) | Приходят вместе с плагином |

### Формат конфигурации

В `settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/pretooluse.py",
        "timeout": 10
      }]
    }]
  }
}
```

В `hooks/hooks.json` плагина — аналогичный формат.

### Ответ скрипта

Скрипт получает JSON на stdin (контекст события) и возвращает JSON:
- `{"decision": "approve"}` — продолжить
- `{"decision": "block", "reason": "..."}` — заблокировать действие
- Текстовое сообщение — показать AI как предупреждение

### Практическое значение

**Для скиллов:** Хуки решают главную проблему автоматической активации скиллов. Без хуков AI "забывает" проверить скиллы (~20% успешности). Хук на UserPromptSubmit напоминает при каждом сообщении — надёжность вырастает до ~84%. Подробнее: [skill-activation.md](../skills/skill-activation.md).

**Для безопасности:** PreToolUse может блокировать запись в .env, удаление файлов, опасные bash-команды.

**Для качества:** PostToolUse и Stop могут проверять форматирование, запускать тесты, валидировать изменения.

## Agents — субагенты

Субагенты — изолированные AI-агенты для подзадач. Создание/управление: `/agents`. Файл: `.claude/agents/name.md` (YAML frontmatter с name, description, tools, skills + system prompt в теле). Scope: project (`.claude/agents/`) или user (`~/.claude/agents/`).

**Skills в субагентах:** субагенты **НЕ наследуют skills от родителя**. Указывать явно: `skills: ["skill-name"]` в YAML. При dispatch загружается **весь SKILL.md целиком**, но progressive disclosure (bundled resources, файлы по ссылкам) **не работает** (источник: курс Anthropic, не проверено на практике). Рекомендация: для субагентных skills держать всю информацию в самом SKILL.md.

**Паттерн:** main agent делает основную работу, sub-agents (code review, testing) работают в изолированных контекстах, возвращают только результаты — context-efficient approach.

## Безопасность

- **Файловая изоляция** — macOS Seatbelt, Linux namespaces. Claude Code может работать только с разрешёнными директориями
- **Сетевая изоляция** — только одобренные серверы
- **Permission tiers** — default, plan, acceptEdits, bypassPermissions
- **Плагины кешируются** — Claude Code копирует файлы плагина в кеш-директорию (не запускает in-place). Path traversal невозможен — `../` не работает после установки
- **Отдельного sandboxing для плагинов нет** — работают в рамках общей модели разрешений Claude Code

## Известные баги (январь 2026)

1. **Inline `mcpServers` в plugin.json молча игнорируются** (GitHub #16143) — обходить через `.mcp.json` файл
2. **Strict schema validation** молча дропает плагины с неизвестными полями (GitHub #20409) — нет ошибки
3. **Конфликт зарезервированных имён** с официальным маркетплейсом (GitHub #18329)

## Agent Teams (experimental, февраль 2026)

Координация нескольких независимых сессий Claude Code как команды: leader + teammates, общий task list, прямая коммуникация между агентами. В отличие от субагентов — полностью отдельные сессии со своими контекстными окнами. Delegation mode (Shift+Tab) — лидер только координирует, не кодит. Plan approval — teammate планирует, лидер одобряет. Включение: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` в settings.json. Детали: [agent-teams.md](agent-teams.md). [Офиц. доки](https://code.claude.com/docs/en/agent-teams).

## Хронология

| Дата | Событие |
|------|---------|
| Октябрь 2025 | Public beta плагинов, 36+ плагинов в официальном маркетплейсе |
| Октябрь-декабрь 2025 | Добавлены: поиск плагинов, SHA-пиннинг, авто-обновление, output styles, поддержка веток/тегов |
| Декабрь 2025 | v4.0 Superpowers, LSP-серверы в плагинах |
| Январь 2026 | 53 плагина в официальном маркетплейсе, v2.1.x Claude Code |
| Февраль 2026 | Agent Teams (experimental) |

## Примечательные плагины

### Playground — интерактивные HTML-интерфейсы

**Плагин:** `playground` из `anthropics/claude-plugins-official`
**Установка:** `/plugin install playground@claude-plugins-official`

Генерирует self-contained HTML-файлы с интерактивными контролами, live preview и кнопкой "Copy prompt". Вместо текстового вывода — визуальный интерфейс, который пользователь крутит руками, а потом копирует результат обратно в Claude.

**6 встроенных шаблонов:**

| Шаблон | Назначение |
|--------|-----------|
| **design-playground** | Визуальные решения: цвета, отступы, тени, типографика |
| **data-explorer** | Построение запросов: SQL, API, regex |
| **concept-map** | Карты знаний, scope mapping |
| **document-critique** | Ревью документов: approve/reject/comment на каждый пункт |
| **diff-review** | Code review: построчные комментарии |
| **code-map** | Визуализация архитектуры кодовой базы |

**Как работает:** Скилл активируется когда задача визуальная, структурная или когда input space большой и текстом выразить неудобно. Claude генерирует HTML → открывается в браузере → пользователь взаимодействует → копирует промпт → Claude применяет.

**Применение для SVAIB:** Playground можно включить в клиентский плагин как визуальный слой. Кастомные шаблоны (ревью протокола встречи, карта проекта, настройка формата отчётов) создают "вау-эффект" — клиент ожидает чат, а получает интерфейс. Подробнее о клиентском применении — в [tools/cowork.md](../tools/cowork.md), секция "Связь с продуктом SVAIB".

### Claude-mem — постоянная память между сессиями

**Плагин:** `claude-mem` от thedotmack
**Установка:** `/plugin marketplace add thedotmack/claude-mem` → `/plugin install claude-mem`
**GitHub:** https://github.com/thedotmack/claude-mem

Решает context rot: автоматически захватывает наблюдения через lifecycle hooks (SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd), сжимает через AI, инжектит релевантный контекст в будущие сессии. SQLite + Chroma vector DB. 3-слойный progressive disclosure: search (compact index, ~50-100 токенов) → timeline (хронологический контекст) → full details (~500-1000 токенов). ~10x экономия токенов по сравнению с полной загрузкой. Web viewer на localhost:37777. AGPL-3.0. Наш опыт: ~10-15% повышение качества и точности работы агентов.

---

## Связь с другими темами

- **skills/** — Skills как часть экосистемы Claude Code. Формат SKILL.md, паттерны проектирования. См. [!skills.md](../skills/!skills.md)
- **agents/** — Субагенты Claude Code. См. [!agents.md](../agents/!agents.md)
- **Superpowers** — крупнейший плагин, эталонный пример. См. [skills/superpowers.md](../skills/superpowers.md)
- **Cowork** — Anthropic перенёс ту же plugin-архитектуру в GUI для knowledge workers (sales, legal, finance). Формат плагинов идентичен. См. [tools/cowork.md](../tools/cowork.md)

## Источники

- [Plugins Reference — Claude Code Docs](https://code.claude.com/docs/en/plugins-reference)
- [Discover and Install Plugins](https://code.claude.com/docs/en/discover-plugins)
- [Claude Code Plugins Announcement (Oct 2025)](https://claude.com/blog/claude-code-plugins)
- [anthropics/claude-plugins-official (GitHub)](https://github.com/anthropics/claude-plugins-official)
- [Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)
