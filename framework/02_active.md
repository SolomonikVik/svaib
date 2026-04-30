---
title: "Framework — актуальное"
updated: 2026-04-30
version: 17
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

**Б.1 metrics закрыт 2026-04-30** — впервые прогнали pipeline на живых клиентских данных в sandbox. Подробнее — [`03_progress.md`](03_progress.md) запись 30.04. Артефакты Б.1: [`_inbox/metrics-scaffold/sandbox/_b0_findings/03_results.md`](_inbox/metrics-scaffold/sandbox/_b0_findings/03_results.md).

**Next — две задачи на свежую голову:**

**Задача 1 — собрать методологическую базу metrics в одно место.** Сейчас всё растащено: что-то в [`skills/metrics-analysis/`](skills/metrics-analysis/) (HOWTO, rollout, intake-form, open-questions, README, orchestrator), что-то в [`methodology/metrics.md`](methodology/metrics.md) (архитектурный слой 6 слоёв), что-то в [`scaffold/metrics/`](scaffold/metrics/) (канон шаблонов), что-то в [`_inbox/metrics-scaffold/`](_inbox/metrics-scaffold/) (план, sandbox). Нужно навести порядок — собрать методологию в одно место (предположительно `methodology/metrics/`), оставить в skills только оркестратор + промпты, проверить ошибки и связность ссылок. По ходу — пересмотреть открытые вопросы в [`open-questions.md`](skills/metrics-analysis/open-questions.md) и понять, какие финальные вопросы задать клиенту.

**Задача 2 — двинуть клиентскую задачу.** После того как методологическая база собрана и понятен список вопросов: дать клиенту [`intake-form.md`](skills/metrics-analysis/intake-form.md) + дополнительные вопросы → получить ответы → начать тестировать на его живой базе через Cowork (см. [`COWORK-TEST.md`](_inbox/metrics-scaffold/cowork-test/COWORK-TEST.md) как готовый pack).

Цель к концу следующей недели — pipeline работает на боевых данных клиента в его Cowork-окружении.

---

## Активные задачи

### Метрики у клиента
- [ ] **Сборка методологической базы metrics** — навести порядок (методология / skills / scaffold / inbox растащены), проверить ошибки, финализировать список вопросов клиенту
- [ ] **Клиент-1 на живой базе** — intake-form + ответы → Cowork-тест на боевом
- Детали — [_inbox/metrics-scaffold/plan.md](_inbox/metrics-scaffold/plan.md) и [skills/metrics-analysis/open-questions.md](skills/metrics-analysis/open-questions.md)



### Порядок в Scaffold
- [ ] Понять что необходимо сделать минимально и достаточно для обновления клиентского скаффолд
- [ ] Приступить к наведению порядка в скаффолд полного (детали в [02_backlog](02_backlog.md))


### Помощники
* [ ] **Email v1** — первая версия атомарного скилла-помощника по почте

## Открытые вопросы

- 
