# dev/

> Часть проекта svaib. Полная структура: [../README.md](../README.md)

## Назначение

Разработка и реализация продукта. Отвечает на вопрос КАК строить. Включает код сайта, документацию продукта, технические промпты.

## Навигация по направлению

- [01_overview.md](01_overview.md) — миссия направления, стадия, цель декады
- [02_active.md](02_active.md) — что в работе сейчас, Session Handoff
- [02_backlog.md](02_backlog.md) — задачи направления на будущее
- [03_progress.md](03_progress.md) — хроника сделанного
- [_inbox/01_inbox.md](_inbox/01_inbox.md) — входящее на разбор

Направление устроено по универсальной модели svaib: `_inbox → backlog → active → progress + decisions`. Правила работы — [../lab/work-model.md](../lab/work-model.md).

## Структура

```
dev/
├── src/           — Публичный сайт svaib.com (Next.js, App Router)
├── dev_context/   — Техническая документация сайта и архивные product docs
└── n8n_backup/    — Бэкапы n8n workflows
```

## Файлы (dev_context/)

> Полный список и подробные описания: [dev_context/README.md](dev_context/README.md)

| Файл | Что внутри | Когда читать |
|------|-----------|--------------|
| site_rebuild_plan.md | Технический план новой версии сайта | Реализация и review |
| site_rebuild_creative_brief.md | Copy, design constraints, demo/content specs | Источник контента |
| design_system.md | Дизайн-система (цвета, шрифты, компоненты) | Работа с UI |
| infrastructure.md | Инвентаризация ресурсов (серверы, домены, API) | DevOps, деплой |
| archive_notes.md | Какие docs актуальны, а какие архивны | Быстрая ориентация |
| architecture.md | Архивный архитектурный контракт прошлого meeting pivot | История |
| product_release.md | Архивный релиз meeting/presentation MVP | История |
| product_roadmap.md | Архивная roadmap прошлого pivot | История |
| workflows.md | Архив отключённых n8n workflows | История |

## src/ — Сайт svaib.com

**Tech Stack:** Next.js 16, React 19, Tailwind CSS
**Deployment:** Vercel (auto-deploy on push to main)
**Live:** https://svaib.com

**Публичные маршруты:** `/`, `/second-ai-brain`, `/lab`, `/knowledge`, `/archive`
**История пивотов:** `public/archive/`
**Внутренний модуль:** `/vote` — internal-only, выключен по умолчанию через `ENABLE_INTERNAL_VOTE=false`

## Связанные папки

- **meta/** — Стратегия проекта и продукта (ЧТО, ЗАЧЕМ)
