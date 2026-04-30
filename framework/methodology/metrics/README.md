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

[`../../scaffold/metrics/`](../../scaffold/metrics/)

| Файл | Что внутри |
|---|---|
| [`README.md`](../../scaffold/metrics/README.md) | Устройство папки `metrics/` у клиента, правила уровня папки |
| [`01_metrics.md`](../../scaffold/metrics/01_metrics.md) | Шаблон витрины: target metrics CEO, карта доменов, OKR-секция, глоссарий |
| [`template-domain.md`](../../scaffold/metrics/template-domain.md) | Шаблон domain-файла: `datasets / regions / fields / metrics / routes / known_issues` |
| [`source/README.md`](../../scaffold/metrics/source/README.md) | Правила работы с xlsx-источниками клиента |
| [`extractors/README.md`](../../scaffold/metrics/extractors/README.md) | Правила работы с per-client extractors у клиента |

### Pilot / Sandbox — рабочая площадка пилота (Лебедев)

[`../../_inbox/metrics-scaffold/`](../../_inbox/metrics-scaffold/)

| Артефакт | Что |
|---|---|
| [`plan.md`](../../_inbox/metrics-scaffold/plan.md) | План пилота: этапы А/Б/С, контекст, тест-вопросы, перечень что прочитать новому чату |
| `sandbox/` | Git-tracked полигон: 3 domain-файла (`customer.md`, `sales.md`, `operations.md`), витрина, `source/`, `extractors/`, `_b0_findings/`, `_runs/` |
| `cowork-test/COWORK-TEST.md` | Готовый pack для тестирования pipeline в Cowork-окружении клиента |

### Решения

[`../../04_decisions.md`](../../04_decisions.md) №5 — «Раскладка metrics в scaffold (B1+O1/O5)»: имена доменов, OKR-проекция, не переименовывать domain под OKR.

---

## Текущий статус

```
Этап А — Канон-каркас metrics            ✅ DONE 2026-04-29
Этап Б.1 — Sandbox у Виктора              ✅ DONE 2026-04-29
Этап Б.2 — Боевой перенос у первого клиента NEXT (начинаем с intake-form)
Этап С  — Меняем канон + расширения        планируется после Б.2
```

**Б.2 success criteria (явно):** compound route на **OKR1** работает в боевом Cowork клиента, числа сходятся со скриншотом, sub-agent проходит без подсказок про пути. Только OKR1, только пилотный лист. OKR2/OKR3, контракты BuildIn, временной анализ — в Этап С.

---

## С чего начать

| Кто ты | Читай первым |
|---|---|
| Хочу понять как это работает на пальцах | [`HOWTO.md`](HOWTO.md) — за 10 минут с примером первого клиента end-to-end |
| Хочу развернуть metrics для нового клиента | [`rollout.md`](rollout.md) — 12-шаговый playbook |
| Я AI-агент, у меня вопрос CEO про метрики | [`../../skills/metrics-analysis/orchestrator-metrics.md`](../../skills/metrics-analysis/orchestrator-metrics.md) |
| Хочу понять архитектурный замысел | [`architecture.md`](architecture.md) — 6 слоёв методологии |
| Хочу понять продуктовое решение по раскладке | [`../../04_decisions.md`](../../04_decisions.md) №5 |
| Хочу собрать с CEO материал для пилота | [`intake-form.md`](intake-form.md) |
| Какие вопросы по архитектуре открыты | [`open-questions.md`](open-questions.md) |
| Что прочитать перед стартом Б.2 | секция «Что прочитать новому чату» в [`plan.md`](../../_inbox/metrics-scaffold/plan.md) |

---

## Принципы (короткое напоминание)

- **AI не считает в голове.** Любой расчёт — через Python (детерминированный).
- **Данные у клиента.** Мы не трогаем клиентский xlsx, не нормализуем. Делаем семантический слой между данными и LLM.
- **Воспроизводимость.** Тот же вопрос на ту же дату даёт ту же цифру через день, неделю, месяц.
- **Стабильные ID метрик.** Маршруты ссылаются на `metric_<id>`, не на физические колонки.
- **Канон 8 имён domain-файлов** — закрытый список, источник правды в [`architecture.md`](architecture.md).

Полный список принципов и слоёв — в [`architecture.md`](architecture.md).
