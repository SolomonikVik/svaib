---
title: "Ландшафт экосистемы плагинов Claude Code — бенчмарки, конкуренты, модели монетизации"
updated: 2026-02-26
version: 1
type: research
scope: "product_strategy"
---

# Plugin Landscape

## Кратко

Исследование экосистемы плагинов Claude Code / Cowork: метрики adoption, бенчмарки для нового плагина, конкуренты по позиционированию, модели монетизации. Снимок: февраль 2026.

## Связанные файлы

- ../management/02_goal.md — цели по плагину (метрики)
- ../../framework/plugin/README.md — сам плагин (реализация)
- ../../knowledge/plugins/!plugins.md — техническая документация по формату плагинов

---

## Экосистема в цифрах (февраль 2026)

| Метрика | Значение |
|---------|----------|
| Claude Code (основной репо) | 70,192 stars |
| Plugin system (public beta) | запущен октябрь 2025 |
| Cowork plugins | запущен 30 января 2026 |
| Плагины на claude-plugins.dev | 75,000+ |
| anthropics/claude-plugins-official | 8,360 stars, 42 плагина |
| anthropics/knowledge-work-plugins | 7,989 stars, 17 категорий |
| Возраст экосистемы | ~5 месяцев |

**Публичного счётчика установок НЕТ.** GitHub stars — единственный надёжный публичный proxy.

---

## Топ community-плагинов по stars

| Плагин | Stars | Возраст | Ниша |
|--------|-------|---------|------|
| claude-mem (thedotmack) | 31,012 | ~6 мес | Memory/context |
| planning-with-files | 14,567 | ~2 мес | Workflow/planning |
| compound-engineering-plugin | 9,572 | ~4 мес | Engineering workflow |
| humanizer | 6,824 | ~2 мес | Writing/AI-detection |
| claude-hud | 3,771 | ~2 мес | Developer UX |
| trailofbits/skills | 2,932 | — | Security |
| **arscontexta** | **1,891** | **11 дней** | **Knowledge management / Second Brain** |
| playwright-skill | 1,791 | — | Testing |
| superpowers-marketplace | 549 | ~4 мес | Dev workflow (marketplace) |

---

## arscontexta — прямой конкурент по позиционированию

| Аспект | Данные |
|--------|--------|
| Автор | Heinrich (@arscontexta) |
| GitHub | agenticnotetaking/arscontexta |
| Stars | 1,891 за 11 дней (создан 15.02.2026) |
| Forks | 112, contributors: 4 |
| Лицензия | MIT |
| Что делает | Генерирует персональную knowledge system через 2-4 раунда диалога. 249 файлов, three-space model, 6Rs pipeline, 10 skills |
| Позиционирование | "Second Brain", "persistent memory for agents" — пересекается с SVAIB |
| Монетизация | НЕТ. Сайт arscontexta.org — заглушка "app: coming soon". Стратегия: audience building → SaaS/сервис |
| Как набрал аудиторию | Хук "claude now builds itself a second brain" + серия постов в X + timing на пике хайпа + MIT + GIF-демо |

**Отличие SVAIB:** управленческая методология (ритуалы, decision frames, протоколы встреч), а не conversational knowledge derivation. arscontexta генерирует структуру из разговора. SVAIB даёт архитектуру + экспертизу руководителя.

---

## Бенчмарки для нового нишевого плагина (6 месяцев)

| Сценарий | Stars | Условия |
|----------|-------|---------|
| Минимум | 100-300 | Опубликовать в marketplace, organic discovery |
| Средний | 300-800 | Посты X/Reddit, включение в awesome-листы |
| Хороший | 800-2,000 | Product Hunt, YouTube, awesome-claude-code |
| Вирусный | 2,000+ | Сильный нарратив + Twitter virality |

### Факторы роста

1. Включение в anthropics/claude-plugins-official — мультипликатор x3-5
2. Попадание в ComposioHQ/awesome-claude-skills (37.7K stars) — главный каталог
3. Twitter/X thread с демо — основной канал вирального роста
4. Anthropic валидирует нишу: knowledge-work-plugins включает product-management, productivity, operations

---

## Модели монетизации плагинов

### Текущее состояние

Рынок платных плагинов Claude Code **не существует**. Все плагины open source. У Anthropic нет billing для сторонних плагинов. Экосистема на стадии "всё бесплатно, набираем adoption".

### Аналогии из других экосистем

| Экосистема | Монетизация | Уроки для SVAIB |
|------------|-------------|-----------------|
| **VS Code extensions** | Нет billing в marketplace. Только крупные (Copilot, GitLens) через external SaaS | Без billing монетизация работает только для крупных или через внешний сервис |
| **Obsidian plugins** | Все бесплатные. Деньги на контенте вокруг (курсы, YouTube) | Плагин = маркетинговый инструмент, не продукт |
| **Notion templates** | Прямая продажа: $5-200. Thomas Frank: $1M+, Easlo: $500K+. Средний доход: $1-3K/мес | **Ближайшая аналогия к SVAIB.** Ценность в structure + workflow, не в коде |

### Модели для SVAIB (по убыванию релевантности)

| Модель | Суть | Релевантность |
|--------|------|---------------|
| Open source плагин + платный консалтинг | Плагин = вход, revenue = время | Высокая (текущая модель) |
| Плагин + платная методология | Бесплатный scaffold, платные advanced skills + agents ($50-200) | Высокая (аналогия Notion) |
| Freemium | Core free, premium features за подписку | Средняя (нет billing инфраструктуры) |
| Enterprise onboarding | Высокий чек, длинный цикл | Средняя (фаза 2) |

---

## Главные каталоги экосистемы (для будущего листинга)

| Каталог | Stars | Что это |
|---------|-------|---------|
| ComposioHQ/awesome-claude-skills | 37,749 | Крупнейший каталог skills |
| hesreallyhim/awesome-claude-code | 25,110 | Курированный список: skills, hooks, plugins |
| VoltAgent/awesome-claude-code-subagents | 11,448 | Каталог субагентов |
| anthropics/claude-plugins-official | 8,360 | Официальный маркетплейс |
| claude-plugins.dev | — | Веб-каталог, 75K+ плагинов |
| claudemarketplaces.com | — | Агрегатор маркетплейсов |

---

*Исследование: 26 февраля 2026. Пересмотреть через 3 месяца — экосистема быстро меняется.*
