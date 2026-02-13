---
title: "Skills — исполняемые инструкции для AI — сводка знаний"
status: processed
added: 2026-01-30
updated: 2026-02-07
review_by: 2026-04-30
tags: [skills, index, marketplace, ecosystem]
publish: false
version: 9
---

# Skills — Исполняемые инструкции для AI

## Кратко

Skills — структурированные промпт-инструкции, которые AI загружает по необходимости. Папки с SKILL.md файлами, содержащими инструкции, шаблоны, примеры. НЕ код — это "учебники", которые AI читает и следует им. Пример: skill для TDD объясняет агенту, как писать тесты перед кодом. Skills делают AI специалистом в конкретной области без повторения инструкций каждый раз. В декабре 2025 Anthropic опубликовал Agent Skills как открытый стандарт — его приняли OpenAI, Vercel и другие. Вокруг стандарта выросла экосистема: официальный репозиторий Anthropic, CLI-инструмент Vercel (`npx skills`), агрегаторы (SkillsMP). **Важно:** автоматическая активация скиллов ненадёжна (~20% базовая успешность), требует forced eval hooks для стабильной работы. Детали: [skill-activation.md](skill-activation.md).

Знания о создании и организации Skills — рабочий материал для продукта SVAIB (см. product_vision.md).

## Что такое Skill

Skill — это папка с файлом `SKILL.md` внутри. AI читает этот файл и следует инструкциям. Не код, не конфиг — текст на естественном языке, написанный для AI.

**Простой скилл** = одна папка, один SKILL.md.
**Сложный скилл** = SKILL.md + bundled resources. Официальная структура (Anthropic):

```
skill-name/
├── SKILL.md          # Обязательно. До 500 строк — если больше, выносить в references
├── scripts/          # Исполняемый код (Python/Bash). Важно: в SKILL.md явно указать — execute или read as reference
├── references/       # Документация по необходимости. Файлы >100 строк → table of contents сверху
└── assets/           # Файлы для вывода, не для контекста (шаблоны, логотипы, схемы, boilerplate)
```

Пример: systematic-debugging в Superpowers содержит 11 файлов. Пример из Anthropic: pdf-skill хранит `scripts/rotate_pdf.py` чтобы не переписывать код каждый раз.

**Что НЕ включать:** README.md, CHANGELOG.md, INSTALLATION_GUIDE.md — скилл содержит только то, что нужно AI для работы. Никакой вспомогательной документации.

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

Два источника: официальный skill-creator от Anthropic и анализ Superpowers (14 скиллов, [superpowers.md](superpowers.md)).

### Concise is Key — контекст как общественное благо

Официальный принцип Anthropic: контекстное окно — общий ресурс. Скиллы делят его с системным промптом, историей диалога, метаданными других скиллов.

**"Claude уже очень умный. Добавляй только то, чего он не знает."** Каждый абзац должен оправдывать свою стоимость в токенах. Лаконичные примеры лучше многословных объяснений.

### Degrees of Freedom — степени свободы инструкций

Уровень детализации инструкций зависит от хрупкости задачи:

- **High freedom** (текстовые инструкции) — несколько подходов валидны, решения зависят от контекста
- **Medium freedom** (псевдокод, скрипты с параметрами) — есть предпочтительный паттерн, но вариации допустимы
- **Low freedom** (конкретные скрипты, мало параметров) — операции хрупкие, консистентность критична

Метафора Anthropic: узкий мост с обрывами → жёсткие перила (low freedom). Открытое поле → много маршрутов (high freedom).

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

### Много маленьких скиллов лучше одного большого

Системы обрабатывают 100+ скиллов. Лучше разбить сложный workflow на несколько узких скиллов с понятными именами, чем делать один монолитный. Каждый скилл — одна задача.

### Self-contained — каждый файл понятен без контекста

Скилл должен быть полностью понятен AI без чтения других файлов. Это важно потому что AI может загрузить только один скилл, без контекста проекта или других скиллов.

### Cross-references — скиллы ссылаются друг на друга

Связанные скиллы указывают друг на друга в секции "Related Skills". Это создаёт связную методологию, а не набор изолированных инструкций. Пример: systematic-debugging ссылается на test-driven-development для финальной фазы (написание теста, предотвращающего повторение бага).

### Progressive Disclosure — три уровня загрузки

Скиллы используют трёхуровневую систему для экономии контекста:

1. **Metadata** (name + description) — всегда в контексте (~100 слов)
2. **SKILL.md body** — загружается при активации (<5k слов, до 500 строк)
3. **Bundled resources** — по необходимости (без лимита, скрипты исполняются без чтения в контекст)

Три паттерна организации (из Anthropic skill-creator):

- **High-level guide + references** — SKILL.md содержит quick start, ссылается на отдельные файлы для продвинутых тем
- **Domain-specific** — references разбиты по доменам (finance.md, sales.md, product.md), загружается только нужный
- **Conditional details** — базовое в SKILL.md, продвинутое (tracked changes, OOXML) — в отдельных файлах по ссылке

Подробнее о механике загрузки и надёжности активации: [skill-activation.md](skill-activation.md).

### Table of Contents для reference-файлов

Reference-файлы >100 строк → `## Contents` (буллет-лист секций) в начале файла. Claude может читать вложенные файлы частично (`head -100`), ToC даёт карту при partial read. Формат: простые буллеты, без ссылок и номеров. Источник: [Anthropic Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).

## Процесс создания скилла

Два подхода: от Anthropic (официальный, 6 шагов) и от Superpowers (TDD-подход, 3 фазы).

**Anthropic (skill-creator):** Понять юзкейсы → Спланировать ресурсы → Инициализировать → Написать → Упаковать → Итерировать. Фокус на bundled resources и progressive disclosure. Полный процесс: установленный скилл `skill-creator`.

**Superpowers (writing-skills):** RED (наблюдай провал без скилла) → GREEN (минимальный скилл) → REFACTOR (pressure-тесты, закрытие лазеек). Фокус на Iron Law и устойчивости к давлению.

Подходы не противоречат — дополняют. Anthropic даёт структуру и инфраструктуру (как организовать файлы), Superpowers даёт методологию контента (как написать устойчивые инструкции).

### Evaluation и тестирование скиллов

**Evaluation через skill-creator:** skill-creator можно использовать не только для создания, но и для ревью существующих скиллов. Прогоняешь скилл — получаешь оценку (9/10, 10/10) с конкретными рекомендациями по best practices. В Claude Code — через субагентов параллельно для нескольких скиллов.

**Unit testing скиллов:** Скиллы тестируются как софт. Определяешь test queries → expected behavior (порядок шагов, форматы, какие скрипты запускаются) → проверяешь output (структура файлов, корректность). Финальные шаги: human feedback + тест на разных моделях.

### Skills + MCP: комбинирование скиллов с внешними данными

Скилл может опираться на MCP-сервер как источник данных. Best practice от Anthropic: в SKILL.md явно указывать имя MCP-сервера и конкретного инструмента, чтобы AI знал через что получать данные. Пример: скилл анализа маркетинга указывает `bigquery` MCP-сервер и таблицу со схемой, вместо ожидания CSV-загрузки от пользователя.

Это позволяет комбинировать несколько скиллов в одном разговоре: один скилл получает данные через MCP, другой задаёт brand guidelines с логотипами из assets/, третий (встроенный PowerPoint) генерирует презентацию. Каждый скилл отвечает за своё, вместе — полный workflow.

Подробнее о MCP: [../agents/mcp.md](../agents/mcp.md).

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

### Уровни установки скиллов

| Уровень | Путь | Область действия |
|---------|------|-----------------|
| Enterprise | Managed settings | Все пользователи организации |
| Personal | `~/.claude/skills/name/SKILL.md` | Все проекты пользователя |
| Project | `.claude/skills/name/SKILL.md` | Только этот проект |
| Plugin | `<plugin>/skills/name/SKILL.md` | Где плагин включён |

При конфликте имён — побеждает более высокий уровень.

### Как устанавливать скиллы

**Вручную:** скопировать папку со SKILL.md в `~/.claude/skills/` (все проекты) или `.claude/skills/` (этот проект).

**Через CLI (Vercel):** `npx skills add owner/repo` — устанавливает скилл из GitHub-репо. Поддерживает 40+ агентов, создаёт симлинки для каждого. Команды: `add`, `list`, `find`, `update`, `init`.

**Через плагин-систему Claude Code:** `/plugin marketplace add anthropics/skills` → `/plugin install skill-name@anthropic-agent-skills`.

## Использование с Claude API

Работает. Для работы скиллов через Claude Messages API требуется Code Execution Tool + Files API. При разработке через API необходимо вручную настраивать контейнер для выполнения кода и загрузку файлов. 

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

## Источники

- [Agent Skills with Anthropic](https://learn.deeplearning.ai/courses/agent-skills-with-anthropic) — Официальный курс от Anthropic и DeepLearning.AI (Elie Schoppik, Andrew Ng). Выпущен 28 января 2026. Охватывает создание и применение скиллов в Claude AI, API, Code и SDK.

## Связанные файлы

- [../plugins/!plugins.md](../plugins/!plugins.md) — Плагины: зонтичный формат, объединяющий Skills + Commands + Agents + Hooks + MCP + LSP
- [../agents/subagents.md](../agents/subagents.md) — Субагенты: когда Skill недостаточно и нужна изоляция контекста
- [../agents/!agents.md](../agents/!agents.md) — Сводка по агентным системам (Skills как компонент)
