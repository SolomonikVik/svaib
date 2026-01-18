---
title: "Модель данных Supabase"
updated: 2025-12-25
version: 5
scope: "development"
priority: high
---

# Модель данных Supabase

## Кратко

Детальная структура таблиц Supabase: типы полей, FK-связи, constraints. Используется для работы с Claude Chat (у которого нет MCP). Claude Code может получить актуальную схему через `mcp__supabase__list_tables`.

## Связанные файлы

- architecture.md — архитектурный контракт (концептуальное описание схемы)
- workflows.md — реализация: data flow, структура workflows, контракты промптов
- data_dictionary.md — справочник сущностей (роли промптов, типы документов)
- infrastructure.md — credentials и подключения к Supabase

---

> **Source of truth:** Supabase MCP `list_tables`
>
> При изменении схемы в Supabase — обновить этот файл.

## Диаграмма связей

```
┌─ Справочники ─────────────────────────────┐
│                                           │
│  prompt_roles ◄──── prompts.role          │
│  document_types ◄── documents.doc_type    │
│                                           │
└───────────────────────────────────────────┘

clients
  ├── team_members
  ├── oauth_tokens
  ├── prompts (кастомные, client_id NOT NULL)
  ├── documents (досье, протоколы)
  ├── meetings
  │     ├── transcripts
  │     ├── tasks
  │     ├── documents (протоколы встреч)
  │     └── pipeline_runs
  └── pipeline_runs

prompts (системные: client_id IS NULL)
  └── client_id → clients (кастомные промпты)
```

---

## Справочники

### prompt_roles

Справочник ролей AI-промптов в пайплайне обработки встреч.

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| key | text | PK | required | Уникальный ключ роли (snake_case) |
| title | text | — | required | Название на русском |
| description | text | — | optional | Описание роли |
| is_active | boolean | — | required | default true |
| created_at | timestamptz | — | optional | default now() |
| updated_at | timestamptz | — | optional | default now() |

**Значения:** meeting_cleaner, meeting_analyst, meeting_protocol_finalizer, meeting_protocol_telegram, meeting_docs_editor, meeting_task_extractor

### document_types

Справочник типов документов в системе.

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| key | text | PK | required | Уникальный ключ типа (snake_case) |
| title | text | — | required | Название на русском |
| description | text | — | optional | Описание типа |
| template_md | text | — | optional | Шаблон документа (TODO Phase 2) |
| is_unique_per_client | boolean | — | required | default false |
| is_unique_per_meeting | boolean | — | required | default false |
| is_active | boolean | — | required | default true |
| created_at | timestamptz | — | optional | default now() |
| updated_at | timestamptz | — | optional | default now() |

**Значения:** dossier, meeting_protocol, project_goals, project_roadmap, project_team, glossary

---

## Таблицы

### clients

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | uuid_generate_v4() |
| name | text | — | required | |
| google_folder_id | text | — | optional | |
| telegram_chat_id | text | — | optional | UNIQUE |
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
| status | text | — | optional | default 'scheduled', check: scheduled, recording, recorded, transcribed, processing, processed, failed |
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
| cleaned_content | text | — | optional | Очищенный текст после meeting_cleaner |
| speakers | jsonb | — | optional | default '[]', массив {speaker, text} |
| asr_provider | text | — | optional | check: soniox, elevenlabs, other |
| duration_seconds | integer | — | optional | |
| created_at | timestamptz | — | optional | default now() |

### prompts

AI-промпты с версионированием. Системные промпты (client_id IS NULL) видны всем, кастомные — только владельцу.

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| role | text | FK→prompt_roles | required | Роль промпта |
| content | text | — | required | Текст промпта |
| version | integer | — | required | default 1 |
| is_active | boolean | — | required | default true |
| client_id | uuid | FK→clients | optional | NULL = системный, UUID = кастомный |
| created_at | timestamptz | — | optional | default now() |

**Constraint:** Одна активная версия на (role, client_id) — partial unique index.

**Логика выбора промпта:**
```sql
SELECT * FROM prompts
WHERE role = $1 AND is_active = true
  AND (client_id = $2 OR client_id IS NULL)
ORDER BY client_id NULLS LAST
LIMIT 1
```

### documents

Текстовый контент проекта: досье, протоколы, цели, roadmap, команда, глоссарий.

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| client_id | uuid | FK→clients | required | |
| meeting_id | uuid | FK→meetings | optional | Для протоколов |
| doc_type | text | FK→document_types | required | Тип документа |
| title | text | — | optional | Для отображения |
| content | text | — | required | Markdown |
| source | text | — | required | check: svaib, client |
| external_file_id | text | — | optional | Reserved for Google Drive link |
| created_at | timestamptz | — | optional | default now() |
| updated_at | timestamptz | — | optional | default now() |

**Индексы:**
- UNIQUE (client_id, doc_type) WHERE meeting_id IS NULL — для "одна на клиента"
- UNIQUE (meeting_id, doc_type) WHERE meeting_id IS NOT NULL — для протоколов
- INDEX (client_id, doc_type, created_at DESC) — для выборки истории протоколов

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

---

## Vote Module (Internal Tool)

Изолированный модуль для взвешенного голосования на стратсессиях. Не связан с основной схемой — все таблицы с префиксом `vote_`.

### Диаграмма связей

```
vote_sessions
  ├── vote_participants (session_id FK)
  ├── vote_projects (session_id FK)
  └── vote_ballots (через participant_id)
        └── vote_participants.id FK
        └── vote_projects.id FK
```

### vote_sessions

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | uuid_generate_v4() |
| name | text | — | required | Название сессии |
| status | text | — | required | default 'draft', check: draft, voting, completed |
| created_at | timestamptz | — | optional | default now() |
| completed_at | timestamptz | — | optional | Когда завершено голосование |

### vote_participants

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| session_id | uuid | FK→vote_sessions | required | ON DELETE CASCADE |
| name | text | — | required | Имя участника |
| position | text | — | required | check: CEO, C-1, C-2, Специалист |
| weight | integer | — | required | check: 1, 2, 3, 5 (вес голоса) |
| has_voted | boolean | — | required | default false |
| created_at | timestamptz | — | optional | default now() |

**Constraint:** UNIQUE (session_id, name)

**Весовая система:**
| Position | Weight |
|----------|--------|
| CEO | 5 |
| C-1 (CTO, CFO...) | 3 |
| C-2 (Directors) | 2 |
| Специалист | 1 |

### vote_projects

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| session_id | uuid | FK→vote_sessions | required | ON DELETE CASCADE |
| name | text | — | required | Название проекта |
| description | text | — | optional | Комментарий |
| order_index | integer | — | required | default 0, для сортировки |
| created_at | timestamptz | — | optional | default now() |

**Constraint:** UNIQUE (session_id, name)

### vote_ballots

Закрытое голосование — RLS блокирует чтение для anon. Результаты доступны только через API после завершения.

| Поле | Тип | Связь | Обязательность | Примечание |
|------|-----|-------|----------------|------------|
| id | uuid | PK | auto | |
| participant_id | uuid | FK→vote_participants | required | ON DELETE CASCADE |
| project_id | uuid | FK→vote_projects | required | ON DELETE CASCADE |
| votes_given | integer | — | required | check: 1 или 2 |
| created_at | timestamptz | — | optional | default now() |

**Constraint:** UNIQUE (participant_id, project_id)

**Правила голосования:**
- Количество голосов на участника = ceil(количество_проектов / 2)
- За один проект: 0, 1 или 2 голоса
- Итоговый балл = Σ(votes_given × participant.weight)

---

## Таблицы НЕ созданы (запланированы)

| Таблица | Фаза | Назначение |
|---------|------|------------|
| files | MVP (Неделя 4-5) | Карта файлов Google Drive для RAG (google_file_id, mime_type, summary, indexed_at) |
| reasoning_bank_items | Phase 2 | Паттерны команды |
| feedback | Phase 2 | Обратная связь от клиентов |
