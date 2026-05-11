# extractors/ — per-client Python-скрипты

Папка для **per-client extractors** — Python-скриптов, которые открывают `source/*.xlsx` клиента, забирают значения по заранее известным координатам и пишут результат в JSON-файл. AI-агент дёргает скрипт через Bash, читает результат через файл.

**Где лежит у клиента:** `metrics/extractors/` (рядом с `metrics/source/`). Не в `claude/skills/` — extractor не общий skill, у каждого клиента свой.

**Где лежат пример и шаблон-паттерн:** пример — `framework/_inbox/metrics-scaffold/sandbox/extractors/ssp_okr1.py`; полные правила написания — [`../../../methodology/metrics/rollout.md`](../../../methodology/metrics/rollout.md) шаг 6.

## Что лежит

| Файл | Что |
|------|-----|
| `<client>_<sheet>.py` | per-client extractor: знает координаты метрик в xlsx именно этого клиента |

> Заполняется при rollout (шаг 6 playbook).

## Принципы

**Один скрипт на клиента+лист.** У каждого клиента xlsx свой → координаты свои → extractor свой. Не пытаться сделать «универсальный» extractor — теряется детерминированность.

**Координаты захардкожены.** В скрипте словарь `METRIC_REGISTRY` вида `metric_id → {row, col, label, ...}`. Не вычисляются на лету, не генерируются LLM.

**Не генерирует код на лету.** Если структура xlsx меняется (CEO добавил колонку) — правится `METRIC_REGISTRY`, не сам алгоритм. На-лету-генерация = недетерминированность + шум в контексте агента.

**Stdout молчит.** В stdout — только короткий статус (`OK: wrote N metrics to <path>` или `FAIL: <reason>`). Дамп результатов в stdout = шум в контексте AI-агента и потеря детерминированности. Результат — всегда в JSON-файл (`metrics/_runs/<timestamp>_<question_id>.json` или аналогичный путь).

**Статусы вместо null.** Каждой метрике в JSON — `status`: `ok | div0 | missing | error`. Не подставлять `0` или `null` без статуса — это убивает дальнейшую классификацию (red/win/ok/blocked).

**CLI через argparse.** Принимает `--metrics m1,m2,m3` (или `--okr okr1`), `--period`, `--out`. Параметры явные, без скрытой магии.

## Как обновлять

- Изменилась схема xlsx у клиента (новая колонка, переименован лист) → правится `METRIC_REGISTRY` + проверяется на тест-прогоне.
- Появилась новая метрика → паспорт в `../<domain>.md` + строка в `METRIC_REGISTRY`.
- Скрипт версионируется через git вместе с остальными артефактами клиента.

## Связи

- [`../source/README.md`](../source/README.md) — правила работы с xlsx-источниками
- [`../template-domain.md`](../template-domain.md) — `routes[].extractor` ссылается сюда
- [`../../../skills/metrics-analysis/orchestrator-metrics.md`](../../../skills/metrics-analysis/orchestrator-metrics.md) Шаг 2 Режим А — как агент дёргает extractor
- [`../../../methodology/metrics/rollout.md`](../../../methodology/metrics/rollout.md) шаг 6 — полные правила написания
