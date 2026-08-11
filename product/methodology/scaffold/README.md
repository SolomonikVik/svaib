---
title: "Scaffold methodology — source of truth слоя scaffold"
created: 2026-05-06
updated: 2026-08-07
version: 4.1
status: final
---

# Scaffold methodology — source of truth слоя scaffold

Канон слоя `scaffold`: архитектура клиентского каркаса, грамматика папок/файлов/README и миссии управленческих сущностей. Старт — [01_architecture.md](01_architecture.md), шаблоны — в [../../plugin/skills/scaffold/template/](../../plugin/skills/scaffold/template/).

## 🔵 Актуальная модель

Scaffold v4.1 строится как **composable management architecture**.

- **Unit** — объект управления: компания, направление, продукт, филиал, клиентский портфель.
- **Aspect** — управленческий ракурс: сторона, через которую смотрим на объект управления.
- **Kit** — управленческая панель узла: overview, active, backlog, progress, decisions.
- **Node** — узел: управляемая сущность в дереве, файл или папка, которая может расти.
- **Infrastructure folders** — `_inbox/`, `_private/`, `meetings/`, `source/`, `extractors/`, `zz_archive/`.
- **Client workspace folders** — свободные рабочие папки клиента (`docs/`, `contracts/`, `pages/` и т.д.).


## Содержимое папки

| Файл / папка | Миссия | Когда читать |
|---|---|---|
| [01_architecture.md](01_architecture.md) | Требования, design-принципы, модель верхнего уровня | Когда нужно понять «как устроен scaffold и почему» |
| [management-unit.md](management-unit.md) | Что считать объектом управления и как разворачиваются `00_ceo/`, `01_company/`, `product/`, `clients/` | Когда проектируешь Management Units и корневую структуру клиента |
| [management-aspect.md](management-aspect.md) | Управленческие ракурсы: `strategic`, `team`, `metrics`, `projects`, `processes`, `knowledge` | Когда подключаешь управленческий ракурс внутри объекта управления |
| [management-kit.md](management-kit.md) | Миссии файлов управленческой панели: overview, active, backlog, progress, decisions | Когда создаёшь или правишь управленческую панель узла |
| [02_folder-spec.md](02_folder-spec.md) | Грамматика папки: management / infrastructure / client workspace, имя, миссия, жизненный цикл | При проектировании структуры или разворачивании папок |
| [02_file-spec.md](02_file-spec.md) | Канон md-файла: имя, YAML, шапка, H2, текст, правила, связи | При создании или ревизии любого md-файла scaffold |
| [02_readme-spec.md](02_readme-spec.md) | Канон README как карты папки | При создании или ревизии README в любой папке |
| [deployment.md](deployment.md) | Развёртывание каркаса у клиента: стартовый минимум, триггеры расширения, выбор формы узла | При первичной сборке scaffold у клиента |
| [deployment-node-review.md](deployment-node-review.md) | QA-гейт узла перед выгрузкой: промпт ревьюера по клиентскому канону scaffold | Перед финальной передачей scaffold клиенту |
| [open-questions.md](open-questions.md) | Открытые вопросы v4.1: lifecycle миграций, визуальный UX, finance, нумерация | Когда тема упирается в нерешённый вопрос |
| [scaffold-evolution-log.md](scaffold-evolution-log.md) | Историческая память: эволюция модели | Когда нужно понять, как развивалась модель |

## Маршруты чтения

| Триггер задачи | Что читать |
|---|---|
| Понять scaffold v4.1 целиком | [01_architecture.md](01_architecture.md) → [management-unit.md](management-unit.md) → [management-aspect.md](management-aspect.md) → [management-kit.md](management-kit.md) |
| Развернуть scaffold у нового клиента | [deployment.md](deployment.md) → [management-unit.md](management-unit.md) |
| Проверить узел перед выгрузкой клиенту | [deployment-node-review.md](deployment-node-review.md) |
| Создать или ревизовать scaffold-файл | [02_file-spec.md](02_file-spec.md), для README — [02_readme-spec.md](02_readme-spec.md) |

## Связанные контексты

- [../../plugin/skills/scaffold/template/](../../plugin/skills/scaffold/template/) — клиентский каркас scaffold v4.1, практическая реализация (не SOT методологии)
- [../../plugin/skills/scaffold/](../../plugin/skills/scaffold/) — автоматизация развёртывания scaffold
- [../memory/01_context_memory.md](../memory/01_context_memory.md) — протокол навигации агента
- [Клиентский scaffold-конфигуратор](https://svaib.com/tools/scaffold) — интерактивный инструмент сборки scaffold с клиентом на встрече (визуализирует модель unit/aspect/панель). Исходник — scaffold-configurator.html.
