---
title: "Механизмы Claude Code"
updated: 2026-02-10
version: 14
scope: "claude_reference"
priority: high
---

# Механизмы Claude Code

## Кратко

Справочник по механизмам Claude Code Extension: MCP-серверы (подключение к внешним сервисам), субагенты (AI-специалисты с изолированным контекстом), промпты (роли без изоляции), скиллы (процедуры для повторяемых задач). Используется при создании новых агентов, настройке MCP или скиллов. Не для ежедневной работы — для настройки среды.

---

## Основной стек

| Компонент | Инструмент |
|-----------|------------|
| IDE | VS Code |
| AI-ассистент | Claude Code Extension |
| Авторизация | Claude Max подписка |
| Актуальные данные | MCP-серверы |
| Специалисты | Субагенты, промпты |

## Связанные файлы

- meta/meta_context/ai_team.md — каталог AI-агентов (когда какого использовать)
- .claude/agents/ — файлы субагентов (пока только context-editor)
- dev/prompts/ — промпты ролей (CTO, Dify-эксперт)

---

## Быстрый справочник

### GUI-задачи через Chrome

```bash
claude --chrome -p "открой n8n Dashboard и проверь статус workflow"
```

Вызывается через Bash tool. Chrome extension видит страницу, кликает, заполняет формы.

**Где использовать:**
- n8n Dashboard (активация workflow, перенос в проект)
- Google Cloud Console
- Supabase Dashboard (GUI-настройки)
- Тестирование веб-страниц

**Ограничения:**
- Не работает с финансовыми сервисами
- Нужен открытый Chrome с extension 1.0.36+
- Медленнее прямых API (скриншот после каждого действия)

---

## Механизмы

| Механизм | Что это | Когда использовать | Где лежит |
|----------|---------|-------------------|-----------|
| **MCP** | Доступ к сервисам + актуальные данные | Нужен доступ к n8n, Supabase, документации | `.mcp.json` |
| **Субагент** | AI с изолированным контекстом | Специалист для автономной работы | `.claude/agents/` |
| **Промпт** | Роль без изоляции | Диалог в основном треде | `dev/prompts/` |
| **Скилл** | Инструкции + скрипты для повторяемых задач | Одна и та же процедура много раз | `.claude/skills/` |

### Принцип различия

- **MCP** = инструменты + данные (что использовать)
- **Субагент** = AI-специалист с изоляцией (кто делает автономно)
- **Промпт** = роль без изоляции (кто обсуждает)
- **Скилл** = процедура (как делать повторяемое, не AI)

---

## MCP-серверы

MCP (Model Context Protocol) — подключение AI к внешним сервисам. Это "руки" Claude для работы с n8n, Supabase и др.

### Текущие MCP

| MCP | Что делает | Статус |
|-----|------------|--------|
| **context7** | Быстрый доступ к документации библиотек | ✅ Активен |
| **n8n-mcp** | Создание/редактирование workflow | ⏸️ Отключён (n8n Cloud отменён 10.02.2026) |
| **supabase** | SQL, таблицы, миграции, управление схемой | ⏸️ Отключён (токен истёк) |

### Возможности n8n-mcp (39+ инструментов)

| Категория | Что может Claude |
|-----------|------------------|
| **Создание** | `n8n_create_workflow` — полное создание workflow |
| **Редактирование** | `n8n_update_full_workflow`, `n8n_update_partial_workflow` |
| **Тестирование** | `n8n_test_workflow` — запуск и проверка |
| **Автоисправление** | `n8n_autofix_workflow` — автоматический фикс ошибок |
| **Шаблоны** | `n8n_deploy_template` — деплой из 2709 готовых шаблонов |
| **Документация** | `search_nodes`, `get_node` — доступ к документации 543 нод |

### ⚠️ Ограничения n8n-mcp (исследование 15-16.12.2025)

**Три ключевых ограничения:**

| Что НЕ может MCP | Кто делает | Как |
|------------------|------------|-----|
| Создать webhook workflow | **UI** (Виктор / Claude Chrome) | n8n Dashboard → New workflow → Webhook node |
| Активировать/деактивировать workflow | **UI** | Toggle в правом верхнем углу |
| Создать workflow в проекте (не в personal) | **UI** | Drag & drop из Personal в Project |

**Что МОЖЕТ MCP:**
- ✅ Редактировать любой workflow (добавлять nodes, connections, код)
- ✅ Тестировать webhook (отправлять запросы)
- ✅ Валидировать workflow
- ✅ Читать структуру и executions

---
**!!! ОБЯЗАТЕЛЬНО перед изменением любой ноды:**

Получить структуру входных данных — выполнить n8n_get_workflow, найти ноду-предшественника, понять какие поля доступны в $json
Проверить execution history — какие данные реально приходили?
Сначала маппинг — понять что откуда берётся
Потом тестировать по одной ноде — не весь workflow сразу
---

**Рабочий процесс для webhook workflow:**

1. **UI создаёт** пустой workflow с webhook node в проекте svaib-app
2. **UI активирует** workflow
3. **MCP дорабатывает** — добавляет остальные nodes, код, connections
4. **UI переактивирует** если нужно (после изменений webhook node)

**Project ID svaib-app:** `9JhFwkoFVBxpUd8P`

---

**Почему webhook только через UI:**

n8n Cloud регистрирует production webhook только при создании через UI. API-созданные webhook nodes не регистрируются в routing table, возвращают 404. Добавление `webhookId` вручную не помогает — нужна внутренняя регистрация n8n.

**⚠️ Webhook + Respond to Webhook (ошибка 16.12.2025):**

При использовании `Respond to Webhook` node, параметр `responseMode` должен быть на **верхнем уровне** `parameters`, НЕ внутри `options`:

```json
// ❌ НЕПРАВИЛЬНО — ошибка "Unused Respond to Webhook node"
"parameters": {
  "options": { "responseMode": "responseNode" }
}

// ✅ ПРАВИЛЬНО
"parameters": {
  "httpMethod": "POST",
  "path": "...",
  "responseMode": "responseNode",
  "options": {}
}
```

После изменения webhook node параметров — нужно переактивировать workflow (toggle off → on).

**⚠️ Credentials через MCP (ошибка 16.12.2025):**

При создании нод через MCP — брать credential ID из `infrastructure.md` (секция n8n Credentials). НЕ выдумывать ID, не брать из памяти.

**Важно:** После любых изменений в workflow — обновить infrastructure.md (секция Workflows).


## Работа с n8n: обязательные правила

### ШАГ 0: Сначала логика — потом реализация

**Перед любыми изменениями в workflow:**

1. **Сформулируй логику потока:**
   - Какие шаги? Что от чего зависит?
   - Что можно выполнять параллельно?
   - Где точки ветвления/слияния?

2. **Согласуй с Виктором:**
   - Покажи схему потока (текстом или списком)
   - Дождись подтверждения логики
   - Только после OK — переходи к реализации

3. **Потом детали:**
   - Маппинг данных (какие поля откуда)
   - Конфигурация нод
   - Тестирование по одной ноде

**❌ НЕ ДЕЛАЙ:** Сразу прыгать в код/конфиг без согласованной логики потока.

---

### Перед изменением ЛЮБОЙ ноды:

1. **Узнай поток данных** — какая нода стоит ПЕРЕД изменяемой?
2. **Проверь что в $json** — после каждой ноды $json меняется!
   - После Webhook: `$json.body`, `$json.headers`
   - После Code Node: то что вернул return
   - После HTTP Request: ответ API
   - После Postgres: результат запроса

3. **Выбери правильную ссылку на данные:**
   - `$json.field` — данные из ПРЕДЫДУЩЕЙ ноды (только она!)
   - `$('Имя Ноды').item.json.field` — данные из КОНКРЕТНОЙ ноды по имени
   - Имя ноды должно ТОЧНО совпадать (регистр, пробелы)

### Postgres Query Parameters (КРИТИЧНО!):
- **Имя параметра:** `queryReplacement` (НЕ queryParams!)
- **Тип:** строка (string), НЕ массив
- **Формат:** значения через запятую: `{{ $json.value1 }}, {{ $json.value2 }}`
- **В SQL:** `$1`, `$2`, `$3` — позиционные плейсхолдеры
- **Расположение:** внутри `options`

**Пример для одного параметра:**
```json
{
  "options": {
    "queryReplacement": "={{ $json.bot_id }}"
  }
}
```

**Пример для нескольких параметров:**
```json
{
  "options": {
    "queryReplacement": "={{ $json.client_id }}, {{ $json.meeting_id }}, {{ JSON.stringify($json.metadata) }}"
  }
}
```

**❌ НЕПРАВИЛЬНО (частая ошибка):**
- `queryParams` — такого параметра НЕТ
- `{{ [$value1, $value2] }}` — массив НЕ работает, нужна строка с запятыми

### ⚠️ БАГ: queryReplacement ломается на запятых в тексте (Issue #16354)

**Проблема:** Если текст содержит запятые, n8n разбивает его на части неправильно.
**Статус:** Closed as "not planned" — n8n НЕ будет исправлять.

**Workaround:**

| Операция | Решение |
|----------|---------|
| **INSERT** | Использовать операцию `insert` с маппингом колонок, НЕ `executeQuery` |
| **SELECT/UPDATE** | Если параметр может содержать запятые → Code Node перед Postgres |

**Пример Insert (правильно):**
```json
{
  "operation": "insert",
  "schema": {"__rl": true, "mode": "list", "value": "public"},
  "table": {"__rl": true, "mode": "list", "value": "transcripts"},
  "columns": {
    "mappingMode": "defineBelow",
    "value": {
      "meeting_id": "={{ $json.meeting_id }}",
      "content": "={{ $json.full_text }}",
      "speakers": "={{ $json.speakers }}",
      "asr_provider": "soniox"
    }
  }
}
```

### typeVersion для часто используемых нод

n8n-mcp не отдаёт версии нод (`get_node mode="versions"` → "No version history available"). Справочник актуальных версий:

| Нода | typeVersion | Примечание |
|------|-------------|------------|
| postgres | 2.5 | Использовать операции insert/update, не executeQuery с запятыми |
| if | 2.1 | — |
| code | 2 | — |
| httpRequest | 4.2 | — |
| webhook | 2.1 | Создавать только через UI |
| respondToWebhook | 1.1 | responseMode на верхнем уровне parameters |
| executeWorkflow | 1.2 | Вызов другого workflow |
| executeWorkflowTrigger | 1.1 | Trigger для вызываемого workflow |
| openAi | 1.1 | OpenAI API (chat, completions) |
| telegram | 1.2 | Отправка сообщений |
| splitInBatches | 3 | ⚠️ output[0]=done, output[1]=loop (противоинтуитивно!) |

**Как узнать typeVersion:** Открыть существующий работающий workflow, найти ноду того же типа.

### ⚠️ splitInBatches (Loop Over Items) — индексы противоинтуитивны!

```
Output 0 = "done" (после завершения цикла)
Output 1 = "loop" (текущий batch для обработки)
```

**Правильное подключение:**
- Ноды обработки внутри цикла → подключать к **Output 1 (loop)**
- Ноды после завершения цикла → подключать к **Output 0 (done)**
- Последняя нода в цикле должна возвращаться обратно в splitInBatches

### ⚠️ IF node через MCP — операция isNotEmpty не работает

**Проблема:** IF node с операцией `isNotEmpty` созданный через MCP не рендерится в UI и не работает.

**Решение:** Использовать `notEquals` с пустой строкой:

```json
// ❌ Не работает через MCP:
{"operator": {"type": "string", "operation": "isNotEmpty"}, "leftValue": "={{ $json.id }}"}

// ✅ Работает:
{"operator": {"type": "string", "operation": "notEquals"}, "leftValue": "={{ $json.id }}", "rightValue": ""}
```

### ⚠️ Postgres node — 0 rows останавливает pipeline

**Проблема:** Если SELECT возвращает 0 строк, следующие ноды не получают данных и pipeline останавливается.

**Решение:** Добавить `alwaysOutputData: true` на уровне ноды (не в parameters):

```json
{
  "id": "load-dossier",
  "name": "Load Dossier",
  "type": "n8n-nodes-base.postgres",
  "alwaysOutputData": true,
  "parameters": {...}
}
```

Через MCP:
```json
{"type": "updateNode", "nodeName": "Load Dossier", "updates": {"alwaysOutputData": true}}
```

### ⚠️ Две OpenAI ноды — не путать!

| Тип | Назначение |
|-----|------------|
| `n8n-nodes-base.openAi` | Стандартная. Для chat completion, images, audio |
| `@n8n/n8n-nodes-langchain.openAi` | Для AI Agents, chains, vector stores. Другие параметры! |

**Правило:** Для простых GPT вызовов ВСЕГДА использовать `n8n-nodes-base.openAi`.

### ⚠️ GPT-5 (reasoning models) — несовместимы с n8n OpenAI node v1.1!

**Проблема:** GPT-5 — это reasoning models. Они НЕ поддерживают стандартные параметры:
- `max_tokens` → заменён на `max_completion_tokens`
- `temperature` → только default (1), другие значения = ошибка
- `top_p`, `presence_penalty`, `frequency_penalty` → не поддерживаются

**Ошибки:**
```
Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead.
Unsupported value: 'temperature' does not support 0.1 with this model. Only the default (1) value is supported.
```

**n8n OpenAI node v1.1** отправляет эти параметры как есть → API отклоняет.

**Решения (из n8n Ask AI, 29.12.2025):**

| Решение | Что делать | Статус |
|---------|-----------|--------|
| **A) OpenAI node V2** | n8n v1.117.0+ имеет OpenAI node V2 с операцией "Generate a Model Response" | ⏳ потом |
| **B) HTTP Request** | Заменить на HTTP Request, вручную формировать body | ⏳ потом |
| **C) Пустые options** | Убрать все параметры из `options: {}` — GPT-5 работает с дефолтами | ✅ работает |

**Workaround (29.12.2025):** Убрать `maxTokens` и `temperature` из options → `options: {}`. GPT-5 использует дефолты (temperature=1). Workflow работает.

```json
// ✅ Работает с GPT-5:
"options": {}
```

**Ограничения workaround:**
- Нет контроля над temperature (всегда 1)
- Нет контроля над длиной ответа

### Перед отправкой изменений:
- Назови ноду-источник данных
- Покажи какие поля берёшь и откуда
- Если не уверен — спроси execution log или запроси структуру workflow

### НЕ ДЕЛАЙ:
- Не пиши код пока не понял структуру данных
- Не угадывай имена полей — проверь
- Не меняй несколько нод сразу — по одной, с проверкой

### ⚠️ Эскалация: Ask AI в n8n

**Если застрял после 2 попыток — не бейся головой, спроси Ask AI в n8n.**

n8n имеет встроенный AI-помощник (кнопка "Ask AI" в интерфейсе). Он знает актуальную документацию и даёт корректные ответы по:
- Конфигурации нод
- Форматам параметров
- Ошибкам и их решениям

**Как использовать:**
1. **Через Claude Chrome:** `claude --chrome -p "открой n8n, найди ноду X, нажми Ask AI, спроси: [вопрос]"`
2. **Через Виктора:** "Виктор, спроси Ask AI в n8n: [конкретный вопрос]"

**Когда эскалировать:**
- 2 попытки не дали результата
- Документация MCP не помогает
- Непонятный формат параметров

### n8n_update_partial_workflow — формат операций

**addConnection — правильный формат:**

```json
// ✅ Правильно:
{"type": "addConnection", "source": "Node A", "target": "Node B"}

// ❌ Неправильно (лишняя вложенность):
{"type": "addConnection", "connection": {"source": "Node A", "target": "Node B"}}
```

**Полный пример batch операции:**

```json
{
  "operations": [
    {"type": "addNode", "node": {"name": "X", "type": "...", "typeVersion": 1.1, "position": [400, 300], "parameters": {}}},
    {"type": "addConnection", "source": "Existing Node", "target": "X"}
  ]
}
```

---

### Возможности Supabase MCP

| Что может Claude |
|------------------|
| Выполнять SQL запросы (`execute_sql`) |
| Создавать таблицы и миграции (`apply_migration`) |
| Читать схему (`list_tables`, `list_extensions`) |
| Генерировать TypeScript типы |

**⚠️ Ограничение:** Supabase MCP рекомендуют только для dev, не production.

### Хранение и управление конфигурацией MCP

**Конфиг:** `.mcp.json` в корне проекта (project scope, gitignored — содержит API-ключи)

**Отключение/включение MCP:**

В `.claude/settings.local.json` поле `disabledMcpjsonServers`:

```json
// Для knowledge/context сессий (n8n и supabase не нужны):
"disabledMcpjsonServers": ["n8n-mcp", "supabase"]

// Для dev-сессий (всё включено):
"disabledMcpjsonServers": []
```

**Как переключить:** Отредактировать `settings.local.json`, перезапустить сессию Claude Code.

**Команды CLI:**

```bash
# Проверить статус
claude mcp list

# Детали конкретного MCP
claude mcp get n8n-mcp

# Добавить новый (project scope — пишет в .mcp.json)
claude mcp add --scope project server-name -- npx server-package

# Удалить
claude mcp remove server-name -s project
```

**Важно:** `disabledMcpjsonServers` работает ТОЛЬКО для серверов из `.mcp.json`. Если MCP в `~/.claude.json` — отключить через этот механизм нельзя.

### Токены и сроки

| MCP | Статус | Примечание |
|-----|--------|-----------|
| context7 | Бессрочно | Работает без токена |
| n8n-mcp | ⏸️ Отключён | n8n Cloud отменён 10.02.2026. Workflows в `dev/n8n_backup/` |
| supabase | ⏸️ Отключён | Токен истёк ~10.01.2026. Для включения: создать новый токен в Supabase Dashboard |

**При включении MCP:** Создать токен → обновить `.mcp.json` → убрать из `disabledMcpjsonServers` в `.claude/settings.local.json` → перезапустить сессию

---

## Documentation Policy

Правила работы с документацией внешних сервисов (Recall.ai, Soniox, n8n).

### Источники документации

| Источник | Назначение | Когда использовать |
|----------|------------|-------------------|
| **Context7** (default) | Быстрый справочник | По умолчанию для любых вопросов |
| **Official docs** (canonical) | Источник истины | Красные зоны, верификация, ошибки |

**Official docs URLs:**
- Recall.ai: https://docs.recall.ai
- Soniox: https://docs.soniox.com

### Правила использования

**1. По умолчанию — Context7**

Использовать `use context7` или `use library /websites/recall_ai` для быстрого доступа.

**2. Красные зоны — сразу official docs (минуя Context7):**
- Authentication / API keys / permissions
- Regions & Base URLs
- Webhooks / realtime / lifecycle статусы
- Breaking changes / версии API

**3. При ошибках API (401 / 403 / 404 / 409):**
- Переключиться на official docs
- Исправить реализацию строго по ним

**4. При неуверенности** в корректности поля, статуса или payload — свериться с official docs

**5. Конфликт источников:** official docs имеют приоритет над Context7

**6. Запрещено:** выдумывать поля, параметры, статусы или поведение API, отсутствующие в Context7 или official docs

### Работа с official docs (если Context7 недоступен)

**При 404:**
1. Искать через `site:docs.recall.ai <ключевые слова>`
2. Проверить эквивалент в `/reference/` вместо `/docs/`
3. Попробовать versioned URL (например `/v1.10/...`)

**При больших файлах (10MB+):**
- Предпочитать "узкие" страницы вместо "комбайнов":
  - `Verify events` / `Verify webhooks`
  - `Bot status change events`
  - `Recording webhooks`
  - `Real-time endpoints`

### ⚠️ Эскалация: когда не могу решить

**Если документация недоступна / ломается / непонятна:**

Попросить Виктора использовать "Ask AI" в документации Recall.ai:
> "Виктор, я не могу найти информацию о [конкретный вопрос]. Пожалуйста, задай этот вопрос через 'Ask AI' на docs.recall.ai и скопируй ответ сюда."

### Library IDs для Context7

| Сервис | Library ID |
|--------|------------|
| Recall.ai | `/websites/recall_ai` |
| Soniox | использовать при наличии |
| n8n | использовать при наличии |

---

## Субагенты

AI-специалисты с изолированным контекстом. Claude делегирует им задачи автоматически или по запросу.

**Расположение:** `.claude/agents/*.md`

### Механика загрузки

```
Старт сессии → сканирует .claude/agents/ → загружает name + description (~100 токенов на агента)

Вызов субагента → загружает полный system prompt → изолированный контекст (200k токенов)
```

- При старте: координатор видит только description
- При вызове: субагент получает system prompt, НЕ видит историю диалога
- После выполнения: контекст субагента освобождается, не засоряет основной чат

### Главное правило

**Prompt = ЧТО делать. System prompt = КАК делать.**

Детальный чеклист в prompt **перебивает** system prompt субагента. Субагент выполнит буквально то, что в prompt, игнорируя свою инструкцию.

### Формат вызова субагента

```
[ЗАДАЧА]: краткое описание
[ФАЙЛЫ]: путь — новый/обновлён
[СВЯЗИ]: для обратных ссылок (если нужно)
```

**Никаких чеклистов и алгоритмов** — всё это в инструкции субагента.

### Обработка результата субагента

**Правило проверки коллизий (для context-editor):**

- **Проверять** — если изменения могут затрагивать другие файлы
- **Не проверять** — если мелкие правки внутри файла, гарантированно не влияющие на другие
- **Сомневаешься — проверяй**

### Формат description субагента

```yaml
description: "Когда использовать. ФОРМАТ вызова: [ЗАДАЧА] + [ФАЙЛЫ]."
```

Description должен объяснять координатору КОГДА вызывать и В КАКОМ ФОРМАТЕ передавать задачу.

**Вызов:**
```
# Автоматически — Claude решает по description
> "Создай workflow для транскрибации"

# Явно
> "Используй n8n-expert для создания webhook"

# Список
> /agents
```

### Формат файла субагента

```markdown
---
name: n8n-expert
description: "Создание n8n workflow. Используй для любых задач с workflow, webhooks, интеграциями."
tools: Read, Write, Edit, Bash
model: sonnet
---

Ты n8n-разработчик проекта svaib.

## Контекст
Прочитай: dev/dev_context/svaib_architecture.md

## Правила
- Используй MCP n8n-mcp для документации и API
- Валидируй workflow перед деплоем
```

**Поля frontmatter:**
- `name` — имя (обязательно)
- `description` — когда использовать (обязательно, это главный триггер)
- `tools` — доступные инструменты через запятую (опционально, по умолчанию все)
- `model` — модель: sonnet, opus, haiku (опционально)

**Документация:** https://docs.claude.com/en/docs/claude-code/sub-agents

---

### Взаимодействие координатор-субагент

**Что субагент видит:**
- Задание от координатора (verbatim)
- Свой системный промпт (`.claude/agents/*.md`)
- Файлы проекта (через Read/Glob/Grep)
- **НЕ видит:** историю диалога, предыдущий контекст разговора

**Что координатор получает:**
- Только финальный результат субагента
- НЕ видит внутренние рассуждения и промежуточные шаги

**Workflow координатора:**
1. Сформулировать конкретное задание для субагента
2. Дождаться результата
3. **Проверить через `git diff`** — что именно изменилось
4. Если нужны уточнения — `resume agent <id>`
5. Показать пользователю проверенный результат

**Как координатор выбирает субагента:**
Субагенты видны как инструменты (наряду с Read, Write, Bash). Description = критерий выбора. Чем точнее description описывает текущую задачу, тем выше шанс автоматического вызова.

**Best practices для субагентов:**

| Аспект | Рекомендация |
|--------|--------------|
| Description | Добавлять триггеры: "ИСПОЛЬЗУЙ ПРОАКТИВНО", "ОБЯЗАТЕЛЬНО использовать при..." |
| Контекст | В начале промпта указать какие файлы читать: "Прочитай: `path/to/file.md`" |
| Возврат | Субагент должен возвращать список изменённых файлов (абсолютные пути) |
| Single Source | Не дублировать правила — ссылаться на SOURCE файлы |
| Изоляция | Помнить: субагент НЕ видит историю диалога, писать полное ТЗ |

---

## Скиллы

Папки с инструкциями и скриптами для повторяемых задач. Claude загружает автоматически по контексту.

**Расположение:** `.claude/skills/`

**Работают:** Claude Code, Claude.ai, API

### Структура

```
skill-name/
├── SKILL.md           ← инструкции + YAML frontmatter (обязательно)
├── scripts/           ← исполняемый код
├── references/        ← документация
└── assets/            ← шаблоны, файлы для вывода
```

**Документация:** https://support.claude.com/en/articles/12512176-what-are-skills

---

## Skills vs Subagents

|  | Skills | Subagents |
|---|---|---|
| При старте | ~50 токенов (metadata) | ~100 токенов (description) |
| При вызове | В текущий контекст (<5k) | Изолированный контекст (200k) |
| Засоряет чат? | Да | Нет |
| После выполнения | Остаётся в контексте | Контекст освобождается |

### Когда что использовать

**Skills** — процедурное знание, нужное периодически:
- Brand guidelines, coding standards
- Шаблоны документов
- Справочная информация

**Subagents** — задачи которые:
- Требуют много контекста (исследование кодовой базы)
- Засоряют чат промежуточными шагами
- Могут выполняться параллельно
- Нужна изоляция от основного контекста

---

## Claude for Chrome

GUI-инструмент для работы с браузером. **Интегрирован с Claude Code** через CLI (с версии 2.0.73).

### Как вызвать

```bash
claude --chrome -p "задача"
```

Выполняется через Bash tool. Chrome extension управляет браузером.

### Что умеет

| Возможность | Описание |
|-------------|----------|
| Открывать страницы | Навигация по URL |
| Скриншоты | Видит интерфейс как человек |
| Кликать и заполнять | Кнопки, формы, меню |
| Multi-tab | Несколько вкладок одновременно |
| Console logs | Читает ошибки браузера |

### Ограничения

- Не работает с финансовыми сервисами (банки, крипто)
- Медленнее человека (скриншот после каждого действия)
- Нужен открытый Chrome с extension 1.0.36+

---

## Структура файлов проекта

```
.claude/
├── agents/          ← субагенты
└── skills/          ← скиллы

~/.claude.json       ← MCP-серверы (user-level, не в проекте!)

dev/
├── prompts/         ← промпты ролей
└── dev_context/     ← документация

CLAUDE.md            ← общие правила проекта
```

---

## Ссылки

| Что | Документация |
|-----|--------------|
| Claude Code | https://docs.claude.com/en/docs/claude-code/overview |
| MCP | https://docs.claude.com/en/docs/mcp |
| Субагенты | https://docs.claude.com/en/docs/claude-code/sub-agents |
| Скиллы | https://support.claude.com/en/articles/12512176-what-are-skills |
| n8n-mcp | https://github.com/czlonkowski/n8n-mcp |
| supabase-mcp | https://supabase.com/docs/guides/getting-started/mcp |
| context7 | https://github.com/upstash/context7 |
| Claude for Chrome | https://support.claude.com/en/articles/12431227-simplify-your-browsing-experience-with-claude-for-chrome |