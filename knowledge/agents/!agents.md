---
title: "Агентные системы — сводка знаний"
status: processed
updated: 2026-02-11
added: 2026-01-30
review_by: 2026-05-05
tags: [agents, subagents, mcp, multi-agent, patterns]
publish: false
version: 4
---

# Agents — Агентные системы

## Кратко

AI-системы, способные автономно принимать решения, использовать инструменты и выполнять многошаговые задачи. Три ключевых направления: (1) **MCP** — открытый протокол подключения AI к инструментам, де-факто стандарт (70+ клиентов, Linux Foundation); (2) **Субагенты** — изолированные агенты для подзадач, SDK от Anthropic и OpenAI, архитектурные паттерны; (3) **A2A** — протокол коммуникации между агентами (Google, 150+ организаций). Знания о проектировании агентов — рабочий материал для продукта SVAIB (см. product_vision.md).

## Ключевые концепции

- **Agent** — AI, который сам решает какие инструменты вызвать и в каком порядке. Цикл: gather context → take action → verify → repeat
- **SubAgent** — изолированный агент, вызываемый основным для подзадачи. Свой контекст (200k токенов), возвращает только результат
- **Workflow** — детерминированный пайплайн с предопределёнными шагами (в отличие от агента)
- **MCP (Model Context Protocol)** — открытый протокол подключения AI к инструментам. Под Linux Foundation, 70+ клиентов (OpenAI, Google, Microsoft, Amazon). Текущая спека: 2025-11-25. Подробнее → mcp.md
- **A2A (Agent-to-Agent)** — протокол коммуникации между агентами (Google, 2025). Комплементарен MCP: MCP = "агент ↔ инструмент", A2A = "агент ↔ агент". Подробнее → subagents.md
- **Function calling / Tools** — механизм вызова функций агентом (может быть через MCP или нативный API)

## SDK и фреймворки

### Первого уровня (SDK от вендоров моделей)

| SDK | Вендор | Языки | Ключевая фича |
|-----|--------|-------|---------------|
| **Claude Agent SDK** | Anthropic | Python, TypeScript | Встроенные инструменты (Read, Write, Bash), субагенты через Task tool, Skills/CLAUDE.md |
| **OpenAI Agents SDK** | OpenAI | Python, TypeScript | Handoffs (peer-to-peer передача управления), provider-agnostic, Realtime Agents |

Оба SDK поддерживают MCP-серверы как инструменты.

### Оркестрационные (community)

| Фреймворк | Подход | Состояние |
|-----------|--------|-----------|
| **LangGraph** | Graph-based: nodes = agents, edges = transitions | Самый используемый, активен |
| **CrewAI** | Role-based: Agent + Task + Crew | Хорош для прототипов |
| **AutoGen** (Microsoft) | Conversational: GroupChat | Растёт, radical rewrite v0.4+ |

Общая оценка: хороши для прототипов, но "incomplete for production" — security/governance/deployment нужно достраивать.

## Архитектурные паттерны

| Паттерн | Суть | Когда |
|---------|------|-------|
| **Orchestrator / Supervisor** | Центральный агент делегирует, субагенты не общаются друг с другом | Контроль, предсказуемость, простая отладка |
| **Peer-to-peer / Swarm** | Агенты общаются напрямую (Handoffs, Agent Teams, GroupChat) | Динамическая маршрутизация, но сложная отладка |
| **Pipeline / Chain** | Output одного → input следующего | Этапная обработка |
| **Hierarchical** | Дерево: supervisor → team leads → specialists | Крупные проекты |
| **Parallel Specialists** | Несколько агентов анализируют одно с разных ракурсов | Многоаспектная оценка (security + perf + architecture) |
| **Closed Feedback Loop** | Agent → Eval → Analyzer → Evolver → Agent (next gen). Автономная эволюция промпта/кода через замкнутый цикл с измеримой обратной связью | Оптимизация метрики, прохождение тестов, prompt engineering at scale. Подробнее → [feedback-loop-evolution.md](feedback-loop-evolution.md) |

### Gateway-Agent-Skills-Memory
Архитектура из проекта OpenClaw (см. openclaw.md). Gateway абстрагирует канал доставки, Agent — reasoning, Skills — модульные действия, Memory — персистентный контекст на Markdown. Подтверждает: Skills как плагины + Memory на файлах + проактивность агента — рабочая комбинация для self-hosted AI-ассистентов.

## Практика: когда что использовать

| Задача | Решение |
|--------|---------|
| Подключить внешний сервис | MCP-сервер (→ mcp.md) |
| Исследование / параллельная работа / изоляция контекста | Субагент (→ subagents.md) |
| Повторяющаяся процедура (стандарты, шаблоны) | Skill (→ ../skills/!skills.md) |
| Агенты разных вендоров должны общаться | A2A протокол (→ subagents.md) |
| Прототип мульти-агентной системы | LangGraph / CrewAI / AutoGen |
| Production-grade агент с инструментами | Claude Agent SDK / OpenAI Agents SDK |

## Связанные папки

- **../skills/** — Skills как модуль агентных систем: формат SKILL.md, библиотеки, активация
- **../coding/** — Claude Code как агентная платформа: субагенты, MCP, Swarm Mode
- **../tools/** — Инструменты автоматизации (n8n, Dify) — потенциальные MCP-серверы
- **../context/** — Context Engineering — ключевой компонент эффективности агентов
