---
title: "Последовательность создания Skill"
updated: 2026-03-02
verified: 2026-03-02
---

# Создание Skill — пошаговая инструкция

Выполняй шаги по порядку. Справочник по формату — в конце файла.

---

## Шаг 1. Понять боль

Разговор с Виктором: что отнимает время? Как часто? Что на входе, что на выходе?

**Критерий:** можешь в одном предложении сформулировать: "Скилл делает X когда Y".

---

## Шаг 2. Поиск аналогов + проверка конфликтов

Два действия параллельно (независимы друг от друга):

**a) Поиск аналогов — проверь каталоги:**

| Каталог | Что внутри | Как искать |
|---------|-----------|-----------|
| [Superpowers](https://github.com/obra/superpowers) | 14 скиллов: TDD, debugging, planning, code review. MIT | Плагин Claude Code |
| [anthropics/skills](https://github.com/anthropics/skills) | Официальные скиллы Anthropic. Documents, creative, enterprise | `/plugin marketplace add` |
| [skills.sh](https://skills.sh) | CLI + каталог Vercel Labs. 40+ агентов, лидерборд | `npx skills add owner/repo` |
| [SkillsMP](https://skillsmp.com) | Веб-агрегатор. Десятки тысяч скиллов, фильтрация | Найти → клонировать с GitHub |
| [antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | Курированная коллекция 883+ скиллов, 9 категорий | `npx antigravity-awesome-skills` |
| [HashiCorp](https://github.com/hashicorp/agent-skills) | Terraform, Packer, инфраструктура | `npx skills add hashicorp/agent-skills` |

Также: [add-skill.org](https://add-skill.org), [SkillHub](https://www.skillhub.club/) — дополнительные агрегаторы.

Если не нашёл в каталогах — веб-поиск: "claude code skill [задача]".

Также проверь **bundled skills** Claude Code — может задача уже решена: `/simplify` (код-ревью, 3 параллельных агента), `/batch` (массовые изменения с worktree и PR), `/debug` (дебаг сессии).

**b) Проверка конфликтов:**
- Glob `.claude/skills/` и `.claude/commands/` — нет ли скилла с похожим триггером или пересечением
- **Важно:** commands и skills объединены. Если есть `.claude/commands/review.md` и ты создашь `.claude/skills/review/SKILL.md` — skill перекроет command

**Критерий:** ответ "аналогов нет, строим сами" или "нашёл X, адаптируем" + конфликтов нет (или обсуждён с Виктором).

---

## Шаг 3. Спроектировать

Определи и покажи Виктору:

| Параметр | Что указать |
|----------|-------------|
| Тип | **Reference** (conventions, guidelines — inline) или **Task** (step-by-step — часто `disable-model-invocation: true`) |
| `name` | kebab-case, ≤64 символа |
| Триггер | Когда скилл активируется (точные фразы пользователя) |
| Анти-триггеры | Когда НЕ активируется |
| Входы | Что получает (аргументы, контекст) |
| Логика | Шаги выполнения |
| Выходы | Что создаёт/меняет |
| `allowed-tools` | Какие инструменты нужны |

**Покажи Виктору. Получи одобрение. Только после этого — строить.**

---

## Шаг 4. Построить

Два варианта:

**a) Через `document-skills:skill-creator`** (рекомендуется для новых скиллов):
- Запусти через Skill tool: `skill: "document-skills:skill-creator"`
- Он проведёт интервью: уточнит use cases, trigger-фразы, нужные ресурсы
- Сгенерирует структуру директории и шаблон SKILL.md
- Поможет с формулировкой description

**b) Вручную** — если скилл простой или адаптируешь существующий.

**Куда класть:**

| Уровень | Путь | Когда |
|---------|------|-------|
| Project | `.claude/skills/<name>/SKILL.md` | Скилл для этого проекта |
| Personal | `~/.claude/skills/<name>/SKILL.md` | Скилл для всех проектов |
| Plugin | `framework/plugin/skills/<name>/SKILL.md` | Скилл для продукта (клиентам) |

Чеклист перед сохранением:

- [ ] `name`: kebab-case, ≤64 символа, не `claude-*`/`anthropic-*`
- [ ] `description`: что делает + когда использовать. Trigger-фразы конкретные. Экономь бюджет (~16K на ВСЕ скиллы)
- [ ] Anti-triggers в description: "Do NOT use when..."
- [ ] SKILL.md ≤500 строк; детали → `references/`
- [ ] Нет XML-тегов в frontmatter
- [ ] Информация — либо в SKILL.md, либо в references (не дублировать)
- [ ] Для скиллов с side effects: настрой permission rules (`Skill(name)` в `/permissions`)

---

## Шаг 5. Валидировать

**a) Triggering тесты** — запусти на реальном примере:

- [ ] 5 промптов где ДОЛЖЕН сработать
- [ ] 5 промптов где НЕ должен
- [ ] Скилл видим в `/context`
- [ ] Не конфликтует с существующими

**b) Скоринг через skill-creator** — запусти `document-skills:skill-creator` на готовом скилле для оценки:
- Качество description и trigger-фраз
- Структура SKILL.md (секции, progressive disclosure)
- Best practices (Iron Law, self-contained, composability)
- Рекомендации по улучшению

**Troubleshooting:**

| Проблема | Решение |
|----------|---------|
| Не триггерится | Description слишком абстрактный. Добавь точные trigger-фразы. **Debug:** спроси Claude "When would you use the [skill-name] skill?" — он процитирует description, видно что не хватает |
| Триггерится лишний раз | Добавь anti-triggers: "Do NOT use when..." |
| Не видим в `/context` | Проверь: SKILL.md (регистрозависимо!), структура директории, бюджет описаний |
| Ошибки при вызове | Нет real-time валидации YAML; проверь синтаксис вручную |

---
---

# Справочник: формат Skill

> Дистилляция из knowledge/skills/ (4 файла), context7, внешних ссылок (code.claude.com/docs, agentskills.io/spec, блоги). Дата: 2026-03-02.

## Структура директории

```
my-skill/
├── SKILL.md              # Основной файл (обязательный, регистрозависимо)
├── references/           # (опц.) Справочные — загружаются on demand
├── scripts/              # (опц.) Утилиты — запускаются без чтения в контекст (token efficient)
└── assets/               # (опц.) Медиа, шаблоны
```

Для простого скилла достаточно одного `SKILL.md`. Поддиректории — по необходимости.

## YAML frontmatter

### Ключевые атрибуты

| Атрибут | Статус | Описание |
|---------|--------|----------|
| `name` | рекомендован | kebab-case, ≤64 символа. Fallback: имя директории |
| `description` | рекомендован | Что делает + когда использовать. Trigger-фразы конкретные. ≤1024 символов (Agent Skills spec). Fallback: 1-й абзац markdown |

**Примеры description:**
- Хорошо: `"Analyzes Figma design files and generates handoff documentation. Use when user uploads .fig files, asks for 'design specs' or 'design-to-code handoff'."`
- Плохо: `"Helps with projects."` / `"Creates sophisticated multi-page documentation systems."` — нет триггеров, непонятно КОГДА

### Управление вызовом

| Атрибут | Значение | Эффект |
|---------|----------|--------|
| (default) | — | description в контексте, full skill при вызове |
| `disable-model-invocation` | `true` | description НЕ в контексте. Только ручной вызов через `/name` |
| `user-invocable` | `false` | скрыт из `/` меню, но description в контексте — Claude вызывает сам |

### Опциональные атрибуты

| Атрибут | Описание |
|---------|----------|
| `allowed-tools` | Ограничение инструментов. Comma или space-delimited. Примеры: `Read, Grep, Glob` или `Read Bash(git:*)` |
| `model` | Модель: `sonnet`, `haiku`, `opus` |
| `argument-hint` | Подсказка аргументов: `[filename] [format]` |
| `context` | `fork` — запуск в изолированном субагенте. SKILL.md body становится промптом субагента. Субагент НЕ видит историю разговора. Не подходит для скиллов-guidelines без конкретной задачи |
| `agent` | Тип субагента при context: fork (`Explore`, `Plan`, `general-purpose`, кастомный из `.claude/agents/`) |
| `hooks` | Хуки жизненного цикла скилла. Формат: см. [CC docs: Hooks in skills and agents](https://code.claude.com/docs/en/hooks#hooks-in-skills-and-agents) |
| `version` | Семантическая версия *(Agent Skills spec, не используется Claude Code)* |
| `license`, `compatibility`, `metadata` | Мета-информация *(Agent Skills spec — нужны при дистрибуции плагина)* |

## Тело SKILL.md

Markdown инструкции для Claude. Рекомендуется императивный стиль: "To accomplish X, do Y".

Типичные секции: Overview, Iron Law, When to Use / When NOT, Core Process, Red Flags, Quick Reference, Related Skills.

### Динамические возможности

| Механизм | Синтаксис | Что делает |
|----------|-----------|-----------|
| Аргументы | `$ARGUMENTS`, `$ARGUMENTS[0]`, `$1`, `$2` | Подстановка аргументов пользователя. Если `$ARGUMENTS` нет в контенте — аргументы добавляются в конец как `ARGUMENTS: <value>` |
| Session ID | `${CLAUDE_SESSION_ID}` | ID текущей сессии |
| Shell preprocessing | `` !`command` `` | Выполняет shell-команду ДО отправки Claude, output подставляется |
| Extended thinking | слово `ultrathink` в контенте | Включает extended thinking |

## Архитектурные ограничения

- **Бюджет описаний:** 2% от context window (fallback ~16K символов). Env: `SLASH_COMMAND_TOOL_CHAR_BUDGET`. Проверка: `/context`
- **Активация:** LLM-based routing по description. Базовая надёжность ~20%. С forced eval hook ~84%
- **Progressive disclosure:** metadata (~100 токенов) → SKILL.md body (≤500 строк) → references (on demand)
- **Нет real-time валидации** — ошибки в YAML видны только при вызове
- **Имена:** не `claude-*`, не `anthropic-*` (зарезервированы). Нет XML-тегов в frontmatter
- **Приоритет при конфликте:** enterprise > personal > project. Skill > command при совпадении имён

## Повышение надёжности активации

| Стратегия | Надёжность | Описание |
|-----------|-----------|----------|
| Только description | ~20% | Базовый вариант |
| Forced eval hook | ~84% | Hook `UserPromptSubmit` — Claude оценивает ВСЕ скиллы перед ответом |
| Критичные правила в CLAUDE.md | + | Дублирование ключевых триггеров |
| Subagent с preloaded skills | + | Полный контент скилла при старте субагента |

## Skill vs Command vs Agent

| | Skill | Command | Agent |
|---|---|---|---|
| Файл | `SKILL.md` в поддиректории | `.md` файл | `.md` файл |
| Auto-trigger | Да (по description) | Нет (только `/name`) | Нет (вызывается координатором) |
| Структура | Директория + поддиректории | Один файл | Один файл |
| Контекст | Основной (или fork) | Основной | Изолированный |
| Когда | Повторяемая процедура | Смена роли/режима | Автономная работа, изоляция |
