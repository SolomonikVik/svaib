---
title: "Cowork — агентная платформа Anthropic для knowledge workers (не разработчиков)"
source: "https://claude.com/blog/cowork-research-preview"
source_type: docs
status: raw
added: 2026-02-01
updated: 2026-02-07
review_by: 2026-05-01
tags: [cowork, anthropic, plugins, knowledge-work, agents, svaib-product]
publish: false
version: 3
---

# Cowork — агентная платформа для knowledge workers

## Кратко

Cowork — фича Claude Desktop (macOS), запущена 12 января 2026 как research preview. Приносит агентную архитектуру Claude Code (субагенты, параллельная работа) в GUI для не-разработчиков: sales, legal, finance, marketing. Работает в sandboxed VM с доступом только к разрешённым папкам. 30 января 2026 запущены **Plugins** — бандлы из Skills + Commands + Agents + MCP-коннекторов. Формат плагинов **идентичен Claude Code** (`.claude-plugin/plugin.json`). Критически важно для продукта SVAIB: плагины = техническая реализация модели подписки "Skills + Agents + Онтология" (см. product_vision.md v3).

---

## Cowork vs Claude Code

| | Cowork | Claude Code |
|---|---|---|
| **Интерфейс** | Claude Desktop GUI (macOS) | CLI / VS Code / JetBrains |
| **Аудитория** | Knowledge workers (sales, legal, finance) | Разработчики |
| **Среда** | Sandboxed VM | Прямой доступ к файловой системе |
| **Формат плагинов** | Идентичный | Идентичный |
| **Субагенты** | Через Task tool (до ~10 параллельных) | Через Task tool (до ~10 параллельных) |
| **Запуск** | Январь 2026 (research preview) | Доступен с 2025 |

Прямая цитата Anthropic: *"Built for Cowork, also compatible with Claude Code."*

Техническая архитектура одна: тот же Task tool, те же субагенты, тот же формат плагинов. Различие — в интерфейсе и целевой аудитории.

---

## Plugins — система расширения

### Структура плагина

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json          # Манифест (обязательный)
├── .mcp.json                # MCP-серверы (коннекторы к внешним сервисам)
├── skills/                  # Доменные знания (SKILL.md, авто-активация)
├── commands/                # Слэш-команды (явный вызов пользователем)
├── agents/                  # Субагенты
├── hooks/                   # Event handlers
│   └── hooks.json
└── README.md
```

Всё файловое. Markdown + JSON. Никакого кода, инфраструктуры, build steps. Тот же формат что у Claude Code плагинов — подробная спецификация в [coding/claude-code.md](../coding/claude-code.md).

### Установка и дистрибуция

```bash
claude plugins add knowledge-work-plugins           # вся коллекция
claude plugins add knowledge-work-plugins/sales      # конкретный плагин
```

Также: установка из Cowork UI, загрузка своего плагина, `claude --plugin-dir ./my-plugin` для разработки/тестирования.

**Маркетплейсы:**
- [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) — 11 official (Apache-2.0)
- [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) — 53+ плагина, `marketplace.json`
- **Internal catalogs** — для компаний (анонсировано, в разработке)
- Community-built маркетплейсы уже появились (87+ плагинов)

### 11 официальных плагинов (knowledge work)

| Плагин | Назначение | Ключевые коннекторы |
|--------|-----------|---------------------|
| **productivity** | Задачи, календари, daily workflows | Slack, Notion, Asana, Linear, Jira, Monday, ClickUp, Microsoft 365 |
| **sales** | Prospect research, call prep, pipeline | Slack, HubSpot, Close, Clay, ZoomInfo, Fireflies, Microsoft 365 |
| **customer-support** | Тикеты, эскалации, knowledge base | Slack, Intercom, HubSpot, Guru, Jira, Microsoft 365 |
| **product-management** | Спеки, roadmaps, research synthesis | Slack, Linear, Asana, Figma, Amplitude, Pendo |
| **marketing** | Контент, кампании, brand voice | Slack, Canva, Figma, HubSpot, Ahrefs, Klaviyo |
| **legal** | Контракты, NDA, compliance | Slack, Box, Egnyte, Jira, Microsoft 365 |
| **finance** | Journal entries, reconciliation | Snowflake, Databricks, BigQuery, Microsoft 365 |
| **data** | SQL, визуализация, дашборды | Snowflake, Databricks, BigQuery, Hex, Amplitude |
| **enterprise-search** | Поиск по email, chat, docs, wikis | Slack, Notion, Guru, Jira, Asana, Microsoft 365 |
| **bio-research** | Литература, геномика, target prioritization | PubMed, bioRxiv, ClinicalTrials.gov, ChEMBL |
| **cowork-plugin-management** | Создание и кастомизация плагинов | — |

Все Apache-2.0 — можно форкать, кастомизировать, продавать как сервис.

---

## Pricing / Access

| План | Цена | Cowork + Plugins |
|------|------|-----------------|
| Free | $0 | Нет Cowork |
| Pro | $20/мес | Есть (лимиты usage) |
| Max 5x | $100/мес | Есть (225+ сообщений / 5 часов) |
| Max 20x | $200/мес | Есть (900+ сообщений / 5 часов) |
| Team Standard | $20-25/seat/мес | Есть + admin controls |
| Team Premium | $100-125/seat/мес | Есть + Claude Code + Connectors |
| Enterprise | Custom | SSO, audit logs, SCIM, 400K+ context |

**Ограничения:**
- macOS only (research preview)
- Cowork НЕ попадает в Audit Logs, Compliance API, Data Exports (пока)
- Запрещено для HIPAA, FedRAMP, FSI regulated workloads

---

## Связь с продуктом SVAIB

Product vision v3 описывает модель подписки "Плагин": Skills (методология) + Agents (автоматизация) + Онтология (структура). Клиент использует "любой AI-интерфейс (Claude, GPT, Cowork...)".

Cowork Plugins — техническая реализация этой модели:

| SVAIB продаёт | Cowork Plugin содержит |
|--------------|----------------------|
| Skills (методология) | `skills/` (SKILL.md) |
| Agents (автоматизация) | `agents/` + `hooks/` |
| Онтология (структура) | CLAUDE.md + commands/ |
| Коннекторы | `.mcp.json` |

**Что это означает:**
1. **Delivery mechanism готов** — Anthropic построила инфраструктуру (marketplace, CLI, internal catalogs)
2. **Наша `.claude/` уже plugin-compatible** — шаг до плагина: создать `plugin.json`, реорганизовать файлы
3. **Internal catalogs** (анонсированы) = точка входа для корпоративных клиентов
4. **Не нужно изобретать дистрибуцию** — заполняем готовую инфраструктуру содержимым
5. **Anthropic покрывает generic** (sales, legal) — наша ценность в кастомизации + русскоязычный рынок

### Playground как визуальный слой для клиентов

Плагин `playground` из `anthropics/claude-plugins-official` генерирует интерактивные HTML-интерфейсы вместо текстового вывода: контролы + live preview + кнопка Copy prompt. Подробное описание и шаблоны — в [coding/claude-code.md](../coding/claude-code.md), секция "Примечательные плагины".

**Гипотеза:** Playground можно подключить как часть клиентского плагина SVAIB. Клиент ожидает чат — а получает интерфейс. Кастомные шаблоны под управленческие задачи:

- **Ревью протокола встречи** (на базе document-critique) — 8 решений из транскрипции, каждое с кнопкой approve/reject. Руководитель кликает, а не читает стену текста
- **Карта проекта** (на базе concept-map) — задачи, связи, риски в визуальной схеме вместо текстовой wiki
- **Настройка формата отчётов** (на базе design-playground) — слайдеры и превью вместо текстового описания "хочу такой-то формат"

**Ограничение:** Playground генерирует одноразовые HTML-файлы, не полноценный UI. Хорош как wow-эффект и точка входа, но не замена dashboard-у, если клиенту понадобится постоянный интерфейс.

---

## Ссылки

- Cowork launch: https://claude.com/blog/cowork-research-preview
- Cowork Plugins launch: https://claude.com/blog/cowork-plugins
- Knowledge-work plugins (GitHub): https://github.com/anthropics/knowledge-work-plugins
- Plugin docs: https://code.claude.com/docs/en/plugins
- Official plugin directory: https://github.com/anthropics/claude-plugins-official

---

## Связанные материалы

- [plugins/!plugins.md](../plugins/!plugins.md) — Плагины: формат, спецификация, маркетплейсы, экосистема, best practices
- [coding/claude-code.md](../coding/claude-code.md) — Claude Code: рабочая среда, система расширения
- [skills/!skills.md](../skills/!skills.md) — Skills как формат: проектирование, экосистема, активация
- [coding/agent-teams.md](../coding/agent-teams.md) — Agent Teams: координация команды AI-агентов в Claude Code (leader + teammates, общий task list, delegation mode)
