---
title: "VS Code Agent Sessions — multi-agent платформа (v1.109+)"
source: "https://code.visualstudio.com/blogs/2026/02/05/multi-agent-development"
source_type: docs
status: processed
added: 2026-02-11
updated: 2026-02-11
review_by: 2026-05-11
tags: [vscode, agents, multi-agent, claude, codex, copilot]
publish: false
version: 1
---

# VS Code Agent Sessions

## Кратко

С версии 1.109 (февраль 2026) VS Code — полноценная multi-agent платформа, а не просто IDE с AI-расширениями. Unified Agent Sessions: единый workspace для local, background и cloud агентов. Поддержка Claude и Codex как агентов наравне с Copilot. Параллельные субагенты, встроенный браузер, MCP Apps (интерактивный UI в чате), Agent Skills (стандарт Anthropic, GA). Всё через подписку GitHub Copilot.

## Три типа агентов

| Тип | Где работает | Режим | Изоляция | Видимость команде |
|-----|-------------|-------|----------|-------------------|
| **Local** | На машине | Интерактивный, real-time | Прямой доступ к workspace | Нет |
| **Background** | На машине (CLI) | Async, без присмотра | Git worktrees (изолированно) | Нет |
| **Cloud** | Удалённая инфраструктура | Автономный | Полная | Да (PR, issues) |

Все три — в одной панели Agent Sessions. Переключаешься между сессиями как между вкладками.

## Поддерживаемые агенты

- **GitHub Copilot** — встроенный, работает из коробки
- **Claude** — через официальный Agent harness от Anthropic. Local и cloud. Включается: `github.copilot.chat.claudeAgent.enabled`
- **Codex** — local (требует Copilot Pro+ и расширение OpenAI Codex) и cloud

Все работают через подписку GitHub Copilot.

## Ключевые фичи (v1.109)

**Parallel subagents** — субагенты запускаются параллельно, не последовательно. Визуализация: видно какой агент что делает, можно развернуть промпт и результат.

**Integrated browser** (preview) — встроенный браузер прямо в VS Code. Логин на сайты, навигация — как в обычном браузере.

**MCP Apps** — tool calls возвращают интерактивный UI: дашборды, формы, визуализации прямо в чате (а не текст).

**Agent Skills** — стандарт Anthropic для расширения агентов специализированными способностями. GA в VS Code, распространяются через extensions.

**Handoffs** — передача контекста между агентами: planning → implementation → review.

## Связанные файлы

- [claude-code.md](claude-code.md) — Claude Code: CLI/VS Code extension, плагины, система расширения
- [agent-teams.md](agent-teams.md) — Agent Teams: координация команды AI-агентов в Claude Code
- [../tools/ai-workspaces.md](../tools/ai-workspaces.md) — Каталог AI-оболочек (краткая запись VS Code)

## Источники

- Блог: https://code.visualstudio.com/blogs/2026/02/05/multi-agent-development
- Release notes v1.109: https://code.visualstudio.com/updates/v1_109
- Docs — Agents overview: https://code.visualstudio.com/docs/copilot/agents/overview
