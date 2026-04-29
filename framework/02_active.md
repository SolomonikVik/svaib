---
title: "Framework — актуальное"
updated: 2026-04-29
version: 13
scope: product_core
priority: high
type: plan
---

# Framework — актуальное

## Кратко

Операционный хаб направления: контекст передачи между чатами (Session Handoff), активные задачи, открытые вопросы. Всё, что требует внимания сейчас — в одном месте. State-файл: перезаписывается, не растёт. Вся история — в [03_progress.md](03_progress.md).

**Работа с файлом:** Что сюда: текущие задачи направления, блокеры, открытые вопросы. Что НЕ сюда: что за продукт и зачем (→ [00_product.md](00_product.md)), как устроен внутри (→ [architecture.md](architecture.md)), состояние реализации (→ [01_overview.md](01_overview.md)), задачи на будущее (→ [02_backlog.md](02_backlog.md)), история (→ [03_progress.md](03_progress.md)), продуктовые решения (→ [04_decisions.md](04_decisions.md)), входящее на разбор (→ [_inbox/01_inbox.md](_inbox/01_inbox.md)).


---
## Session Handoff

**Этап А плана metrics закрыт (2026-04-29).** Канон-каркас собран:

- `framework/scaffold/metrics/` — `README.md`, `01_metrics.md`, `template-domain.md`, `source/README.md` (canonical scaffold-стиль: без YAML, без ссылок на framework-only).
- `framework/skills/metrics-analysis/` — `README.md`, `orchestrator-metrics.md`.
- `framework/scaffold/MODEL.md` v3 (раздел 8, `metrics/` как опциональная), `framework/scaffold/README.md`, `framework/methodology/metrics.md` v5.
- Решение целиком зафиксировано в [`04_decisions.md`](04_decisions.md) №5 «Раскладка metrics в scaffold (B1+O1/O5)». Файлы `_inbox/metrics-scaffold/b1.md` и `o1.md` удалены — обоснования воплощены в скаффолде и в записи 04_decisions.

**Next — Этап Б. Открываем новый чат с чистой головой.**

Перед стартом координатор нового чата спрашивает Виктора 5 групп вопросов (пилот / данные / семантика / тест / runtime) — список в [`_inbox/metrics-scaffold/plan.md`](_inbox/metrics-scaffold/plan.md) → секция «Что мне нужно узнать у Виктора ДО старта Этапа Б». После ответов — стартуют шаги Этапа Б.

Список файлов для чтения новым чатом — в последней секции `plan.md`.

---

## Активные задачи

### Метрики у клиента
- [ ] Этап Б плана: пилот у клиента — развернуть `metrics/`, подключить xlsx, заполнить domain, прогнать тест-промпт. Детали — [_inbox/metrics-scaffold/plan.md](_inbox/metrics-scaffold/plan.md)



### Порядок в Scaffold
- [ ] Понять что необходимо сделать минимально и достаточно для обновления клиентского скаффолд
- [ ] Приступить к наведению порядка в скаффолд полного (детали в [02_backlog](02_backlog.md))


### Помощники
* [ ] **Email v1** — первая версия атомарного скилла-помощника по почте

## Открытые вопросы

- 
