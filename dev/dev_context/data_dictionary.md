---
title: "Справочник сущностей системы svaib"
updated: 2025-12-25
version: 3
scope: "development"
priority: high
---

# Справочник сущностей системы svaib

## Кратко

Справочник сущностей системы svaib. Источник правды — таблицы `prompt_roles` и `document_types` в БД. Этот файл — человекочитаемая документация.

## Связанные файлы

- data_model.md — структура таблиц (типы полей, FK, constraints)
- workflows.md — реализация: data flow, структура workflows, контракты промптов
- architecture.md — архитектурный контракт

---

## Prompt Roles

Роли AI-промптов в пайплайне обработки встреч.

| Key | Название | Описание | Вход → Выход |
|-----|----------|----------|--------------|
| meeting_cleaner | Очистка транскрипта | Сжатие и нормализация сырого транскрипта | raw transcript → cleaned markdown |
| meeting_analyst | Аналитик встречи | Извлекает всё важное с опорами-цитатами | cleaned transcript + dossier → RAW_ANALYSIS |
| meeting_protocol_finalizer | Финализатор протокола | Классификация, фильтрация, проверка повторов | RAW_ANALYSIS + dossier → CANONICAL_PROTOCOL |
| meeting_protocol_telegram | Форматировщик Telegram | Добавляет эмодзи, разбивает на сообщения | CANONICAL_PROTOCOL → telegram message |
| meeting_docs_editor | Редактор документов | Обновляет досье клиента | CANONICAL_PROTOCOL + dossier → updated dossier |
| meeting_task_extractor | Извлечение задач | Достаёт задачи, дедлайны, ответственных | CANONICAL_PROTOCOL → JSON tasks |

**Таблица в БД:** `prompt_roles`

**Порядок в пайплайне (разветвление после finalizer):**
```
meeting_cleaner → meeting_analyst → meeting_protocol_finalizer → meeting_protocol_telegram
                                                              ↘ meeting_docs_editor
                                                              ↘ meeting_task_extractor
```

> **Связанные документы:** `_inbox/meeting_protocol_ontology.md`, `_inbox/dossier_structure.md`

---

## Document Types

Типы документов в системе.

| Key | Название | Описание | Уникальность |
|-----|----------|----------|--------------|
| dossier | Досье клиента | Накопительный документ знаний о проекте клиента. Обновляется после каждой встречи. | Один на клиента |
| meeting_protocol | Протокол встречи | Итог встречи: решения, договорённости, задачи, контекст. | Один на встречу |
| project_goals | Цели проекта | Цели, метрики, критерии успеха. | Один на клиента |
| project_roadmap | Роадмап проекта | План работ, этапы, вехи. | Один на клиента |
| project_team | Команда проекта | Роли, участники, зоны ответственности. | Один на клиента |
| glossary | Глоссарий | Термины и определения проекта. | Один на клиента |

**Таблица в БД:** `document_types`

---

## Как добавить новую сущность

### Новая роль промпта

1. Добавить запись в таблицу `prompt_roles`:
   ```sql
   INSERT INTO prompt_roles (key, title, description)
   VALUES ('new_role', 'Название', 'Описание');
   ```
2. Обновить этот файл (data_dictionary.md)
3. Создать запись в таблице `prompts` с новой ролью

### Новый тип документа

1. Добавить запись в таблицу `document_types`:
   ```sql
   INSERT INTO document_types (key, title, description, is_unique_per_client, is_unique_per_meeting)
   VALUES ('new_type', 'Название', 'Описание', true, false);
   ```
2. Обновить этот файл (data_dictionary.md)

---

## Статусы встречи (meetings.status)

| Статус | Описание | Следующий |
|--------|----------|-----------|
| scheduled | Встреча запланирована, бот создан | recording |
| recording | Идёт запись | recorded |
| recorded | Запись завершена, аудио получено | transcribed |
| transcribed | Транскрипт готов | processing |
| processing | AI обрабатывает (защита от гонок) | processed |
| processed | Протокол создан, задачи извлечены | — |
| failed | Ошибка на любом этапе | — |
