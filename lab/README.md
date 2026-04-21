---
title: "lab/ — мастерская AI-помощников svaib"
updated: 2026-04-20
version: 2
scope: lab
priority: high
type: reference
---

# lab/

Мастерская AI-помощников для **внутренней работы svaib**: скиллы, команды, агенты, хуки в `.claude/`. Здесь накапливается знание *как строить* (принципы, todo-файлы, tooling-registry), проектируются новые помощники и чинятся существующие. Не путать с `framework/skills/` — там продуктовые скиллы для клиентов Second AI Brain.

Загружается принудительно при вызове `/svaib-lab`. Служит навигатором — отсюда агент находит нужный файл, не читая всё подряд.

## Связанные файлы

- [01_overview.md](01_overview.md) — миссия направления, стадия, цель декады
- [02_active.md](02_active.md) — что в работе сейчас, Session Handoff
- [02_backlog.md](02_backlog.md) — задачи направления на будущее
- [03_progress.md](03_progress.md) — хроника по направлению
- [_inbox/01_inbox.md](_inbox/01_inbox.md) — входящее на разбор

Направление устроено по универсальной модели svaib: `_inbox → backlog → active → progress + decisions`. Правила работы — [work-model.md](work-model.md).

---

## Что делаешь → где искать

| Задача | Файл в lab/ | Знания в knowledge/ |
|--------|------------|---------------------|
| Выбрать тип помощника (Skill/Command/Agent/Hook) | `tooling.md` | — |
| Создать Skill | `todo-skill.md` | `knowledge/skills/` — паттерны, skill graphs, arscontexta |
| Создать Command | `todo-command.md` | `knowledge/coding/claude-code.md` — механики |
| Создать Agent | `todo-agent.md` | `knowledge/agents/` — субагенты, MCP, паттерны |
| Создать Hook | `todo-hook.md` | `knowledge/coding/claude-code.md` — механики hooks |
| Понять принципы проектирования | `principles.md` | — |
| Понять context engineering | — | `knowledge/context/` — RAG, memory, progressive disclosure |
| Понять промптинг | — | `knowledge/prompting/` — техники, паттерны |
| Посмотреть чужие решения | — | `knowledge/plugins/` — плагины, каталоги |
| Посмотреть наши эксперименты | — | `knowledge/cases/` — кейсы применения |

**Навигация в knowledge/:** каждая категория имеет README (что есть) и !файл (сводка знаний). Читай README категории → потом конкретный файл.

**Архитектура arscontexta** — reference-реализация skill graph подхода: progressive disclosure, session-orient, mode separation, hooks как enforcement. Изучено и задокументировано в `knowledge/context/skill-graphs/` (README → architecture → patterns → skill anatomy → полный пример /architect). Наши design constraints для команд выведены из этой архитектуры.

---

## Инструментарий

| Файл | Что внутри |
|------|-----------|
| `tooling-registry.md` | Сводный реестр всего инструментария: команды, скиллы, хуки, инструменты. Читай первым если нужно понять что у нас есть |
| `tooling.md` | Как выбрать тип помощника (Skill/Command/Agent/Hook) |

---

## Процессы и правила

| Файл | Что внутри |
|------|-----------|
| `work-model.md` | Модель работы в направлениях svaib: структура, движение задачи, Session Handoff, контракт `/close-session` |
| `subagent-rules.md` | Правила работы с субагентами: permissions, чанкинг, контекст |
| `autonomous-mode.md` | Переключение permissions для автономной ночной работы |

---

## Диагностика и история

| Файл | Что внутри |
|------|-----------|
| `.claude/rescue-log.yml` | История всех диагностированных сбоев — паттерны, root cause, что починили. Читай перед проектированием чтобы не повторять |
| `03_progress.md` | Хроника завершённых задач направления |
| `_inbox/lab-runtime-conclusions.md` | Выводы диагностики runtime (S5-S6): design constraints, инсайты |
| `_inbox/` | Материалы на разбор, research |
| `inbox-last30days-patterns.md` | Паттерны из анализа `_inbox` |
