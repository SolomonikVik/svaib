---
title: "Pipelines & Data Flow"
updated: 2025-12-29
version: 1.3
scope: "implementation"
priority: high
---

# Pipelines & Data Flow

## Кратко

Реализация системы svaib: потоки данных между компонентами, структура n8n workflows, контракты AI-промптов, маппинг плейсхолдеров к источникам данных. Этот файл отвечает на вопрос "КАК работает система".

## Связанные файлы

- architecture.md — архитектурный контракт (ЧТО строим)
- infrastructure.md — инвентаризация ресурсов (credentials, URLs)
- data_model.md — структура таблиц БД
- data_dictionary.md — справочник значений (prompt_roles, document_types)
- _inbox/prompts_draft.md — черновики промптов (детали контрактов)

---

## 1. Общий поток данных

```
Telegram (chat_id)
    │
    ▼
┌─ meeting_create_bot ──────────────────────┐
│  1. Найти/создать client по chat_id       │
│  2. Создать meeting (status: scheduled)   │
│  3. Создать бота Recall.ai                │
│  4. Сохранить recall_bot_id в meeting     │
└───────────────────────────────────────────┘
    │
    ▼
Recall.ai (запись встречи)
    │
    ▼ webhook: audio_mixed.done
┌─ recall_webhook_receiver ─────────────────┐
│  1. Найти meeting по recall_bot_id        │
│  2. Создать pipeline_run (soniox_job_id)  │
│  3. Обновить meeting.status → recorded    │
│  4. Отправить аудио в Soniox              │
└───────────────────────────────────────────┘
    │
    ▼
Soniox (транскрибация)
    │
    ▼ webhook: completed
┌─ soniox_webhook_receiver ─────────────────┐
│  1. Найти pipeline_run по soniox_job_id   │
│  2. Получить meeting_id                   │
│  3. Создать transcript                    │
│  4. Обновить meeting.status → transcribed │
│  5. Обновить pipeline_run.status          │
└───────────────────────────────────────────┘
    │
    ▼
┌─ meeting_process_transcript ──────────────┐
│  AI Pipeline (SGR) — см. секцию 3         │
│  → Протокол в Telegram                    │
│  → Досье обновлено                        │
│  → Задачи сохранены                       │
└───────────────────────────────────────────┘
```

---

## 2. Workflows (n8n)

### Каталог

| ID | Название | Trigger | Результат | Статус |
|----|----------|---------|-----------|--------|
| kG4emaP9j50nZoGu | meeting_create_bot | Telegram message | meeting создан, recall_bot запущен | ✅ |
| 4v1G30AX1eHfRQjF | recall_webhook_receiver | Webhook Recall.ai | audio отправлен в Soniox | ✅ |
| 51ZGGJZp5sINBsQy | soniox_webhook_receiver | Webhook Soniox | transcript → meeting_process_transcript | ✅ |
| vO3W2eWVBCMwuLTi | test_supabase_connection | Manual | Тест подключения | ✅ |
| uZpjaRlzrSb4mBtV | meeting_process_transcript | Execute Workflow Trigger | Протокол → Telegram → status=processed | ✅ |

### 2.1 meeting_create_bot

**ID:** `kG4emaP9j50nZoGu`
**Trigger:** Telegram message с URL встречи
**Дата создания:** 17.12.2025

```
Telegram Trigger → Parse Command → Has Valid URL?
    [true]  → Upsert Client (PG) → Create Meeting → Recall.ai → Update Meeting (PG) → Reply Success
    [false] → Reply Error Format
```

**Credentials:**
- `Supabase Postgres` (hsHQlDm7rm2EsEGu) — PostgreSQL UPSERT надёжнее Supabase node
- `Telegram svaib` (thIFX3ToFrZky7ka)
- `Recall.ai` (5KV81RaV9Gn79hUo)

**Ключевые решения:**
- Используем PostgreSQL UPSERT для клиентов (ON CONFLICT)
- Сохраняем `recall_bot_id` в meeting для связи с webhook

### 2.2 recall_webhook_receiver

**ID:** `4v1G30AX1eHfRQjF`
**Trigger:** Webhook от Recall.ai (event: `audio_mixed.done`)
**Дата создания:** 17.12.2025

```
Webhook → Parse → Is Bot Done? → Get Bot → Get Audio → Soniox Transcribe → Find Meeting → Create Pipeline Run → Update Meeting → Respond
```

**Credentials:**
- `Recall.ai` (5KV81RaV9Gn79hUo)
- `Soniox` (UlRllRLpPr7ylsXa)
- `Supabase Postgres` (hsHQlDm7rm2EsEGu)

**Ключевые решения:**
- Используем `audio_mixed` (не `audio_separate`) — Soniox сам диаризует
- `pipeline_runs.metadata` хранит `soniox_job_id` для связи с Soniox webhook
- `insert` операция вместо `executeQuery` для INSERT (баг n8n #16354)

### 2.3 soniox_webhook_receiver

**ID:** `51ZGGJZp5sINBsQy`
**Trigger:** Webhook от Soniox (status: `completed`)
**Webhook URL:** `https://svaib-app.app.n8n.cloud/webhook/soniox-transcript`
**Дата создания:** 17.12.2025

```
Webhook → Is Completed? → Get Transcript → Parse Transcript → Find Pipeline Run → Save Transcript → Update Meeting → Update Pipeline Run → Respond OK
```

**Credentials:**
- `Soniox` (UlRllRLpPr7ylsXa)
- `Supabase Postgres` (hsHQlDm7rm2EsEGu)

**Ключевые решения:**
- Ищем `pipeline_run` по `soniox_job_id` в metadata (JSONB)
- `JSON.stringify()` для JSONB полей (speakers)
- Сохраняем в `transcripts.content`, `cleaned_content` заполняется позже

### 2.4 meeting_process_transcript

**ID:** `uZpjaRlzrSb4mBtV`
**Trigger:** Execute Workflow Trigger (вызывается из soniox_webhook_receiver)
**Дата создания:** 29.12.2025
**Статус:** ✅ active (20 nodes)

```
Execute Workflow Trigger
    │ (meeting_id, client_id, transcript_id)
    ▼
Lock Meeting (UPDATE...WHERE status='transcribed' RETURNING)
    │
    ▼
Check Lock (IF: notEquals $json.id "")
    │
    ├─[false]→ No Action (exit)
    │
    └─[true]→ ┬─ Load Transcript
              ├─ Load Dossier (alwaysOutputData: true)
              └─ Load Prompts
                    │ (параллельно)
                    ▼
              Run Cleaner (дешёвая)
                    │
                    ▼
              Run Analyst (умная)
                    │
                    ▼
              Run Finalizer (умная)
                    │
                    ▼
              Save Protocol (documents)
                    │
                    ▼
              Run Telegram Format (дешёвая)
                    │
                    ▼
              Prepare Telegram (Code: split по 4096)
                    │
                    ▼
              Split In Batches (output[1]=loop)
                    │
                    ▼
              Send Telegram → обратно в Split
                    │
                    ▼ (output[0]=done)
              Update Status (status='processed')
                    │
                    ▼
              Respond OK
```

**Credentials:**
- `Supabase Postgres` (hsHQlDm7rm2EsEGu)
- `OpenAi account` (5QtuGFTAdv2v9S7V)
- `Telegram svaib` (thIFX3ToFrZky7ka)

**Защита от гонок:**
```sql
UPDATE meetings
SET status = 'processing'
WHERE id = $meeting_id AND status = 'transcribed'
RETURNING *
```
Если RETURNING пустой → уже обрабатывается другим процессом, выходим.

**Известные особенности:**
- `alwaysOutputData: true` на Load Dossier — продолжает pipeline если досье нет
- IF node с `notEquals` вместо `isNotEmpty` — MCP-ограничение
- splitInBatches: output[0]=done, output[1]=loop (противоинтуитивно)

---

## 3. AI Pipeline (SGR)

### 3.1 Схема цепочки

```
meeting_cleaner → meeting_analyst → meeting_protocol_finalizer
                                                            ↘ meeting_protocol_telegram
                                                            ↘ meeting_docs_editor
                                                            ↘ meeting_task_extractor
```

Шаги 3-5 выполняются параллельно (все получают CANONICAL_PROTOCOL).

### 3.2 Контексты: кто что получает

| Промпт | Transcript | Dossier | RAW_ANALYSIS | CANONICAL_PROTOCOL |
|--------|------------|---------|--------------|-------------------|
| meeting_cleaner | ✅ (raw) | ❌ | — | — |
| meeting_analyst | ✅ (cleaned) | ✅ | — | — |
| meeting_protocol_finalizer | ❌ | ✅ | ✅ | — |
| meeting_protocol_telegram | ❌ | ❌ | ❌ | ✅ |
| meeting_docs_editor | ❌ | ✅ | ❌ | ✅ |
| meeting_task_extractor | ❌ | ❌ | ❌ | ✅ |

**Важно:** История протоколов НЕ передаётся. Досье — единственный источник контекста.

### 3.3 Контракты промптов

| # | Промпт | Вход | Выход | Версия |
|---|--------|------|-------|--------|
| 0 | meeting_cleaner | transcripts.content | Очищенный текст (2-3× сжатие) | v1 |
| 1 | meeting_analyst | cleaned + dossier | RAW_ANALYSIS (кандидаты с опорами) | v2.1 |
| 2 | meeting_protocol_finalizer | RAW_ANALYSIS + dossier | CANONICAL_PROTOCOL (markdown) | v2.1 |
| 3 | meeting_protocol_telegram | CANONICAL_PROTOCOL | Telegram-сообщение с эмодзи | v1.1 |
| 4 | meeting_docs_editor | CANONICAL_PROTOCOL + dossier | Полный текст досье | ⏳ |
| 5 | meeting_task_extractor | CANONICAL_PROTOCOL | JSON: [{title, assignee, deadline, priority}] | ⏳ |

**Детали контрактов:** См. `_inbox/prompts_draft.md` секция "3. Контракты промптов"

### 3.4 Маппинг плейсхолдеров

| Плейсхолдер | Таблица.поле | Как получить |
|-------------|--------------|--------------|
| `{{project_name}}` | clients.name | `SELECT c.name FROM clients c JOIN meetings m ON m.client_id = c.id WHERE m.id = $meeting_id` |
| `{{meeting_date}}` | meetings.scheduled_at | `SELECT scheduled_at FROM meetings WHERE id = $meeting_id` |
| `{{participants}}` | meetings.participants | MVP: "unknown". Задача в product_sprint.md |
| `{{transcript}}` | transcripts.cleaned_content | `SELECT COALESCE(cleaned_content, content) FROM transcripts WHERE meeting_id = $meeting_id ORDER BY created_at DESC LIMIT 1` |
| `{{dossier}}` | documents.content | `SELECT content FROM documents WHERE client_id = $client_id AND doc_type = 'dossier'` |

### 3.5 Шаблон входных данных для meeting_analyst

```
## МЕТАДАННЫЕ ВСТРЕЧИ
Проект: {{project_name}}
Дата: {{meeting_date}}
Участники: {{participants}}

## ДОСЬЕ ПРОЕКТА
{{dossier}}

## ТРАНСКРИПЦИЯ
{{transcript}}
```

---

## 4. Сохранение результатов

После AI Pipeline:

```
1. UPSERT documents (досье)
   → client_id + doc_type = 'dossier'
   → Обновляем content

2. INSERT documents (протокол)
   → doc_type = 'meeting_protocol', meeting_id = $meeting_id
   → UNIQUE (meeting_id, doc_type) гарантирует один протокол на встречу

3. INSERT tasks
   → svaib_task_id = hash(meeting_id + normalized(title) + assignee)
   → Идемпотентность: проверяем существование перед INSERT

4. UPDATE pipeline_runs
   → status = 'completed', metadata = {...}

5. UPDATE meetings
   → status = 'processed'

6. Telegram Send Message
   → Если > 4096 символов → split по секциям
```

---

## 5. Логирование (pipeline_runs.metadata)

```json
{
  "steps": [
    {"prompt_role": "meeting_cleaner", "prompt_version": 1},
    {"prompt_role": "meeting_analyst", "prompt_version": 1},
    {"prompt_role": "meeting_protocol_finalizer", "prompt_version": 1},
    {"prompt_role": "meeting_protocol_telegram", "prompt_version": 1}
  ],
  "transcript_raw_length": 12345,
  "transcript_clean_length": 4567,
  "transcript_compression_ratio": 2.7,
  "transcript_used": "clean",
  "protocol_length": 2847,
  "telegram_messages_count": 1
}
```

---

## 6. Известные ограничения и баги

| Проблема | Решение | Где задокументировано |
|----------|---------|----------------------|
| n8n queryReplacement ломается на запятых (#16354) | Использовать `insert` операцию, не `executeQuery` | claude_code_mechanics.md |
| Webhook workflow создаётся только через UI | UI создаёт → MCP дорабатывает | claude_code_mechanics.md |
| Telegram лимит 4096 символов | Split по секциям в meeting_protocol_telegram | prompts_draft.md |
| meetings.participants — нет поля | MVP: "unknown", задача в product_sprint.md | — |

---

## 7. Внешние источники данных

### 7.1 Recall.ai

| Данные | Endpoint | Где сохранить |
|--------|----------|---------------|
| Участники | `participants_download_url` | meetings.participants |
| Метаданные | `meeting_metadata.data` | meetings.title |
| Аудио | `audio_mixed.download_url` | → Soniox |

**Требование:** При создании бота добавить `"participant_events": {}` в recording_config.

### 7.2 Soniox

| Данные | Поле | Где сохранить |
|--------|------|---------------|
| Транскрипт | `result.words[]` | transcripts.content |
| Спикеры | `result.words[].speaker` | transcripts.speakers |

**Ограничение:** Soniox даёт Speaker 0, 1, 2 — не имена. Сопоставление с именами через team_members.aliases (Phase 2).
