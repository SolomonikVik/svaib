---
title: "Product — ядро продукта Second Value AI Brain"
updated: 2026-10-06
version: 15
scope: "product_core"
priority: high
---

# Product

## Кратко

Ядро продукта Second Value AI Brain: vision, методология, scaffold, skills, plugin. Всё, чтобы развернуть персональную AI-инфраструктуру для руководителя.

**`product/` = продукт.** Продуктовое видение, архитектура, решения и состояние реализации живут здесь.

**Пять частей продукта:**
- **Vision** — целевой образ продукта: как должен выглядеть Second Value AI Brain
- **Methodology** — онтология, память, принципы, модели мышления и методологии слоёв
- **Scaffold** — готовый каркас папок и документов (открыл — скопировал)
- **Skills** — мастерская промптов и навыков по доменам (где разрабатываем)
- **Plugin** — собранный пакет для клиента: skills + agents + hooks (что деплоим)

## Связанные файлы

### Смысловое ядро продукта

- [01_overview.md](01_overview.md) — что за продукт, для кого, принципы, границы, бизнес-модель
- [01_alpha-dod.md](01_alpha-dod.md) — DoD альфы: что считаем сделанным, что явно не входит, открытые вопросы
- [01_v1-dod.md](01_v1-dod.md) — DoD версии 1: что получает руководитель в каждом ракурсе, что под капотом, что не входит. Набросок DoD беты — в архиве
- [skills-catalog.md](skills-catalog.md) — единый реестр управленческих скиллов по ракурсам: что получает руководитель, статус (в продукте · альфа · бэклог), ссылки на методологию и реализацию
- [offerings-and-pricing/](offerings-and-pricing/README.md) — что продаёт svaib, что входит и не входит в продукт, стоимость
- [architecture.md](architecture.md) — как продукт устроен внутри (слои, компоненты, связи)
- [docs/README.md](docs/README.md) — документация продукта для клиента: как пользователь с ним работает (пара к методологии — «как устроено»); внутри — [docs/mcp-platform.md](docs/mcp-platform.md) (🚧 draft: возможности серверной части — MCP на рабочем месте и партнёр в Telegram и почте)
- [docs/instructions/README.md](docs/instructions/README.md) — все пользовательские инструкции: единый маршрут записи и источник справок онбординга
- [vision/README.md](vision/README.md) — карта целевого образа продукта, семи ракурсов, доказательной базы, исследований и target architecture
- [05_decisions.md](05_decisions.md) — журнал продуктовых решений: архитектура, поставка, границы, развитие
- [glossary.md](glossary.md) — канонический словарь продукта: одно принятое имя и одно определение на понятие
- [development-operating-model.md](development-operating-model.md) — как команда версионирует и ведёт разработку: релизы, оси, бэклог, актив, статусы файлов
- CHANGELOG.md — заметные изменения продукта по версиям; верхняя секция уходит в релизный коммит

### Операционка направления

- [02_active.md](02_active.md) — что горит сейчас: компактный список задач, в том числе задач к релизу; у задачи — ссылка на её план, если он нужен. Session Handoff живёт не здесь, а в файле плана-трека своей задачи
- [03_backlog.md](03_backlog.md) — задачи на будущее
- [04_progress.md](04_progress.md) — хроника сделанного
- [ideas.md](ideas.md) — продуктовые идеи, инсайты, открытые вопросы (накопитель с синков)
- _inbox/ — входящее на разбор

### Связи наружу

- [../01_company/01_strategic/vision.md](../01_company/01_strategic/vision.md) — vision проекта svaib (блок «Продукт» → [01_overview.md](01_overview.md))
- [../01_company/01_strategic/goal.md](../01_company/01_strategic/goal.md) — цели svaib (фокус «Продукт» → операционка [02_active.md](02_active.md))
- ../01_company/04_progress/weekly-progress.md — агрегатор svaib ([04_progress.md](04_progress.md) → туда)
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

## Навигация по задаче

| Задача | Куда идти | Что найдёшь |
|--------|-----------|-------------|
| Понять что за продукт и зачем | [01_overview.md](01_overview.md) | Проблема, для кого, решение, принципы, границы, бизнес-модель |
| Понять как продукт устроен внутри | [architecture.md](architecture.md) | Слои, компоненты, общая схема |
| Понять целевой образ продукта | [vision/README.md](vision/README.md) | Product Vision, семь ракурсов, клиентская доказательная база, исследования, target architecture |
| Понять работу svaib в семи ракурсах | [vision/02_aspects.md](vision/02_aspects.md) | Роли svaib, способы работы, результаты, границы и связи ракурсов |
| Найти/зафиксировать клиентское свидетельство для vision | [vision/customer-evidence.md](vision/customer-evidence.md) | Что клиенты реально говорят и как это подтверждает, уточняет или ломает vision |
| Найти скилл и проверить его результат и статус | [skills-catalog.md](skills-catalog.md) | Реестр управленческих скиллов по ракурсам, статусы и ссылки |
| Понять что горит сейчас | [02_active.md](02_active.md) | Компактный список задач и целей релиза, ссылки на планы |
| Зафиксировать/найти продуктовую идею с синка | [ideas.md](ideas.md) | Идеи, инсайты, открытые вопросы, принципы-кандидаты |
| Узнать почему выбрано так | [05_decisions.md](05_decisions.md) | Архитектура, поставка, границы |
| Свериться с названием понятия или ввести новый термин | [glossary.md](glossary.md) | Принятые продуктовые термины и правила пополнения |
| Разобраться в сущностях | [methodology/management-system/](methodology/management-system/) | Файлы, связи, правила размещения |
| Как агент работает с информацией | [methodology/memory/01_context_memory.md](methodology/memory/01_context_memory.md) | Протокол чтения, сбор контекста, хуки, детерминированность |
| Понять как работать с X | [methodology/](methodology/) | Протоколы, decision frames, ритуалы |
| Добавить/изменить сущность | [methodology/management-system/entities.md](methodology/management-system/entities.md) | Каталог атомарных сущностей |
| Создать/улучшить шаблон | [plugin/skills/space/scaffold/templates/root/](plugin/skills/space/scaffold/templates/root/) | Готовый каркас + спецификации |
| Понять архитектуру scaffold | [methodology/space/scaffold/01_architecture.md](methodology/space/scaffold/01_architecture.md) | Требования, принципы, модель верхнего уровня |
| Спроектировать структуру папок | [methodology/space/scaffold/02_folder-spec.md](methodology/space/scaffold/02_folder-spec.md) | Спецификация папок scaffold |
| Развернуть scaffold для клиента | [plugin/skills/space/scaffold/templates/root/](plugin/skills/space/scaffold/templates/root/) | Канонический scaffold продукта |
| Спроектировать навык | [plugin/skills/](plugin/skills/) | Мастерская промптов по доменам |
| Собрать пакет клиенту | [plugin/](plugin/) | Skills + agents + hooks |
| Ракурс «Цели и показатели»: методология метрик | [methodology/aspect-metrics/](methodology/aspect-metrics) | Точка входа — `README.md`; внутри: `architecture.md`, `metrics-spec.md`, `extractor.md` |
| Работа со встречами | [methodology/aspect-rhythm/meeting-debrief/workflow.md](methodology/aspect-rhythm/meeting-debrief/workflow.md) | Пайплайн анализа транскриптов |
| Формат файлов | [methodology/space/scaffold/02_file-spec.md](methodology/space/scaffold/02_file-spec.md) | Действующий канон: YAML, шапка, секции, связи |
| Оформить результат скилла, собрать макет спецификации | [design/output.md](methodology/design/output.md) | Дизайн результатов: макет, элементы вида, словарь знаков |

---

## Масштабирование

**Соло / малый бизнес:** ядро продукта + управленческий контекст. Один человек, LLM помогает.

**CEO с командой (до 100-200 чел):** та же структура, но для личного пространства CEO. Разница — в глубине наполнения, не в количестве файлов.
