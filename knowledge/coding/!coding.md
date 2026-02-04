---
title: "AI-кодинг — среды разработки, AI-ассистенты и практики"
status: raw
added: 2026-01-30
review_by: 2026-04-30
tags: [coding, ai-coding, ide, claude-code, index]
publish: false
version: 5
---

# Coding — AI-кодинг и разработка

## Кратко

Всё, что связано с написанием кода и разработкой с помощью AI. Среды разработки (Claude Code, Cursor, VS Code), AI-кодинг ассистенты (Codex, Antigravity, GitHub Copilot), практики (vibe coding, agentic coding, TDD с AI, code review с AI), UI-дизайн (Lovable, v0, Bolt, Figma Make, Mobbin). Ключевой тренд января 2026: переход от single-agent к multi-agent разработке — Swarm Mode в Claude Code позволяет запускать команды из 8-12 агентов, работающих параллельно. Если вопрос про код, программирование, разработку, генерацию UI — ищи здесь. Не путать с tools/ (платформы автоматизации, не связанные с кодом).

## Два уровня AI-кодинга

**Single-agent** — один AI-ассистент работает с разработчиком. Claude Code, Cursor, Copilot. Основной рабочий режим сейчас. Расширяется через Skills, Commands, Agents, Hooks.

**Multi-agent** — координатор управляет командой агентов с ролями. Swarm Mode в Claude Code (TeammateTool) — агенты общаются через inbox, работают с общим task board, зависимости через blockedBy. Позволяет параллелить: требования → код → ревью. Пока экспериментальный, но уже используется через неофициальные инструменты. Детали: [swarm-mode.md](swarm-mode.md).

Даже без Swarm Mode базовая параллельная работа возможна через Task tool (встроенный) — субагенты с изолированным контекстом, но без межагентной коммуникации.

## UI-дизайн

Всё про создание интерфейсов с AI: workflow, инструменты, кейсы, фишки. Проверенный подход: референсы (Mobbin) → описание текущего состояния → параллельный запуск генераторов (Lovable, v0, Bolt) → выбор лучшего → интеграция через Claude Code. Скриншоты работают лучше текстовых описаний. Детали: [ui-design.md](ui-design.md).

## Файлы в этой папке

- [claude-code.md](claude-code.md) — Claude Code: CLI-инструмент Anthropic для AI-assisted разработки. Система расширения (Skills, Commands, Agents, Hooks, MCP, LSP), плагины, маркетплейсы, безопасность
- [swarm-mode.md](swarm-mode.md) — Swarm Mode: multi-agent оркестрация в Claude Code (TeammateTool), паттерны (Specialist, Pipeline, Swarm, Plan Approval), практический workflow, риски. Статус: raw, ожидает официального релиза
- [ui-design.md](ui-design.md) — UI-дизайн: workflow создания интерфейсов с AI (кейс Полякова), генераторы (Lovable, v0, Bolt), дизайн-инструменты (Figma Make), референсы (Mobbin). Обновляется по мере находок

## Связанные материалы

- [skills/superpowers.md](../skills/superpowers.md) — крупнейшая авторская библиотека скиллов для AI-кодинга (TDD, debugging, code review, субагенты). Скиллы subagent-driven-development и dispatching-parallel-agents — формализация паттернов multi-agent работы
