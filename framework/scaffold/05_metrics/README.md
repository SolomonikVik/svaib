# 05_metrics/ — метрики бизнеса

Metrics-вертикаль у клиента: семантика метрик бизнеса CEO для AI-аналитика. Числа здесь не лежат — они в источниках клиента (`source/`); markdown-файлы описывают, что метрики значат и как считаются, но не дублируют значения.

**Точка входа — `business-metrics.md`:** ключевые target metrics CEO одним файлом. С него начинается работа у каждого клиента.

## Что в папке

- `README.md` — этот файл
- `business-metrics.md` — базовый файл метрик: ключевые метрики бизнеса с паспортами. Точка входа
- `source/` — исходные файлы-источники клиента (xlsx и пр.), read-only для AI
- `extractors/` — per-client Python-скрипты извлечения значений из источников

Функциональные `{domain}-metrics.md` (finance, sales, …) добавляются позже, по живому триггеру — когда у CEO появилась реальная работа в домене.

## Методология — не здесь

В этой папке только клиентский каркас. Как устроена вертикаль и как с ней работать:

- [`../../methodology/metrics/architecture.md`](../../methodology/metrics/architecture.md) — устройство вертикали
- [`../../methodology/metrics/metrics-spec.md`](../../methodology/metrics/metrics-spec.md) — формат metrics-файлов
- [`../../methodology/metrics/extractor.md`](../../methodology/metrics/extractor.md) — построение extractor'ов

## Связи наружу

- `../02_strategy/02_goal.md` — KR, на которые работают метрики
- `../04_company/{node}/01_overview.md` — KPI подразделения ссылается на паспорт метрики здесь
