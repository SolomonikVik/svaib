---
title: "AI-кодинг — среды разработки, AI-ассистенты и практики"
status: raw
added: 2026-01-30
updated: 2026-02-11
review_by: 2026-04-30
tags: [coding, ai-coding, ide, claude-code, index]
publish: false
version: 9
---

# Coding — AI-кодинг и разработка

## Кратко

Всё, что связано с написанием кода и разработкой с помощью AI. Среды разработки (Claude Code, Cursor, VS Code), AI-кодинг ассистенты (Codex, Antigravity, GitHub Copilot), практики (vibe coding, agentic coding, TDD с AI, code review с AI), UI-дизайн (Lovable, v0, Bolt, Figma Make, Mobbin). Ключевой тренд: переход от single-agent к multi-agent разработке — Agent Teams в Claude Code (официально с февраля 2026) позволяют запускать команды агентов, работающих параллельно. Если вопрос про код, программирование, разработку, генерацию UI — ищи здесь. Не путать с tools/ (платформы автоматизации, не связанные с кодом).

## Два уровня AI-кодинга

**Single-agent** — один AI-ассистент работает с разработчиком. Claude Code, Cursor, Copilot. Основной рабочий режим сейчас. Расширяется через Skills, Commands, Agents, Hooks.

**Multi-agent** — координатор (leader) управляет командой агентов (teammates) с ролями. Agent Teams в Claude Code (официально с февраля 2026) — агенты общаются через inbox, работают с общим task list, зависимости через blockedBy, delegation mode (Shift+Tab). Позволяет параллелить: исследование, ревью, кодинг независимых модулей. Экспериментальный, но официально документирован. Детали: [agent-teams.md](agent-teams.md).

Даже без Swarm Mode базовая параллельная работа возможна через Task tool (встроенный) — субагенты с изолированным контекстом, но без межагентной коммуникации.

**Cross-model review** — одна модель пишет код/план, другая ревьюит. Паттерн "senior review" из software engineering, переложенный на AI. Работает даже когда writer не в форме — reviewer ловит ошибки. Реализация через Claude Code Skill: Claude пишет → отправляет в OpenAI Codex → получает замечания → дорабатывает (до 3 итераций). Скилл: [codex-review](https://github.com/artwist-polyakov/polyakov-claude-skills/tree/main/plugins/codex-review/skills/codex-review). Ревьюер не привязан к Codex — завтра может быть другая модель.

## Автономные агенты и инфраструктура

**[AutoForge](https://github.com/AutoForgeAI/autoforge)** (автор Leon Van Zyl, ранее Autocoder) — долгоживущий автономный кодинг-агент на Claude Agent SDK. Двухагентная архитектура: Initializer разбивает проект на фичи, Coding Agent реализует их последовательно. SQLite для трекинга между сессиями, React-мониторинг. Multi-model (Claude, Ollama, GLM, Kimi). Наш опыт: 80% проекта через AutoForge, 20% добиваешь в Claude Code CLI. Идеален для PoC и несложных задач.

**[Sandboxed.sh](https://github.com/Th0rgal/sandboxed.sh)** — self-hosted оркестратор AI-кодинг-агентов в изолированных контейнерах (systemd-nspawn/Docker). Поддерживает Claude Code, OpenCode, Amp. Web dashboard + iOS app. Git-backed библиотека скиллов и MCP. Rust + TypeScript. MIT. Позволяет развернуть автономную фабрику агентного кодирования в облаке. Активная разработка.

## UI-дизайн

Всё про создание интерфейсов с AI: workflow, инструменты, кейсы, фишки. Проверенный подход: референсы (Mobbin) → описание текущего состояния → параллельный запуск генераторов (Lovable, v0, Bolt) → выбор лучшего → интеграция через Claude Code. Скриншоты работают лучше текстовых описаний. Детали: [ui-design.md](ui-design.md).

## Связанные материалы

- [skills/superpowers.md](../skills/superpowers.md) — крупнейшая авторская библиотека скиллов для AI-кодинга (TDD, debugging, code review, субагенты). Скиллы subagent-driven-development и dispatching-parallel-agents — формализация паттернов multi-agent работы
