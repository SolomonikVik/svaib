---
title: "Model Context Protocol (MCP) — открытый протокол подключения AI к инструментам"
source: "https://modelcontextprotocol.io"
source_type: docs
status: processed
added: 2026-02-05
updated: 2026-02-11
review_by: 2026-05-05
tags: [mcp, protocol, tools, integration, anthropic, linux-foundation]
publish: false
version: 2
---

# Model Context Protocol (MCP)

## Кратко

Открытый протокол стандартизации подключения AI-приложений к внешним инструментам и данным. Запущен Anthropic в ноябре 2024, к 2026 стал де-факто стандартом — 70+ клиентов (OpenAI, Google, Microsoft, Amazon, JetBrains), 10 SDK, управление под Linux Foundation. Аналогия: USB для AI — один разъём, много устройств.

## Что решает

До MCP каждый AI-продукт писал свои интеграции: Claude — свой плагин для GitHub, ChatGPT — свой, Cursor — свой. Разработчик инструмента должен был поддерживать N интеграций. MCP задаёт единый формат: один MCP-сервер работает со всеми MCP-клиентами.

## Архитектура

### Участники

- **MCP Host** — AI-приложение (Claude Desktop, VS Code, ChatGPT)
- **MCP Client** — компонент хоста, поддерживающий соединение с одним сервером
- **MCP Server** — программа, предоставляющая инструменты/данные

Один хост создаёт несколько клиентов, каждый подключён к одному серверу.

### Два слоя

**Слой данных (протокол):**
- JSON-RPC 2.0
- Lifecycle management (инициализация, согласование возможностей, завершение)

**Транспортный слой:**

| Транспорт | Назначение | Особенности |
|-----------|-----------|-------------|
| **STDIO** | Локальные серверы | Standard I/O, без сети, один клиент |
| **Streamable HTTP** | Удалённые серверы | HTTP POST + SSE, OAuth 2.1, множество клиентов |

Streamable HTTP заменил оригинальный SSE-транспорт (более масштабируемый).

### Примитивы

**Серверные (сервер предоставляет клиенту):**

| Примитив | Назначение | Методы |
|----------|-----------|--------|
| **Tools** | Исполняемые функции (API, БД, поиск) | `tools/list`, `tools/call` |
| **Resources** | Источники данных (файлы, записи БД) | `resources/list`, `resources/read` |
| **Prompts** | Шаблоны взаимодействия | `prompts/list`, `prompts/get` |

**Клиентские (клиент предоставляет серверу):**

| Примитив | Назначение |
|----------|-----------|
| **Sampling** | Сервер запрашивает LLM-completion у клиента |
| **Elicitation** | Сервер запрашивает ответ от пользователя (диалоги подтверждения, ввод) |
| **Logging** | Сервер отправляет лог-сообщения клиенту |

**Экспериментальные / расширения:**

| Примитив | Назначение | Статус |
|----------|-----------|--------|
| **Tasks** | Durable execution, отложенное получение результатов | Experimental |
| **Apps** | Интерактивный HTML UI (графики, формы) в чатах | Extension (ext-apps) |

## Версии спецификации

MCP использует дата-версионирование (`YYYY-MM-DD`). Версия не инкрементируется при обратно-совместимых изменениях.

| Версия | Статус | Ключевое |
|--------|--------|----------|
| 2024-11-05 | Final | Запуск: Tools, Resources, Prompts, STDIO + SSE |
| 2025-03-26 | Final | Первая ревизия |
| 2025-06-18 | Final | Elicitation, Structured Tool Output, OAuth Resource Server, Resource Links |
| **2025-11-25** | **Current** | Tasks (experimental), OpenID Connect, Icons, Incremental Scope Consent, Tool Naming, SSE Polling |

### Ключевые изменения после мая 2025

**2025-06-18:**
- Elicitation — сервер может спросить пользователя (подтверждение, выбор, ввод)
- Structured Tool Output — инструменты возвращают структурированный JSON, не только текст
- Resource Links в результатах вызова инструментов
- MCP-серверы классифицированы как OAuth Resource Servers (RFC 9728)
- Resource Indicators (RFC 8707) — клиенты ОБЯЗАНЫ реализовать (защита от кражи токенов)
- Удалена поддержка JSON-RPC batching
- Заголовок `MCP-Protocol-Version` обязателен в HTTP-запросах

**2025-11-25:**
- Tasks — durable execution для долгих операций (SEP-1686)
- OpenID Connect Discovery 1.0
- Icons для инструментов, ресурсов, промптов (SEP-973)
- Incremental scope consent через `WWW-Authenticate` (SEP-835)
- Tool naming guidance (SEP-986)
- JSON Schema 2020-12 как дефолтный диалект
- SSE Polling — серверы могут отключаться, клиенты продолжают через GET

## Экосистема и adoption

### Кто поддерживает MCP (выборка ключевых)

| Компания | Продукт | Поддержка |
|----------|---------|-----------|
| Anthropic | Claude Desktop, Claude Code, Claude.ai | Полная (Tools, Resources, Prompts, Sampling, Elicitation, Apps) |
| OpenAI | ChatGPT | Tools |
| OpenAI | Codex | Resources, Tools, Elicitation |
| Google | Gemini CLI | Prompts, Tools, Instructions |
| Microsoft | VS Code Copilot | Полная |
| Microsoft | Copilot Studio | Resources, Tools, Discovery |
| Amazon | Q CLI / Q IDE | Prompts, Tools |
| JetBrains | AI Assistant + Junie | Tools |
| Cursor | Cursor IDE | Prompts, Tools, Roots, Elicitation |
| Block | Goose | Полная |
| Vercel | v0 | Tools |
| NVIDIA | AIQ Toolkit | Tools |
| Mistral AI | Le Chat | Tools |
| Langflow | Langflow | Tools (client + server) |

Всего 70+ клиентов (полный список: modelcontextprotocol.io/clients).

**Фрагментация:** Большинство клиентов реализуют только Tools. Resources и Prompts (ключевые отличия от function calling) — слабо поддержаны.

### MCP Registry

**Статус:** Preview (запущен 2025, GA ещё нет).

Централизованный каталог метаданных MCP-серверов. Бэкенд: Anthropic, GitHub, PulseMCP, Microsoft.

- Формат `server.json` — стандартизированные метаданные
- Namespace через DNS-верификацию (reverse DNS: `io.github.user/server-name`)
- REST API для discovery
- Поддерживает npm, PyPI, Docker Hub как источники пакетов
- **Не хостит код, не сканирует на уязвимости** — это делегировано пакетным реестрам и агрегаторам

### Расширения (Extensions)

Модульный механизм с vendor-prefixed идентификаторами (`{vendor}/{extension-name}`).

| Расширение | Описание |
|-----------|----------|
| **ext-auth** | OAuth Client Credentials (M2M), Enterprise-Managed Authorization |
| **ext-apps** | Интерактивный HTML UI в чатах (графики, формы, видеоплееры). Спека от 2026-01-26 |

Расширения opt-in, отключены по умолчанию, не требуются для conformance.

## SDK

10 официальных SDK с системой тиринга (SEP-1730):

| Язык | Tier |
|------|------|
| TypeScript | Tier 1 |
| Python | Tier 1 |
| Go, Kotlin, Swift, Java, C#, Ruby, Rust, PHP | — |

Все SDK поддерживают: создание серверов и клиентов, STDIO + Streamable HTTP, type safety.

## Модель безопасности

### Remote-серверы (Streamable HTTP)

Полноценный OAuth 2.1:

1. Сервер отвечает `401 Unauthorized` + `WWW-Authenticate`
2. Клиент находит Authorization Server через Protected Resource Metadata (`.well-known/oauth-protected-resource`)
3. Browser-based OAuth code flow с PKCE
4. Bearer token в `Authorization` header

| Слой | Механизм |
|------|---------|
| Транспорт | HTTPS (обязателен в production) |
| Идентификация | OAuth 2.1 + PKCE |
| Audience | Resource Indicators (RFC 8707) |
| Scope | Fine-grained per tool (`mcp:tools`) |
| Origin | Сервер MUST вернуть 403 для невалидных Origin |
| Сессия | `Mcp-Session-Id` — untrusted input |
| Registry | Namespace authentication через DNS |

### Локальные серверы (STDIO)

Авторизация опциональна. Сервер работает на той же машине, что клиент — environment credentials.

## Governance

MCP теперь под **Linux Foundation Projects, LLC**.

**Lead Maintainers (BDFL):** Justin Spahr-Summers, David Soria Parra (оба изначально из Anthropic).

**Core Maintainers:** 8 человек. Bi-weekly meetings, публичный Discord.

**SEP (Specification Enhancement Proposals)** — формальный процесс внесения изменений.

**Замечание:** Несмотря на LF, BDFL из Anthropic. Голос OpenAI/Google/Microsoft в governance неясен из публичных документов.

## MCP vs альтернативы

| Аспект | MCP | OpenAI Function Calling | LangChain Tools |
|--------|-----|------------------------|-----------------|
| Scope | Открытый протокол | API-фича одного вендора | Библиотечная абстракция |
| Governance | Linux Foundation | OpenAI | LangChain Inc. |
| Transport | STDIO + HTTP | N/A (API) | In-process |
| Reusability | Один сервер → 70+ клиентов | Привязан к OpenAI API | Привязан к LangChain |
| Resources | Да | Нет | Retriever concept |
| Prompts | Да | Нет | PromptTemplate |
| Elicitation | Да | Нет | Нет |

**Вердикт:** Принятие MCP OpenAI, Google и Microsoft — сильнейший сигнал, что MCP стал стандартом.

## Связь с A2A

**MCP** и **A2A (Agent-to-Agent, Google)** — комплементарные протоколы:
- **MCP** = "AI ↔ инструменты" (агент вызывает инструмент)
- **A2A** = "агент ↔ агент" (агенты общаются между собой)

Подробнее об A2A → subagents.md.

## MCP + Skills

MCP-серверы и Agent Skills (SKILL.md) — комплементарные механизмы: MCP даёт доступ к данным и инструментам, скилл описывает КАК с ними работать. Best practice от Anthropic: в SKILL.md явно указывать имя MCP-сервера и инструмента. Пример: скилл маркетинговой аналитики ссылается на BigQuery MCP-сервер и конкретную таблицу вместо ожидания CSV от пользователя. Это делает скилл самодостаточным — AI знает откуда брать данные.

Подробнее о Skills: [../skills/!skills.md](../skills/!skills.md).

## Заметные MCP-серверы

Production-ready или перспективные MCP-серверы, которые могут пригодиться SVAIB или клиентам. Список растёт по мере находок.

| Сервер | Автор | Назначение | Ссылка |
|--------|-------|-----------|--------|
| **MCP Toolbox for Databases** | Google | Подключение любой БД к AI-агентам за минимальный код. Connection pooling, OAuth, OpenTelemetry. SDK: Python, JS/TS, Go. Интеграции с LangChain, LlamaIndex, Genkit, ADK. Бета, Apache 2.0. | [googleapis/genai-toolbox](https://github.com/googleapis/genai-toolbox) |

## Ограничения

1. **Stateful по дефолту** — lifecycle management, масштабирование в работе (SEP-1442)
2. **Tasks экспериментальны** — async-операции только добавляются
3. **Нет sandboxing** — протокол не определяет модель изоляции, зависит от хоста
4. **STDIO — один клиент** — не масштабируется, нет авторизации, нет remote discovery
5. **Фрагментация поддержки** — ChatGPT только Tools, VS Code Copilot почти всё
6. **Нет permission model** — нет понятия "этот инструмент опасен, требуй подтверждения"
7. **Registry в preview** — не production-ready, нет compliance test suites
8. **Resources и Prompts underused** — большинство клиентов реализуют только Tools

## Источники

- modelcontextprotocol.io (спецификация, changelog, roadmap, governance, registry, clients, extensions)
- modelcontextprotocol.io/specification/versioning — текущая версия 2025-11-25

## Связанные файлы

- [subagents.md](subagents.md) — агентные фреймворки и A2A протокол
- [openclaw.md](openclaw.md) — OpenClaw использует MCP для интеграций
- [../coding/claude-code.md](../coding/claude-code.md) — MCP как механизм расширения Claude Code
- [../tools/cowork.md](../tools/cowork.md) — MCP-серверы в Cowork
