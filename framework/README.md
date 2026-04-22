---
title: "Framework — ядро продукта Second AI Brain"
updated: 2026-04-21
version: 9
scope: "product_core"
priority: high
---

# Framework

## Кратко

Ядро продукта Second AI Brain: онтология, память, методология, scaffold, skills, plugin. Всё, чтобы развернуть персональную AI-инфраструктуру для руководителя.

**Framework = продукт.** Отдельной папки «продукт» в meta нет — продуктовое видение, архитектура, решения и состояние реализации живут здесь.

**Шесть частей:**
- **Ontology** — какие сущности существуют и как связаны (справочник)
- **Memory** — как устроены файлы, папки, связи и как агент их находит и читает (инфраструктурный слой)
- **Methodology** — принципы и модели мышления (почему так устроено)
- **Scaffold** — готовый каркас папок и документов (открыл — скопировал)
- **Skills** — мастерская промптов и навыков по доменам (где разрабатываем)
- **Plugin** — собранный пакет для клиента: skills + agents + hooks (что деплоим)

## Связанные файлы

### Смысловое ядро продукта

- [00_product.md](00_product.md) — что за продукт, для кого, принципы, границы, бизнес-модель
- [architecture.md](architecture.md) — как продукт устроен внутри (слои, компоненты, связи)
- [04_decisions.md](04_decisions.md) — продуктовые решения (runtime, границы, путь skills)

### Операционка направления

- [01_overview.md](01_overview.md) — состояние реализации шести частей, roadmap декады, модель поставки
- [02_active.md](02_active.md) — что горит сейчас, Session Handoff
- [02_backlog.md](02_backlog.md) — задачи на будущее
- [03_progress.md](03_progress.md) — хроника сделанного
- [_inbox/01_inbox.md](_inbox/01_inbox.md) — входящее на разбор

### Связи наружу

- [../meta/management/01_vision.md](../meta/management/01_vision.md) — vision проекта svaib (связь ①: блок «Продукт» → [00_product.md](00_product.md))
- [../meta/management/02_goal.md](../meta/management/02_goal.md) — цели декады svaib (связь ②: фокус «Продукт» → [01_overview.md](01_overview.md))
- [../meta/management/04_weekly_progress.md](../meta/management/04_weekly_progress.md) — агрегатор svaib (связь ③: [03_progress.md](03_progress.md) → туда)
- [../clients/playbook/delivery/01_delivery_plan.md](../clients/playbook/delivery/01_delivery_plan.md) — delivery plan (онбординг, ДЗ, инструменты)

Направление устроено по универсальной модели svaib: `_inbox → backlog → active → progress + decisions`. Правила работы — [../lab/work-model.md](../lab/work-model.md).

---

## Как части связаны внутри framework

```
ontology/          → описывает сущности
                        ↓
memory/            → описывает как они хранятся и находятся
                        ↓
methodology/       → описывает как с ними работать
                        ↓
scaffold/          → воплощает в готовую структуру
                        ↓
skills/            → промпты и навыки по доменам (разработка)
                        ↓
plugin/            → собранный пакет для клиента (деплой)
```

Онтология отвечает «что существует». Memory — «как это хранится и находится». Методология — «как с этим работать». Scaffold — «как это выглядит». Skills — «мастерская, где создаём автоматизацию». Plugin — «что получает клиент».

Онтология меняется редко. Memory — при найденных паттернах работы агента с файлами. Методология — при новых инсайтах. Scaffold — при изменении онтологии. Skills — постоянно (это мастерская). Plugin — при релизе клиенту.

---

## Карта связей svaib ↔ framework

```
┌─ УРОВЕНЬ SVAIB — meta/management/ ─────────────────────────┐
│                                                            │
│  01_vision.md ── идентичность, 3 направления               │
│      └─ блок "Продукт"  ──────── связь ① ──────┐           │
│                                                │           │
│  02_goal.md ── декады, метрики                 │           │
│      └─ декада/фокус "Продукт" ── связь ② ──┐  │           │
│                                             │  │           │
│  03_plan / 04_weekly_progress / 05_timeline │  │           │
│              ▲                              │  │           │
└──────────────│──────────────────────────────│──│───────────┘
               │ связь ③                      │  │
┌──────────────│──────────────────────────────│──│───────────┐
│ УРОВЕНЬ ПРОДУКТА — framework/               │  │           │
│                                             ▼  ▼           │
│  00_product.md       ◀──── ЧТО строим и зачем (связь ①)       │
│  architecture.md  ─────  КАК устроено                      │
│  01_overview.md   ◀──── КАК идёт стройка (связь ②)         │
│                                                            │
│  02_active / 02_backlog / 03_progress ── операционка       │
│  03_progress.md ──── связь ③ ──▶ 04_weekly_progress        │
│  04_decisions.md  ─────  журнал решений                    │
└────────────────────────────────────────────────────────────┘
```

### Три связи между уровнями

| № | Откуда | Куда | Частота |
|---|--------|------|---------|
| ① | [../meta/management/01_vision.md](../meta/management/01_vision.md) (блок «Продукт») | [00_product.md](00_product.md) | Стабильная, меняется при пивотах |
| ② | [../meta/management/02_goal.md](../meta/management/02_goal.md) (цель декады / Продукт) | [01_overview.md](01_overview.md) | Каждую декаду (~10 нед) |
| ③ | [03_progress.md](03_progress.md) | [../meta/management/04_weekly_progress.md](../meta/management/04_weekly_progress.md) | Еженедельно |

### Три скорости жизни

- **Стабильный контур (месяцы):** [00_product.md](00_product.md), [architecture.md](architecture.md)
- **Тактический контур (декады):** [01_overview.md](01_overview.md)
- **Оперативный контур (дни/недели):** [02_active.md](02_active.md), [02_backlog.md](02_backlog.md), [03_progress.md](03_progress.md)

Подпапки `ontology/`, `memory/`, `methodology/`, `scaffold/`, `skills/`, `plugin/` — территория, где живут детали частей продукта. [architecture.md](architecture.md) даёт карту, они — детализация.

---

## Навигация по задаче

| Задача | Куда идти | Что найдёшь |
|--------|-----------|-------------|
| Понять что за продукт и зачем | [00_product.md](00_product.md) | Проблема, для кого, решение, принципы, границы, бизнес-модель |
| Понять как продукт устроен внутри | [architecture.md](architecture.md) | Слои, компоненты, общая схема |
| Понять где мы в стройке | [01_overview.md](01_overview.md) | Стадия шести частей, roadmap декады |
| Узнать почему выбрано так | [04_decisions.md](04_decisions.md) | Runtime, границы, путь skills |
| Разобраться в сущностях | [ontology/](ontology/) | Файлы, связи, правила размещения |
| Как агент работает с информацией | [memory/01_context_memory.md](memory/01_context_memory.md) | Протокол чтения, сбор контекста, хуки, детерминированность |
| Понять как работать с X | [methodology/](methodology/) | Протоколы, decision frames, ритуалы |
| Добавить/изменить сущность | [ontology/entities.md](ontology/entities.md) | Каталог атомарных сущностей |
| Создать/улучшить шаблон | [scaffold/](scaffold/) | Готовый каркас + спецификации |
| Спроектировать структуру папок | [scaffold/principles.md](scaffold/principles.md) | Принципы: миссия файла, развёртывание, маршрутизация |
| Развернуть scaffold для клиента | [scaffold/clients/](scaffold/clients/) | Шаблоны клиентских проектов |
| Спроектировать навык | [skills/](skills/) | Мастерская промптов по доменам |
| Собрать пакет клиенту | [plugin/](plugin/) | Skills + agents + hooks |
| Работа со встречами | [methodology/meeting_analysis.md](methodology/meeting_analysis.md) | Пайплайн анализа транскриптов |
| Онбординг клиента | [methodology/onboarding.md](methodology/onboarding.md) | Последовательность освоения |
| Формат файлов | [memory/file_spec.md](memory/file_spec.md) | YAML, секции, ограничения |

---

## Масштабирование

**Соло / малый бизнес:** ядро (8 файлов) + мета. Один человек, LLM помогает.

**CEO с командой (до 100-200 чел):** та же структура, но для личного пространства CEO. Разница — в глубине наполнения, не в количестве файлов.

---

## Модель поставки

Данные у клиента (развёрнутый scaffold). Методология у нас (обновляемый plugin). Плагин не хранит данные — интеллектуальный слой поверх.
