---
title: "Superpowers — крупнейшая библиотека Skills для Claude Code"
source: "https://github.com/obra/superpowers"
source_type: repo
status: processed
added: 2026-01-30
review_by: 2026-04-30
tags: [skills, claude-code, plugins, superpowers, tdd, debugging, code-review]
publish: false
version: 2
---

# Superpowers — библиотека Skills для Claude Code

## Кратко

Superpowers — крупнейшая авторская open-source библиотека скиллов для Claude Code (MIT). Автор: Jesse Vincent (@obra). 14 скиллов, покрывающих полный цикл AI-кодинга: планирование, TDD, отладка, code review, субагенты, git workflow. Фактически — целая методология разработки с AI, закодированная в машинно-читаемые инструкции. Эталонный пример того, как строить библиотеку Skills.

## Общие характеристики

| Показатель | Значение |
|-----------|----------|
| Лицензия | MIT |
| Кроссплатформенность | Claude Code, Codex, OpenCode |
| Масштаб | Один из самых популярных open-source проектов в экосистеме Claude Code |

Развитие быстрое: v2.0 (октябрь 2025) → v3.0 (середина октября) → v4.0 (декабрь 2025). Десятки релизов за ~3 месяца.

## Структура репозитория

```
superpowers/
├── .claude-plugin/plugin.json   — манифест плагина Claude Code
├── agents/code-reviewer.md      — субагент для code review
├── commands/                    — 3 слэш-команды
│   ├── brainstorm.md            — /brainstorm
│   ├── write-plan.md            — /write-plan
│   └── execute-plan.md          — /execute-plan
├── hooks/                       — хуки (session-start.sh, hooks.json)
├── lib/skills-core.js           — JS-библиотека ядра
├── skills/                      — 14 скиллов (основное содержание)
├── tests/                       — тест-сценарии для скиллов
└── docs/plans/                  — куда сохраняются сгенерированные планы
```

Ключевое: плагин — это не только Skills. Это пакет: **Skills + Commands + Agents + Hooks**. Superpowers использует все четыре механизма.

## Полный список скиллов (14)

### Планирование и выполнение
| Скилл | Суть |
|-------|------|
| **brainstorming** | Дизайн-сессия ДО кода. Вопросы по одному, 2-3 альтернативы, документ в docs/plans/ |
| **writing-plans** | Декомпозиция дизайна на задачи 2-5 мин с путями к файлам и примерами кода |
| **executing-plans** | Пакетное выполнение (batch=3 задачи → отчёт → фидбек → продолжение) |

### Разработка
| Скилл | Суть |
|-------|------|
| **test-driven-development** | Строгий RED-GREEN-REFACTOR. 13 red flags, таблица "отговорок vs реальность" |
| **systematic-debugging** | 4 фазы: Root Cause → Pattern Analysis → Hypothesis Testing → Implementation. 11 файлов в папке |
| **subagent-driven-development** | Каждая задача — свежий субагент + двухэтапное ревью (spec compliance → code quality) |
| **dispatching-parallel-agents** | Параллельные агенты для независимых задач. Правило: только если задачи действительно независимы |

### Code Review
| Скилл | Суть |
|-------|------|
| **requesting-code-review** | Запрос ревью через субагента code-reviewer. Severity: Critical / Important / Minor |
| **receiving-code-review** | Обработка фидбека. "Verify before implementing." YAGNI enforcement |

### Git и завершение
| Скилл | Суть |
|-------|------|
| **using-git-worktrees** | Изолированные workspace для веток. Safety: проверка .gitignore |
| **finishing-a-development-branch** | 4 варианта: merge locally / create PR / keep branch / discard |
| **verification-before-completion** | Финальный чеклист перед "готово" |

### Мета-скиллы
| Скилл | Суть |
|-------|------|
| **using-superpowers** | "If a skill applies, you must use it." AI обязан проверять скиллы перед каждым ответом |
| **writing-skills** | Как создавать новые скиллы. TDD для документации |

## Паттерны проектирования скиллов

Извлечено из анализа всех 14 скиллов и мета-скилла writing-skills. Это знание — рабочий материал для построения собственных Skills в SVAIB.

### Формат SKILL.md

```yaml
---
name: skill-name-in-lowercase
description: "Use when [триггер]. [Что происходит]."
---
```

- YAML-заголовок **минимальный**: только `name` и `description`
- `description` до 1024 символов
- Description отвечает на **"когда использовать"**, НЕ "что делает"
- Остальное — markdown

### Структура содержания

Типичные секции (не обязательно все):
1. **Overview** — суть в 1-2 предложения
2. **The Iron Law** — одно нерушимое правило (якорь скилла)
3. **When to Use** — конкретные триггерные условия
4. **Core Process** — фазы пошагово
5. **Red Flags** — признаки нарушения скилла
6. **Common Rationalizations** — таблица "отговорка → реальность"
7. **Quick Reference** — сводная таблица фаз
8. **Related Skills** — cross-ссылки на другие скиллы

### Ключевые принципы

**Iron Law** — каждый скилл строится вокруг ОДНОГО нерушимого правила. Не десяти. Это якорь, который не даёт AI "уплыть" при давлении пользователя.

**Trigger-based activation** — description описывает КОГДА применять, не ЧТО скилл делает. AI активирует скилл по ситуации, а не по запросу.

**Pressure-тесты** — скиллы тестируются сценариями, в которых AI искушают нарушить правила. Файлы `test-pressure-*.md` моделируют: "пользователь торопит", "кажется что можно пропустить". Фактически TDD для документации.

**Скилл = папка** — `SKILL.md` + supporting files (скрипты, примеры, тест-сценарии). Простые скиллы = 1 файл. Сложные (systematic-debugging) = 11 файлов.

**Self-contained** — каждый файл понятен без контекста других скиллов.

**Cross-references** — скиллы ссылаются друг на друга, образуя связную методологию.

### TDD для создания скиллов (из writing-skills)

1. **RED** — наблюдай как агент проваливается без скилла
2. **GREEN** — напиши минимальный скилл, который решает проблему
3. **REFACTOR** — закрой лазейки, добавь pressure-тесты

## Связь с другими темами

- **coding/** — Superpowers можно использовать как практический инструмент AI-кодинга (TDD, debugging, code review с AI). См. [!coding.md](../coding/!coding.md)
- **agents/** — паттерны субагентов (subagent-driven-development, dispatching-parallel-agents, code-reviewer agent)
- **tools/** — Superpowers распространяется как Claude Code plugin (когда появится файл про плагины, добавить ссылку)
