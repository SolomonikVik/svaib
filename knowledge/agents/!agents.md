---
title: "Агентные системы — сводка знаний"
status: processed
updated: 2026-08-03
added: 2026-01-30
review_by: 2026-05-16
tags: [agents, subagents, mcp, multi-agent, patterns, hosting, workflows, verification]
publish: false
---

# Agents — Агентные системы

## Кратко

AI-системы, способные автономно принимать решения, использовать инструменты и выполнять многошаговые задачи. Три ключевых направления: (1) **MCP** — открытый протокол подключения AI к инструментам, де-факто стандарт (70+ клиентов, Linux Foundation); (2) **Субагенты** — изолированные агенты для подзадач, SDK от Anthropic и OpenAI, архитектурные паттерны; (3) **A2A** — протокол коммуникации между агентами (Google, 150+ организаций). Знания о проектировании агентов — рабочий материал для продукта SVAIB (см. product/01_overview.md).

## Ключевые концепции

- **Agent** — AI, который сам решает какие инструменты вызвать и в каком порядке. Цикл: gather context → take action → verify → repeat
- **SubAgent** — изолированный агент, вызываемый основным для подзадачи. Свой контекст (200k токенов), возвращает только результат
- **Workflow** — детерминированный пайплайн с предопределёнными шагами (в отличие от агента). Когда workflow, когда agent, и гибрид (агент пишет workflow) → [workflow-automation.md](workflow-automation.md)
- **MCP (Model Context Protocol)** — открытый протокол подключения AI к инструментам. Под Linux Foundation, 70+ клиентов (OpenAI, Google, Microsoft, Amazon). Текущая спека: 2025-11-25. Подробнее → mcp.md
  - ❗️ **Норма не отвечает за поведение клиентов.** Серверный поток (`GET` + SSE) в спецификации — «MAY»: замер 28.08 на боевом сервере показал, что из трёх семейств клиентов его открывает только Codex, и притом неавторизованным и по контракту двухлетней давности. Если уведомление о смене набора инструментов нужно всем — поток его не обеспечит; дешёвая замена — отпечаток набора в ответе обычной ручки. Подробнее → mcp.md
  - ❗️ **Доставка новых прав подключённым агентам ломается тише всего.** Потолок прав клиента — снимок на момент регистрации, и без его обновления каждое расширение набора означает для человека переустановку подключения, а не вход заново. Разбор четырёх фактов, которые из RFC не следуют → agent-authorization.md
- **A2A (Agent-to-Agent)** — протокол коммуникации между агентами (Google, 2025). Комплементарен MCP: MCP = "агент ↔ инструмент", A2A = "агент ↔ агент". Подробнее → subagents.md
- **Function calling / Tools** — механизм вызова функций агентом (может быть через MCP или нативный API)

## SDK и фреймворки

### Первого уровня (SDK от вендоров моделей)

| SDK | Вендор | Языки | Ключевая фича |
|-----|--------|-------|---------------|
| **Claude Agent SDK** | Anthropic | Python, TypeScript | Встроенные инструменты (Read, Write, Bash), субагенты через Task tool, Skills/CLAUDE.md |
| **OpenAI Agents SDK** | OpenAI | Python, TypeScript | Handoffs (peer-to-peer передача управления), provider-agnostic, Realtime Agents |

Оба SDK поддерживают MCP-серверы как инструменты. Claude Agent SDK — long-running процесс, деплоится в контейнерах (4 паттерна: ephemeral, long-running, hybrid, single). Провайдеры: Modal, Cloudflare, Daytona, E2B, Fly Machines, Vercel. Подробнее → subagents.md.

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
| **Schema-Guided Reasoning (SGR)** | Структурирование рассуждений LLM через Pydantic-схемы (constrained decoding). Три компонуемых паттерна: Cascade (последовательность), Routing (ветвление), Cycle (повторение) | Предсказуемое поведение агентов, работа с дешёвыми моделями, аудитируемые решения. Подробнее → [sgr.md](sgr.md) |
| **Adversarial verification** | Проверяющий агент отделён от автора и судит по рубрике. Мотив: агент предпочитает собственный результат, верификатор со своим интересом не бывает честным; свежий контекст превосходит самокритику | Везде, где цена незамеченной ошибки выше стоимости второго прогона |
| **Tournament** | N агентов решают задачу разными подходами, судья выбирает победителя попарным сравнением | Ранжирование больших наборов, выбор дизайн-направления |
| **Loop until done** | Спаунить агентов до выполнения условия («нет новых находок», «нет ошибок в логах»), а не фиксированное число проходов | Поиск неизвестного объёма: баги, находки, edge-кейсы |

**Dynamic workflows** — сборка этих паттернов на лету: агент пишет собственный харнес под задачу (JS-файл с функциями создания и координации субагентов, у каждого своё контекстное окно). Лечит agentic laziness, self-preferential bias и goal drift, но стоит заметно больше токенов — «параллелизм и специализация должны окупить стоимость координации». Реализация в Claude Code → [../coding/claude-code.md](../coding/claude-code.md).

### Gateway-Agent-Skills-Memory
Архитектурный паттерн: Gateway абстрагирует канал доставки, Agent — reasoning, Skills — модульные действия, Memory — персистентный контекст на Markdown. Skills как плагины + Memory на файлах + проактивность агента — рабочая комбинация для AI-ассистентов. Реализация паттерна: OpenClaw (→ [../tools/openclaw.md](../tools/openclaw.md)).

### Agent gateway — авторизация и guardrails на каждом вызове
Развитие идеи Gateway в сторону безопасности: между агентом и данными/инструментами ставится шлюз, где каждый вызов проходит аутентификацию, политику (scoped по пользователю, приложению, модели), guardrails на входе и выходе (prompt injection, PII/DLP) и попадает в сквозную трассу. Zero-trust: никакого доступа по умолчанию. Смежное — авторизация самого агента как субъекта: acting-as пользователя, права = права человека ∩ scope агента, вынос истины о правах из хранилища в отдельный authorization plane (Zanzibar-семейство: OpenFGA, SpiceDB; политики — OPA). Спецификация авторизации MCP закрывает давнюю дыру «нет permission model»: MCP-серверы становятся OAuth 2.1 resource servers с audience-bound токенами. Подробнее → [agent-authorization.md](agent-authorization.md).

## Практика: когда что использовать

| Задача | Решение |
|--------|---------|
| Автоматизировать повторяемый процесс: workflow или агент? | Decision frame + гибрид (→ workflow-automation.md) |
| Подключить внешний сервис | MCP-сервер (→ mcp.md) |
| Дать агенту доступ к корпоративным данным без «божественных» прав | Acting-as + отдельный authorization plane + шлюз на действия (→ agent-authorization.md) |
| Исследование / параллельная работа / изоляция контекста | Субагент (→ subagents.md) |
| Повторяющаяся процедура (стандарты, шаблоны) | Skill (→ ../skills/!skills.md) |
| Агенты разных вендоров должны общаться | A2A протокол (→ subagents.md) |
| Прототип мульти-агентной системы | LangGraph / CrewAI / AutoGen |
| Production-grade агент с инструментами | Claude Agent SDK / OpenAI Agents SDK |

## Связанные папки

- **../skills/** — Skills как модуль агентных систем: формат SKILL.md, библиотеки, активация
- **../coding/** — Claude Code как агентная платформа: субагенты, MCP, Swarm Mode
- **../tools/** — Инструменты автоматизации (n8n, Dify) и готовые агентные продукты (OpenClaw, Manus)
- **../context/** — Context Engineering, Memory — ключевой компонент эффективности агентов. Карта архитектур памяти агентов → [../context/agent-memory.md](../context/agent-memory.md); смена правил сборки контекста на поколении Claude 5 → [../context/context-engineering-claude5.md](../context/context-engineering-claude5.md)
- **../prompting/** — промптинг долгоживущих агентов: effort, длинные прогоны, делегирование субагентам, память как файлы, инструмент send-to-user → [../prompting/claude-5-prompting.md](../prompting/claude-5-prompting.md)
