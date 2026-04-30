---
title: "metrics-analysis — точка входа в metrics-вертикаль"
updated: 2026-04-30
version: 3
scope: product_core
priority: high
type: reference
---

# metrics-analysis — карта вертикали

**Это точка входа.** Если ты новый чат / новый инженер / новый клиент-CTO — начинай здесь. Дальше иди по ссылкам в нужный артефакт.

Метрики бизнеса CEO живут в xlsx/Sheets. Цель metrics-вертикали в Second AI Brain — CEO задаёт AI-агенту вопрос своими словами и получает воспроизводимый ответ с trace. Не «вот цифра», а «вот цифра, вот источник, вот код, timestamp данных».

---

## С чего начать

| Кто ты | Читай первым |
|---|---|
| Хочу понять как это работает на пальцах | [`HOWTO.md`](HOWTO.md) — за 10 минут с примером первого клиента end-to-end |
| Хочу развернуть metrics для нового клиента | [`rollout.md`](rollout.md) — 12-шаговый playbook |
| Я AI-агент, у меня вопрос CEO про метрики | [`orchestrator-metrics.md`](orchestrator-metrics.md) — системный промпт оркестратора |
| Хочу понять архитектурный замысел | [`../../methodology/metrics.md`](../../methodology/metrics.md) — 6 слоёв методологии |
| Хочу понять продуктовое решение по раскладке | [`../../04_decisions.md`](../../04_decisions.md) №5 |
| Хочу собрать с CEO материал для пилота | [`intake-form.md`](intake-form.md) — карта метрик для самозаполнения CEO |

---

## Карта артефактов

### Канон фреймворка (живёт здесь, переносится клиентам)

| Артефакт | Тип | Что содержит |
|---|---|---|
| [`HOWTO.md`](HOWTO.md) | reference | Как работает pipeline на пальцах. Целевая аудитория: новый коллега, клиент-CTO, CEO svaib |
| [`orchestrator-metrics.md`](orchestrator-metrics.md) | procedure | Системный промпт AI-агента: ветки А/В/Б, обработка ошибок, Cowork-чек-лист, критические правила |
| [`rollout.md`](rollout.md) | procedure | 12-шаговый playbook развёртывания metrics-вертикали для нового клиента |
| [`intake-form.md`](intake-form.md) | procedure | Анкета для CEO: структура OKR, ключевые метрики, источники, типовые вопросы. Заполняется при онбординге |
| [`../../scaffold/metrics/template-domain.md`](../../scaffold/metrics/template-domain.md) | template | Шаблон domain-файла: `datasets / regions / fields / metrics / routes / known_issues` |
| [`../../scaffold/metrics/01_metrics.md`](../../scaffold/metrics/01_metrics.md) | template | Шаблон витрины: target metrics, карта доменов, OKR-секция, глоссарий CEO |
| [`../../scaffold/metrics/source/README.md`](../../scaffold/metrics/source/README.md) | template | Правила работы с xlsx-источниками |

### Методология и решения

| Артефакт | Что в нём |
|---|---|
| [`../../methodology/metrics.md`](../../methodology/metrics.md) | Архитектурный слой: 6 слоёв (snapshot, semantic, verified routes, маршруты, processing, ритуалы), `[СЕЙЧАС]/[ПОЗЖЕ]` пометки |
| [`../../04_decisions.md`](../../04_decisions.md) №5 | Раскладка metrics в scaffold: имена доменов (8 канонических), OKR-проекция в витрине, не переименовывать domain под OKR |
| [`../../architecture.md`](../../architecture.md) | Где metrics живут в архитектуре: вертикаль управленческого цикла поверх 3 слоёв продукта и 6 частей framework |

### Рабочие материалы пилота (первый клиент)

| Артефакт | Что в нём |
|---|---|
| [`../../_inbox/metrics-scaffold/plan.md`](../../_inbox/metrics-scaffold/plan.md) | План пилота: Этапы А/Б/С, контекст пилота, тест-вопросы, что прочитать новому чату |
| [`../../_inbox/metrics-scaffold/sandbox/`](../../_inbox/metrics-scaffold/sandbox/) | Sandbox клиента: 3 domain-файла, витрина, source/, extractor, narrative, _b0_findings/, _runs/ |
| `../../_inbox/metrics-scaffold/sandbox/_b0_findings/03_results.md` | Итоги Б.1 — что сработало, что нет, артефакты прогона |
| `../../_inbox/metrics-scaffold/sandbox/_extractors/ssp_okr1.py` | Per-client extractor с захардкоженными координатами SSP клиента |
| `../../_inbox/metrics-scaffold/sandbox/_extractors/narrative.py` | Универсальный narrative composer (потенциально кандидат на пересмотр — см. open-questions) |

---

## Текущий статус

```
Этап А — Канон-каркас metrics            ✅ DONE 2026-04-29
Этап Б.1 — Sandbox у Виктора              ✅ DONE 2026-04-29
Этап Б.2 — Боевой перенос у первого клиента NEXT (начинаем с intake-form)
Этап С  — Меняем канон + расширения        планируется после Б.2
```

**Б.2 success criteria (явно):** compound route на **OKR1** работает в боевом Cowork клиента, числа сходятся со скриншотом, sub-agent проходит без подсказок про пути. Только OKR1, только пилотный лист SSP. OKR2/OKR3, контракты BuildIn, временной анализ — **в Этап С**.

**Что прочитать перед стартом нового чата:** список в [`plan.md`](../../_inbox/metrics-scaffold/plan.md) секция «Что прочитать новому чату перед стартом Б.2».

---

## Открытые вопросы

См. [`open-questions.md`](open-questions.md). Здесь — заголовки:

1. **Архитектура narrative.py vs LLM-сборка.** Сейчас сборка narrative — Python-скрипт с фиксированным каркасом. Возможно `classify(direction)` остаётся в Python, а сборка ответа CEO переходит в LLM (учёт контекста разговора, приоритетов в моменте, сколько подсветить).
2. **Стоимость sub-agent end-to-end test.** ~10% контекстного бюджета на один прогон тест-вопроса. Для регулярного eval — слишком дорого. Альтернативы?
3. **Дубль метрик KR1.** `metric_churn_90d_mrr_monthly` ≡ `metric_churn_ltv_90d_mrr` за Q1 (числа байт-в-байт). Решить с клиентом: одна метрика или две.
4. **Threshold vs ranking** в narrative composer. Для «топ-N худших» порог 10% не нужен — нужен ranking без cutoff.
5. **Топ-N + сводка** «всего N в красной зоне, отсёк top-5 / показал все».

---

## Файлы в этой папке

| Файл | Тип | Что делает |
|------|-----|-----------|
| [`README.md`](README.md) | index | Этот файл |
| [`HOWTO.md`](HOWTO.md) | reference | Как работает pipeline на пальцах |
| [`orchestrator-metrics.md`](orchestrator-metrics.md) | procedure | Системный промпт AI-агента |
| [`rollout.md`](rollout.md) | procedure | Playbook развёртывания для нового клиента |
| [`intake-form.md`](intake-form.md) | procedure | Анкета для CEO при онбординге |
| [`open-questions.md`](open-questions.md) | log | Архитектурные вопросы и решения, отложенные на потом |
| `prompt-route-resolver.md` | prompt | (планируется) Классификатор: вопрос → ветка А/В/Б |
| `prompt-thinking-branch.md` | prompt | (планируется) Ветка Б (думающая): план → валидация → исполнение → сборка |
