---
title: "lab/ — мета-знания лаборатории"
updated: 2026-03-17
---

# lab/

Знания о строительстве AI-помощников. Принципы, процессы, инсайты из экспериментов.

Загружается принудительно при вызове `/svaib-lab`. Служит навигатором — отсюда агент находит нужный файл, не читая всё подряд.

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

**Архитектура arscontexta** — reference-реализация skill graph подхода: progressive disclosure, session-orient, mode separation, hooks как enforcement. Изучено и задокументировано в `knowledge/skills/skill-graphs/` (README → architecture → patterns → skill anatomy → полный пример /architect). Наши design constraints для команд выведены из этой архитектуры.

---

## Процессы и правила

| Файл | Что внутри |
|------|-----------|
| `session-handoff.md` | Полный цикл: план → задача → worklog → сессии → close-session |
| `subagent-rules.md` | Правила работы с субагентами: permissions, чанкинг, контекст |
| `inbox-rules.md` | Правила работы с _inbox/ — единые для всего проекта |
| `autonomous-mode.md` | Переключение permissions для автономной ночной работы |

---

## Диагностика и история

| Файл | Что внутри |
|------|-----------|
| `.claude/rescue-log.yml` | История всех диагностированных сбоев — паттерны, root cause, что починили. Читай перед проектированием чтобы не повторять |
| `roadmap.md` | История версий лаборатории, backlog идей |
| `_inbox/lab-runtime-conclusions.md` | Выводы диагностики runtime (S5-S6): design constraints, инсайты |
| `_inbox/` | Материалы на разбор, research |
| `inbox-last30days-patterns.md` | Паттерны из анализа _inbox |
