---
title: "metrics-analysis — skill (системный промпт + черновик narrative)"
updated: 2026-04-30
version: 5
scope: product_core
priority: high
type: reference
---

# metrics-analysis — skill

Здесь живёт **только собственно skill** вертикали `metrics`. Методология, HOWTO, rollout, intake-form, открытые вопросы, карта вертикали — переехали в [`../../methodology/metrics/`](../../methodology/metrics/).

**Точка входа в вертикаль:** [`../../methodology/metrics/README.md`](../../methodology/metrics/README.md).

## Что в этой папке

| Файл | Тип | Что делает |
|------|-----|-----------|
| [`README.md`](README.md) | index | Этот файл |
| [`orchestrator-metrics.md`](orchestrator-metrics.md) | procedure | Системный промпт оркестратора AI-агента: ветки А/В/Б, обработка ошибок, Cowork-чек-лист, критические правила |
| [`narrative.py`](narrative.py) | code (draft) | Универсальный narrative composer (классификация red/win/ok/blocked + сборка markdown). **Черновик** — судьба под открытым вопросом #1 (vs LLM-сборка), см. [`../../methodology/metrics/open-questions.md`](../../methodology/metrics/open-questions.md) |

## Запланировано (когда дойдёт очередь)

- `prompt-route-resolver.md` — классификатор: вопрос → ветка А/В/Б
- `prompt-thinking-branch.md` — ветка Б (думающая): план → валидация → исполнение → сборка

## Что НЕ живёт здесь

- **Per-client extractor** (типа `ssp_okr1.py`) — это код клиента, лежит в `metrics/extractors/` клиентского scaffold, не в общей библиотеке skill. Шаблон-паттерн — в [`../../scaffold/metrics/extractors/README.md`](../../scaffold/metrics/extractors/README.md), пример — в `framework/_inbox/metrics-scaffold/sandbox/extractors/ssp_okr1.py`.
- **Методология цикла** (HOWTO, rollout, intake-form, open-questions, architecture) — в [`../../methodology/metrics/`](../../methodology/metrics/).
- **Шаблоны клиента** (витрина, template-domain, source-README, extractors-README) — в [`../../scaffold/metrics/`](../../scaffold/metrics/).

## Связи

- [`../../methodology/metrics/README.md`](../../methodology/metrics/README.md) — карта всей вертикали (точка входа)
- [`../../methodology/metrics/architecture.md`](../../methodology/metrics/architecture.md) — источник правды по архитектуре и канону доменов
- [`../../scaffold/metrics/`](../../scaffold/metrics/) — каркас, который разворачивается у клиента
