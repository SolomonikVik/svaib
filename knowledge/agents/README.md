# Agents — Разработка агентов

Как проектировать и строить агентные системы: протоколы (MCP, A2A), SDK, субагенты, архитектурные паттерны.

**Границы:** Сюда — архитектуры, протоколы, SDK, паттерны оркестрации, фреймворки для разработки агентов. НЕ сюда: готовые агентные продукты (Manus, OpenClaw → tools/), IDE с агентами (→ coding/), платформы автоматизации (→ tools/), скиллы как формат (→ skills/).

## Файлы

- [!agents.md](!agents.md) — сводка знаний
- [workflow-automation.md](workflow-automation.md) — workflow-first vs agent-first и гибрид (агент пишет workflow): decision frame, схемы, граница применимости
- [mcp.md](mcp.md) — MCP: протокол, экосистема, SDK, security
- [agent-authorization.md](agent-authorization.md) — авторизация агентов: acting-as, права = права человека ∩ scope, Zanzibar-стек (OpenFGA/SpiceDB/OPA), MCP поверх OAuth 2.1, agent gateway
- [subagents.md](subagents.md) — Субагенты и мульти-агентные архитектуры
- [feedback-loop-evolution.md](feedback-loop-evolution.md) — Closed Feedback Loop: автономная эволюция агентов
- [sgr.md](sgr.md) — Schema-Guided Reasoning: паттерны структурирования рассуждений (Cascade, Routing, Cycle)

## Связи

- [../skills/](../skills/) — скиллы как инструмент агента (формат SKILL.md)
- [../tools/](../tools/) — оценил готовый продукт (Manus, OpenClaw) → как такое строят
- [../context/](../context/) — память и контекст для агентов
- [../coding/](../coding/) — строишь агента в IDE → среды и тулинг разработки
