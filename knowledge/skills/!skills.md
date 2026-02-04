---
title: "Skills — исполняемые инструкции для AI — сводка знаний"
status: processed
added: 2026-01-30
review_by: 2026-04-30
tags: [skills, index, marketplace, ecosystem]
publish: false
version: 5
---

# Skills — Исполняемые инструкции для AI

## Кратко

Skills — структурированные промпт-инструкции, которые AI загружает по необходимости. Папки с SKILL.md файлами, содержащими инструкции, шаблоны, примеры. НЕ код — это "учебники", которые AI читает и следует им. Пример: skill для TDD объясняет агенту, как писать тесты перед кодом. Skills делают AI специалистом в конкретной области без повторения инструкций каждый раз. В декабре 2025 Anthropic опубликовал Agent Skills как открытый стандарт — его приняли OpenAI, Vercel и другие. Вокруг стандарта выросла экосистема: официальный репозиторий Anthropic, CLI-инструмент Vercel (`npx skills`), агрегаторы (SkillsMP). **Важно:** автоматическая активация скиллов ненадёжна (~20% базовая успешность), требует forced eval hooks для стабильной работы. Детали: [skill-activation.md](skill-activation.md).

Знания о создании и организации Skills — рабочий материал для продукта SVAIB (см. product_vision.md).

## Что такое Skill

Skill — это папка с файлом `SKILL.md` внутри. AI читает этот файл и следует инструкциям. Не код, не конфиг — текст на естественном языке, написанный для AI.

**Простой скилл** = одна папка, один SKILL.md.
**Сложный скилл** = SKILL.md + supporting files (скрипты, примеры, тест-сценарии). Пример: systematic-debugging в Superpowers содержит 11 файлов.

Skill НЕ путать с:
- **Command** (слэш-команда) — вызывается пользователем вручную (`/brainstorm`). Задаёт режим работы на всю сессию.
- **Agent** (субагент) — изолированный AI для подзадачи. Имеет свой контекст и инструменты.
- **Plugin** — пакет, который может включать Skills + Commands + Agents + Hooks вместе.

## Формат SKILL.md

### YAML-заголовок

```yaml
---
name: skill-name-in-lowercase
description: "Use when [триггер]. [Что происходит]."
---
```

Всего два поля. `description` до 1024 символов. Критически важно: description отвечает на **"КОГДА использовать"**, а не "что делает". AI активирует скилл по триггерной ситуации, не по запросу пользователя.

Пример хорошего description: "Use when debugging a failing test or unexpected behavior. Guides through root cause investigation before attempting fixes."

Пример плохого: "A debugging methodology with 4 phases that helps find bugs." — не говорит когда применять.

### Типичная структура содержания

1. **Overview** — суть в 1-2 предложения
2. **The Iron Law** — одно нерушимое правило (см. ниже)
3. **When to Use** — конкретные триггерные условия
4. **Core Process** — фазы пошагово
5. **Red Flags** — признаки того, что AI нарушает скилл
6. **Common Rationalizations** — таблица "отговорка AI → почему это неправильно"
7. **Quick Reference** — сводная таблица фаз
8. **Related Skills** — cross-ссылки на другие скиллы

Не обязательно все секции. Но Iron Law и Core Process — обязательны.

## Ключевые принципы проектирования

Извлечено из анализа Superpowers (14 скиллов) — самой успешной авторской библиотеки скиллов. Детали: [superpowers.md](superpowers.md).

### Iron Law — один скилл = одно нерушимое правило

Каждый скилл строится вокруг ОДНОГО нерушимого правила. Не десяти, не пяти — одного. Это якорь, который не даёт AI "уплыть" под давлением пользователя.

Примеры:
- TDD: "No production code without a failing test first."
- Debugging: "No fixes without root cause investigation first."
- Code review: "Verify before implementing."

Почему одно: AI под давлением ("давай быстрее", "пропусти тесты") начинает рационализировать нарушение правил. Одно чёткое правило сложнее обойти, чем десять размытых.

### Trigger-based activation — скилл активируется по ситуации

Description в YAML описывает КОГДА применять, не ЧТО скилл делает. Мета-скилл using-superpowers в Superpowers формулирует это жёстко: "If a skill applies to your task, you do not have a choice. You must use it." AI обязан проверять список скиллов перед каждым ответом.

Идея: скиллы — не "инструменты по запросу", а **правила, которые AI применяет автоматически** когда ситуация подходит.

**Реальность:** Автоматическая активация работает через LLM reasoning (не алгоритмический роутинг) с базовой надёжностью ~20%. Для стабильной работы нужны forced eval hooks (~84%) или явный вызов пользователем. Подробности механики загрузки и стратегии повышения надёжности: [skill-activation.md](skill-activation.md).

### Pressure-тесты — TDD для документации

Скиллы тестируются сценариями, в которых AI искушают нарушить правила. Файлы `test-pressure-*.md` моделируют ситуации:
- Пользователь торопит ("просто исправь, без тестов")
- Кажется что можно пропустить ("это мелкий баг, не нужен root cause analysis")
- Предыдущий контекст давит ("мы уже потратили час, давай закоммитим что есть")

Методология создания скилла (из writing-skills в Superpowers):
1. **RED** — наблюдай как AI проваливается без скилла
2. **GREEN** — напиши минимальный скилл, который решает проблему
3. **REFACTOR** — закрой лазейки, добавь pressure-тесты

### Self-contained — каждый файл понятен без контекста

Скилл должен быть полностью понятен AI без чтения других файлов. Это важно потому что AI может загрузить только один скилл, без контекста проекта или других скиллов.

### Cross-references — скиллы ссылаются друг на друга

Связанные скиллы указывают друг на друга в секции "Related Skills". Это создаёт связную методологию, а не набор изолированных инструкций. Пример: systematic-debugging ссылается на test-driven-development для финальной фазы (написание теста, предотвращающего повторение бага).

## Skill vs Command vs Agent

| | Skill | Command | Agent |
|---|-------|---------|-------|
| **Кто активирует** | AI автоматически (по триггеру) | Пользователь вручную (`/name`) | Основной AI вызывает для подзадачи |
| **Scope** | Конкретная задача | Режим на всю сессию | Изолированная подзадача |
| **Контекст** | Читает SKILL.md | Загружает @file ссылки | Получает свой отдельный контекст |
| **Пример** | "Сейчас делай TDD" | "Ты — партнёр по research" | "Проверь code quality этого PR" |
| **Формат** | SKILL.md + supporting files | Свободный markdown | Markdown с инструкциями |
| **Когда нужен** | Повторяющаяся задача, AI должен следовать процессу | Роль/режим работы | Задача требует изоляции |

На практике они работают вместе. В Superpowers: Command `/brainstorm` запускает Skill brainstorming, который может вызвать Agent code-reviewer.

## Экосистема и распространение

### Agent Skills как открытый стандарт

В декабре 2025 Anthropic опубликовал спецификацию Agent Skills — открытый стандарт формата SKILL.md. Стандарт принят OpenAI (Codex CLI использует тот же формат) и поддерживается 40+ AI-агентами. Это значит: скилл, написанный для Claude Code, работает в Cursor, Copilot, Cline и других без изменений.

Спецификация: [github.com/anthropics/skills/spec](https://github.com/anthropics/skills/tree/main/spec)

### Как устанавливать скиллы

**Вручную:** скопировать папку со SKILL.md в `~/.claude/skills/` (личные) или `.claude/skills/` (проектные).

**Через CLI (Vercel):** `npx skills add owner/repo` — устанавливает скилл из GitHub-репо. Поддерживает 40+ агентов, создаёт симлинки для каждого. Команды: `add`, `list`, `find`, `update`, `init`.

**Через плагин-систему Claude Code:** `/plugin marketplace add anthropics/skills` → `/plugin install skill-name@anthropic-agent-skills`.

### Где найти скиллы

| Ресурс | Что это | Как использовать |
|--------|---------|-----------------|
| **[anthropics/skills](https://github.com/anthropics/skills)** | Официальный репо Anthropic. Reference implementation стандарта. Скиллы для документов (docx, pdf, pptx, xlsx), creative, enterprise. Apache 2.0 | `/plugin marketplace add anthropics/skills` → `/plugin install skill-name` |
| **[Superpowers](https://github.com/obra/superpowers)** | Крупнейшая авторская библиотека. 14 скиллов: TDD, debugging, planning, code review, субагенты, git workflow. Автор: Jesse Vincent (@obra). [Детали](superpowers.md) | Устанавливается как плагин Claude Code |
| **[skills.sh](https://skills.sh) / npx skills** | CLI + каталог (Vercel Labs). Установка скиллов из любого GitHub-репо. 40+ агентов. Лидерборд, trending | `npx skills add owner/repo`, `npx skills find keyword` |
| **[SkillsMP](https://skillsmp.com)** | Веб-агрегатор (независимый). Индексирует GitHub-репо со SKILL.md. Десятки тысяч скиллов. Фильтрация по качеству, категории, поиск | Найти на сайте → клонировать репо с GitHub |
| **[HashiCorp](https://github.com/hashicorp/agent-skills)** | Отраслевой репо. Скиллы для Terraform, Packer, инфраструктуры | `npx skills add hashicorp/agent-skills` |

Также существуют: [add-skill.org](https://add-skill.org) (альтернативный CLI), openskills (npm-пакет, универсальный загрузчик), [SkillHub](https://www.skillhub.club/).

### Качество и безопасность

Экосистема open source — качество варьируется. Перед установкой стороннего скилла рекомендуется:
- Прочитать SKILL.md (что скилл просит AI делать)
- Проверить supporting files (скрипты, хуки)
- Оценить репо (активность, автор)

Официальный `anthropics/skills` — наиболее безопасный источник, но содержит мало скиллов.

## Файлы в этой папке

- [superpowers.md](superpowers.md) — Superpowers: крупнейшая авторская библиотека скиллов для Claude Code (14 skills, полный список скиллов, структура репо)
- [skill-activation.md](skill-activation.md) — Механика активации скиллов: progressive disclosure, LLM routing, проблема надёжности (~20% → 84% с hooks), frontmatter поля, стратегии
