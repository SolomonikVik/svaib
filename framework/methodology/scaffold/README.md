---
title: "Scaffold methodology — source of truth слоя scaffold"
created: 2026-05-06
updated: 2026-05-11
---

# Scaffold methodology — source of truth слоя scaffold

Source of truth по слою `scaffold` — архитектура клиентского каркаса, спецификации файлов и папок, канон README, шаблоны, развёртывание у клиента, открытые вопросы. Эта папка — framework-only: клиенту отгружается чистый каркас из `framework/scaffold/`, методологические файлы отсюда не копируются.

## Содержимое папки

| Файл / папка | Миссия | Когда читать |
|---|---|---|
| [01_architecture.md](01_architecture.md) | Требования, design-принципы, модель верхнего уровня | Когда нужно понять «как устроен scaffold и почему» |
| [02_file-spec.md](02_file-spec.md) | Канон md-файла: имя, YAML, секции, связи, режимы, ограничения | При создании или ревизии любого файла scaffold |
| [02_folder-spec.md](02_folder-spec.md) | Канон папки: типы, имя, миссия, полная форма узла, правила жизни | При проектировании структуры или разворачивании папок |
| [02_folder-templates.md](02_folder-templates.md) | Анатомия конкретных контуров: `01_ceo`, `02_strategy`, `03_team`, `04_company`, `05_metrics`, опциональные | Когда работаешь с конкретным контуром |
| [02_file-templates.md](02_file-templates.md) | Миссии и структура канонических файлов узла (overview, active, backlog, progress, decisions, profile) | При создании или ревизии файла внутри узла |
| [02_readme-spec.md](02_readme-spec.md) | Канон README как карты папки | При создании или ревизии README в любой папке |
| [deployment.md](deployment.md) | Правила первичного развёртывания у клиента и расширения по триггерам | При онбординге нового клиента или разворачивании контура |
| [open-questions.md](open-questions.md) | Нерешённые вопросы scaffold, ждущие практики | Чтобы не переоткрывать уже зафиксированные позиции |

## Маршруты чтения

| Триггер задачи | Что читать |
|---|---|
| Понять «как устроено и почему» | [01_architecture.md](01_architecture.md) → [02_folder-spec.md](02_folder-spec.md) |
| Создать или поправить markdown-файл scaffold | [02_file-spec.md](02_file-spec.md) → [02_file-templates.md](02_file-templates.md) (если файл — канонический) |
| Спроектировать структуру папок узла | [02_folder-spec.md](02_folder-spec.md) → [02_folder-templates.md](02_folder-templates.md) |
| Создать или поправить README | [02_readme-spec.md](02_readme-spec.md) |
| Развернуть scaffold у нового клиента | [deployment.md](deployment.md) → [02_folder-templates.md](02_folder-templates.md) |
| Проверить, не открытый ли это вопрос | [open-questions.md](open-questions.md) |

## Связанные контексты

- [../../scaffold/](../../scaffold/) — клиентский каркас scaffold v1, практическая реализация (не SOT методологии)
- [../../skills/scaffold/](../../skills/scaffold/) — автоматизация развёртывания scaffold
- [../../memory/01_context_memory.md](../../memory/01_context_memory.md) — протокол навигации агента
- [../../memory/file_spec.md](../../memory/file_spec.md) — независимый файл-спека слоя Memory (не путать с [02_file-spec.md](02_file-spec.md) — канон scaffold-файла)
