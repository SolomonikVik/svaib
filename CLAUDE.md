# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**svaib** - AI-мастерская, создающая AI-решения для бизнеса. Миссия: переводчик между сложными AI-технологиями и практическими потребностями бизнеса.

**Current Stage:** MVP development, первые недели работы
**Team:** Виктор Соломоник (vision, product, strategy, development) — solo founder

**User:** Виктор (обращайся по имени всегда)

## Repository Structure

```
svaib/
├── .claude/       — Claude Code configuration
│   ├── agents/    — Subagents (context-editor, etc.)
│   └── claude_code_mechanics.md — MCP servers, subagents, skills reference
│
├── _inbox/        — Входящие на разбор (в .gitignore, но важно знать)
│   ├── README.md  — Правила работы с inbox
│   └── todo_*.md  — Идеи и задачи на проработку
│
├── meta/          — Project context, strategy, documentation
│   ├── meta_context/
│   │   ├── !chat_navigation.md — Navigation for Claude Chat/Projects
│   │   ├── !context_rules.md — Context management rules (this system)
│   │   ├── marketing.md — Positioning, messaging, sales strategy
│   │   ├── monetization.md — Monetization model (pricing, revenue streams)
│   │   ├── product_vision.md — Product description (AI meeting assistant)
│   │   ├── project_overview.md — OKR, strategy, team, MVP stage
│   │   ├── storage_system.md — Storage structure (Git + Google Drive)
│   │   └── weekly_progress.md — Weekly progress tracking ("stones of the week")
│   ├── prompts/   — Role-specific prompts (editor, strategist, HRD)
│   └── research/  — Market research and analysis
│
├── dev/           — Development codebase
│   ├── src/       — ⚠️ DEPLOYED TO VERCEL (current production)
│   │   ├── app/   — Next.js 16 App Router
│   │   │   ├── page.js — Main landing page
│   │   │   ├── layout.js — Root layout with fonts
│   │   │   ├── globals.css — Global styles and design tokens
│   │   │   └── vote/ — Vote Module (internal lab tool, isolated)
│   │   │       ├── page.jsx — Voting interface
│   │   │       ├── admin/ — Session/project/participant management
│   │   │       └── results/ — Voting results page
│   │   ├── api/vote/  — 5 API routes (sessions, participants, projects, cast, results)
│   │   ├── components/  — React components
│   │   │   ├── Header.jsx — Logo svaib (fixed top-right)
│   │   │   ├── Hero.jsx — Hero section with gradient CTA
│   │   │   ├── Architecture.jsx — Interactive architecture diagram (desktop) + card list (mobile)
│   │   │   ├── ArchBlock.jsx — Individual architecture block component
│   │   │   ├── ConnectionLines.jsx — SVG connections between blocks
│   │   │   ├── BlockModal.jsx — Modal with detailed block information
│   │   │   ├── CTA.jsx — Call-to-action section
│   │   │   └── Footer.jsx — Footer with contacts and links
│   │   ├── data/  — Data sources
│   │   │   └── architectureData.js — Architecture blocks and connections
│   │   ├── lib/  — Utilities
│   │   │   └── supabase.js — Supabase client
│   │   ├── archive/  — Old HTML/JS/CSS version (preserved)
│   │   ├── package.json — Next.js 16.0.1, React 19.2.0
│   │   └── next.config.js — Next.js configuration
│   ├── dev_context/
│   │   ├── architecture.md — Product architecture (7 components, connections, tech)
│   │   ├── data_model.md — Supabase data model (detailed table structure)
│   │   ├── data_dictionary.md — Entity reference (prompt roles, document types)
│   │   ├── design_system.md — Design system reference (#00B4A6 primary, #FF4D8D accent)
│   │   ├── guide_presentation.md — Presentation structure (slide-by-slide spec)
│   │   ├── infrastructure.md — Tech infrastructure (VPS, APIs, deployment)
│   │   └── product_roadmap.md — Product roadmap (stages, vision features)
│   └── prompts/   — Technical prompts (CTO, Dify copilot)
│
├── framework/     — Product core: Second AI Brain methodology & automation
│   ├── ontology/      — Entities, relationships, structure
│   ├── methodology/   — Principles, rituals, decision frames
│   ├── model.md       — Product model for client presentations
│   ├── scaffold/      — Ready-made template (management/, knowledge/, _inbox/, archive/)
│   └── plugin/        — Deployable package skeleton (skills, agents, hooks)
│
├── knowledge/     — External knowledge base (AI tools, methods, practices)
│
├── clients/       — Client projects and consulting methodology
│   ├── _playbook/ — Sales process (offers, onboarding)
│   └── {name}/    — Client folder (profile.md, project.md, tracking.md, meetings/)
│
└── pub/           — Public materials
    ├── pub_context/
    │   └── svaib_presentation_guide.md — Presentation style guide
    ├── prompts/   — Public-facing role prompts
    └── Liga_2025/ — Conference materials
```

## Current Application Architecture

**Tech Stack:** Next.js 16.0.1 with App Router, React 19.2.0, Tailwind CSS
**Deployment:** Vercel auto-deploy from `dev/src/` on push to main
**Live URL:** [https://svaib.com](https://svaib.com)

### Application Structure

Single-page landing with sections:

1. **Header** - Fixed logo `svaib` (top-right): "sv" and "b" in teal, "ai" in pink
2. **Hero** - Main heading, subtitle, CTA button to Telegram
3. **Architecture** - Interactive diagram showing AI-management system:
   * **Desktop:** Canvas with positioned blocks and SVG connections
   * **Mobile:** Simple card list (responsive adaptation)
4. **CTA** - Call-to-action section
5. **Footer** - Contacts, links, archive access

### Interactive Features

**Architecture Diagram (Desktop):**

* 7 interactive blocks positioned on canvas (800px height)
* SVG lines showing data flow between blocks
* Hover effects: teal shadow + lift animation
* Click opens modal with detailed information
* Hint text: "Нажмите на блок, чтобы узнать подробности"

**Mobile Adaptation:**

* Header logo: smaller (text-2xl vs text-3xl)
* Architecture: hides canvas, shows simple card list
* All sections responsive with Tailwind breakpoints

### State Management

React hooks in `Architecture.jsx`:

* `activeBlock` — Currently selected block for modal
* `containerSize` — Canvas dimensions (tracked with useRef + useEffect)
* Modal opens on block click, closes on backdrop/X click

### Data Structure

`architectureData.js` contains:

* `blocks[]` — Array of 7 architecture blocks:
  * Presentation, AI-ассистент (central)
  * Контекст, Метрики, Задачи, Протоколы (data)
  * AI-слой (processing)
* Each block: title, subtitle, icon, position, size, category, description, features, etc.
* `connections[]` — SVG line connections between blocks
* `blockSizes` — Pixel dimensions for each block type

## Vote Module (Internal Lab Tool)

Изолированный модуль для взвешенного голосования на стратсессиях. Не связан с основным продуктом — лабораторный подпроект.

**URLs:**
- `/vote` — Страница голосования (публичная)
- `/vote/results` — Результаты (публичные после завершения)
- `/vote/admin` — Админка (скрыта из меню, доступ по прямой ссылке)

**Логика:**
- Участники имеют вес по должности: CEO=5, C-1=3, C-2=2, Специалист=1
- Количество голосов = ceil(проекты / 2)
- За один проект: 0, 1 или 2 голоса
- Итоговый балл = Σ(голоса × вес участника)

**Таблицы Supabase:** vote_sessions, vote_participants, vote_projects, vote_ballots (см. data_model.md)

**Код:** `dev/src/app/vote/`, `dev/src/app/api/vote/`, `dev/src/lib/supabase.js` (POSITIONS)

## Design System

**Colors:**

* Primary (Teal): `#00B4A6` (buttons, interactive elements)
* Accent (Pink): `#FF4D8D` (gradients, website only)
* Text: `#1A1A1A` primary, `#6B7280` secondary

**Typography:**

* Headings: `Sora` (bold, semibold)
* Body: `Inter` (regular, medium, semibold)

**Spacing:** All spacing multiples of 4px (12px, 16px, 24px, 32px)
**Border Radius:** 12px (buttons/inputs), 16px (cards)

Full design specs: [dev/dev\_context/design\_system.md](dev/dev_context/design_system.md)

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
   * meta/ — Project strategy, product strategy (WHAT, WHY, WHEN, WHO)
   * dev/ — Product development, implementation (HOW to build)
   * framework/ — Product core: Second AI Brain methodology, ontology, scaffold, plugin
   * knowledge/ — External AI knowledge, tools, methods (not tied to svaib)
   * clients/ — Client projects, sales process (_playbook/), profiles, meetings
   * pub/ — Public materials (presentations, conference materials)
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

## Key Principles

* **Практичность:** Focus on working solutions, not tech for tech's sake
* **Честность:** Document failures alongside successes
* **Легкость:** Approach with humor, self-irony over perfectionism
* **Weekly releases:** Ship every week, gather feedback

## Getting More Context

| When you need                             | Read this file                           |
| ----------------------------------------- | ---------------------------------------- |
| Project strategy, OKR, team               | @meta/meta\_context/project\_overview.md |
| Product description (what, why, for whom) | @meta/meta\_context/product\_vision.md   |
| Positioning, messaging, sales             | @meta/meta\_context/marketing.md         |
| Product architecture (7 components)       | @dev/dev\_context/architecture.md        |
| Database schema (tables, fields, FK)      | @dev/dev\_context/data\_model.md         |
| Entity reference (roles, types, statuses) | @dev/dev\_context/data\_dictionary.md    |
| Infrastructure, APIs, VPS, deployments    | @dev/dev\_context/infrastructure.md      |
| Workflows, data flow, prompt contracts    | @dev/dev\_context/workflows.md           |
| Presentation structure (slide-by-slide)   | @dev/dev\_context/guide\_presentation.md |
| Design system specs                       | @dev/dev\_context/design\_system.md      |
| MCP servers, subagents, tools             | @.claude/claude\_code\_mechanics.md      |
| Team workflow (who does what)             | @meta/meta\_context/ai\_team.md          |
| External AI knowledge (tools, methods)    | @knowledge/README.md                     |
| Product methodology (ontology, rituals)   | @framework/README.md                     |
| Product scaffold (templates)              | @framework/scaffold/                     |
| Product model (client presentation)       | @framework/model.md                      |
| Client profile, meeting prep              | @clients/{name}/profile.md               |
| Client project (deal, decisions)          | @clients/{name}/project.md               |
| Client training progress, blocks          | @clients/{name}/tracking.md              |
| Client methodology, offers, onboarding    | @clients/\_playbook/README.md             |

***

## Maintenance: Keeping CLAUDE.md Updated

**This file is the single source of truth. After making changes, always check if CLAUDE.md needs updating.**

### When to update CLAUDE.md:

| Change                                               | What to update in CLAUDE.md                              |
| ---------------------------------------------------- | -------------------------------------------------------- |
| Created/deleted slash command in `.claude/commands/` | Update "Slash Commands" section                          |
| Changed folder structure (added/removed folders)     | Update "Repository Structure" section                    |
| Changed tech stack (e.g., migrated to Next.js)       | Update "Current Application Architecture"                |
| Changed deployment process (e.g., new Vercel config) | Update "Development Workflow"                            |
| Changed design system colors/fonts                   | Update "Design System" section                           |
| Major architectural change                           | Update relevant sections + "Planned Migration" if needed |

### Automatic check:

**After making changes to `.claude/commands/`, `dev/`, or `meta/` structure, always ask:**

> "Does CLAUDE.md need updating? Check the maintenance table above."