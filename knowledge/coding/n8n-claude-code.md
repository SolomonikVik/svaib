---
title: "Claude Code + n8n — разработка автоматизаций через AI"
source: "https://github.com/czlonkowski/n8n-mcp"
source_type: repo
status: processed
added: 2026-02-21
updated: 2026-02-21
review_by: 2026-05-21
tags: [n8n, claude-code, mcp, automation, workflow, skills]
publish: false
version: 1
---

# Claude Code + n8n — разработка автоматизаций через AI

## Кратко

Экосистема инструментов для создания n8n-автоматизаций через Claude Code и другие AI-кодинг-ассистенты. Три направления интеграции: (1) AI строит workflow через MCP-сервер + скиллы, (2) n8n выставляет workflow как MCP-тулы для AI, (3) n8n вызывает Claude Code как инструмент внутри workflow. Доминантный community-проект — экосистема czlonkowski (n8n-mcp + n8n-skills). n8n также развивает нативные AI-фичи (AI Workflow Builder, Instance-Level MCP).

---

## Три паттерна интеграции

### Паттерн A: AI строит n8n workflow

Claude Code подключается к MCP-серверу с документацией по нодам n8n → генерирует workflow JSON → деплоит через n8n API.

**Направление:** AI → MCP Server → n8n

**Основной стек:** n8n-mcp (документация) + n8n-skills (паттерны) + supabase-mcp (БД) + context7 (актуальная документация).

### Паттерн B: n8n выставляет workflow как MCP-тулы

Instance-Level MCP (нативная фича n8n). Готовые workflow становятся инструментами, которые AI-клиент может вызывать.

**Направление:** AI ← MCP ← n8n workflow

**Применение для svaib:** автоматизации в n8n под капотом, клиент работает через Claude Code. Ложится на модель подписки "Плагин".

### Паттерн C: n8n вызывает Claude Code

n8n запускает Claude Code CLI через SSH-ноду или community-ноду с Claude Code SDK.

**Направление:** n8n workflow → SSH/SDK → Claude Code → результат

---

## Экосистема czlonkowski

**Автор:** Romuald Czlonkowski, Варшава, [AiAdvisors.pl](https://aiadvisors.pl). Опытный разработчик (671 подписчик на GitHub, множество достижений). Построил полную коммерческую экосистему вокруг n8n + AI.

### n8n-MCP — MCP-сервер с документацией n8n

**Репо:** [czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp)
Что даёт AI:
- 1236 документированных нод (806 core + 430 community)
- 2709 шаблонов workflow с метаданными
- 265 AI-capable tools с документацией
- 2646 pre-extracted конфигураций из популярных workflow
- Валидация workflow

Установка: hosted-сервис (dashboard.n8n-mcp.com, бесплатный tier — 100 запросов/день), npx, Docker, Railway.

**Важно:** Это **knowledge server** — предоставляет документацию и схемы нод. Для управления workflow (CRUD) нужен API-ключ n8n и полная конфигурация.

### n8n-skills — 7 скиллов для Claude Code

**Репо:** [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills)
| Скилл | Что делает |
|-------|-----------|
| n8n Expression Syntax | Корректные `{{}}` паттерны, переменные `$json`, `$node`, `$now`, `$env` |
| n8n MCP Tools Expert | Гайд по использованию MCP-тулов, валидация, автосанитизация |
| n8n Workflow Patterns | 5 архитектурных паттернов: webhook, HTTP API, database, AI agent, scheduled |
| n8n Validation Expert | Интерпретация ошибок валидации, отличие false positive от реальных |
| n8n Node Configuration | Зависимости свойств, 8 типов AI-соединений |
| n8n Code JavaScript | Data access паттерны, `$helpers`, production patterns |
| n8n Code Python | Стандартная библиотека (без pandas/numpy/requests) |

Установка: plugin install (`/plugin install czlonkowski/n8n-skills`), ручное копирование в `~/.claude/skills/`, или загрузка через Claude.ai Settings.

Скиллы активируются автоматически и работают вместе. Требуют Claude Pro.

### Практический workflow (Spec Driven Development)

Методология из видео "ИИшенка | AI Automation" — пошаговый подход вместо "одного промпта":

1. **Кастомная slash-команда `/create-spec`** — Claude Code генерирует спецификацию автоматизации (какие ноды, какие данные, какие интеграции)
2. **Ручной review спецификации** — проверка глазами
3. **Plan mode** — формирование технического плана реализации
4. **Ручной review плана**
5. **Имплементация** — Claude Code создаёт workflow через MCP, таблицы через Supabase, валидирует результат

**Честная оценка:** ускоряет работу, решает проблему пустого листа. Ошибки неизбежны (синтаксис, пустые поля, неправильные маппинги). Нужны знания n8n для доводки.

---

## Другие MCP-серверы для n8n

| Сервер | Фокус |
|--------|-------|
| [leonardsellem/n8n-mcp-server](https://github.com/leonardsellem/n8n-mcp-server) | Управление workflow через API: CRUD, execute, monitor. Фокус на operations |

**Отличие от czlonkowski:** leonardsellem — **management server** (управляет инстансом n8n), czlonkowski — **knowledge server** (учит AI строить workflow правильно). Дополняют друг друга.

---

## Нативные AI-фичи n8n

### Instance-Level MCP (beta)

n8n v1.76+, работает в self-hosted и cloud.

**Что делает:** Выставляет выбранные n8n workflow как MCP-тулы. Любой MCP-клиент подключается по одному URL + access token и получает доступ к workflow как к инструментам.

**Настройка:** Settings → Instance-level MCP → включить → выбрать workflow → сгенерировать token.

**Ограничения:** workflow должны иметь поддерживаемые триггеры и быть опубликованы.

**Для svaib:** Автоматизации в n8n под капотом, клиент работает через AI-интерфейс. Прямое попадание в модель "Плагин" (данные у клиента, автоматизация у svaib).

### AI Workflow Builder (beta)

Describe workflow на естественном языке → n8n генерирует ноды, логику, конфигурацию. **Только cloud** (Trial, Starter, Pro планы). В self-hosted недоступен. 20 кредитов на trial.

### MCP Client Node

n8n как MCP-клиент — подключается к внешним MCP-серверам из workflow. Двусторонняя интеграция с Instance-Level MCP.

---

## SSH-паттерн (NetworkChuck)

**Репо:** [theNetworkChuck/n8n-claude-code-guide](https://github.com/theNetworkChuck/n8n-claude-code-guide)

n8n вызывает Claude Code CLI через SSH-ноду на удалённом Linux-сервере. `claude -p "prompt"` с session management (`--session-id`). Включает интеграцию со Slack-чатботом для мобильного доступа.

Простой и элегантный подход, но ограничен CLI-взаимодействием.

---

## Что пока не работает

- **Официального MCP-сервера от n8n** для build-workflow нет — все community-built
- **Self-hosted AI Workflow Builder** недоступен (highly requested)
- **Credential management** через AI — остаётся tricky
- **Quality assurance** — AI-generated workflow всегда требуют ручного review
- Контекст Claude Code расходуется быстро (75% на один workflow в примере из видео)

---

## Связанные файлы

- [claude-code.md](claude-code.md) — Claude Code: CLI, MCP, скиллы
- [../agents/mcp.md](../agents/mcp.md) — протокол MCP, экосистема, adoption
- [../tools/!tools.md](../tools/!tools.md) — n8n как платформа автоматизации
- [../skills/!skills.md](../skills/!skills.md) — формат скиллов, библиотеки

## Источники

- [czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp) — MCP-сервер
- [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) — скиллы
- [leonardsellem/n8n-mcp-server](https://github.com/leonardsellem/n8n-mcp-server) — management MCP
- [n8n Instance-Level MCP docs](https://docs.n8n.io/advanced-ai/accessing-n8n-mcp-server/) — нативная фича
- [n8n AI Workflow Builder docs](https://docs.n8n.io/advanced-ai/ai-workflow-builder/) — cloud beta
- [YouTube: "Claude Code ЛУЧШЕ в N8N Чем Ты!"](https://www.youtube.com/watch?v=s6BzgrTwyg0) — видео ИИшенка
