---
title: "Framework — актуальное"
updated: 2026-05-01
version: 20
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

**Реорганизация metrics завершена 2026-04-30.** Методология вертикали собрана в `methodology/metrics/`, skill-папка очищена, стандарт `extractors/` зафиксирован, smoke-test пройден, Codex-ревью отработан. Подробнее — [`03_progress.md`](03_progress.md) запись 30.04 (вторая за день).

**Next — двинуть клиентскую задачу.** Дать клиенту [`intake-form.md`](methodology/metrics/intake-form.md) + дополнительные вопросы из [`open-questions.md`](methodology/metrics/open-questions.md) секция «Что спросить у первого клиента до Б.2» → получить ответы → начать тестировать на его живой базе через Cowork (см. [`COWORK-TEST.md`](_inbox/metrics-scaffold/cowork-test/COWORK-TEST.md) как готовый pack).

Цель к концу следующей недели — pipeline работает на боевых данных клиента в его Cowork-окружении.

Точка входа в вертикаль для нового чата — [`methodology/metrics/README.md`](methodology/metrics/README.md).

---

## Активные задачи

### Метрики у клиента

- [ ] **Клиент-1 на живой базе** — intake-form + ответы → Cowork-тест на боевом

- Детали — [_inbox/metrics-scaffold/plan.md](_inbox/metrics-scaffold/plan.md) и [methodology/metrics/open-questions.md](methodology/metrics/open-questions.md) (секция «Что спросить у первого клиента до Б.2»)

### Scaffold — поэтапное прохождение плана

Идём шаг за шагом по 12 шагам финального плана в [02_backlog.md](02_backlog.md) → раздел `## Scaffold`.

- [ ] **Шаг 1 (сейчас):** обсудить [scaffold-draft-v1.md](_inbox/scaffold/2026-05-01_scaffold-draft-v1.md) + [HTML](_inbox/scaffold/2026-05-01_scaffold-draft-v1.html) с клиентами на предстоящих встречах. Собрать обратную связь.

Дальше — Шаги 2-12 из бэклога по очереди.

### Помощники

- [ ] **Email v1** — первая версия атомарного скилла-помощника по почте

## Открытые вопросы

- 