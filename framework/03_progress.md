---
title: "Framework — хроника"
updated: 2026-04-20
version: 1
scope: product_core
type: log
---

# Framework — хроника

## Кратко

Журнал сделанного по направлению. Завершённые задачи, ключевые сдвиги, значимые релизы частей фреймворка. Не дублирует [_inbox/_worklog.md](_inbox/_worklog.md) (активная задача) и не дублирует meta `session-log.md` (процесс работы с Claude). Даёт **результат** в домене — что было готово когда.

**Работа с файлом:** log — дописывать при завершении значимой задачи по направлению или релизе части фреймворка. Не менять старые записи. Формат: дата → 1-3 строки (что сделано, ссылка на артефакт если есть).

## Связанные файлы

- [01_overview.md](01_overview.md) — обзор направления (миссия, стадия, цель декады)
- [02_active.md](02_active.md) — что в работе сейчас
- [_inbox/_worklog.md](_inbox/_worklog.md) — активная задача (временно, до Фазы 3 миграции)
- [../meta/management/04_weekly_progress.md](../meta/management/04_weekly_progress.md) — агрегатор по всем направлениям

---

## 2026-04-20 · Work model v2 approved

Спроектирована модель универсального шаблона управления работой в направлениях svaib (`_inbox/01_inbox` + `01_overview` + `02_active` с Session Handoff + `03_progress` + расширения `02_backlog`/`04_decisions`). [work_model_spec.md v2](_inbox/work_model_spec.md) approved, собран план миграции Фаз 2 и 3 с правилом безопасности переноса.

## 2026-04-15 · Создан слой memory/ (6-я часть фреймворка)

Перенесён workbench контекстной памяти → `01_context_memory.md`. `file_spec.md` переехал из `ontology/` в `memory/`. Обновлены `architecture.md` v8, `README.md` v7 («шесть частей» + memory в диаграмме и таблице), 5 сервисных файлов.
