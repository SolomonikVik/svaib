---
title: "Модель данных Supabase"
updated: 2025-12-22
version: 2
scope: "development"
priority: high
---

# Модель данных Supabase

## Кратко

Детальная структура таблиц Supabase: типы полей, FK-связи, constraints. Используется для работы с Claude Chat (у которого нет MCP). Claude Code может получить актуальную схему через `mcp__supabase__list_tables`.

## Связанные файлы

- architecture.md — архитектурный контракт (концептуальное описание схемы)
- infrastructure.md — credentials и подключения к Supabase

---

> **Source of truth:** Supabase MCP `list_tables`
>
> При изменении схемы в Supabase — обновить этот файл.

## Диаграмма связей

```
clients
  ├── team_members
  ├── oauth_tokens
  ├── documents (досье, протоколы)
  ├── meetings
  │     ├── transcripts
  │     ├── tasks
  │     ├── documents (протоколы)
  │     └── pipeline_runs
  └── pipeline_runs

prompts (системные: client_id IS NULL)
  └── client_id → clients (кастомные промпты)
```

---

## Таблицы

### clients

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | uuid_generate_v4() |
| name | text | — | required | |
| google_folder_id | text | — | optional | |
| telegram_chat_id | text | — | optional | |
| settings | jsonb | — | optional | default '{}' |
| created_at | timestamptz | — | optional | default now() |

### meetings

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| client_id | uuid | FK→clients | required | |
| title | text | — | optional | |
| platform | text | — | optional | check: zoom, meet, teams |
| meeting_url | text | — | optional | |
| recall_bot_id | text | — | optional | ID бота Recall.ai |
| status | text | — | optional | default 'scheduled', check: scheduled, recording, recorded, transcribed, **processing**, processed, failed |
| scheduled_at | timestamptz | — | optional | |
| started_at | timestamptz | — | optional | |
| ended_at | timestamptz | — | optional | |
| created_at | timestamptz | — | optional | default now() |

### transcripts

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| meeting_id | uuid | FK→meetings | required | |
| content | text | — | optional | Полный текст транскрипта (сырой) |
| cleaned_content | text | — | optional | Очищенный текст после transcript_cleaner |
| speakers | jsonb | — | optional | default '[]', массив {speaker, text} |
| asr_provider | text | — | optional | check: soniox, elevenlabs, other |
| duration_seconds | integer | — | optional | |
| created_at | timestamptz | — | optional | default now() |

### tasks

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| meeting_id | uuid | FK→meetings | required | |
| svaib_task_id | text | — | required, unique | Hash для идемпотентности |
| title | text | — | required | |
| assignee | text | — | optional | |
| deadline | date | — | optional | |
| priority | text | — | optional | check: high, medium, low |
| status | text | — | optional | default 'new', check: new, in_progress, done, cancelled |
| sheet_row_id | integer | — | optional | Reserved for Week 4 Google Sheets sync |
| created_at | timestamptz | — | optional | default now() |

### pipeline_runs

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| client_id | uuid | FK→clients | optional | |
| meeting_id | uuid | FK→meetings | optional | |
| pipeline | text | — | required | Название пайплайна |
| stage | text | — | required | Этап выполнения |
| status | text | — | optional | default 'started', check: started, completed, failed |
| error | text | — | optional | Текст ошибки |
| metadata | jsonb | — | optional | default '{}' |
| started_at | timestamptz | — | optional | default now() |
| finished_at | timestamptz | — | optional | |

### oauth_tokens

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| client_id | uuid | FK→clients | required | |
| access_token | text | — | required | TODO: шифрование |
| refresh_token | text | — | required | TODO: шифрование |
| expires_at | timestamptz | — | required | |
| scopes | text[] | — | optional | default '{}' |
| created_at | timestamptz | — | optional | default now() |

### team_members

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| client_id | uuid | FK→clients | required | |
| name | text | — | required | |
| email | text | — | optional | |
| telegram_username | text | — | optional | |
| role | text | — | optional | |
| aliases | text[] | — | optional | default '{}', альтернативные имена для диаризации |
| created_at | timestamptz | — | optional | default now() |

### prompts

AI-промпты с версионированием. Системные промпты (client_id IS NULL) видны всем, кастомные — только владельцу.

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| role | text | — | required | check: transcript_cleaner, meeting_analyst, meeting_critic, docs_editor, task_extractor |
| content | text | — | required | Текст промпта |
| version | integer | — | required | default 1 |
| is_active | boolean | — | required | default true |
| client_id | uuid | FK→clients | optional | NULL = системный, UUID = кастомный |
| created_at | timestamptz | — | optional | default now() |

**Constraint:** Одна активная версия на (role, client_id) — через partial unique index или логику в запросе.

**Логика выбора промпта:**
```sql
SELECT * FROM prompts
WHERE role = $1 AND is_active = true
  AND (client_id = $2 OR client_id IS NULL)
ORDER BY client_id NULLS LAST
LIMIT 1
```

### documents

Каноническое хранилище текстового контента проекта: досье, протоколы, цели, roadmap, команда, глоссарий.

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| client_id | uuid | FK→clients | required | |
| meeting_id | uuid | FK→meetings | optional | Для протоколов |
| doc_type | text | — | required | check: dossier, meeting_protocol, project_goals, project_roadmap, project_team, glossary |
| title | text | — | optional | Для отображения |
| content | text | — | required | Markdown |
| source | text | — | required | check: svaib, client |
| external_file_id | text | — | optional | Reserved for Google Drive link |
| created_at | timestamptz | — | optional | default now() |
| updated_at | timestamptz | — | optional | default now() |

**Правила уникальности:**
- `dossier`, `project_goals`, `project_roadmap`, `project_team`, `glossary` — одна запись на клиента (UPSERT)
- `meeting_protocol` — одна запись на встречу (UNIQUE meeting_id + doc_type)

**Индексы:**
- UNIQUE (client_id, doc_type) WHERE meeting_id IS NULL — для "одна на клиента"
- UNIQUE (meeting_id, doc_type) WHERE meeting_id IS NOT NULL — для протоколов
- INDEX (client_id, doc_type, created_at DESC) — для выборки истории протоколов

---

## Таблицы НЕ созданы (запланированы)

| Таблица | Фаза | Назначение |
|---------|------|------------|
| files | MVP (Неделя 4-5) | Карта файлов Google Drive для RAG (google_file_id, mime_type, summary, indexed_at) |
| reasoning_bank_items | Phase 2 | Паттерны команды |
| feedback | Phase 2 | Обратная связь от клиентов |
