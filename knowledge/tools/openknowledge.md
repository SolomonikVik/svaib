---
title: "OpenKnowledge (Inkeep) — AI-native markdown IDE / LLM-wiki с нативным MCP для агентов"
source: "https://github.com/inkeep/open-knowledge"
source_type: repo
status: raw
added: 2026-07-25
updated: 2026-07-25
review_by: 2026-10-25
tags: [openknowledge, inkeep, llm-wiki, markdown, mcp, crdt, yjs, knowledge-base, agent-writable, second-brain, svaib-clients]
publish: false
version: 1
---

# OpenKnowledge (Inkeep)

## Кратко

OpenKnowledge — открытый (GPL-3.0) «AI-native markdown IDE / LLM-wiki» от Inkeep: WYSIWYG-редактор поверх обычных .md/.mdx-файлов, которые агент (Claude Code, Codex, Cursor и др.) читает и правит **нативно через MCP**, без облака. Прямая продуктовая реализация паттерна LLM Wiki (Карпатый) с фокусом «company brain / second brain». Для SVAIB интересен как готовый образец ровно нашей модели — файловая md-база, данные у пользователя, агент-писатель — собранный в цельный продукт.

## Почему интересно для продукта

Топики репозитория говорят сами за себя: `company-brain`, `second-brain`, `llm-wiki-karpathy`, `agent-skills`. Это то же направление, что SVAIB (персональная/командная AI-инфраструктура на md), доведённое до продукта. Полезно и как бенчмарк UX (WYSIWYG над md для не-техника), и как источник паттернов (нативный MCP + skills, git-синхра команды).

## Три слоя (архитектура)

1. **Редактор** — WYSIWYG над markdown/MDX; богатый контент: интерактивный HTML/JS, Mermaid, LaTeX, видео, PDF.
2. **Инструменты агента** — **MCP + skills**: агент ищет, навигирует и поддерживает базу (read/write). Интеграции: Claude, Cursor, Codex, OpenCode, OpenClaw, Pi, Antigravity + встроенный TUI.
3. **Контент** — обычные .md/.mdx на диске, source of truth, версионируются git'ом.

## Ключевые механики

- **Dual-observer Yjs/CRDT** — держит WYSIWYG-вид и сырой markdown-файл в непрерывной **байт-точной** синхронизации *локально*: агент пишет в файл → вид обновляется мгновенно; человек печатает в виде → файл обновляется. Мерж-логика на локальной машине, без сервера. ⚠️ Это синхра «человек ↔ агент ↔ файл» на одной машине, **не** многопользовательский real-time (в отличие от Relay у Obsidian).
- **Командный шаринг** — «no-code», через **auto-sync git/GitHub** (не CRDT). Команда синхронизируется репозиторием, а не живым CRDT-каналом.
- **Orama** — гибридный поиск по базе (полнотекст + вектор), локально.

## Платформы

Нативное приложение под macOS; CLI/TUI для Linux/Windows/Intel Mac; может подниматься как локальное web-приложение. Local-first, данные не уходят в облако.

## На что смотреть при оценке

- **GPL-3.0 (copyleft).** Для продуктовой компании существенно: производные и распространение тянут обязательства GPL. Использовать как инструмент — ок; строить на его коде закрытый продукт — с оглядкой на лицензию.
- **Свежий (релиз июнь 2026), активный.** Зрелость и стабильность API проверять перед ставкой.
- **Командная синхра — git/GitHub:** наследует плюсы (версии, откат) и минус — порог git для не-техника, тот самый барьер, что критичен у клиентов SVAIB (→ [../context/claude_integrations_gdrive.md](../context/claude_integrations_gdrive.md)).

## Связанные файлы

- [../context/llm-wiki.md](../context/llm-wiki.md) — паттерн LLM Wiki (Карпатый), который OpenKnowledge реализует как продукт
- [obsidian.md](obsidian.md) — Obsidian + Relay: другой путь (файлы + командный CRDT, а не git)
- [../agents/mcp.md](../agents/mcp.md) — MCP как канал доступа агента к файлам
- [../cases/arscontexta.md](../cases/arscontexta.md) — генератор персональных md-knowledge-систем (родственный подход)
- [ai-workspaces.md](ai-workspaces.md) — каталог AI-оболочек (OpenKnowledge — среда «для людей и агентов»)
