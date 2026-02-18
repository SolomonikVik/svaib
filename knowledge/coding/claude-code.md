---
title: "Claude Code — AI-ассистент для разработки (CLI)"
source: "https://code.claude.com/docs"
source_type: docs
status: processed
added: 2026-01-30
updated: 2026-02-16
review_by: 2026-05-16
tags: [claude-code, tools, plugins, mcp, hooks, agents, anthropic, permissions, sandbox]
publish: false
version: 11
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

Hooks — автоматические перехватчики событий жизненного цикла Claude Code. 14 событий (PreToolUse, PostToolUse, UserPromptSubmit, Stop, SessionStart, SessionEnd, Notification, SubagentStart/Stop, PostToolUseFailure, PermissionRequest, TeammateIdle, TaskCompleted, PreCompact). Полный список событий, форматы ввода/вывода, matchers, конфигурация — в официальной документации.

**Документация:** [Hooks Guide](https://code.claude.com/docs/en/hooks-guide) (паттерны и примеры) | [Hooks Reference](https://code.claude.com/docs/en/hooks) (полная спецификация)

### Три типа хуков

| Тип | Что делает | Когда использовать |
|-----|-----------|-------------------|
| `command` | Bash/Python скрипт. stdin → проверка → stdout/exit code | Детерминированные правила: блокировать файлы, проверить формат, напомнить про скилл |
| `prompt` | LLM (Haiku по умолчанию) читает контекст, возвращает ok/not ok + reason | Проверки требующие понимания: "все задачи выполнены?", "это workaround или нормальное решение?" |
| `agent` | Субагент с доступом к файлам и инструментам, до 50 tool-use ходов | Верификация через действия: запустить тесты, проверить файлы, сравнить с ожидаемым |

**prompt и agent — ключевое обновление.** Раньше хук = "grep по словам". Теперь хук = "спроси AI, правильно ли я делаю". Prompt — одноходовая оценка (дёшево, 2-3 сек). Agent — полная проверка с инструментами (дороже, 10-60 сек).

### Экономика контекста (чего нет в документации)

Сами скрипты не засоряют контекст (живут на диске). Только stdout попадает в контекст AI, и только когда условие совпало. 20 хуков × каждое сообщение = 20 запусков скриптов, но если совпал 1 — в контекст попадает вывод только этого одного. Это экономнее CLAUDE.md, где ВСЕ правила грузятся ВСЕГДА.

**Риск накопления:** ~50-200 токенов за срабатывание. За 50 сообщений широкий grep = +5000-10000 токенов мусора. Подбирать ключевые слова точно.

**Фильтрация stdout:** скрипт должен выводить минимум — диагноз + рекомендацию, НЕ сырой лог билда. Пример хорошего вывода: "ОШИБКА: бинарники старее исходников → пересобери". Пример плохого: весь output сборки.

### Когда хук, когда скилл

- **Хук** = гардрейл: агент повторяет нежелательное действие → блокируй или напоминай. Примеры: пишет workaround вместо нормального решения, забывает пересобрать, удаляет файлы
- **Скилл** = знание: агент не понимает контекст домена → объясни. Примеры: неправильные единицы в отчёте, не знает терминологию проекта, нужна методология
- **Правило:** если ошибка повторяется 3+ раза — это кандидат на хук. Если агент не знает как правильно — это кандидат на скилл

### Практическое значение

**Для скиллов:** Хуки решают главную проблему автоматической активации. Без хуков AI "забывает" проверить скиллы (~20% успешности). Хук на UserPromptSubmit — надёжность ~84%. Подробнее: [skill-activation.md](../skills/skill-activation.md).

**Re-inject после компакции:** SessionStart с matcher `compact` — вставляет напоминания обратно в контекст после сжатия. Критично для длинных сессий.

**Защита от бесконечного цикла:** Stop-хук может пушить агента продолжать → агент останавливается → хук опять пушит. Решение: проверять поле `stop_hook_active` и пропускать если `true`.

### Stop hook — практика реализации (из опыта svaib)

**Stop хук НЕ получает текст ответа.** stdin содержит только метаданные: `{session_id, transcript_path, cwd, permission_mode, hook_event_name, stop_hook_active}`. Чтобы проверить что Claude написал — читай файл по `transcript_path`.

**Транскрипт = JSONL.** Каждая строка — JSON с полем `type`: `user`, `assistant`, `result`, `system`, `queue-operation`, `file-history-snapshot`, `progress`. Формат assistant-записи: `{"type": "assistant", "message": {"content": [{"type": "text", "text": "..."}, {"type": "tool_use", ...}]}}`. Один ход Claude = несколько JSONL-строк (text + tool_use + text).

**Ловушка: системные записи сдвигают текст от конца файла.** После assistant-сообщения и ДО запуска хука система дописывает `queue-operation` (~140 B) + `file-history-snapshot` (~1.4 KB). Если Claude вызывал инструменты — между текстом и концом файла 10-30 KB записей tool_use + result. Буфер чтения от конца должен быть достаточным (50 KB надёжно, <1 мс на SSD).

**Читать только последний ход.** При парсинге хвоста: встретил `type: "user"` → обнулить собранный текст. Тогда остаётся только текст после последнего сообщения пользователя. Без этого — ложные срабатывания на фразах из предыдущих ходов.

**Блокировка остановки:** stdout `{"decision": "block", "reason": "..."}`. Поле `reason` обязательно — попадает в контекст Claude. Тишина (exit 0, пустой stdout) = хук пропускает, Claude останавливается. Формат `decision: "block"` — для Stop и SubagentStop. Для PreToolUse другой формат: `hookSpecificOutput` с `permissionDecision`.

**Конфиг** — `.claude/settings.json` (проектный, коммитится). Пути через `$CLAUDE_PROJECT_DIR`. Timeout в секундах. Альтернатива JSON-блокировке: exit code 2 (но JSON с reason информативнее).

**Рабочий пример:** `.claude/hooks/check_deferred_actions.py` — ловит deferred-action фразы ("в следующий раз", "I'll remember for future"). Источник: собственная разработка, февраль 2026.

### Паттерны использования (community)

**1. Reminder через command-хук (UserPromptSubmit)** — напоминает про инструменты/процессы когда видит ключевые слова. Пример: grep по "depend|library|npm" → напомнить использовать Context7 MCP.

**2. Проверка качества через prompt-хук (Stop)** — LLM проверяет: "все задачи выполнены?", "нет ли workaround в коде?". Дешевле и умнее чем bash grep.

**3. Auto-continue (Stop)** — пушит Claude продолжать когда он останавливается. Важно: использовать `stop_hook_active` чтобы не зациклиться.

**4. No-fallback policy (PreToolUse)** — warning хук: если агент пишет workaround/fallback → напоминает про policy и предлагает правильный подход.

**Скилл для разработки хуков:** плагин `plugin-dev` от Anthropic содержит скилл `hook-development` — полное руководство с примерами всех событий, типов, matchers. Установка: `/plugin install plugin-dev@claude-plugins-official`. [GitHub](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/hook-development/SKILL.md). При работе с хуками — использовать этот скилл вместо ручного похода в доки.

**Управление хуками:** `/hooks` меню внутри Claude Code — просмотр активных хуков, добавление через UI, одобрение изменений. Хуки подхватываются при старте сессии (snapshot), изменения settings.json на лету не применяются.

Источники: [тред @bcherny](https://x.com/bcherny/status/2021699851499798911), @elkornacio + community discussion, февраль 2026.

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
- **Sandbox runtime** — `/sandbox` включает open-source изолированную среду ([sandbox-runtime](https://github.com/anthropic-experimental/sandbox-runtime)). File + network isolation. Меньше запросов на разрешение внутри песочницы. Windows — скоро.

### Permissions — управление разрешениями

Команда `/permissions` — настройка allow/block списков. Wildcard синтаксис для точечного контроля:

| Паттерн | Что разрешает |
|---------|--------------|
| `Bash(npm run *)` | Все npm run команды |
| `Bash(uv run *)` | Все uv run команды |
| `Edit(/docs/**)` | Редактирование всего в /docs/ |
| `WebFetch(domain:*)` | Все домены |
| `WebFetch(domain:github.com)` | Конкретный домен |

Хранение:

| Файл | Scope | Git |
|------|-------|-----|
| `.claude/settings.json` | project (команда) | да |
| `.claude/settings.local.json` | local (только я) | нет (.gitignore) |
| `~/.claude/settings.json` | global (все проекты) | нет |

Рекомендация (Boris Cherny, Anthropic): коммитить permissions в `settings.json` чтобы вся команда работала с одинаковыми настройками.

Источник: [тред @bcherny, февраль 2026](https://x.com/bcherny/status/2021699851499798911)

## Кастомизация

### Spinner verbs (CLI only)

Кастомные глаголы в спиннере вместо стандартных "Thinking...", "Analyzing...". Показываются и в анимации, и в итоге ("Pondered for 1m 6s"). Настройка в settings.json:

```json
{
  "spinnerVerbs": {
    "mode": "append",    // добавить к стандартным
    "verbs": ["Pondering", "Crafting"]
  }
}
```

`mode`: `"append"` (добавить к дефолтным) или `"replace"` (заменить полностью).

**Только CLI.** В VS Code extension не работает — у расширения свой UI-индикатор. Проверено февраль 2026.

### Output styles

`/config` → output style. Меняет КАК Claude отвечает:

| Стиль | Поведение | Когда полезно |
|-------|----------|---------------|
| **default** | Молча делает работу, показывает diff | Обычная работа |
| **explanatory** | Объясняет архитектуру, паттерны, причины по ходу работы | Разбор чужого кода, изучение нового проекта |
| **learning** | Не делает за тебя, а коучит: объясняет что и почему менять | Обучение, менторинг |
| **кастомный** | Свой стиль вывода | Любые специфические требования к формату |

Рекомендация Бориса Черного: `explanatory` при знакомстве с новой кодовой базой.

Кастомные стили можно включать в плагины (папка `outputStyles/` в плагине).

### Effort level

`/model` → выбор effort level. Контролирует сколько токенов Claude тратит на размышления:

| Уровень | Поведение | Когда |
|---------|----------|-------|
| **Low** | Минимум токенов, быстрые ответы | Тривиальные задачи, высокий объём |
| **Medium** | Баланс | Обычная работа |
| **High** | Максимум токенов, глубокое рассуждение | Сложный анализ, рефакторинг, архитектура |

Effort и thinking budget — независимые параметры. High effort без thinking = больше токенов на ответ, но без reasoning. High effort + thinking = максимальное качество.

Рекомендация Бориса Черного: High для всего, не жалеть токены — разница в качестве заметна, особенно на рефакторинге.

**В VS Code extension:** отдельной настройки effort нет. Есть выбор модели и toggle "Thinking". Через CLI — `/model`.

### Общие настройки

**37 настроек, 84 env vars.** Поле `"env"` в settings.json позволяет задать переменные окружения без wrapper-скриптов:

```json
{
  "env": {
    "SOME_VAR": "value"
  }
}
```

Рекомендация: коммитить settings.json в git чтобы команда работала с одинаковой конфигурацией.

Источник: [тред @bcherny, февраль 2026](https://x.com/bcherny/status/2021699851499798911). [Доки по настройкам](https://code.claude.com/docs/en/settings).

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

- **plugins/** — Плагины как формат и экосистема: спецификация, маркетплейсы, best practices, enterprise-фичи. См. [!plugins.md](../plugins/!plugins.md)
- **skills/** — Skills как часть экосистемы Claude Code. Формат SKILL.md, паттерны проектирования. См. [!skills.md](../skills/!skills.md)
- **agents/** — Субагенты Claude Code. См. [!agents.md](../agents/!agents.md)
- **Superpowers** — крупнейший плагин, эталонный пример. См. [skills/superpowers.md](../skills/superpowers.md)
- **Cowork** — Anthropic перенёс ту же plugin-архитектуру в GUI для knowledge workers (sales, legal, finance). Формат плагинов идентичен. См. [tools/cowork.md](../tools/cowork.md)
- **Механика поиска Claude Code** — как Claude Code ищет файлы (агентный grep без индекса, двухмодельная архитектура, сравнение с Cursor и Claude Projects). См. [context/search-mechanics.md](../context/search-mechanics.md)

## Источники

- [Plugins Reference — Claude Code Docs](https://code.claude.com/docs/en/plugins-reference)
- [Discover and Install Plugins](https://code.claude.com/docs/en/discover-plugins)
- [Claude Code Plugins Announcement (Oct 2025)](https://claude.com/blog/claude-code-plugins)
- [anthropics/claude-plugins-official (GitHub)](https://github.com/anthropics/claude-plugins-official)
- [Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)
