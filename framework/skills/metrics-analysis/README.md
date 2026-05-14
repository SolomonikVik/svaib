---
title: "metrics-analysis — skill (промпты + код вертикали metrics)"
updated: 2026-05-14
version: 2
scope: product_core
priority: high
type: reference
---

# metrics-analysis — skill

Здесь живёт **только собственно skill** вертикали `metrics` — промпты и код. Методология вертикали и карта — в [`../../methodology/metrics/`](../../methodology/metrics/).

**Точка входа в вертикаль:** [`../../methodology/metrics/README.md`](../../methodology/metrics/README.md).

## Что в этой папке

| Файл | Тип | Что делает |
|------|-----|-----------|
| [`README.md`](README.md) | index | Этот файл |
| [`business-metrics-intake.md`](business-metrics-intake.md) | procedure | Промпт-помощник заполнения клиентского `business-metrics.md`: ведёт диалог с CEO, собирает каноническое имя / бизнес-смысл / правило расчёта / единицу / направление по каждой метрике, по спеке [`metrics-spec.md`](../../methodology/metrics/metrics-spec.md) |
| [`orchestrator-metrics.md`](orchestrator-metrics.md) | procedure | Операционный пайплайн оркестратора: чем исполняется каждый шаг потока обработки запроса в проде. Приведён к `architecture.md` v2 |
| [`probe_xlsx.py`](probe_xlsx.py) | code | Универсальный helper разведки xlsx: листы, размеры, объединённые ячейки, формулы, cached errors, заполненность колонок |

## Что НЕ живёт здесь

- **Per-client extractor** — код клиента, лежит в `metrics/extractors/` клиентского scaffold, не в общей библиотеке skill. Как строится — [`../../methodology/metrics/extractor.md`](../../methodology/metrics/extractor.md).
- **Методология цикла** (architecture, metrics-spec, extractor) — в [`../../methodology/metrics/`](../../methodology/metrics/).
- **Шаблоны клиента** (`business-metrics.md`, READMEs папок) — в [`../../scaffold/05_metrics/`](../../scaffold/05_metrics/).

## Связи

- [`../../methodology/metrics/README.md`](../../methodology/metrics/README.md) — карта всей вертикали (точка входа)
- [`../../methodology/metrics/architecture.md`](../../methodology/metrics/architecture.md) — источник правды по устройству вертикали
- [`../../scaffold/05_metrics/`](../../scaffold/05_metrics/) — каркас, который разворачивается у клиента
