---
title: "Scaffold — README spec"
updated: 2026-05-05
version: 1
type: reference
scope: product_core
---

# Scaffold README spec

## Миссия файла

Канон README как карты папки: миссия, структура, порядок чтения, навигация, что должно и не должно жить в README.

## Черновик

## Источники на перенос

- [../../scaffold/README.md](../../scaffold/README.md) — root README старого scaffold; забрать только канон README как карты.
- [../../scaffold/01_ceo/README.md](../../scaffold/01_ceo/README.md) — пример README обязательной папки.
- [../../scaffold/02_strategy/README.md](../../scaffold/02_strategy/README.md) — пример README обязательной папки.
- [../../scaffold/03_team/README.md](../../scaffold/03_team/README.md) — пример README обязательной папки.
- [../../scaffold/04_management/README.md](../../scaffold/04_management/README.md) — пример README управления; при переносе учитывать будущее `04_company`.
- [../../scaffold/product/README.md](../../scaffold/product/README.md) — пример README опционального контура.
- [../../scaffold/projects/README.md](../../scaffold/projects/README.md) — пример README типа папки.
- [../../scaffold/projects/{project_name}/README.md](../../scaffold/projects/%7Bproject_name%7D/README.md) — пример README конкретного узла проекта.
- [../../scaffold/clients/README.md](../../scaffold/clients/README.md) — пример README композитной сущности.
- [../../scaffold/metrics/README.md](../../scaffold/metrics/README.md) — пример README отдельной парадигмы.

## Не сюда

- Общий технический формат markdown-файла → [02_file-spec.md](02_file-spec.md)
- Миссии `overview`, `active`, `progress`, `decisions` → [02_file-templates.md](02_file-templates.md)


### 3. README vs overview

**README — компактный смысловой вход в папку (контейнер).** Карта файлов, правила содержимого, порядок чтения. **Главная роль — для AI-агента:** быстро понять, читать-не-читать содержимое, нужно ли заходить в overview, в ту ли папку он попал.

**01_overview.md — смысловой вход в сущность папки.** Понять: «что это, в каком состоянии, куда дальше». Стабильный, не операционка, не хроника, не лог решений.

**Правило применения:**

- **README — в любой папке.** Это канон.

**Антиканон:**

- В README **не пишем:** метрики, лидер, миссию сущности, состояние стройки → это в overview.
- В overview **не пишем:** голый листинг файлов («файл X лежит здесь, файл Y там»). Но **необходимые смысловые ссылки в канве текста допустимы** — «принципы и бизнес-модель — в [profile.md](profile.md)», «раскладка папки — в [README.md](README.md)».

`01_overview.md` не является картой связей сущности.

В overview не описываем все зависимости, влияния и соседние контуры объекта. Для живой управленческой единицы это почти всегда бесконечно: стратегия, команда, продажи, продукт, клиенты, метрики, финансы и т.д.

Недопустимо:

- отдельный раздел «Связи» / «Связанные файлы»;
- перечисление соседних файлов;
- перечисление всех контуров, на которые сущность влияет или от которых зависит;
- превращение overview в карту системы.

Карта папки, порядок чтения и связи этой папки с другими  живут в `README.md`.
Карта архитектурных / стратегических связей живёт в профильных документах, если она вообще нужна как отдельный артефакт.
