---
title: "Scaffold methodology — source of truth слоя scaffold"
created: 2026-05-06
updated: 2026-05-11
---
	
# Scaffold methodology — source of truth слоя scaffold

Канон слоя `scaffold`: архитектура, спецификации, миссии файлов и контуров, развёртывание у клиента. **Методология нормирует, scaffold материализует** — болванки лежат в [../../scaffold/](../../scaffold/) и должны соответствовать канону, но первоисточником не являются. Эта папка — framework-only: клиенту не отгружается.

## Уровни канона

Файлы разнесены по трём уровням — нумерация в имени отражает уровень:

- **1 — модель**: `01_architecture.md` — зачем нужен scaffold и какая базовая модель.
- **2 — грамматика**: `02_*-spec.md` — что такое папка, md-файл, README в принципе (абстрактный канон).
- **3 — применение**: `03_*.md` — миссии универсальных файлов узла и анатомия конкретных контуров.

## Содержимое папки

| Файл / папка | Миссия | Когда читать |
|---|---|---|
| [01_architecture.md](01_architecture.md) | Требования, design-принципы, модель верхнего уровня | Когда нужно понять «как устроен scaffold и почему» |
| [02_file-spec.md](02_file-spec.md) | Канон md-файла: имя, YAML, секции, связи, ограничения | При создании или ревизии любого файла scaffold |
| [02_folder-spec.md](02_folder-spec.md) | Канон папки: типы, имя, миссия, полная форма узла, правила жизни | При проектировании структуры или разворачивании папок |
| [03_node-files.md](03_node-files.md) | Миссии **универсальных** канонических файлов узла: `01_overview`, `02_active`, `02_backlog`, `03_progress`, `04_decisions`, `profile`, `person` | Создаёшь/правишь файл, который встречается во многих контурах |
| [03_contours.md](03_contours.md) | Анатомия канонических контуров + миссии **контурно-специфичных** файлов (`01_my-profile`, `01_vision`, `org-structure`, `01_metrics`, …) | Работаешь с контуром или с файлом, существующим только в одном контуре |
| [02_readme-spec.md](02_readme-spec.md) | Канон README как карты папки | При создании или ревизии README в любой папке |
| [deployment.md](deployment.md) | Правила первичного развёртывания у клиента и расширения по триггерам | При онбординге нового клиента или разворачивании контура |
| [open-questions.md](open-questions.md) | Нерешённые вопросы scaffold, ждущие практики | Чтобы не переоткрывать уже зафиксированные позиции |

## Маршруты чтения

| Триггер задачи | Что читать |
|---|---|
| Понять «как устроено и почему» | [01_architecture.md](01_architecture.md) → [02_folder-spec.md](02_folder-spec.md) |
| Создать/поправить **универсальный** файл узла (overview, active, backlog, progress, decisions, profile, person) | [02_file-spec.md](02_file-spec.md) → [03_node-files.md](03_node-files.md) |
| Создать/поправить **контурно-специфичный** файл (`01_my-profile`, `01_vision`, `org-structure`, `01_metrics`, …) | [02_file-spec.md](02_file-spec.md) → [03_contours.md](03_contours.md) |
| Спроектировать структуру папок узла | [02_folder-spec.md](02_folder-spec.md) → [03_contours.md](03_contours.md) |
| Создать или поправить README | [02_readme-spec.md](02_readme-spec.md) |
| Развернуть scaffold у нового клиента | [deployment.md](deployment.md) → [03_contours.md](03_contours.md) |
| Проверить, не открытый ли это вопрос | [open-questions.md](open-questions.md) |

## Связанные контексты

- [../../scaffold/](../../scaffold/) — клиентский каркас scaffold v1, практическая реализация (не SOT методологии)
- [../../skills/scaffold/](../../skills/scaffold/) — автоматизация развёртывания scaffold
- [../../memory/01_context_memory.md](../../memory/01_context_memory.md) — протокол навигации агента
- [../../memory/file_spec.md](../../memory/file_spec.md) — независимый файл-спека слоя Memory (не путать с [02_file-spec.md](02_file-spec.md) — канон scaffold-файла)
