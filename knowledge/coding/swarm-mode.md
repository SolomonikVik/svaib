---
title: "Swarm Mode — multi-agent оркестрация в Claude Code (TeammateTool)"
source: "https://github.com/mikekelly/claude-sneakpeek"
source_type: repo
status: raw
added: 2026-02-01
review_by: 2026-05-01
tags: [claude-code, swarm, multi-agent, orchestration, teammatetool]
publish: false
version: 1
---

# Swarm Mode — Multi-Agent оркестрация в Claude Code

## Кратко

Swarm Mode — скрытая (feature-flagged) функция Claude Code для запуска команды AI-агентов, работающих параллельно. Основана на TeammateTool API: координатор (team lead) не пишет код сам, а спавнит агентов с ролями, которые общаются через inbox-файлы, работают с общим task board и координируются через зависимости (blockedBy). Обнаружена сообществом в январе 2026 в бинарнике Claude Code v2.1.19. Неофициально доступна через claude-sneakpeek. Официальный релиз ожидается.

**Статус:** экспериментальная, за feature flags. API может измениться при официальном релизе. Паттерны оркестрации — стабильные.

---

## Task tool vs TeammateTool

Это разные уровни multi-agent работы:

| | Task tool (доступен сейчас) | TeammateTool (swarm mode) |
|---|---|---|
| **Связь между агентами** | Только через координатора | Напрямую через inbox (JSON-файлы) |
| **Жизненный цикл** | Короткоживущий: задача → результат → смерть | Персистентный: живёт пока не попросят уйти |
| **Задачи** | Одна задача на агента | Общий task board, агенты сами берут задачи |
| **Зависимости** | Нет | blockedBy — задачи авто-разблокируются при завершении зависимостей |
| **Видимость** | Скрытый в фоне | Видимый в tmux/iTerm панелях |
| **Координация** | Координатор собирает результаты вручную | Task board + inbox + plan approval workflow |

Task tool = вызов подрядчика на конкретную задачу. TeammateTool = управление командой.

---

## Паттерны оркестрации

### 1. Parallel Specialists
Несколько агентов проверяют одно и то же параллельно с разных точек зрения. Пример: security-ревьюер + performance-ревьюер + architecture-ревьюер анализируют PR одновременно. Координатор собирает findings.

### 2. Pipeline (Sequential Dependencies)
Цепочка зависимых задач: spec → code → test → review. Каждый этап блокирован предыдущим через blockedBy. Задачи авто-разблокируются при завершении.

### 3. Swarm (Self-Organizing)
Воркеры непрерывно опрашивают task board, берут свободные задачи, выполняют, повторяют. Естественная балансировка нагрузки. Подходит для рефакторинга большой кодовой базы.

### 4. Research + Implementation
Сначала синхронное исследование (возвращает результат), потом спавн агентов-кодеров на основе результатов исследования.

### 5. Plan Approval
Архитектор работает в plan mode. Код пишется только после одобрения плана координатором. Даёт контроль качества на уровне архитектуры.

---

## Практический workflow (из реальных кейсов)

Паттерн, который используют практики:

1. **Требования:** координатор + субагенты (архитектор, продуктолог, рисёрчер) прорабатывают требования. Координатор передаёт вопросы к человеку, возвращает ответы агентам
2. **Нарезка задач:** координатор декомпозирует требования, создаёт task board с зависимостями
3. **Кодинг:** 8-12 агентов-кодеров работают параллельно, каждый в своём git worktree (нет конфликтов). Мерж — только при прохождении тестов
4. **Ревью:** те же ревьюеры-требовальщики (продуктолог, архитектор) принимают работу
5. **Итерация:** ревью → доработки → повторное ревью

Кейс AgentControlTower: 10 агентов, 13 минут, 22 Swift файла + 6 скриптов = macOS Menu Bar приложение.

---

## Коммуникация агентов

Агенты общаются через JSON-файлы:

```
~/.claude/teams/{team-name}/
├── config.json                    — настройки команды
└── inboxes/
    ├── team-lead.json             — входящие координатора
    ├── builder-1.json             — входящие строителя
    └── qa.json                    — входящие тестера
```

Сообщение — JSON с полями `from`, `text`, `timestamp`, `read`. Структурированные сообщения (shutdown_request, task_completed, plan_approval_request) передаются как JSON внутри text.

Ключевое: `write` (личное сообщение конкретному агенту) дешевле `broadcast` (всем).

---

## Spawn backends

| Backend | Видимость | Персистентность | Скорость |
|---------|-----------|----------------|----------|
| **in-process** | Скрытый | Умирает с координатором | Быстрый |
| **tmux** | Видимые панели | Переживает выход | Средний |
| **iterm2** | Split panes | Умирает с окном | Средний |

Авто-выбор: tmux внутри tmux → tmux, iTerm2 с it2 CLI → iterm2, иначе in-process. Принудительно: `CLAUDE_CODE_SPAWN_BACKEND=tmux`.

---

## Риски и ограничения

- **Токены:** 10 агентов = 10 контекстных окон. Задача за $0.20 в одиночном режиме → $1.50+ в swarm. Зацикленные Builder-QA могут сжечь $50 за минуты
- **Надёжность:** агенты принимают неверные решения (пример: переписывание библиотеки вместо npm install). Hallucination cascades — если архитектор придумал несуществующую библиотеку, builder потратит время на установку
- **Code review невозможен:** при 10 агентах объём кода выходит за возможности человеческой проверки
- **Не для продакшена:** feature flags выключены не просто так, Anthropic рекомендует ждать официальный релиз

---

## Как попробовать (неофициально)

```bash
npx @realmikekelly/claude-sneakpeek quick --name claudesp
# добавить ~/.local/bin в PATH
claudesp  # запуск с разблокированными фичами
```

Создаёт изолированную установку, не трогает основной Claude Code. Обновление: `npx @realmikekelly/claude-sneakpeek update claudesp`. Удаление: `npx @realmikekelly/claude-sneakpeek remove claudesp`.

---

## Альтернативы

- **claude-flow** (github.com/ruvnet/claude-flow) — фреймворк оркестрации поверх Claude Code через MCP. Hierarchical и mesh паттерны
- **Oh My Claude Code (OMC)** — 32 агента + 40 скиллов, multi-agent orchestration
- **Task tool (встроенный)** — базовая параллельная работа субагентов, без inbox и task board, но работает уже сейчас без хаков

---

## Ссылки

- claude-sneakpeek: https://github.com/mikekelly/claude-sneakpeek
- Swarm Orchestration Skill (полный гайд): https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea
- Deep Dive Case Study: https://github.com/BayramAnnakov/edu-ai-product-engineer-s3/tree/main/case_studies/claudesp-swarm-deep-dive
- Technical analysis: https://paddo.dev/blog/claude-code-hidden-swarm/
- HN Discussion: https://news.ycombinator.com/item?id=46743908
