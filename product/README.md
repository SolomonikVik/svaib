---
title: "Product — ядро продукта Second Value AI Brain"
updated: 2026-07-17
version: 13
scope: "product_core"
priority: high
---

# Product

## Кратко

Ядро продукта Second Value AI Brain: vision, методология, scaffold, skills, plugin. Всё, чтобы развернуть персональную AI-инфраструктуру для руководителя.

**`product/` = продукт.** Отдельной папки «продукт» в meta нет — продуктовое видение, архитектура, решения и состояние реализации живут здесь.

**Пять частей продукта:**
- **Vision** — целевой образ продукта: как должен выглядеть Second Value AI Brain
- **Methodology** — онтология, память, принципы, модели мышления и методологии слоёв
- **Scaffold** — готовый каркас папок и документов (открыл — скопировал)
- **Skills** — мастерская промптов и навыков по доменам (где разрабатываем)
- **Plugin** — собранный пакет для клиента: skills + agents + hooks (что деплоим)

## Связанные файлы

### Смысловое ядро продукта

- [01_overview.md](01_overview.md) — что за продукт, для кого, принципы, границы, бизнес-модель
- [architecture.md](architecture.md) — как продукт устроен внутри (слои, компоненты, связи)
- [vision/](vision/) — целевой образ продукта, клиентская доказательная база, исследования и target architecture
- [04_decisions.md](04_decisions.md) — продуктовые решения (runtime, границы, путь skills)

### Операционка направления

- [02_active.md](02_active.md) — что горит сейчас, Session Handoff
- [02_backlog.md](02_backlog.md) — задачи на будущее
- [03_progress.md](03_progress.md) — хроника сделанного
- [ideas.md](ideas.md) — продуктовые идеи, инсайты, открытые вопросы (накопитель с синков)
- _inbox/ — входящее на разбор

### Связи наружу

- ../meta/management/01_vision.md — vision проекта svaib (связь ①: блок «Продукт» → [01_overview.md](01_overview.md))
- ../meta/management/02_goal.md — цели svaib (связь ②: фокус «Продукт» → операционка [02_active.md](02_active.md))
- ../meta/management/04_weekly_progress.md — агрегатор svaib (связь ③: [03_progress.md](03_progress.md) → туда)
- ../clients/playbook/delivery/01_delivery_plan.md — delivery plan (онбординг, ДЗ, инструменты)

Направление устроено по универсальной модели svaib: `_inbox → backlog → active → progress + decisions`. Правила работы — ../lab/work-model.md.

---

## Как части связаны внутри product

```
vision/        → описывает целевой образ продукта
                   ↓
01_overview.md
architecture.md → фиксируют канон продукта
                   ↓
methodology/   → описывает сущности, память и способы работы
                   ↓
scaffold/      → воплощает в готовую структуру
                   ↓
skills/        → промпты и навыки по доменам (разработка)
                   ↓
plugin/        → собранный пакет для клиента (деплой)
```

Vision отвечает «куда строим». `01_overview.md` и `architecture.md` фиксируют стабильный канон. Methodology отвечает «что существует, как это хранится и как с этим работать». Scaffold — «как это выглядит». Skills — «мастерская, где создаём автоматизацию». Plugin — «что получает клиент».

Vision меняется при уточнении целевого образа. Methodology — при новых инсайтах. Scaffold — при изменении методологии. Skills — постоянно (это мастерская). Plugin — при релизе клиенту.

---

## Карта связей svaib ↔ product

```
┌─ УРОВЕНЬ SVAIB — meta/management/ ─────────────────────────┐
│                                                            │
│  01_vision.md ── идентичность, 3 направления               │
│      └─ блок "Продукт"  ──────── связь ① ──────┐           │
│                                                │           │
│  02_goal.md ── цели, метрики                   │           │
│      └─ фокус "Продукт" ──────── связь ② ──┐  │           │
│                                             │  │           │
│  03_plan / 04_weekly_progress / 05_timeline │  │           │
│              ▲                              │  │           │
└──────────────│──────────────────────────────│──│───────────┘
               │ связь ③                      │  │
┌──────────────│──────────────────────────────│──│───────────┐
│ УРОВЕНЬ ПРОДУКТА — product/                 │  │           │
│                                             ▼  ▼           │
│  01_overview.md       ◀──── ЧТО строим и зачем (связь ①)       │
│  architecture.md  ─────  КАК устроено                      │
│                                                            │
│  02_active / 02_backlog / 03_progress ◀── операционка (②)   │
│  03_progress.md ──── связь ③ ──▶ 04_weekly_progress        │
│  04_decisions.md  ─────  журнал решений                    │
└────────────────────────────────────────────────────────────┘
```

### Три связи между уровнями

| № | Откуда | Куда | Частота |
|---|--------|------|---------|
| ① | ../meta/management/01_vision.md (блок «Продукт») | [01_overview.md](01_overview.md) | Стабильная, меняется при пивотах |
| ② | ../meta/management/02_goal.md (фокус «Продукт») | [02_active.md](02_active.md) | Оперативно (недели) |
| ③ | [03_progress.md](03_progress.md) | ../meta/management/04_weekly_progress.md | Еженедельно |

### Две скорости жизни

- **Стабильный контур (месяцы):** [01_overview.md](01_overview.md), [architecture.md](architecture.md)
- **Оперативный контур (дни/недели):** [02_active.md](02_active.md), [02_backlog.md](02_backlog.md), [03_progress.md](03_progress.md)

Подпапки `vision/`, `methodology/`, `plugin/` — разделы, где живут детали частей продукта; `scaffold/` и `skills/` сейчас внутри `plugin/`. Ontology живёт внутри `methodology/ontology/`, Memory — внутри `methodology/memory/`. [architecture.md](architecture.md) даёт карту, они — детализация.

---

## Навигация по задаче

| Задача | Куда идти | Что найдёшь |
|--------|-----------|-------------|
| Понять что за продукт и зачем | [01_overview.md](01_overview.md) | Проблема, для кого, решение, принципы, границы, бизнес-модель |
| Понять как продукт устроен внутри | [architecture.md](architecture.md) | Слои, компоненты, общая схема |
| Понять целевой образ продукта | [vision/](vision/) | Product Vision, клиентская доказательная база, исследования, target architecture |
| Найти/зафиксировать клиентское свидетельство для vision | [vision/customer-evidence.md](vision/customer-evidence.md) | Что клиенты реально говорят и как это подтверждает, уточняет или ломает vision |
| Понять что горит сейчас | [02_active.md](02_active.md) | Активные задачи, Session Handoff |
| Зафиксировать/найти продуктовую идею с синка | [ideas.md](ideas.md) | Идеи, инсайты, открытые вопросы, принципы-кандидаты |
| Узнать почему выбрано так | [04_decisions.md](04_decisions.md) | Runtime, границы, путь skills |
| Разобраться в сущностях | [methodology/ontology/](methodology/ontology/) | Файлы, связи, правила размещения |
| Как агент работает с информацией | [methodology/memory/01_context_memory.md](methodology/memory/01_context_memory.md) | Протокол чтения, сбор контекста, хуки, детерминированность |
| Понять как работать с X | [methodology/](methodology/) | Протоколы, decision frames, ритуалы |
| Добавить/изменить сущность | [methodology/ontology/entities.md](methodology/ontology/entities.md) | Каталог атомарных сущностей |
| Создать/улучшить шаблон | [plugin/skills/scaffold/template/](plugin/skills/scaffold/template/) | Готовый каркас + спецификации |
| Понять архитектуру scaffold | [methodology/scaffold/01_architecture.md](methodology/scaffold/01_architecture.md) | Требования, принципы, модель верхнего уровня |
| Спроектировать структуру папок | [methodology/scaffold/02_folder-spec.md](methodology/scaffold/02_folder-spec.md) | Спецификация папок scaffold |
| Развернуть scaffold для клиента | [plugin/skills/scaffold/template/](plugin/skills/scaffold/template/) | Канонический scaffold продукта |
| Спроектировать навык | [plugin/skills/](plugin/skills/) | Мастерская промптов по доменам |
| Собрать пакет клиенту | [plugin/](plugin/) | Skills + agents + hooks |
| Вертикаль metrics (методология цикла) | [methodology/metrics/](methodology/metrics/) | Точка входа — `README.md` (карта вертикали); внутри: `architecture.md`, `metrics-spec.md`, `extractor.md` |
| Работа со встречами | [methodology/meeting_analysis.md](methodology/meeting_analysis.md) | Пайплайн анализа транскриптов |
| Онбординг клиента | [methodology/onboarding.md](methodology/onboarding.md) | Последовательность освоения |
| Формат файлов | [methodology/scaffold/02_file-spec.md](methodology/scaffold/02_file-spec.md) | Действующий канон: YAML, шапка, секции, связи |

---

## Масштабирование

**Соло / малый бизнес:** ядро (8 файлов) + мета. Один человек, LLM помогает.

**CEO с командой (до 100-200 чел):** та же структура, но для личного пространства CEO. Разница — в глубине наполнения, не в количестве файлов.

---

## Модель поставки

Данные у клиента (развёрнутый scaffold). Методология у нас (обновляемый plugin). Плагин не хранит данные — интеллектуальный слой поверх.
