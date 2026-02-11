---
title: "Субагенты и мульти-агентные архитектуры — паттерны, фреймворки, практика"
source: "https://platform.claude.com/docs/en/agent-sdk/overview"
source_type: docs
status: processed
added: 2026-02-05
updated: 2026-02-07
review_by: 2026-05-05
tags: [subagents, multi-agent, agent-sdk, orchestration, patterns]
publish: false
version: 2
---

# Субагенты и мульти-агентные архитектуры

## Кратко

Субагент — изолированный AI-агент, вызываемый основным агентом для подзадачи. Мульти-агентные системы координируют нескольких агентов для выполнения сложных задач. К 2026 оформились три уровня: SDK-фреймворки (Claude Agent SDK, OpenAI Agents SDK), протоколы коммуникации (A2A от Google), и оркестрационные фреймворки (LangGraph, CrewAI, AutoGen). Ключевые паттерны: orchestrator/supervisor, peer-to-peer/swarm, pipeline, hierarchical delegation.

## Зачем субагенты

1. **Параллелизация** — несколько субагентов работают одновременно над независимыми задачами
2. **Изоляция контекста** — субагент не засоряет основной контекст промежуточными шагами, возвращает только результат
3. **Специализация** — каждый субагент заточен под свою задачу (исследование, код, ревью)
4. **Масштабирование** — декомпозиция сложной задачи в управляемые подзадачи

## Фреймворки и SDK

### Anthropic Claude Agent SDK

**Что это:** SDK (Python + TypeScript), дающий программный доступ к тому же ядру что Claude Code. Переименован из Claude Code SDK.

**Ключевые абстракции:**

| Концепция | Назначение |
|-----------|-----------|
| `query()` | Запуск агента с промптом и набором инструментов |
| `AgentDefinition` | Определение субагента: description, prompt, tools |
| `Task` tool | Встроенный механизм спавна субагентов |
| Hooks | Callback-функции на этапах lifecycle (PreToolUse, PostToolUse, Stop) |
| Sessions | Персистентный контекст между вызовами (resume, fork) |
| MCP | Подключение внешних серверов как инструментов |

**Субагенты в Agent SDK:**
```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Glob", "Grep", "Task"],
    agents={
        "code-reviewer": AgentDefinition(
            description="Expert code reviewer.",
            prompt="Analyze code quality and suggest improvements.",
            tools=["Read", "Glob", "Grep"]
        )
    }
)
```

Координатор решает когда вызвать субагента через Task tool. Субагент получает изолированный контекст (200k токенов), возвращает результат, контекст освобождается.

**Отличия от других SDK:**
- Встроенные инструменты (Read, Write, Edit, Bash, Glob, Grep, WebSearch) — не нужно реализовывать tool execution
- Тот же агентный цикл что Claude Code: gather context → take action → verify work → repeat
- Skills, Commands, CLAUDE.md — файловая конфигурация через `setting_sources=["project"]`

**Docs:** platform.claude.com/docs/en/agent-sdk/overview

### OpenAI Agents SDK

**Что это:** Фреймворк для мульти-агентных workflow (Python + TypeScript). Преемник экспериментального Swarm.

**Ключевые абстракции:**

| Концепция | Назначение |
|-----------|-----------|
| Agent | Обёртка над LLM с instructions, tools, handoffs, guardrails |
| **Handoff** | Передача управления от агента другому агенту (ключевая фича) |
| Guardrails | Валидация input/output параллельно с выполнением |
| Runner | Оркестратор агентной петли |
| Sessions | Персистентный контекст внутри агентного цикла |
| Realtime Agents | Голосовые агенты с прерыванием, контекстом, guardrails |

**Handoffs — главная инновация:**
```python
agent = Agent(
    name="Triage",
    handoffs=[billing_agent, support_agent, sales_agent]
)
```
Агент сам решает кому передать разговор. Нет явного координатора — это peer-to-peer делегация.

**Отличия от Claude Agent SDK:**
- Provider-agnostic (работает не только с OpenAI моделями)
- Handoff как первоклассный примитив (Claude использует Task tool для делегации)
- MCP server integration встроена
- Нет встроенных инструментов (Read, Write и т.д.) — только функции-инструменты

**Docs:** openai.github.io/openai-agents-python/

### Google A2A Protocol (Agent-to-Agent)

**Что это:** Открытый протокол коммуникации между AI-агентами. Запущен Google апрель 2025, под Linux Foundation с июня 2025.

**Отличие от MCP:**
- **MCP** = "агент ↔ инструмент" (агент вызывает функцию)
- **A2A** = "агент ↔ агент" (агенты общаются между собой)

**Характеристики:**
- Построен на HTTP, SSE, JSON-RPC
- 150+ поддерживающих организаций (Atlassian, Salesforce, SAP, PayPal, Langchain, MongoDB)
- v0.3: gRPC support, signed security cards, Python SDK
- Apache 2.0 лицензия

**Применение:** Enterprise-интеграции, где агенты разных вендоров должны координироваться. Пример: агент Tyson Foods общается с агентом Gordon Food Service для координации supply chain.

**Docs:** github.com/a2aproject/A2A, google.github.io/adk-docs/a2a/

### Оркестрационные фреймворки

| Фреймворк | Подход | Состояние (2026) |
|-----------|--------|-----------------|
| **LangGraph** (LangChain) | Graph-based: nodes = agents/tools, edges = transitions. StateGraph для shared state | Самый используемый. Активно развивается |
| **CrewAI** | Role-based: Agent + Task + Crew. Интуитивный API, последовательные/иерархические процессы | Активен. Хорош для прототипов |
| **AutoGen** (Microsoft) | Conversational: agents в "комнате" общаются. GroupChat, nested chats | Растёт. Radical rewrite в v0.4+ |

**Общая оценка:** Все три хороши для прототипирования, но "dangerously incomplete for production" — security, governance и deployment нужно достраивать самостоятельно.

## Архитектурные паттерны

### 1. Orchestrator / Supervisor

Центральный агент решает кому делегировать. Субагенты не общаются друг с другом.

**Реализации:**
- Claude Code Task tool — координатор спавнит субагентов, получает результат
- CrewAI hierarchical process — manager координирует workers
- OpenClaw supervisor-specialist (см. openclaw.md)

**Когда:** Нужна единая точка контроля, простая отладка, предсказуемость.

### 2. Peer-to-peer / Swarm

Агенты общаются напрямую без центрального координатора.

**Реализации:**
- OpenAI Agents SDK Handoffs — агент передаёт управление другому
- AutoGen GroupChat — агенты говорят по очереди
- Claude Code Agent Teams (экспериментальный, февраль 2026) — inbox-файлы, общий task list

**Когда:** Естественная балансировка нагрузки, динамическая маршрутизация. Но сложнее отладка.

### 3. Pipeline / Chain

Последовательная обработка: output одного агента = input следующего.

**Реализации:**
- CrewAI sequential process
- Claude Code Agent Teams с blockedBy зависимостями (spec → code → test → review)

**Когда:** Этапная обработка с чёткой последовательностью.

### 4. Hierarchical Delegation

Дерево: supervisor → team leads → specialists.

**Реализации:**
- OpenClaw supervisor-specialist с кросс-сессионной координацией
- Claude Code — субагенты теоретически могут спавнить своих субагентов

**Когда:** Крупные проекты с разделением ответственности.

### 5. Parallel Specialists

Несколько агентов проверяют одно и то же с разных ракурсов параллельно.

**Пример:** security-reviewer + performance-reviewer + architecture-reviewer анализируют PR одновременно. Координатор собирает findings.

**Когда:** Задачи с несколькими ортогональными аспектами оценки.

## Коммуникация

### Context Passing (через координатора)

Task tool в Claude Code / Agent SDK:
- Координатор формулирует задание
- Субагент получает: задание + system prompt + доступ к файлам
- Субагент НЕ видит историю диалога
- Координатор получает только финальный результат

### Message Passing (напрямую)

OpenAI Handoffs:
- Полный conversation context передаётся от агента к агенту

Claude Code Agent Teams:
- JSON-файлы в `~/.claude/teams/{name}/inboxes/`
- `write` (личное) дешевле `broadcast` (всем)

### Shared State

- Agent Teams: общий task list, blockedBy зависимости
- LangGraph: StateGraph — единый state dict
- OpenClaw: sessions_list, sessions_history, sessions_send

### File-based (паттерн Claude Code)

Файлы как medium of communication:
- SKILL.md — инструкции для агента (текст, не код)
- CLAUDE.md — project-level инструкции
- Inbox JSON — сообщения между агентами
- Plans/ — планы выполнения, доступные всем агентам

## Lifecycle

### Spawning

| Подход | Когда создаётся | Время жизни |
|--------|----------------|-------------|
| Task tool | Координатор решает по description (LLM reasoning) | Короткоживущий: задача → результат → смерть |
| AgentDefinition (SDK) | Программно, через конфигурацию | Зависит от реализации |
| Agent Teams | Персистентный, живёт пока не попросят уйти | Долгоживущий |
| Handoff (OpenAI) | При передаче управления | Живёт пока не передаст дальше |

### Мониторинг

- **Task tool:** координатор видит только финальный output
- **Agent Teams:** видимые tmux/iTerm панели, task list с прогрессом
- **OpenAI Tracing:** встроенная трассировка всех шагов

### Error Handling

- Task tool: при фейле субагента координатор получает ошибку, решает сам
- Agent Teams: зацикленные Builder-QA могут сжечь значительный бюджет
- Hallucination cascades — если один агент выдумал, другие подхватят

### Ресурсы

- 10 субагентов = 10 контекстных окон
- Задача за $0.20 в одиночном режиме → $1.50+ в swarm
- Skills: ~50 токенов (description) при старте, <5k при вызове, остаются в контексте
- Субагенты: ~100 токенов (description) при старте, 200k при вызове, контекст освобождается

## Практические рекомендации

### Когда использовать субагентов

| Ситуация | Решение |
|----------|---------|
| Задача требует много контекста (исследование кодовой базы) | Субагент |
| Промежуточные шаги засоряют чат | Субагент |
| Независимые задачи можно параллелить | Субагенты |
| Повторяющаяся процедура (brand guidelines, coding standards) | Skill |
| Доступ к внешнему сервису | MCP/Tool |

### Когда НЕ нужны субагенты

- Задача простая и линейная
- Задачи зависят друг от друга (нет параллелизации)
- Нужен тесный контроль промежуточных шагов
- Бюджет ограничен (7-10x стоимость по токенам)
- Нужно творческое единство (один голос, один стиль)

### Failure modes

1. **Hallucination cascades** — агент-архитектор выдумал библиотеку, агент-кодер тратит время на установку
2. **Зацикленные Builder-QA** — бесконечные раунды ревью
3. **Неверные решения** — агент переписывает библиотеку вместо npm install
4. **Code review невозможен** — при 10+ агентах объём кода выходит за возможности человеческой проверки
5. **Cost multiplication** — 10 агентов = 7-10x по токенам

### Activation reliability (для Skills)

Базовая надёжность автоматической активации: ~20%. С forced eval hook: ~84%. Подробнее → ../skills/skill-activation.md.

## Сравнение ключевых фреймворков

| Аспект | Claude Agent SDK | OpenAI Agents SDK | A2A |
|--------|-----------------|-------------------|-----|
| Тип | SDK для агентов | SDK для агентов | Протокол агент-агент |
| Языки | Python, TypeScript | Python, TypeScript | Любой (HTTP/JSON-RPC) |
| Делегация | Task tool (субагенты) | Handoffs (передача управления) | Агент-агент сообщения |
| Встроенные инструменты | Да (Read, Write, Bash, Glob...) | Нет (только function tools) | Нет |
| MCP поддержка | Да | Да | Комплементарен MCP |
| Provider lock-in | Claude models | Provider-agnostic | Provider-agnostic |
| Файловая конфигурация | Skills, CLAUDE.md, agents/ | Нет | Нет |
| Governance | Anthropic | OpenAI | Linux Foundation |

## Источники

- platform.claude.com/docs/en/agent-sdk/overview — Claude Agent SDK документация
- openai.github.io/openai-agents-python/ — OpenAI Agents SDK
- github.com/a2aproject/A2A — A2A Protocol
- developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/ — анонс A2A
- o-mega.ai/articles/langgraph-vs-crewai-vs-autogen-top-10-agent-frameworks-2026 — сравнение фреймворков

## Связанные файлы

- [mcp.md](mcp.md) — протокол подключения к инструментам (комплементарен субагентам)
- [openclaw.md](openclaw.md) — OpenClaw: Gateway-Agent-Skills-Memory архитектура
- [../skills/!skills.md](../skills/!skills.md) — Skills vs Subagents: когда что использовать
- [../skills/superpowers.md](../skills/superpowers.md) — субагентные скиллы (subagent-driven-development, dispatching-parallel-agents)
- [../skills/skill-activation.md](../skills/skill-activation.md) — надёжность активации
- [../coding/claude-code.md](../coding/claude-code.md) — Claude Code как платформа для субагентов
