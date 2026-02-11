---
title: "Agent Teams — координация команды AI-агентов в Claude Code"
source: "https://code.claude.com/docs/en/agent-teams"
source_type: docs
status: processed
added: 2026-02-01
updated: 2026-02-07
review_by: 2026-05-07
tags: [claude-code, agent-teams, multi-agent, orchestration]
publish: false
version: 2
---

# Agent Teams — координация команды AI-агентов в Claude Code

## Кратко

Agent Teams — экспериментальная фича Claude Code (официальные доки с февраля 2026) для запуска команды AI-агентов, работающих параллельно. Leader координирует, teammates работают независимо в своих контекстных окнах, общаются напрямую через inbox-файлы, координируются через общий task list с зависимостями. Включение: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` в settings.json.

**Статус:** experimental, официально документирован, но с известными ограничениями (нет resume, нет вложенных команд). Паттерны оркестрации — стабильные.

**История:** Обнаружено сообществом в январе 2026 как "Swarm Mode" через reverse-engineering бинарника Claude Code v2.1.19 (claude-sneakpeek). В феврале 2026 Anthropic выпустили официальную документацию под названием Agent Teams.

---

## Task tool (субагенты) vs Agent Teams

| | Task tool (субагенты) | Agent Teams |
|---|---|---|
| **Контекст** | Своё окно, результат возвращается вызывающему | Своё окно, полностью независимы |
| **Связь** | Только через координатора | Напрямую через inbox (JSON-файлы) |
| **Жизненный цикл** | Короткоживущий: задача → результат → смерть | Персистентный: живёт пока не попросят уйти |
| **Задачи** | Одна задача на агента | Общий task list, агенты сами берут задачи |
| **Зависимости** | Нет | blockedBy — авто-разблокировка при завершении |
| **Видимость** | Скрытый в фоне | Видимый в tmux/iTerm панелях или in-process |
| **Стоимость** | Ниже: результаты суммируются в основной контекст | Выше: каждый teammate — отдельный экземпляр Claude |

Task tool = подрядчик на задачу. Agent Teams = управление командой.

---

## Включение и запуск

```json
// settings.json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Запрос на естественном языке: опиши задачу и структуру команды. Claude создаёт команду, спавнит teammates, координирует.

---

## Режимы отображения (teammateMode)

| Backend | Видимость | Требования | Навигация |
|---------|-----------|------------|-----------|
| **in-process** (default) | Внутри основного терминала | Никаких | Shift+Up/Down |
| **tmux** | Split panes | tmux | Клик в панель |
| **iterm2** | Split panes | iTerm2 + it2 CLI | Клик в панель |

Настройка: `"teammateMode": "in-process"` в settings.json или `claude --teammate-mode in-process`.

---

## Ключевые механики

### Delegation mode (Shift+Tab)
Ограничивает лидера инструментами координации: спавн, сообщения, завершение, управление задачами. Лидер не кодит сам — только оркестрирует. Включать когда нужна чистая координация.

### Plan Approval
Teammate работает в plan mode (только чтение) → отправляет план лидеру → лидер одобряет или отклоняет с фидбеком → после одобрения teammate начинает реализацию.

### Прямое общение с teammates
- **In-process:** Shift+Up/Down для выбора, Enter для просмотра сессии, Escape для прерывания
- **Split-pane:** клик в панель

### Задачи и зависимости
Общий task list: pending → in_progress → completed. Зависимости через blockedBy — авто-разблокировка. Блокировка файлов предотвращает гонки при взятии задач.

---

## Паттерны оркестрации

### 1. Parallel Specialists
Несколько агентов проверяют одно и то же с разных точек зрения (security + performance + architecture ревьюеры). Лидер синтезирует findings.

### 2. Pipeline (Sequential Dependencies)
Цепочка: spec → code → test → review. Каждый этап блокирован предыдущим через blockedBy.

### 3. Swarm (Self-Organizing)
Workers опрашивают task list, берут свободные задачи, выполняют, повторяют. Подходит для рефакторинга большой кодовой базы.

### 4. Research + Implementation
Синхронное исследование → спавн агентов-кодеров на основе результатов.

### 5. Конкурирующие гипотезы
Несколько teammates исследуют разные теории и оспаривают выводы друг друга. Защита от якорения на первой гипотезе.

---

## Архитектура

```
~/.claude/teams/{team-name}/
├── config.json                    — настройки команды (members[])
└── inboxes/
    ├── team-lead.json             — входящие лидера
    ├── builder-1.json             — входящие строителя
    └── qa.json                    — входящие тестера

~/.claude/tasks/{team-name}/       — task list
```

Сообщения: JSON с `from`, `text`, `timestamp`, `read`. `message` (одному) дешевле `broadcast` (всем).

---

## Ограничения (на февраль 2026)

- **Нет resume:** `/resume` и `/rewind` не восстанавливают teammates
- **Статус задач отстаёт:** teammates иногда не отмечают завершение → ручная проверка
- **Одна команда на сессию**, нет вложенных команд
- **Лидер фиксирован** на всю жизнь команды
- **Разрешения от лидера:** все teammates стартуют с его режимом
- **Split panes не работают** в VS Code Terminal, Windows Terminal, Ghostty
- **Токены:** N teammates = N контекстных окон. Зацикленные пары могут сжечь значительный бюджет

---

## Когда использовать, а когда нет

**Подходит:**
- Параллельное исследование и code review
- Новые модули/фичи с независимыми частями
- Отладка с конкурирующими гипотезами
- Cross-layer работа (frontend + backend + tests)

**Не подходит:**
- Последовательные задачи
- Редактирование одного файла
- Рутинные задачи (один сеанс дешевле)
- Задачи с множеством зависимостей

---

## Связанные файлы

- [claude-code.md](claude-code.md) — общий справочник Claude Code (Agent Teams в хронологии)
- [../agents/subagents.md](../agents/subagents.md) — субагенты как альтернатива (Task tool)
- [../agents/!agents.md](../agents/!agents.md) — паттерны multi-agent оркестрации

---

## Ссылки

- Официальные доки: https://code.claude.com/docs/en/agent-teams
- claude-sneakpeek (исторический, неофициальный): https://github.com/mikekelly/claude-sneakpeek
- Swarm Orchestration Skill (гайд): https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea
- Case Study: https://github.com/BayramAnnakov/edu-ai-product-engineer-s3/tree/main/case_studies/claudesp-swarm-deep-dive
