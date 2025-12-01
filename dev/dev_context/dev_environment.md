---
title: "Среда разработки svaib"
updated: 2025-11-26
version: 1
scope: "development"
priority: high
---

# Среда разработки svaib

## Кратко

Описание среды разработки проекта: VS Code + Claude Code Extension, MCP-серверы (n8n, supabase, context7) для доступа к внешним сервисам, субагенты для автономных задач, промпты ролей и скиллы. Механизмы и когда что использовать.

---

## Основной стек

| Компонент | Инструмент |
|-----------|------------|
| IDE | VS Code |
| AI-ассистент | Claude Code Extension |
| Авторизация | Claude Max подписка |
| Актуальные данные | MCP-серверы |
| Специалисты | Субагенты, промпты |

---

## Команда разработки

| Кто | Что делает | Механизм | Где лежит |
|-----|------------|----------|-----------|
| **n8n-expert** | Workflow, webhooks, интеграции | Субагент + MCP n8n | `.claude/agents/` |
| **supabase-expert** | БД, таблицы, RLS, миграции | Субагент + MCP supabase | `.claude/agents/` |
| **CTO** | Архитектура, приоритеты, координация | Промпт | `dev/prompts/` |

---

## Механизмы

| Механизм | Что это | Когда использовать | Где лежит |
|----------|---------|-------------------|-----------|
| **MCP** | Доступ к сервисам + актуальные данные | Нужен доступ к n8n, Supabase, документации | `.mcp.json` |
| **Субагент** | AI с изолированным контекстом | Специалист для автономной работы | `.claude/agents/` |
| **Промпт** | Роль без изоляции | Диалог в основном треде | `dev/prompts/` |
| **Скилл** | Инструкции + скрипты для повторяемых задач | Одна и та же процедура много раз | `.claude/skills/` |

### Принцип различия

- **MCP** = инструменты + данные (что использовать)
- **Субагент** = AI-специалист с изоляцией (кто делает автономно)
- **Промпт** = роль без изоляции (кто обсуждает)
- **Скилл** = процедура (как делать повторяемое, не AI)

---

## MCP-серверы

MCP (Model Context Protocol) — подключение AI к внешним сервисам.

| MCP | Что делает |
|-----|------------|
| **n8n-mcp** | Создаёт/редактирует workflow, валидирует, документация нод |
| **supabase-mcp** | Таблицы, миграции, SQL, управление схемой |
| **context7** | Актуальная документация библиотек (`use context7`) |

**Конфигурация:** `.mcp.json` (корень проекта)

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "N8N_API_URL": "https://n8n.svaib.com",
        "N8N_API_KEY": "${N8N_API_KEY}"
      }
    },
    "supabase": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp?project_ref=${SUPABASE_PROJECT_REF}",
      "headers": {
        "Authorization": "Bearer ${SUPABASE_ACCESS_TOKEN}"
      }
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

---

## Субагенты

AI-специалисты с изолированным контекстом. Claude делегирует им задачи автоматически или по запросу.

**Расположение:** `.claude/agents/*.md`

**Вызов:**
```
# Автоматически — Claude решает по description
> "Создай workflow для транскрибации"

# Явно
> "Используй n8n-expert для создания webhook"

# Список
> /agents
```

### Формат файла субагента

```markdown
---
name: n8n-expert
description: "Создание n8n workflow. Используй для любых задач с workflow, webhooks, интеграциями."
tools: Read, Write, Edit, Bash
model: sonnet
---

Ты n8n-разработчик проекта svaib.

## Контекст
Прочитай: dev/dev_context/svaib_architecture.md

## Правила
- Используй MCP n8n-mcp для документации и API
- Валидируй workflow перед деплоем
```

**Поля frontmatter:**
- `name` — имя (обязательно)
- `description` — когда использовать (обязательно, это главный триггер)
- `tools` — доступные инструменты через запятую (опционально, по умолчанию все)
- `model` — модель: sonnet, opus, haiku (опционально)

**Документация:** https://docs.claude.com/en/docs/claude-code/sub-agents

---

## Скиллы

Папки с инструкциями и скриптами для повторяемых задач. Claude загружает автоматически по контексту.

**Расположение:** `.claude/skills/`

**Работают:** Claude Code, Claude.ai, API

### Структура

```
skill-name/
├── SKILL.md           ← инструкции + YAML frontmatter (обязательно)
├── scripts/           ← исполняемый код
├── references/        ← документация
└── assets/            ← шаблоны, файлы для вывода
```

**Документация:** https://support.claude.com/en/articles/12512176-what-are-skills

---

## Структура файлов проекта

```
.claude/
├── agents/          ← субагенты
└── skills/          ← скиллы

.mcp.json            ← MCP-серверы

dev/
├── prompts/         ← промпты ролей
└── dev_context/     ← документация

CLAUDE.md            ← общие правила проекта
```

---

## Ссылки

| Что | Документация |
|-----|--------------|
| Claude Code | https://docs.claude.com/en/docs/claude-code/overview |
| MCP | https://docs.claude.com/en/docs/mcp |
| Субагенты | https://docs.claude.com/en/docs/claude-code/sub-agents |
| Скиллы | https://support.claude.com/en/articles/12512176-what-are-skills |
| n8n-mcp | https://github.com/czlonkowski/n8n-mcp |
| supabase-mcp | https://supabase.com/docs/guides/getting-started/mcp |
| context7 | https://github.com/upstash/context7 |