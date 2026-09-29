---
title: "AI-оболочки — среды для работы с AI (каталог)"
source_type: docs
status: raw
added: 2026-02-11
updated: 2026-09-24
review_by: 2026-09-14
tags: [tools, ai-workspace, shells, catalog]
publish: false
---

# AI-оболочки — где работать с AI

## Кратко

Каталог десктопных и терминальных сред для работы с AI. Не только для разработчиков — маркетолог, руководитель, SEO-специалист могут использовать эти инструменты. Часть онтологии продукта SVAIB: клиент выбирает оболочку, мы наполняем её содержимым (Skills, Agents, контекст). Инструменты быстро обновляются — здесь фиксируем суть и ссылки, не детали фич.

---

## Каталог

### Claude Code

**Что:** CLI-инструмент Anthropic для работы с AI в терминале и IDE.
**Платформы:** macOS, Linux, Windows (WSL). Интеграция: VS Code, JetBrains.
**Модели:** Claude (Opus, Sonnet, Haiku).
**Ключевое:** Система плагинов (Skills + Commands + Agents + Hooks + MCP). Субагенты, Agent Teams. Наш основной рабочий инструмент.
**Ссылка:** https://code.claude.com
**Подробнее:** [../coding/claude-code.md](../coding/claude-code.md)

---

### Cowork

**Что:** GUI-оболочка Anthropic внутри Claude Desktop. Агентная платформа для knowledge workers (не разработчиков).
**Платформы:** macOS (research preview, январь 2026).
**Модели:** Claude.
**Ключевое:** Те же плагины что Claude Code, но через GUI. Sandboxed VM. Целевая аудитория: sales, legal, finance, marketing. Маркетплейс плагинов.
**Ссылка:** https://claude.com/blog/cowork-research-preview
**Подробнее:** [cowork.md](cowork.md)

---

### Claude Project

**Что:** Веб-интерфейс Claude (claude.ai) с подключением данных — Project Knowledge, системные инструкции, Google Workspace коннекторы. Основной runtime для клиентов SVAIB (руководители, не разработчики).
**Платформы:** Web, iOS, Android.
**Модели:** Claude (Opus, Sonnet, Haiku).
**Ключевое:** Два режима контекста: full (<200K — всё в памяти) и RAG (>200K). Google Workspace коннекторы: Drive Search + Drive Fetch дают доступ к Google Docs клиента прямо из чата. Scope через системную инструкцию, не через API.
**Ссылка:** https://claude.ai
**Docs:** https://support.claude.com/ru/articles/10166901-используйте-соединители-google-workspace
**Подробнее:** [claude-project.md](claude-project.md)

---

### OpenCode

**Что:** Open-source AI-агент для терминала с десктопным приложением. Позиционируется как открытая альтернатива Claude Code.
**Платформы:** macOS, Windows, Linux. CLI + Desktop app + расширение VS Code/Cursor.
**Модели:** 75+ моделей — Claude, OpenAI, Gemini, локальные.
**Ключевое:** Два встроенных агента (build + plan). LSP-интеграция. Мультипровайдерность — работает с любой моделью. Open-source.
**Ссылка:** https://opencode.ai
**GitHub:** https://github.com/opencode-ai/opencode

---

### Codex (OpenAI)

**Что:** Десктопное приложение OpenAI для работы с AI-агентами. Параллельные агенты, автоматизации, worktrees.
**Платформы:** macOS (февраль 2026). CLI — кроссплатформенный.
**Модели:** OpenAI (актуальные модели — см. docs).
**Ключевое:** Multi-agent: несколько агентов работают параллельно на одном репо через worktrees. Automations — агенты работают по расписанию в фоне. Skills (Figma, Linear, deploy, PDF/docx). Результаты — в review queue.
**Ссылка:** https://openai.com/codex
**Docs:** https://developers.openai.com/codex/app/

---

### bb (get-bb)

**Что:** Открытая оболочка (MIT) поверх агентных движков: десктопный и веб-интерфейс, CLI и API. Движки сохраняют собственные механизмы работы, а bb объединяет их в одном рабочем месте. Код можно форкнуть и настроить.
**Движки и модели:** Claude Code, Codex, OpenCode и другие поддерживаемые агенты. bb использует их авторизацию; оплата зависит от выбранного движка — подписка провайдера или API. Через OpenCode можно подключить модели разных провайдеров, в том числе Gemini и DeepSeek, и локальные модели. bb не снимает ограничений провайдера и сам по себе не защищает его аккаунт от блокировки.
**Отличие:** Плагины меняют интерфейс и действия под конкретную работу: панели, виджеты, навигацию и инструменты агента. Это позволяет собрать рабочее место для задач вне разработки, сохранив возможности подключённого движка.

**Материалы:**
- [Сайт bb](https://getbb.app/) — назначение приложения, поддерживаемые агенты, подписки и возможность форкнуть код.
- [Исходники и README](https://github.com/get-bb/bb) — актуальные способы установки, подключения агентов и разработки плагинов.
- [Видео с разбором bb](https://www.youtube.com/watch?v=rQWGshpC1rc) — по транскрипту агент может изучить разделение оболочки и движка (18–22-я минуты), демонстрацию рабочего места для работы с клиентскими документами (25–32-я минуты), ограничения и доступ через браузер (33–44-я минуты), выбор другого движка (57–58-я минуты).
- [Пост Рефата о bb](https://t.me/nobilix/288) — почему расширяемый интерфейс отличает bb от других оркестраторов и какие рабочие элементы можно добавить плагинами.
- [Пост Рефата об Atlas](https://t.me/nobilix/306) — зачем он собрал карту возможностей плагинов и что в ней можно найти.
- [bb Plugin Atlas](https://nobilix.github.io/bb-plugin-atlas/ru/) — карта зон интерфейса, архитектура и модель доверия плагинов; справочник привязан к конкретной версии bb.

---

### ValeDesk

**Что:** Десктопное AI-приложение (Tauri + React), фокус на приватность и закрытый контур. Данные не покидают машину. Позиционируется как локальная альтернатива облачным AI-инструментам.
**Платформы:** macOS, Windows, Linux.
**Модели:** Любой OpenAI-совместимый API, OpenRouter, Z.AI, локальные (Ollama, vLLM, LM Studio).
**Ключевое:** Чтение PDF/DOCX (встроенное, без зависимостей). Выполнение кода (JS, Python, Bash/PowerShell). Веб-поиск (Tavily, Z.AI) и рендеринг страниц через Chromium. Маркетплейс скиллов. Sandbox-файловые операции. SQLite-сессии. Scheduled tasks с нативными уведомлениями.
**Лицензия:** Бесплатно для физлиц и компаний с выручкой до $1M. Коммерческая лицензия для крупных.
**GitHub:** https://github.com/vakovalskii/ValeDesk
**Сообщество:** https://t.me/neuraldeep

---

### VS Code

**Что:** IDE от Microsoft, с v1.109 (февраль 2026) — полноценная multi-agent платформа.
**Платформы:** macOS, Windows, Linux.
**Модели:** Claude, Codex, Copilot — все через подписку GitHub Copilot.
**Ключевое:** Unified Agent Sessions (local/background/cloud агенты в одной панели). Параллельные субагенты. Встроенный браузер. MCP Apps (интерактивный UI в чате). Agent Skills (стандарт Anthropic, GA). Самая большая экосистема расширений.
**Ссылка:** https://code.visualstudio.com
**Подробнее:** [../coding/vscode-agents.md](../coding/vscode-agents.md)

---

### claudesidian (не оболочка — стартер-кит)

**Что:** Готовый Obsidian-vault под Claude Code для personal knowledge management. Не отдельное приложение, а связка: оболочка (Claude Code) + наполнение (vault + скиллы). Запускаешь Claude Code прямо в директории заметок.
**Модели:** Claude.
**Ключевое:** PARA-структура vault; ~19 agent skills под KM-ритуалы (daily-review, weekly-synthesis, inbox-processor, thinking-partner); `init-bootstrap` — мастер настройки vault (аналог нашего scaffold). Связь не через API/MCP, а через файловую систему + agentic grep. Позиционирование: Claude как «мыслящий партнёр», не writing-ассистент.
**Зачем нам:** живой пример модели «оболочка + наполнение» — ровно подход SVAIB; их набор KM-скиллов и онбординг (`init-bootstrap`) стоит сверить с нашими ритуалами и scaffold.
**GitHub:** https://github.com/heyitsnoah/claudesidian
**Подробнее:** [obsidian.md](obsidian.md) — Obsidian как платформа: командная коллаборация (Relay/CRDT) и agent-writable через MCP

---

## Как выбирать

| Профиль пользователя | Рекомендация |
|----------------------|-------------|
| Разработчик, терминал | Claude Code, OpenCode |
| Разработчик, IDE | VS Code + расширения, Codex |
| Руководитель, маркетолог, не-разработчик | Claude Project, Cowork, bb (при настройке под задачу) |
| Нужна мультимодельность (разные провайдеры) | OpenCode, bb, ValeDesk |
| Нужны автоматизации по расписанию | Codex |
| Закрытый контур, данные не покидают машину | ValeDesk + локальные модели |

## Связь с продуктом SVAIB

Оболочка — это интерфейс клиента. SVAIB наполняет её содержимым:

```
КЛИЕНТ выбирает оболочку          SVAIB даёт содержимое
─────────────────────────          ─────────────────────
Claude Code / Cowork              Skills + Agents + Онтология
OpenCode / Codex / VS Code / bb   (подписка, см. product/01_overview.md)
ValeDesk (закрытый контур)
```

Подробнее о модели подписки "Плагин": [cowork.md](cowork.md), секция "Связь с продуктом SVAIB".

## Связанные файлы

- [cowork.md](cowork.md) — Cowork подробно: плагины, pricing, связь с продуктом
- [../coding/claude-code.md](../coding/claude-code.md) — Claude Code подробно: система расширения, плагины, маркетплейсы
