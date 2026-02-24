# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**svaib** — Second AI Brain: персональная AI-инфраструктура для руководителя (база знаний + навыки + агенты). Консалтинг + подписка на методологический "плагин".

**Team:** Виктор Соломоник (vision, product, strategy, development) — solo founder

**User:** Виктор (обращайся по имени всегда)

## Repository Structure

> **Миграция в процессе** (см. `_migration.md`). Ниже — актуальная верхнеуровневая структура.

| Папка | Назначение |
|-------|-----------|
| `framework/` | Продукт Second AI Brain: онтология, методология, scaffold, plugin |
| `knowledge/` | Внешние знания об AI (open source, 8 категорий) |
| `dev/` | Сайт svaib.com (`dev/src/` → Vercel) + dev_context/ |
| `meta/` | Проект svaib: management/, marketing/, product/, _old/ (разбираем), z_archive/ |
| `clients/` | Клиенты (в .gitignore): _playbook/, {name}/ |
| `.claude/` | Config: agents/, commands/, prompts/, mechanics |
| `_inbox/` | Входящие на разбор (в .gitignore) |

## Current Application Architecture

**Tech Stack:** Next.js 16.0.1 with App Router, React 19.2.0, Tailwind CSS
**Deployment:** Vercel auto-deploy from `dev/src/` on push to main
**Live URL:** [https://svaib.com](https://svaib.com)
**Design:** Teal `#00B4A6` + Pink `#FF4D8D`, Sora/Inter, подробности в `dev/dev_context/design_system.md`

Лендинг + Vote Module (изолированный лабораторный инструмент). Детали компонентов и архитектуры — в `dev/src/` и `dev/dev_context/`.

## Development Workflow

### Making Changes

1. Edit files in `dev/src/` (components, data, styles)
2. Test locally: `cd dev/src && npm run dev` (http://localhost:3000)
3. **ВАЖНО:** Перед деплоем ВСЕГДА показывай изменения пользователю и проси подтверждение
4. После подтверждения: `git add . && git commit -m "description"`
5. Push to GitHub: `git push` (только после подтверждения!)
6. Vercel auto-deploys to [https://svaib.com](https://svaib.com)

### Testing Locally

```bash
cd dev/src
npm install      # First time only
npm run dev      # Start Next.js dev server
# Open http://localhost:3000
```

**Important:**

* Hot reload enabled, changes visible immediately
* Check both desktop and mobile views (responsive design)
* Test interactive features (block clicks, modal, hover effects)

## Slash Commands

* `/svaib-sprint` — Sprint mode: движение по MVP спринту, фокус на product_sprint.md и текущем статусе
* `/svaib-dev` — Development mode (dev/ folder): CTO role for architecture discussion or Developer role for coding tasks
* `/svaib-context` — Work with project context (meta/ folder): format files, update structure, check collisions
* `/svaib-knowledge` — Knowledge base (knowledge/ folder): add, search, review external AI knowledge
* `/svaib-clients` — Client work (clients/ folder): methodology, client prep, meeting notes, proposals
* `/svaib-framework` — Framework expert (framework/ folder): развитие онтологии, методологии, scaffold, plugin Second AI Brain

## Subagents

**context-editor** (`.claude/agents/context-editor.md`)

* Форматирование файлов контекста (meta/, dev/, pub/)
* Работает строго по чеклисту: YAML-заголовок, "Кратко", связанные файлы, README

**⚠️ ОБЯЗАТЕЛЬНО:** При создании/обновлении файлов контекста и перед git commit (если были правки в контекст) → ОБЯЗАТЕЛЬНО вызывай субагента `context-editor`.
Ты — партнёр и координатор, субагент — исполнитель по чеклисту.

## Important Rules

1. **Never break production:** `dev/src/` is live on Vercel, test changes carefully
2. **ALWAYS confirm before deploy:** After making changes, show them to user and ask for confirmation before `git commit` and `git push`. Never deploy without explicit approval.
3. **Critical files — confirm before editing:**
   * **НЕ править без согласования:** architecture.md, product\_roadmap.md, product\_vision.md
   * **Можно обновлять по факту:** infrastructure.md (текущее состояние), product\_sprint.md (чеклисты)
   * **Правило:** Перед правкой критичного файла — показать изменения и получить ОК
4. **Design system compliance:** Use colors/spacing from design-cheatsheet.md
5. **Context separation:**
   * meta/ — Проект svaib: management/ (цели, план, прогресс), marketing/ (каналы, бренд), product/ (продуктовая стратегия)
   * dev/ — Сайт и разработка (HOW to build)
   * framework/ — Продукт Second AI Brain: онтология, методология, scaffold, plugin
   * knowledge/ — Внешние знания об AI (не привязаны к svaib)
   * clients/ — Клиенты: _playbook/, профили, встречи
6. **Open source:** All code will be public on GitHub
7. **Weekly "Камни недели":** Focus on concrete weekly results
8. **Next.js best practices:**
   * Use 'use client' for interactive components
   * Keep components small and focused
   * Test both desktop and mobile (responsive required)
   * Old HTML/JS/CSS version preserved in `dev/src/archive/`
9. **Architecture first:** Перед предложением технических изменений — СНАЧАЛА проверь `architecture.md`. Не предлагай "временные решения" или "упрощения", которые противоречат целевой архитектуре. Если что-то запланировано на будущую фазу — так и скажи, не изобретай костыли.
10. **Сначала план — потом исполнение:**
    * Когда Виктор даёт задачу на реализацию — НЕ прыгай сразу в код/workflow
    * **Шаг 1:** Уточни цель сессии (что конкретно делаем?)
    * **Шаг 2:** Если новый API/сервис — изучи документацию (см. Documentation Policy в `.claude/claude_code_mechanics.md`)
    * **Шаг 3:** Составь план из 3-5 шагов, покажи Виктору
    * **Шаг 4:** Получи одобрение плана
    * **Шаг 5:** Исполняй по шагам, один шаг = один тест
    * После одобрения — бери ответственность. Не "можешь начинать", а "начинаю делать".
11. **GUI-задачи → используй `claude --chrome -p`:**
    * Любая настройка в браузере (n8n Dashboard, Google Cloud Console, Supabase Dashboard, Telegram Web, другие веб-интерфейсы) — вызывай через `claude --chrome -p "задача"`
    * **НЕ пиши пошаговые инструкции для Виктора** — он не исполнитель GUI-задач
    * Виктор только вставляет секреты (пароли, токены из KeePass) — всё остальное делает Chrome extension
    * Выполняется через Bash tool, Chrome extension управляет браузером
12. **Узнал новое — СРАЗУ запиши:**
    * Техническое ограничение (MCP, API, workflow) → `.claude/claude_code_mechanics.md`
    * Состояние ресурса (workflow ID, credential, URL) → `dev/dev_context/infrastructure.md`
    * **НЕ оставляй знания в голове** — следующий чат их не увидит
    * Это правило важнее любой текущей задачи
13. **Точная фиксация данных — без обобщений:**
    * Когда Виктор отправляет списки (события, ID, конфиги, URL) — записывать ДОСЛОВНО
    * **НЕ обобщать** типа "все bot.* события" — записать каждый элемент
    * Даже если список длинный — всё равно записать полностью
    * **Причина:** При compact/summarize обобщения теряют детали. Виктор вынужден искать в чате что уже отправлял — это недопустимо. Точные данные в файлах = источник истины для всех будущих сессий.
14. **AI-модели — не брать из памяти:**
    * Модели в памяти устарели. НЕ подставлять GPT-4o, GPT-4o-mini и т.п.
    * **Спросить Виктора** какую модель использовать, или **сделать веб-поиск** актуальных моделей.
15. **Файлы контекста — пиши для AI, не для человека:**
    * Файлы в meta/, dev/, knowledge/ читает в первую очередь AI. Пиши максимально сжато: факт + источник, без обоснований и объяснений.
    * Если информация нужна человеку — уточни у Виктора формат.
16. **Разбор ошибок — только инженерный анализ:**
    * **Где сбой:** шаг, файл, инструкция
    * **Почему:** что отсутствует/неточно в скилле, хуке или процессе
    * **Фикс:** что изменить и где
    * Если причину не удаётся привязать к конкретному месту — предложить гипотезы и обсудить с Виктором
    * **НЕ использовать:** "не вдумался", "поторопился", "поверхностно подошёл" — антропоморфные объяснения не анализ

## Key Principles

* **Практичность:** Focus on working solutions, not tech for tech's sake
* **Честность:** Document failures alongside successes
* **Легкость:** Approach with humor, self-irony over perfectionism
* **Weekly releases:** Ship every week, gather feedback

## Getting More Context

> Пути обновляются по ходу миграции (см. `_migration.md`)

| When you need | Read this file |
|---------------|---------------|
| **Миграция** (состояние, решения) | `_migration.md` |
| Vision, goals, plan, progress | `meta/management/` (scaffold-структура) |
| Marketing, brand, каналы | `meta/marketing/` |
| Site architecture (svaib.com) | `dev/dev_context/architecture.md` |
| Database schema | `dev/dev_context/data_model.md` |
| Infrastructure, APIs | `dev/dev_context/infrastructure.md` |
| Design system | `dev/dev_context/design_system.md` |
| MCP, subagents, tools | `.claude/claude_code_mechanics.md` |
| AI knowledge (tools, methods) | `knowledge/README.md` |
| Framework (ontology, methodology) | `framework/README.md` |
| Second AI Brain architecture | `framework/architecture.md` |
| Product model (for clients) | `meta/product/model.md` |
| Client work | `clients/_playbook/README.md`, `clients/{name}/` |
| **Old context** (being migrated) | `meta/_old/meta_context/` |

***

> **CLAUDE.md будет полностью переработан в конце миграции** (см. `_migration.md`, Фаза 2). Сейчас — рабочий минимум.