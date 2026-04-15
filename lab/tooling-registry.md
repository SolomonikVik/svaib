---
title: "Реестр инструментария svaib"
updated: 2026-04-15
---

# Tooling Registry

Сводный реестр всех помощников проекта. Источник правды о том, что у нас есть и в каком состоянии. Обновляется при создании/удалении/изменении помощника.

Исполняемые файлы живут в `.claude/`. Этот реестр живёт в `lab/` — описывает, не исполняет.

---

## Команды (6)

Режимы работы. Запуск: `/svaib-*`. Файлы: `.claude/commands/`.

| Команда | Что делает |
|---------|-----------|
| `/svaib-lab` | Лаборатория — создание и правка помощников |
| `/svaib-framework` | Работа с фреймворком Second AI Brain |
| `/svaib-clients` | Работа с клиентами |
| `/svaib-knowledge` | Работа с базой знаний |
| `/svaib-dev` | Разработка проекта (сайт и др.) |
| `/svaib-sprint` | CTO-режим для MVP спринта |

---

## Скиллы (10)

Специализированные навыки. Вызываются автоматически по триггеру или через `/skill-name`. Живут на двух уровнях: проектные (в репо) и персональные (в `~/.claude/`).

### Локальные (проектные) — `svaib/.claude/skills/`

Живут в репо, едут вместе с проектом, доступны только внутри svaib.

| Скилл | Что делает | Триггер |
|-------|-----------|---------|
| `close-session` | Закрытие сессии: лог, проверка инсайтов, вопросы | "закрываем", "close session" |
| `knowledge-research` | Исследование перед добавлением в knowledge/ | Ссылка, тема, "добавь в knowledge" |
| `presentation` | Создание PPTX в svaib-стиле | "сделай презентацию", "слайды" |
| `reader-telegram` | Чтение поста из Telegram-канала | URL t.me |
| `reader-twitter` | Чтение поста из X/Twitter | URL x.com / twitter.com |
| `reader-youtube` | Транскрипт YouTube-видео | URL youtube.com / youtu.be |
| `reader-jina` | Чтение веб-страниц (fallback для JS-сайтов) | URL когда WebFetch не справился |
| `sign-pdf` | Подпись и печать на PDF | "подпиши", "поставь печать" |
| `weekly-progress` | Генерация еженедельной хроники | "итоги недели", "weekly progress" |

### Глобальные (персональные) — `~/.claude/skills/`

Живут вне репо, в домашней папке. Доступны во всех проектах Виктора, не только svaib.

| Скилл | Что делает | Триггер |
|-------|-----------|---------|
| `marp-slides` | Markdown-first презентации в svaib-стиле (SVAIB theme по умолчанию + Dark/Light как альтернативы) | "marp", "slides", "presentation", "deck" |

**Про `marp-slides`:**
- Основан на [robonuggets/marp-slides](https://github.com/robonuggets/marp-slides) v2.0
- Кастомизирован под svaib brand: SVAIB Theme добавлена как третий стартер рядом с Dark/Light, плюс эталонный пример `examples/marp_svaib-sample.md`
- Brand-источник: [meta/marketing/brand-design-presentation.md](../meta/marketing/brand-design-presentation.md) — все цвета/шрифты/маркеры в SKILL.md повторяют его
- **Мы форк** — когда автор выпускает новую версию, смотрим diff и мержим вручную
- **Prerequisites:** VS Code extension `marp-team.marp-vscode` + два settings (глобальные, user-level) — `markdown.marp.html: "all"`, `markdown.marp.allowLocalFiles: true`
- **Когда использовать:** быстрые рабочие decks, markdown-first workflow, git-версионирование слайдов, AI редактирует напрямую. Альтернатива — скилл `presentation` (PPTX) для брендированных PPTX-файлов

---

## Хуки (5)

Автоматические проверки. Работают без вызова. Файлы: `.claude/hooks/`, конфигурация в `.claude/settings.json`.

| Хук | Событие | Что делает |
|-----|---------|-----------|
| `remind_subagent_rules` | PreToolUse (Agent) | Инъекция правил субагентов перед запуском |
| `inject_session_context` | SubagentStart | Инъекция контекста сессии в субагентов |
| `check_deferred_actions` | Stop | Блокирует "в следующий раз сделаю X" — делай сейчас |
| `enforce_rule10` | Stop | Текст отдельно от действий (правило 4 CLAUDE.md) |
| `banned_phrases` | Stop | Блокирует запрещённые фразы |

---

## Инструменты (1)

Скрипты в `lab/tools/`. Запускаются вручную или агентом по инструкции.

| Инструмент | Что делает | Запуск |
|-----------|-----------|--------|
| `day-plan-viewer.py` | Веб-просмотр плана дня с кликабельными чекбоксами | `python3 lab/tools/day-plan-viewer.py` |

---

## Прочее

| Файл | Что это |
|------|--------|
| `.claude/settings.json` | Permissions, конфигурация хуков |
| `.claude/strategic-mode.md` | Стратегический контекст для Architect-маршрута |
| `.claude/rescue-log.yml` | История диагностированных сбоев |
| `.claude/agents/rescue.md` | Агент диагностики сбоев |
