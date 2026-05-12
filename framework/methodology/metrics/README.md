---
title: "Metrics — управленческий цикл (вертикаль)"
updated: 2026-05-12
version: 2
scope: product_core
priority: high
type: reference
---

# Metrics — точка входа в вертикаль

Управленческий цикл `metrics` в Second AI Brain. Эта папка — карта вертикали: куда смотреть за рамкой первого слоя, базовой архитектурой, скиллом, шаблонами клиента, развёртыванием, открытыми вопросами. Сюда заходит любой новый чат / новый инженер / архитектор перед работой с метриками.

**Суть вертикали.** Метрики бизнеса CEO живут в xlsx/Sheets. Цель — CEO задаёт помощнику вопрос своими словами и получает воспроизводимый ответ из источника. Принцип: помощник не считает в голове.

**С чего стартовать у клиента — первый слой.** Минимум, который ставится у каждого нового клиента: каноническое имя метрики, колонка с этим именем в xlsx, помощник по колонке. Без паспортов, без extractor-а, без narrative. Рамка и DoD — [`first-layer.md`](first-layer.md). Полная архитектура — [`architecture.md`](architecture.md), она остаётся базой; над первым слоем по триггерам надстраивается второй и третий.

Архитектурный контекст: вертикаль проходит сквозь 3 слоя продукта (данные / память / помощники) и 6 частей framework — см. [`../../architecture.md`](../../architecture.md), раздел «Вертикали управленческих циклов».

---

## Карта вертикали — где что лежит

### Методология (эта папка)

| Файл | Что внутри |
|---|---|
| [`README.md`](README.md) | Этот файл — карта вертикали |
| [`first-layer.md`](first-layer.md) | Рамка и DoD первого слоя, формат `canonical_metrics.md`, граница со вторым слоем |
| [`architecture.md`](architecture.md) | База: 6 слоёв (snapshot, canonical, semantic, ритуалы, обработка запроса), ветки А/В/Б, канон 8 имён domain-файлов |
| [`HOWTO.md`](HOWTO.md) | Сценарий первого слоя на пальцах: «CEO спрашивает → помощник идёт через каноническое имя → возвращает число» |
| [`rollout.md`](rollout.md) | Playbook первого слоя у нового клиента |
| [`intake-form.md`](intake-form.md) | Внутренний чек-лист координатора: что собрать у клиента до Шага 3 rollout |
| [`open-questions.md`](open-questions.md) | Архитектурные вопросы и решения, отложенные на потом |

### Skill — что компилируется в системный промпт помощника

[`../../skills/metrics-analysis/`](../../skills/metrics-analysis/)

| Файл | Что внутри |
|---|---|
| [`orchestrator-metrics.md`](../../skills/metrics-analysis/orchestrator-metrics.md) | Системный промпт оркестратора для второго слоя: ветки А/В/Б, обработка ошибок, критические правила. На первом слое используется ограниченное подмножество — только Ветка А в редуцированной форме |
| [`probe_xlsx.py`](../../skills/metrics-analysis/probe_xlsx.py) | Одноразовая разведка xlsx: листы, размеры, объединённые ячейки, кэшированные ошибки |
| [`narrative.py`](../../skills/metrics-analysis/narrative.py) | Narrative composer — второй слой; роль Python vs LLM-сборки обсуждается в [`open-questions.md`](open-questions.md) №1 |

### Scaffold — каркас, который разворачивается у клиента

[`../../scaffold/05_metrics/`](../../scaffold/05_metrics/)

| Файл | Что внутри |
|---|---|
| [`README.md`](../../scaffold/05_metrics/README.md) | Устройство папки `metrics/` у клиента, правила уровня папки |
| [`canonical_metrics.md`](../../scaffold/05_metrics/canonical_metrics.md) | Шаблон первого слоя: каноническое имя + бизнес-смысл + как считается |
| [`01_metrics.md`](../../scaffold/05_metrics/01_metrics.md) | Шаблон витрины второго слоя: target metrics CEO, карта доменов, OKR-секция, глоссарий |
| [`template-domain.md`](../../scaffold/05_metrics/template-domain.md) | Шаблон domain-файла второго слоя: `datasets / regions / fields / metrics / routes / known_issues` |
| [`source/README.md`](../../scaffold/05_metrics/source/README.md) | Правила работы с xlsx-источниками клиента |
| [`extractors/README.md`](../../scaffold/05_metrics/extractors/README.md) | Правила работы с per-client extractors (второй слой) |
