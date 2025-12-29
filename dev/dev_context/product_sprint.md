---
title: "MVP Sprint — Week 3"
updated: 2025-12-29
version: 8
scope: "planning"
priority: critical
---

# MVP Implementation Roadmap — svaib

## Кратко

**Что:** MVP AI-ассистента для встреч. Бот записывает Zoom/Meet/Teams, транскрибирует, извлекает задачи, отправляет в Telegram и Google Sheets.

**Когда:** 5 недель, дедлайн 27 декабря 2025

**Где сейчас:** Неделя 3 — ✅ ЗАВЕРШЕНА (29.12.2025)

**Что сделано:** AI Pipeline работает end-to-end с GPT-5 моделями. Запись → транскрибация → протокол в Telegram. Досье и задачи — Неделя 4.

## Связанные файлы

- architecture.md — архитектурный контракт (что строим)
- infrastructure.md — текущие ресурсы (на чем строим)
- workflows.md — реализация: data flow, структура workflows, контракты промптов
- data_model.md — структура таблиц БД
- data_dictionary.md — справочник сущностей (prompt_roles, document_types, статусы)
- product_sprint_future.md — Недели 4-5, Phase 1-2

---

## Неделя 1: Фундамент — ✅ ЗАВЕРШЕНА

**Что сделано:**
- Google Cloud Project (svaib-app) + OAuth Consent Screen
- Supabase: 7 таблиц + RLS политики
- n8n Cloud (svaib-app.app.n8n.cloud)
- Recall.ai + Soniox зарегистрированы
- **ASR тест пройден — Soniox выбран** (качество хорошее, диаризация через раздельные треки)
- MCP-серверы: n8n-mcp, supabase-mcp, Context7

---

## Неделя 2: Запись и транскрибация — ✅ ЗАВЕРШЕНА (18.12.2025)

**Что сделано:**
- 3 workflow работают end-to-end (Telegram → Recall.ai → Soniox → Supabase)
- Полный pipeline: scheduled → recorded → transcribed
- Диаризация спикеров работает (audio_mixed + Soniox)
- pipeline_runs как "мост" между Soniox webhook и meeting
- Credentials настроены (см. infrastructure.md)

**Ключевые решения:**
- `audio_mixed` вместо `audio_separate` — упростило flow, Soniox сам диаризует
- `pipeline_runs.metadata` для хранения `soniox_job_id`
- `insert` операция вместо `executeQuery` для INSERT (баг n8n #16354)
- `JSON.stringify()` для JSONB полей

---

## Неделя 3: AI Pipeline (протокол + досье) — ТЗ v3.1

**Цель:** После транскрипции автоматически: качественный анализ → протокол в Telegram → обновление досье проекта.

> **Изменение приоритетов (22.12.2025):** До Нового года важнее запустить рабочий цикл с протоколом. Google Sheets sync переносится на Неделю 4.

### Ключевые решения

| Вопрос | Решение | Почему |
|--------|---------|--------|
| Задачи | Supabase (не Sheets пока) | Сохраняем в tasks, sync в Sheets — Неделя 4 |
| Документы | Одна таблица `documents` | Гибко, doc_type различает (dossier/meeting_protocol/...) |
| Досье | Supabase (не Google Docs) | Проще для MVP. Клиенту пока хватит Telegram |
| Контекст для анализа | Только досье | Досье — единственный источник контекста. История протоколов не передаётся. |
| Промпты | Supabase с версионированием | client_id nullable: NULL = системный, UUID = кастомный |
| Идемпотентность | Атомарный UPDATE на `processing` | Защита от гонок (см. ниже) |
| Предобработка | meeting_cleaner | Сжатие 2-3×, экономия токенов |

### Изменения в схеме БД

**Новые таблицы:** `prompts`, `documents` — см. [data_model.md](data_model.md)

**Изменения в существующих:**
- `transcripts` — добавить `cleaned_content TEXT NULL`
- `meetings` — добавить статус `processing` в CHECK constraint

### Архитектура workflow: `meeting_process_transcript`

**Trigger:** `meeting.status = 'transcribed'`

**Защита от гонок (атомарный UPDATE):**
```sql
UPDATE meetings
SET status = 'processing'
WHERE id = $meeting_id AND status = 'transcribed'
RETURNING *
```
Если RETURNING пустой → уже не `transcribed`, выходим.

---

#### Шаг 0: meeting_cleaner

Очистка сырой транскрипции от мусора, сжатие в 2-3 раза.

- **Модель:** актуальная дешёвая (спросить Виктора)
- **Вход:** `transcripts.content` (сырой)
- **Выход:** чистый транскрипт
- **Сохранение:** `UPDATE transcripts SET cleaned_content = $cleaned WHERE id = $transcript_id`
- **Fallback:** Если cleaner упал → продолжаем с raw content

---

#### Шаг 1: Загрузка контекста

```
1. SELECT meetings.id, meetings.client_id WHERE meetings.id = $meeting_id
2. SELECT * FROM transcripts WHERE meeting_id = $meeting_id ORDER BY created_at DESC LIMIT 1
   → Использовать cleaned_content, fallback на content
3. SELECT * FROM documents WHERE client_id = $client_id AND doc_type = 'dossier'
```

> **Примечание:** История протоколов не загружается. Досье — единственный источник контекста.

---

#### Шаг 2: Цепочка промптов (6 шагов, разветвление)

| # | role | Вход | Выход |
|---|------|------|-------|
| 0 | meeting_cleaner | Сырой транскрипт | Чистый транскрипт |
| 1 | meeting_analyst | Чистый транскрипт + досье | RAW_ANALYSIS (с опорами-цитатами) |
| 2 | meeting_protocol_finalizer | RAW_ANALYSIS + досье | CANONICAL_PROTOCOL (markdown) |
| 3 | meeting_protocol_telegram | CANONICAL_PROTOCOL | Telegram-сообщение с эмодзи |
| 4 | meeting_docs_editor | CANONICAL_PROTOCOL + досье | ПОЛНЫЙ обновлённый текст досье |
| 5 | meeting_task_extractor | CANONICAL_PROTOCOL | JSON массив задач |

> **Примечание:** Модель выбирается на этапе реализации. Шаги 3-5 выполняются параллельно (все получают CANONICAL_PROTOCOL).

**Контракты промптов:** См. `_inbox/prompts_draft.md` секция "3. Контракты промптов"
**Онтология протокола:** См. `_inbox/meeting_protocol_ontology.md`
**Структура досье:** См. `_inbox/dossier_structure.md`

---

#### Шаг 3: Сохранение

```
1. INSERT pipeline_runs (...) RETURNING id  ← в начале workflow
2. UPSERT documents (досье): client_id + doc_type = 'dossier'
3. INSERT documents (протокол): doc_type = 'meeting_protocol', meeting_id = $meeting_id
   → UNIQUE (meeting_id, doc_type) гарантирует один протокол на встречу
4. INSERT tasks (с генерацией svaib_task_id = hash(meeting_id + normalized(title) + assignee))
5. UPDATE pipeline_runs: status = 'completed', metadata = {...}
6. UPDATE meetings SET status = 'processed'
```

---

#### Шаг 4: Отправка в Telegram

**Лимит Telegram:** 4096 символов.

**Решение для MVP:**
- Если протокол ≤ 4096 → отправляем как есть
- Если > 4096 → split по разделам (если нет заголовков — по 3500-3800 символов)

---

### Логирование (pipeline_runs.metadata)

**Зачем:** Дебаг (где сломалось), метрики (экономия токенов), контроль (длинные протоколы).

```json
{
  "steps": [
    {"prompt_role": "meeting_cleaner", "prompt_version": 1},
    {"prompt_role": "meeting_analyst", "prompt_version": 1},
    {"prompt_role": "meeting_protocol_finalizer", "prompt_version": 1},
    {"prompt_role": "meeting_protocol_telegram", "prompt_version": 1}
  ],
  "transcript_raw_length": 12345,        // символов в сыром транскрипте
  "transcript_clean_length": 4567,       // после очистки (cleaner)
  "transcript_compression_ratio": 2.7,   // во сколько раз сжали
  "transcript_used": "clean",            // "clean" или "raw" (если cleaner упал)
  "protocol_length": 2847,               // длина готового протокола
  "telegram_messages_count": 1           // на сколько сообщений разбили (лимит 4096)
}
```

---

### Telegram Bot

- [x] @BotFather → создать бота (@svaib_bot, 15.12.2025)
- [x] Получить token, добавить в n8n credentials (Telegram svaib)

---

### Чеклист результатов Недели 3

**Схема БД (22.12.2025):**
- [x] Миграция: таблица `prompts`
- [x] Миграция: таблица `documents`
- [x] Миграция: `transcripts.cleaned_content`
- [x] Миграция: `meetings.status` += 'processing'
- [x] Миграция: справочник `prompt_roles` (5 ролей)
- [x] Миграция: справочник `document_types` (6 типов)
- [x] FK связи prompts→prompt_roles, documents→document_types

**Документация (23.12.2025):**
- [x] data_model.md обновлён (v3)
- [x] data_dictionary.md создан (v1)
- [x] architecture.md обновлён (v5)

**Промпты (25.12.2025):**
- [x] 4 промпта загружены в Supabase (meeting_cleaner, meeting_analyst, meeting_protocol_finalizer, meeting_protocol_telegram)
- [ ] 2 промпта в разработке (docs_editor, task_extractor) — отложены

**Workflow:**
- [x] `meeting_process_transcript` работает (20 нод, 29.12.2025)
- [x] Trigger на `status = 'transcribed'` (Execute Workflow Trigger)
- [x] Атомарная защита от гонок (UPDATE...WHERE status='transcribed' RETURNING)
- [x] Цепочка 4 промптов выполняется (cleaner → analyst → finalizer → telegram)
- [ ] Досье обновляется (UPSERT) — ⏳ docs_editor отложен на Неделю 4
- [x] Протокол сохраняется в documents
- [ ] Задачи сохраняются в tasks — ⏳ task_extractor отложен на Неделю 4
- [x] Протокол отправляется в Telegram (splitInBatches для длинных)
- [x] pipeline_runs логирует все шаги

**Тестирование:**
- [x] End-to-end тест пройден (29.12.2025)
- [x] Протокол приходит в Telegram
- [ ] Досье обновляется корректно — ⏳ отложено

---

## Реализация

> **Data flow, структура workflows, контракты промптов:** См. [workflows.md](workflows.md)

### Что перенесено

| Было в плане Недели 3 | Куда перенесено |
|-----------------------|-----------------|
| Google OAuth | Неделя 4 |
| Google Sheets sync | Неделя 4 |
| Google Drive (таблица files) | Неделя 4-5 |

### TODO: meetings.participants (~45 мин)

**Цель:** Получать имена участников из Recall.ai для промптов.

**Шаги:**
1. **Миграция:** `ALTER TABLE meetings ADD COLUMN participants JSONB DEFAULT '[]'`
2. **meeting_create_bot:** Добавить в recording_config: `"participant_events": {}`
3. **recall_webhook_receiver:** После Get Bot:
   - HTTP Request: GET `recordings[].participant_events.data.participants_download_url`
   - Распарсить JSON: `[{id, name, is_host, email}, ...]`
   - UPDATE meetings SET participants = $json

**Сейчас:** MVP работает с `"unknown"` — промпт это поддерживает.

---

## ⚠️ ОТЛОЖЕНО НА ПОТОМ (технический долг)

> Костыли, которые работают для MVP, но требуют доработки.

### Telegram: split длинных сообщений

**Проблема:** Промпт `meeting_protocol_telegram` не определяет формат для нескольких сообщений (если протокол > 4096 символов).

**Текущее решение (костыль):** Путь B — split в n8n Code Node
- Code Node проверяет длину, режет по `---` или по 3500-3800 символов
- Добавляет `(1/N)`, `(2/N)`
- SplitInBatches → Telegram Send

**Почему костыль:**
- Промпт уже в Supabase, менять = миграция
- LLM может ошибиться со счётом символов
- n8n точнее посчитает длину

**TODO потом:**
- [ ] Пересмотреть — может промпт должен сразу возвращать JSON array?
- [ ] Или сделать отдельный промпт для форматирования split?
- [ ] Или оставить как есть (n8n split работает стабильно)

### GPT-5: пустые options (workaround)

**Проблема (29.12.2025):** GPT-5 — reasoning models, не поддерживают `max_tokens` и `temperature`. n8n OpenAI node v1.1 отправляет эти параметры → API отклоняет.

**Текущее решение (workaround):** Убрать все параметры из `options: {}` — GPT-5 работает с дефолтами.

**Ограничения:**
- Нет контроля над temperature (всегда 1)
- Нет контроля над длиной ответа

**TODO потом:**
- [ ] Миграция на OpenAI node V2 (n8n v1.117.0+) — поддерживает reasoning models
- [ ] Или HTTP Request с ручным формированием body

**Детали:** См. `.claude/claude_code_mechanics.md` секция "GPT-5 (reasoning models)"

---

*Недели 4-5, Phase 1-2, бюджет, риски: [product_sprint_future.md](product_sprint_future.md)*
