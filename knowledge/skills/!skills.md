---
title: "Skills — исполняемые инструкции для AI — сводка знаний"
status: processed
added: 2026-01-30
updated: 2026-02-24
review_by: 2026-05-24
tags: [skills, index, marketplace, ecosystem, skill-graph, patterns]
publish: false
version: 12
---

# Skills — Исполняемые инструкции для AI

## Кратко

Skills — структурированные инструкции в формате SKILL.md, которые AI загружает по необходимости и следует им. Не код — "учебники" для AI. Делают AI специалистом в конкретной области без повторения инструкций каждый раз. Открытый стандарт Anthropic (декабрь 2025), принятый OpenAI, Vercel и 40+ AI-агентами. Экосистема: официальный репо Anthropic, CLI `npx skills`, агрегаторы. Автоматическая активация ненадёжна (~20%), детали: [skill-activation.md](skill-activation.md). Знания о Skills — рабочий материал для продукта SVAIB (см. product_vision.md).

---

## Формат

### YAML-заголовок

**Обязательные поля:**

```yaml
---
name: skill-name-in-kebab-case
description: "What it does. Use when [trigger phrases]."
---
```

`name` — kebab-case, без пробелов, заглавных и underscore (`_`), совпадает с именем папки. `description` — до 1024 символов. Должен содержать ЧТО делает и КОГДА использовать (trigger phrases). Это единственный вход для LLM при решении об активации.

**Дополнительные поля:**

```yaml
allowed-tools: "Bash(python:*) Bash(npm:*) WebFetch"  # Ограничение доступных инструментов
license: MIT                                            # Для open-source
compatibility: "Requires network access, Python 3.10+"  # 1-500 символов, требования среды
metadata:
  author: Company Name
  version: 1.0.0
  mcp-server: server-name                               # Связь с MCP-сервером
  category: productivity
  tags: [project-management, automation]
```

**Ограничения безопасности:**
- Запрещены XML-теги (`< >`) — frontmatter попадает в system prompt, возможна инъекция
- Имена с "claude" или "anthropic" зарезервированы
- `SKILL.md` — регистрозависимо (не SKILL.MD, не skill.md)

### Структура SKILL.md

Типичные секции (не обязательно все, но Iron Law и Core Process — обязательны):

1. **Overview** — суть в 1-2 предложения
2. **The Iron Law** — одно нерушимое правило
3. **When to Use** — конкретные триггерные условия
4. **Core Process** — фазы пошагово
5. **Red Flags** — признаки нарушения скилла
6. **Common Rationalizations** — таблица "отговорка AI → почему неправильно"
7. **Quick Reference** — сводная таблица фаз
8. **Related Skills** — cross-ссылки

**Skill vs Command vs Agent:**

| | Skill | Command | Agent |
|---|-------|---------|-------|
| **Кто активирует** | AI автоматически (по триггеру) | Пользователь (`/name`) | Основной AI для подзадачи |
| **Scope** | Конкретная задача | Режим на сессию | Изолированная подзадача |
| **Контекст** | Читает SKILL.md | Загружает @file | Свой отдельный контекст |
| **Когда** | Повторяющаяся задача, нужен процесс | Роль/режим работы | Нужна изоляция |

Plugin — пакет, объединяющий Skills + Commands + Agents + Hooks. На практике они работают вместе: Command `/brainstorm` → Skill brainstorming → Agent code-reviewer.

### Bundled resources

```
skill-name/
├── SKILL.md          # Обязательно. До 500 строк — если больше, выносить в references
├── scripts/          # Исполняемый код (Python/Bash). В SKILL.md указать: execute или read as reference
├── references/       # Документация. Файлы >100 строк → Table of Contents сверху
└── assets/           # Файлы для вывода (шаблоны, логотипы, boilerplate), не для контекста
```

Примеры: systematic-debugging в Superpowers содержит 11 файлов. Anthropic pdf-skill хранит `scripts/rotate_pdf.py` чтобы не переписывать код каждый раз.

**Как ссылаться на resources из SKILL.md:** `"Before writing queries, consult references/api-patterns.md for: rate limiting guidance, pagination patterns, error codes and handling."`

**Что НЕ включать:** README.md, CHANGELOG.md — скилл содержит только то, что нужно AI. При распространении через GitHub — repo-level README отдельно от skill folder.

Много маленьких скиллов лучше одного большого. Системы обрабатывают 100+ скиллов. Один скилл — одна задача. Когда домен глубже — Skill Graph (→ [skill-graphs/](skill-graphs/skill-graphs.md)).

Три паттерна организации ресурсов:
- **High-level guide + references** — SKILL.md содержит quick start, ссылки на отдельные файлы
- **Domain-specific** — references разбиты по доменам, загружается только нужный
- **Conditional details** — базовое в SKILL.md, продвинутое — в отдельных файлах по ссылке

---

## Проектирование

Три источника: официальный Anthropic guide, skill-creator, анализ Superpowers (14 скиллов, [superpowers.md](superpowers.md)).

### Принципы

**Iron Law — один скилл = одно нерушимое правило.** Каждый скилл строится вокруг ОДНОГО правила — якорь, который не даёт AI "уплыть" под давлением. AI рационализирует нарушение правил при давлении ("давай быстрее") — одно чёткое правило сложнее обойти, чем десять размытых. Примеры: TDD — "No production code without a failing test first." Debugging — "No fixes without root cause investigation first." Code review — "Verify before implementing."

**Concise is Key — контекст как общий ресурс.** Контекстное окно делится между системным промптом, историей, метаданными всех скиллов. "Claude уже умный — добавляй только то, чего он не знает." Каждый абзац оправдывает стоимость в токенах. SKILL.md — до 5000 слов. Лаконичные примеры лучше многословных объяснений.

**Degrees of Freedom — детализация зависит от хрупкости.** High freedom (текст) — несколько подходов валидны. Medium (псевдокод) — предпочтительный паттерн, но вариации допустимы. Low (конкретные скрипты) — операции хрупкие, консистентность критична. Метафора: узкий мост → жёсткие перила, открытое поле → много маршрутов. Для критичных валидаций — bundled scripts (код детерминирован, язык — нет).

**Trigger-based description — скилл активируется по ситуации.** Description описывает КОГДА, не ЧТО. Скиллы — не инструменты по запросу, а правила, применяемые автоматически: "If a skill applies to your task, you do not have a choice. You must use it." (Superpowers). Структура: `[What it does] + [When to use it] + [Key capabilities]`.

Хорошо: `"Analyzes Figma design files and generates handoff documentation. Use when user uploads .fig files, asks for 'design specs' or 'design-to-code handoff'."`

Плохо: `"Helps with projects."` / `"Creates sophisticated multi-page documentation systems."` — нет триггеров.

**Activation reality:** автоматическая активация — чистый LLM reasoning (~20% базовая надёжность). Forced eval hook → ~84%. Это архитектурное ограничение. Механика, стратегии, hooks: [skill-activation.md](skill-activation.md).

**Self-contained — каждый файл понятен автономно.** AI может загрузить только один скилл без контекста проекта. В skill graphs: каждый узел самодостаточен, но wikilinks подсказывают когда перейти.

**Cross-references — скиллы ссылаются друг на друга.** Секция "Related Skills" создаёт связную методологию. Пример: systematic-debugging → test-driven-development (написание теста, предотвращающего повторение бага). Skill graphs расширяют: wikilinks в прозе вместо списков.

**Progressive Disclosure — три уровня.** 1) Metadata (name + description) — всегда в контексте (~100 слов). 2) SKILL.md body — при активации (<5k слов). 3) Bundled resources — по необходимости (скрипты исполняются без чтения в контекст). Skill graphs расширяют до пяти уровней. Подробнее: [skill-graphs/](skill-graphs/skill-graphs.md).

**Composability — скилл работает рядом с другими.** Claude загружает несколько скиллов одновременно. Скилл не должен предполагать, что он единственный. Аналогия Anthropic: MCP — профессиональная кухня (инструменты, ингредиенты). Skills — рецепты (как приготовить). Вместе — пользователь получает результат без знания каждого шага. Пример: один скилл получает данные через MCP, другой задаёт brand guidelines с assets/, третий генерирует презентацию.

**Problem-first vs Tool-first.** Два подхода к проектированию. Problem-first: "мне нужно настроить проект" → скилл оркестрирует нужные вызовы, пользователь описывает результат. Tool-first: "у меня подключён Notion MCP" → скилл учит лучшим практикам, пользователь имеет доступ. Большинство скиллов тяготеют к одному подходу. Понимание какой — помогает выбрать паттерн workflow.

### Паттерны workflow

Пять паттернов из Anthropic guide. Типовые подходы для разных задач, не жёсткие шаблоны.

**1. Sequential workflow** — многошаговый процесс в определённом порядке. Явная последовательность, зависимости между шагами, валидация на каждом этапе, rollback при ошибках. Пример: онбординг клиента (create account → setup payment → create subscription → send welcome email).

**2. Multi-MCP coordination** — workflow охватывает несколько сервисов. Фазы привязаны к разным MCP-серверам, данные передаются между фазами, валидация перед переходом. Best practice: в SKILL.md явно указывать имя MCP-сервера и конкретного инструмента — AI должен знать через что получать данные. Пример: design handoff (Figma export → Drive upload → Linear tasks → Slack notification).

**3. Iterative refinement** — качество улучшается с итерацией. Initial draft → quality check (validation script) → refinement loop → finalization. Явные критерии качества, знание когда остановить итерации. Пример: генерация отчётов с `scripts/check_report.py`.

**4. Context-aware tool selection** — один результат, разные инструменты в зависимости от контекста. Decision tree → execute → explain choice. Прозрачность выбора, fallback-опции. Пример: файловое хранилище (>10MB → cloud, docs → Notion, code → GitHub, temporary → local).

**5. Domain-specific intelligence** — специализированные знания поверх доступа к инструментам. Доменная экспертиза встроена в логику, compliance before action, audit trail. Пример: платёжная обработка с compliance-проверками (sanctions, jurisdiction, risk level → process или flag for review).

### Три категории скиллов

| Категория | Что делает | Пример |
|-----------|-----------|--------|
| **Document & Asset Creation** | Консистентный output: документы, презентации, код, дизайн. Без внешних инструментов | frontend-design, docx, pptx |
| **Workflow Automation** | Многошаговые процессы с валидацией и итерацией | skill-creator |
| **MCP Enhancement** | Workflow guidance поверх инструментального доступа MCP | sentry-code-review |

---

## Создание и тестирование

### Процесс создания

Два подхода — дополняют друг друга. Anthropic даёт структуру (как организовать файлы), Superpowers даёт методологию контента (как написать устойчивые инструкции).

**Anthropic (skill-creator, 6 шагов):** Определить 2-3 use cases → Спланировать ресурсы → Инициализировать структуру → Написать инструкции → Упаковать → Итерировать. Фокус на bundled resources и progressive disclosure. Pro tip: итерируй на одной сложной задаче до успеха, потом извлекай подход в скилл.

**Формат определения use case (до начала работы):**
```
Use Case: [название]
Trigger: [что говорит/делает пользователь]
Steps: 1. [действие] 2. [действие] ...
Result: [что получает пользователь]
```

**Superpowers (TDD, 3 фазы):** RED (наблюдай провал без скилла) → GREEN (минимальный скилл, решающий проблему) → REFACTOR (pressure-тесты, закрытие лазеек). Фокус на Iron Law и устойчивости к давлению.

**Evaluation:** skill-creator можно использовать для ревью существующих скиллов — оценка с рекомендациями по best practices. В Claude Code — через субагентов параллельно.

### Тестирование

Три уровня ригор: manual в Claude.ai (быстрая итерация), scripted в Claude Code (повторяемость), programmatic через Skills API (систематическая оценка). Выбирай по масштабу аудитории.

**Triggering tests:** Скилл загружается на очевидных задачах ✅, на перефразированных ✅, НЕ загружается на нерелевантных ❌. Определи 5-10 should-trigger и 5 should-NOT-trigger запросов.

**Functional tests:** Валидные выходы, API-вызовы успешны, error handling работает, edge cases покрыты. Формат: Given → When → Then для каждого сценария.

**Performance comparison:** Одна задача с и без скилла. Сравни: количество сообщений, failed API calls, потреблённые токены, нужда в user correction.

**Pressure-тесты (Superpowers):** Файлы `test-pressure-*.md` моделируют ситуации, где AI искушают нарушить правила: пользователь торопит, кажется что можно пропустить, предыдущий контекст давит. TDD для документации.

### Success metrics

Ориентиры из Anthropic guide, не точные пороги:

**Количественные:** Триггерится на 90% релевантных запросов (измерить: 10-20 test queries). Workflow завершается за X tool calls (сравнить с/без). 0 failed API calls (мониторить логи MCP).

**Качественные:** Пользователю не нужно подсказывать следующий шаг. Workflow завершается без user correction. Консистентные результаты между сессиями (3-5 повторов одного запроса).

### Итерация по фидбеку

**Undertriggering** (скилл не загружается): добавить detail и keywords в description, включая технические термины.

**Overtriggering** (грузится на нерелевантное): добавить negative triggers (`"Do NOT use for..."`), быть специфичнее, уточнить scope.

**Execution issues** (загрузился, работает плохо): улучшить инструкции, добавить error handling, проверить tool names.

### Troubleshooting

**Скилл не загружается (upload error)**
Symptom: "Could not find SKILL.md" или "Invalid frontmatter"
Cause: Имя файла не точно `SKILL.md` (регистрозависимо), незакрытые кавычки в YAML, отсутствуют `---` разделители, пробелы/заглавные в name
Solution: `ls -la` → проверить SKILL.md. YAML: `---` сверху и снизу, кавычки закрыты, name в kebab-case.

**Скилл не триггерится**
Symptom: Никогда не загружается автоматически
Cause: Description слишком общий, нет trigger phrases, нет file types
Solution: Добавить конкретные фразы пользователей. **Debugging technique:** спросить Claude "When would you use the [skill name] skill?" — он процитирует description, видно что не хватает.

**Скилл триггерится лишнее**
Symptom: Загружается на нерелевантные запросы
Solution: 1) Negative triggers: `"Do NOT use for simple exploration (use data-viz instead)."` 2) Специфичнее: `"PDF legal documents for contract review"` вместо `"Processes documents."` 3) Уточнить scope: `"specifically for online payment workflows, not general financial queries."`

**Инструкции не выполняются**
Symptom: Скилл загружен, но Claude не следует инструкциям
Causes и solutions:
- **Verbose** → bullet points, numbered lists, детали в references/
- **Критичное buried** → важное вверх, `## Critical` headers, повторить ключевые точки
- **Ambiguous** → конкретика: `"CRITICAL: Before calling create_project, verify: name non-empty, team member assigned, start date not in past"` вместо `"validate properly"`
- **Model "laziness"** → `"Take your time. Quality > speed. Do not skip validation steps."` (эффективнее в user prompt, чем в SKILL.md)
- **Large context** → SKILL.md до 5000 слов, >20-50 скиллов одновременно → деградация, выносить в references/

### Quick Checklist

**Before:**
- [ ] 2-3 use cases определены (Trigger → Steps → Result)
- [ ] Инструменты определены (built-in или MCP)
- [ ] Структура папки спланирована

**During:**
- [ ] Папка в kebab-case, файл точно `SKILL.md`
- [ ] YAML: `---` разделители, name kebab-case, description содержит WHAT + WHEN
- [ ] Нет XML-тегов (`< >`) в frontmatter
- [ ] Инструкции конкретны и actionable
- [ ] Error handling включён
- [ ] Примеры использования есть
- [ ] References чётко указаны в тексте

**Before upload:**
- [ ] Triggering tests: очевидные ✅, перефразированные ✅, нерелевантные ❌
- [ ] Functional tests пройдены
- [ ] Работа с MCP проверена (если применимо)

**After upload:**
- [ ] Тест в реальных разговорах
- [ ] Мониторинг under/overtriggering
- [ ] Итерация по фидбеку

---

## Экосистема

### Стандарт и установка

Открытый стандарт Agent Skills (декабрь 2025). Принят OpenAI (Codex CLI), поддерживается 40+ AI-агентами. Скилл для Claude Code работает в Cursor, Copilot, Cline без изменений. Org-level deployment (декабрь 2025) — админы разворачивают workspace-wide с авто-обновлением. Спецификация: [github.com/anthropics/skills/spec](https://github.com/anthropics/skills/tree/main/spec)

| Уровень | Путь | Область действия |
|---------|------|-----------------|
| Enterprise | Managed settings | Все пользователи организации |
| Personal | `~/.claude/skills/name/SKILL.md` | Все проекты пользователя |
| Project | `.claude/skills/name/SKILL.md` | Только этот проект |
| Plugin | `<plugin>/skills/name/SKILL.md` | Где плагин включён |

При конфликте имён — побеждает более высокий уровень.

**Установка:** Вручную (скопировать папку), CLI `npx skills add owner/repo` (Vercel, 40+ агентов), плагин-система Claude Code (`/plugin marketplace add`).

### Где найти скиллы

| Ресурс | Что это | Как использовать |
|--------|---------|-----------------|
| **[anthropics/skills](https://github.com/anthropics/skills)** | Официальный репо. Documents, creative, enterprise. Apache 2.0 | `/plugin marketplace add anthropics/skills` |
| **[Superpowers](https://github.com/obra/superpowers)** | Крупнейшая авторская библиотека. 14 скиллов: TDD, debugging, planning, code review. [Детали](superpowers.md) | Плагин Claude Code |
| **[skills.sh](https://skills.sh) / npx skills** | CLI + каталог (Vercel Labs). 40+ агентов, лидерборд | `npx skills add owner/repo` |
| **[SkillsMP](https://skillsmp.com)** | Веб-агрегатор. Десятки тысяч скиллов, фильтрация | Найти → клонировать с GitHub |
| **[HashiCorp](https://github.com/hashicorp/agent-skills)** | Terraform, Packer, инфраструктура | `npx skills add hashicorp/agent-skills` |
| **[antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills)** | Курированная коллекция 883+ скиллов, 9 категорий | `npx antigravity-awesome-skills` |

Также: [add-skill.org](https://add-skill.org), openskills, [SkillHub](https://www.skillhub.club/).

**Качество и безопасность:** Экосистема open source — качество варьируется. Перед установкой: прочитать SKILL.md, проверить скрипты, оценить репо.

### API

Skills API: endpoint `/v1/skills`, параметр `container.skills` в Messages API, интеграция с Claude Agent SDK. Требует Code Execution Tool beta. Use cases: production deployments, automated pipelines, agent systems. Для ручного тестирования — Claude.ai / Claude Code.

---

## Источники

- [The Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) — Официальный PDF-гайд Anthropic (33 стр., 6 глав). Паттерны, troubleshooting, best practices. Полный текст: [_inbox/anthropic-skills-guide-text.md](../../_inbox/anthropic-skills-guide-text.md)
- [Agent Skills with Anthropic](https://learn.deeplearning.ai/courses/agent-skills-with-anthropic) — Курс Anthropic + DeepLearning.AI (Elie Schoppik, Andrew Ng, январь 2026)

## Связанные файлы

- [skill-graphs/](skill-graphs/) — Skill Graphs: сети файлов знаний, связанных wikilinks (теория, архитектура, паттерны)
- [skill-activation.md](skill-activation.md) — Механика активации: надёжность, hooks, стратегии
- [superpowers.md](superpowers.md) — Superpowers: крупнейшая библиотека скиллов
- [../plugins/!plugins.md](../plugins/!plugins.md) — Плагины: Skills + Commands + Agents + Hooks + MCP + LSP
- [../agents/subagents.md](../agents/subagents.md) — Субагенты: когда Skill недостаточно
- [../agents/!agents.md](../agents/!agents.md) — Сводка по агентным системам
- [../agents/mcp.md](../agents/mcp.md) — MCP: Skills + MCP комбинация
- [../context/markdown-for-llm.md](../context/markdown-for-llm.md) — Как LLM видит wikilinks и YAML
