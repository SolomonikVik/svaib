---
title: "Cowork — агентная платформа Anthropic для knowledge workers (не разработчиков)"
source: "https://claude.com/blog/cowork-research-preview"
source_type: docs
status: processed
added: 2026-02-01
updated: 2026-03-01
review_by: 2026-06-01
tags: [cowork, anthropic, plugins, knowledge-work, agents, svaib-product]
publish: false
version: 5
---

# Cowork — агентная платформа для knowledge workers

## Кратко

Cowork — фича Claude Desktop (macOS, Windows), запущена в январе 2026 как research preview. Приносит агентную архитектуру Claude Code (субагенты, параллельная работа) в GUI для не-разработчиков: sales, legal, finance, marketing. Работает в sandboxed VM. Расширяется через Plugins — тот же формат что Claude Code. Критически важно для продукта SVAIB: плагины = техническая реализация модели подписки "Skills + Agents + Онтология".

---

## Cowork vs Claude Code

| | Cowork | Claude Code |
|---|---|---|
| **Интерфейс** | Claude Desktop GUI | CLI / VS Code / JetBrains |
| **Аудитория** | Knowledge workers (sales, legal, finance) | Разработчики |
| **Среда** | Sandboxed VM | Прямой доступ к файловой системе |
| **Формат плагинов** | Идентичный | Идентичный |
| **Субагенты** | Task tool (до ~10 параллельных) | Task tool (до ~10 параллельных) |

Техническая архитектура одна: тот же Task tool, те же субагенты, тот же формат плагинов. Различие — интерфейс и целевая аудитория. Прямая цитата Anthropic: *"Built for Cowork, also compatible with Claude Code."*

---

## Ключевые возможности

**Plugins.** Система расширения через Skills + Commands + Agents + Hooks + MCP. Всё файловое (Markdown + JSON). Подробнее о формате и экосистеме плагинов → [plugins/!plugins.md](../plugins/!plugins.md).

**Scheduled Tasks.** Recurring и on-demand задачи через `/schedule`. Docs: [Anthropic](https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-cowork).

**Multi-App.** Claude работает сквозь Excel и PowerPoint, передавая контекст между приложениями (pivot tables, conditional formatting, генерация презентаций из данных). Research preview.

**Enterprise Private Marketplaces.** Компании создают внутренние каталоги плагинов: per-user provisioning, OpenTelemetry для трекинга, корпоративный брендинг.

---

## Официальные плагины

Anthropic выпускает open-source плагины для knowledge workers по отраслям: productivity, sales, customer support, product management, marketing, legal, finance, data, enterprise search, bio-research, design, engineering, HR, operations + partner-built плагины. Все Apache-2.0.

**Актуальный каталог:** [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)

Примечательные:
- **productivity** — задачи, календари, daily workflows. Коннекторы: Slack, Notion, Asana, Linear, Jira, Monday, ClickUp, Microsoft 365
- **sales** — prospect research, call prep, pipeline. HubSpot, Close, Clay, ZoomInfo, Fireflies
- **data** — SQL, визуализация, дашборды. Snowflake, Databricks, BigQuery, Hex
- **enterprise-search** — поиск по email, chat, docs, wikis. Slack, Notion, Guru, Jira
- **cowork-plugin-management** — создание и кастомизация плагинов изнутри Cowork

Коннекторы: Google Workspace (Calendar, Drive, Gmail), DocuSign, Microsoft 365, FactSet, WordPress и др. Список растёт — актуальный перечень в репозитории.

---

## Pricing / Access

| План | Цена | Cowork |
|------|------|--------|
| Free | $0 | Нет |
| Pro | $20/мес | Есть (research preview) |
| Max 5x | $100/мес | Есть |
| Max 20x | $200/мес | Есть |
| Team | $25/seat/мес | Есть + admin controls |
| Enterprise | Custom | SSO, audit logs, SCIM, private marketplaces |

**Ограничения (research preview):**
- Нет memory между сессиями
- Cowork НЕ попадает в Audit Logs, Compliance API, Data Exports
- Запрещено для HIPAA, FedRAMP, FSI regulated workloads
- История хранится локально, нет cross-device sync

---

## Хронология

| Дата | Событие |
|------|---------|
| 12 января 2026 | Launch (macOS, Max plan) |
| 16 января | Pro план |
| 23 января | Team и Enterprise |
| 30 января | Plugins (research preview, все платные планы) |
| 10 февраля | Windows (x64) |
| 24 февраля | Enterprise: private marketplaces, новые коннекторы, multi-app, отраслевые шаблоны плагинов |
| 25 февраля | Scheduled Tasks |

---

## Связь с продуктом SVAIB

Product vision описывает модель подписки "Плагин": Skills (методология) + Agents (автоматизация) + Онтология (структура).

| SVAIB продаёт | Cowork Plugin содержит |
|--------------|----------------------|
| Skills (методология) | `skills/` (SKILL.md) |
| Agents (автоматизация) | `agents/` + `hooks/` |
| Онтология (структура) | CLAUDE.md + commands/ |
| Коннекторы | `.mcp.json` |

Наша `.claude/` уже plugin-compatible — шаг до плагина: создать `plugin.json`, реорганизовать файлы. Anthropic покрывает generic (sales, legal) — наша ценность в кастомизации + русскоязычный рынок.

---

## Ссылки

- Cowork: https://claude.com/blog/cowork-research-preview
- Plugins: https://claude.com/blog/cowork-plugins
- Enterprise: https://claude.com/blog/cowork-plugins-across-enterprise
- Plugin docs: https://code.claude.com/docs/en/plugins
- Knowledge-work plugins: https://github.com/anthropics/knowledge-work-plugins
- Official plugin directory: https://github.com/anthropics/claude-plugins-official

---

## Связанные материалы

- [plugins/!plugins.md](../plugins/!plugins.md) — Плагины: формат, спецификация, маркетплейсы, best practices
- [coding/claude-code.md](../coding/claude-code.md) — Claude Code: рабочая среда, система расширения
- [skills/!skills.md](../skills/!skills.md) — Skills как формат: проектирование, экосистема
- [coding/agent-teams.md](../coding/agent-teams.md) — Agent Teams: координация команды AI-агентов
- [../context/claude_integrations_gdrive.md](../context/claude_integrations_gdrive.md) — тестирование интеграции Cowork + Google Drive + Claude Projects: что пишет, что видит, где зазоры
