---
title: "Metrics — управленческий цикл (вертикаль)"
updated: 2026-04-30
version: 1
scope: product_core
priority: high
type: reference
---

# Metrics — точка входа в вертикаль

Управленческий цикл `metrics` в Second AI Brain. Эта папка — карта всей вертикали: куда смотреть за методологией, скиллом, шаблонами клиента, пилотом, решениями. Сюда заходит любой новый чат / новый инженер / архитектор перед работой с метриками.

**Суть вертикали.** Метрики бизнеса CEO живут в xlsx/Sheets. Цель — CEO задаёт AI-агенту вопрос своими словами и получает воспроизводимый ответ с trace. Не «вот цифра», а «вот цифра, вот источник, вот код, timestamp данных». Принцип: AI не считает в голове — переводит вопрос в детерминированный расчёт через Python.

Архитектурный контекст: вертикаль проходит сквозь 3 слоя продукта (данные / память / помощники) и 6 частей framework — см. [`../../architecture.md`](../../architecture.md), раздел «Вертикали управленческих циклов».

---

## Карта вертикали — где что лежит

### Методология (эта папка) — как устроена и работает вертикаль

| Файл | Что внутри |
|---|---|
| [`README.md`](README.md) | Этот файл — карта вертикали |
| [`architecture.md`](architecture.md) | **Источник правды:** 6 слоёв (snapshot, canonical, semantic, ритуалы, обработка запроса), ветки А/В/Б, канон 8 имён domain-файлов, `[СЕЙЧАС]/[ПОЗЖЕ]` пометки |
| [`HOWTO.md`](HOWTO.md) | Как работает pipeline на пальцах. Аудитория: новый коллега, клиент-CTO, CEO svaib |
| [`rollout.md`](rollout.md) | 12-шаговый playbook развёртывания вертикали у нового клиента |
| [`intake-form.md`](intake-form.md) | Анкета для CEO: OKR, метрики, источники, типовые вопросы. Заполняется при онбординге |
| [`open-questions.md`](open-questions.md) | Архитектурные вопросы и решения, отложенные на потом |

### Skill — то, что компилируется в системный промпт AI-агента

[`../../skills/metrics-analysis/`](../../skills/metrics-analysis/)

| Файл | Что внутри |
|---|---|
| [`orchestrator-metrics.md`](../../skills/metrics-analysis/orchestrator-metrics.md) | Системный промпт оркестратора: ветки А/В/Б, обработка ошибок, Cowork-чек-лист, критические правила |
| [`narrative.py`](../../skills/metrics-analysis/narrative.py) | **Черновик.** Универсальный narrative composer. Судьба под открытым вопросом #1 (vs LLM-сборка) — см. [`open-questions.md`](open-questions.md) |

### Scaffold — каркас, который разворачивается у клиента

[`../../scaffold/05_metrics/`](../../scaffold/05_metrics/)

| Файл | Что внутри |
|---|---|
| [`README.md`](../../scaffold/05_metrics/README.md) | Устройство папки `metrics/` у клиента, правила уровня папки |
| [`01_metrics.md`](../../scaffold/05_metrics/01_metrics.md) | Шаблон витрины: target metrics CEO, карта доменов, OKR-секция, глоссарий |
| [`template-domain.md`](../../scaffold/05_metrics/template-domain.md) | Шаблон domain-файла: `datasets / regions / fields / metrics / routes / known_issues` |
| [`source/README.md`](../../scaffold/05_metrics/source/README.md) | Правила работы с xlsx-источниками клиента |
| [`extractors/README.md`](../../scaffold/05_metrics/extractors/README.md) | Правила работы с per-client extractors у клиента |


