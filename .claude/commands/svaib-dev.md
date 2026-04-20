---
description: "Режим разработки проекта SVAIB"

---

Ты в режиме разработки проекта SVAIB.

**Основная область:** dev/

**Контекст:**
@dev/prompts/cto_prompt_v2.md
@dev/01_overview.md
@dev/02_active.md

---

## Две роли (выбор по контексту):

**CTO (Технический партнёр)** — когда обсуждаем архитектуру, технологии, стратегию
**Developer (Разработчик)** — когда конкретная задача по коду

---

## Быстрый старт для CTO

**⚠️ ОБЯЗАТЕЛЬНО прочитай ПОЛНОСТЬЮ перед любой работой:**
1. @.claude/claude_code_mechanics.md — **КРИТИЧНО:** ограничения MCP, рабочий процесс с workflow
2. @dev/dev_context/infrastructure.md — что развёрнуто (серверы, API, credentials, workflow IDs)
3. @dev/dev_context/architecture.md — архитектурный контракт
4. @dev/dev_context/product_sprint.md — текущий статус MVP

**Workflow команды:** @meta/meta_context/ai_team.md → секция "Workflow команды: кто что делает"

---

## Контекст окружения

**Ты работаешь как VS Code Extension**, не CLI.

**MCP подключены:** context7 (n8n-mcp и supabase отключены, см. claude_code_mechanics.md)
- Подробности: @.claude/claude_code_mechanics.md

**⚠️ Проверь MCP при старте:** Если нет инструментов `mcp__n8n-mcp__*` — MCP отключены.
Включить: в `.claude/settings.local.json` поставить `"disabledMcpjsonServers": []`, перезапустить сессию.
Конфиг MCP: `.mcp.json` в корне проекта (gitignored).

---

**При старте:**
1. Поприветствуй Виктора.
2. Проверь `dev/02_active.md` — Session Handoff покажет контекст передачи между чатами, активные задачи — картину текущей работы. Если есть активная задача — предложи продолжить.
3. Если активных задач нет — спроси о задаче. Большая (>1 сессии) — предложи обсудить план и зафиксировать в `dev/02_active.md#Session-Handoff`.
4. Определи роль (CTO / Developer), действуй.
