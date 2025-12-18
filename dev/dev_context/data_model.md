---
title: "Модель данных Supabase"
updated: 2025-12-17
version: 1
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
  ├── meetings
  │     ├── transcripts
  │     ├── tasks
  │     └── pipeline_runs
  └── pipeline_runs
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
| status | text | — | optional | default 'scheduled', check: scheduled, recording, recorded, transcribed, processed, failed |
| scheduled_at | timestamptz | — | optional | |
| started_at | timestamptz | — | optional | |
| ended_at | timestamptz | — | optional | |
| created_at | timestamptz | — | optional | default now() |

### transcripts

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| meeting_id | uuid | FK→meetings | required | |
| content | text | — | optional | Полный текст транскрипта |
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
| sheet_row_id | integer | — | optional | Номер строки в Google Sheets |
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

---

## Таблицы НЕ созданы (запланированы)

| Таблица | Фаза | Назначение |
|---------|------|------------|
| documents | MVP (Неделя 5) | Карта файлов для RAG |
| prompts | MVP (Неделя 3) | AI-промпты с версионированием |
| reasoning_bank_items | Phase 2 | Паттерны команды |
| feedback | Phase 2 | Обратная связь от клиентов |
