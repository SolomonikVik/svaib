---
title: "Site Rebuild Plan — Technical Architecture"
updated: 2026-03-13
status: approved_with_brief
owner: codex
paired_brief: "site_rebuild_creative_brief.md"
---

# Site Rebuild Plan — Technical Architecture

## Summary

Цель: переделать публичный сайт `svaib.com` на текущем Next.js app так, чтобы:
- смысл сайта совпадал с `meta/` и current product vision
- copy брался **verbatim из `site_rebuild_creative_brief.md`**, без самостоятельного переписывания
- `/vote` перестал быть публичным security-risk
- `dev/` стал понятным для следующего чата/агента без восстановления контекста вручную

Роли документов:
- `site_rebuild_creative_brief.md` — **source of truth для copy, design constraints, demo cards, article specs**
- этот план — **source of truth для структуры, маршрутов, техархитектуры, cleanup и acceptance**

## Implementation Changes

### 1. Security and technical baseline

- Закрыть `/vote`, `/vote/admin`, `/vote/results` и `/api/vote/*` через feature gate `ENABLE_INTERNAL_VOTE=false` по умолчанию.
- При `ENABLE_INTERNAL_VOTE=false` все vote routes и vote API возвращают `404`; публичная навигация и footer не содержат ссылок на `/vote`.
- Обновить `react` и `react-dom` до безопасного патч-релиза `19.2.4+`.
- Заменить `next lint` на рабочий ESLint CLI для Next 16; `npm run lint` должен снова быть валидным quality gate.
- Публичные страницы не используют Supabase и не создают новых API routes.
- Tailwind оставить на текущем поколении; в этом проходе не делать миграцию на v4.

### 2. Public route architecture

Финальный route set:
- `/` — identity + three directions + teasers + CTA
- `/second-ai-brain` — product page
- `/lab` — author story + `100 weeks of cringe` + philosophy
- `/knowledge` — article listing
- `/knowledge/[slug]` — article page
- `/archive` — history page
- legacy archive artifacts сохраняются по текущим `/archive/index.html` и `/archive/mvp-present.html`

Навигация:
- Header: `svaib.` | `Second AI Brain` | `Lab` | `Knowledge`
- Footer: `Second AI Brain` | `Lab` | `Knowledge` | `Archive` | Telegram | GitHub
- `Archive` есть только в footer, не в main nav

Metadata:
- `layout.js` обновить на значения из brief
- Каждый публичный маршрут получает свой `title`, `description`, `og:title`, `og:description`
- Добавить `robots` и `sitemap` для публичных маршрутов

### 3. Page composition contract

Главная `/`:
- Hero
- `Три направления`
- `Проблема` teaser
- `Как устроен Second AI Brain` teaser
- `Автор` teaser
- `Knowledge Hub` teaser с 3 article cards
- Mission strip
- Final CTA

`/second-ai-brain`:
- Hero
- `Проблема`
- `Три слоя`
- `Demo` section
- `Как это реализовано`
- `Бизнес-модель`
- `Для кого это сейчас`
- CTA

`/lab`:
- Hero
- `Автор`
- `100 недель кринжа`
- `Лаборатория`
- `Ценности`
- `Текущая стадия`
- External links

`/knowledge`:
- Intro
- 3 article cards из локальной content-коллекции
- Каждая карточка: `title`, `excerpt`, `readingTime`, `tags`

`/knowledge/[slug]`:
- clean reading layout без sidebar
- link `← Назад к знаниям`
- article body
- end CTA на `/second-ai-brain`

`/archive`:
- Intro
- 2 archive cards
- badge `Исторический артефакт` на каждой карточке

### 4. Content architecture

- Вынести весь marketing copy из React-компонентов в structured content layer.
- Для маршрутов использовать `RU-first` content object; EN не публикуется, но naming и shape должны позволять добавить `en` без переписывания компонентов.
- Все тексты для hero/sections/CTA брать из `site_rebuild_creative_brief.md`; самостоятельно не сочинять альтернативы.
- Demo section реализовать как **статичные scenario cards**, не интерактивные виджеты.
- Knowledge реализовать как локальную file-based content collection.
- Создать ровно 3 статьи по brief-spec:
  - `pochemu-ai-ne-pronikaet`
  - `kak-ai-razbiraet-vstrechu`
  - `management-design`
- Формат статей: MDX или typed content objects; решение оставить за implementer only if one abstraction is chosen once for all 3. Предпочтение: MDX для reviewability и будущего growth.

### 5. UI system and design constraints

- Сохранить текущие шрифты `Sora + Inter`, текущий brand palette и CSS variables.
- Убрать текущий `Architecture`-блок как главный narrative home page.
- Не использовать generic SaaS visuals, stock AI imagery, gradient backgrounds in cards, fake trust badges.
- Ввести teal top strip и более editorial/founder-led visual language по brief.
- Hero и contrast sections могут использовать dark teal / near-black backgrounds.
- Accent pink использовать только точечно.
- Reuse существующие button/card/badge primitives там, где это не конфликтует с brief; при конфликте приоритет у brief.

### 6. Repo cleanup in `dev/`

- Создать reviewable doc `dev/dev_context/site_rebuild_plan.md` и сохранить там этот план.
- `site_rebuild_creative_brief.md` оставить рядом как paired content spec.
- Обновить `dev/README.md`, чтобы там было ясно:
  - `dev/src` = публичный сайт
  - `public/archive` = история пивотов
  - `/vote` = internal-only, выключен по умолчанию
- Старые meeting/presentation product docs в `dev/dev_context` перевести в явно архивный статус или переместить в archive-зону, если они описывают не current product, а прошлый pivot.

## Public Interfaces / Contracts

- Public routes: `/`, `/second-ai-brain`, `/lab`, `/knowledge`, `/knowledge/[slug]`, `/archive`
- Internal env: `ENABLE_INTERNAL_VOTE=false` by default
- No new public API routes
- Knowledge article schema: `slug`, `title`, `excerpt`, `tags`, `publishedAt`, `readingTime`, `body`
- Page copy contract: content comes from `site_rebuild_creative_brief.md`
- Demo contract: static `Input | Process | Output` cards only
- CTA contract:
  - product CTA → `/second-ai-brain`
  - contact CTA → `https://t.me/solomonikvik`
  - footer social links → Telegram/GitHub only from existing canonical URLs

## Test Plan

Automated:
- `npm run lint` passes
- `npm run build` passes
- All public routes render statically
- `/vote` and `/api/vote/*` return `404` when `ENABLE_INTERNAL_VOTE=false`

Manual acceptance:
- Home page no longer speaks like meeting SaaS or Google Workspace product
- `/second-ai-brain` reflects the current `product_vision.md`
- Demo section on `/second-ai-brain` shows 3 static scenario cards with real content from the brief, not placeholders
- `/lab` is a public founder-story page, not an internal lab/process page
- `/knowledge` shows exactly 3 article cards and each slug opens a readable article page
- `/archive` is reachable from footer only and legacy HTML pages still work
- Footer and metadata reflect 2026 positioning, not old copy
- No page uses invented marketing copy outside the brief/meta source-of-truth

## Assumptions and defaults

- RU-first launch; no public EN routes in this pass
- No real AI backend demos, no forms, no waitlist backend
- No Tailwind v4 migration
- No `/vote` product rewrite; only isolation and shutdown-by-default
- If brief and old `dev_context` conflict, brief + `meta/*` win
- If brief leaves a microcopy gap, fill only by compressing existing `meta/*` wording without changing meaning
