---
title: "Lab — обзор направления"
updated: 2026-04-20
version: 1
scope: lab
priority: high
type: reference
---

# Lab — обзор направления

## Кратко

Lab — мастерская AI-помощников **для внутренней работы svaib**: скиллы, команды, агенты, хуки в `.claude/`. Здесь накапливается знание *как строить* (принципы, todo-файлы по типам, tooling-registry), проектируются новые помощники и чинятся существующие. Результат — работающий инструментарий Виктора в Claude Code. Не путать с `framework/skills/` — там **продуктовые** скиллы для клиентов Second AI Brain.

**Работа с файлом:** reference — обновлять при смене фокуса лаборатории или стадии. Не обновлять при ежедневной работе (текущие задачи → `02_active.md`, сделанное → `03_progress.md`).

## Связанные файлы

- [02_active.md](02_active.md) — что в работе сейчас, Session Handoff, блокеры
- [02_backlog.md](02_backlog.md) — задачи направления на будущее
- [03_progress.md](03_progress.md) — хроника по направлению
- [README.md](README.md) — навигация: где что искать при проектировании помощника
- [tooling-registry.md](tooling-registry.md) — реестр всего инструментария svaib
- [principles.md](principles.md) — принципы проектирования
- [../framework/01_overview.md](../framework/01_overview.md) — продуктовое направление (не путать)

---

## Миссия

Lab производит **внутренний инструментарий** svaib в Claude Code. Два слоя:

1. **Знание как строить** — `principles.md`, `tooling.md`, todo-файлы по типам (`todo-skill.md`, `todo-command.md`, `todo-agent.md`, `todo-hook.md`), правила (`subagent-rules.md`, `work-model.md`, `autonomous-mode.md`).
2. **Реализация** — помощники в `.claude/skills/`, `.claude/commands/`, `.claude/agents/`, `.claude/hooks/`. Lab-файлы — методология, `.claude/` — продукт методологии.

**Входит в scope:** проектирование и сопровождение внутренних помощников, процессы работы с ними (sessions, inbox, autonomous), правила субагентов, tooling-registry.
**НЕ входит:** продуктовые скиллы для клиентов (→ `framework/skills/`), код сайта (→ `dev/`), стратегия (→ `meta/`), клиентская работа (→ `clients/`).

---

## Рамка

Зрелое направление относительно остальных. Набор todo-файлов (skill/command/agent/hook) обкатан, principles зафиксированы, есть tooling-registry, процесс Architect/Engineer прописан в `svaib-lab`. На декаду — поддержка инструментария под основную работу (framework, clients, dev), не продвижение собственных инициатив.

**Стадия:** рабочая. `.claude/` наполнен, скиллы и команды используются ежедневно.

---

## Цель декады (недели 18→30)

Лаборатория играет **сервисную роль** — закрывает узкие места в инструментарии других направлений по мере появления. Собственных стратегических задач на декаде нет.

Текущие приоритеты по бэклогу (см. [02_backlog.md](02_backlog.md)):
- Агент обновления контекста (reweave+verify) — поддержка framework/memory/
- Перевод todo-файлов в Skills — повышение надёжности проектирования помощников
- Workflow клиентского досье — 3 бага для clients/

Детали целей svaib в целом → [../meta/management/02_goal.md](../meta/management/02_goal.md).

---

## Части лаборатории

| Часть | Что производит | Где |
|-------|----------------|-----|
| **Принципы** | Design-правила, фильтры решений | `principles.md` |
| **Tooling** | Выбор типа помощника, реестр существующих | `tooling.md`, `tooling-registry.md` |
| **Todo по типам** | Пошаговые инструкции проектирования | `todo-skill.md`, `todo-command.md`, `todo-agent.md`, `todo-hook.md` |
| **Процессы** | Модель работы, субагенты, автономный режим | `work-model.md`, `subagent-rules.md`, `autonomous-mode.md` |
| **Диагностика** | Rescue-log, паттерны сбоев | `.claude/rescue-log.yml`, `inbox-last30days-patterns.md` |
| **Реализация** | Работающие помощники | `.claude/skills/`, `.claude/commands/`, `.claude/agents/`, `.claude/hooks/` |

**База знаний:** `knowledge/skills/`, `knowledge/agents/`, `knowledge/coding/claude-code.md` — справочник механик Claude Code и чужих решений.

---

## Модель работы

Виктор вызывает `/svaib-lab` → координатор определяет маршрут (Architect для нового помощника / Engineer для правки существующего) → работа по соответствующему todo-файлу → валидация → закрытие через `/close-session`.

Детали — в [.claude/commands/svaib-lab.md](../.claude/commands/svaib-lab.md).
