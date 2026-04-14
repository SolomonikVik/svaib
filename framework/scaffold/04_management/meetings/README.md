# meetings/ — встречи уровня 04_management/

Встречи, охватывающие верхушку компании: стратсессии всех руководителей направлений, кросс-функциональные встречи 2+ высокоуровневых направлений без общей папки-группировки между ними.

**Когда сюда.** По правилу наименьшей общей родительской папки ([04_management/README.md](../README.md)). Встреча внутри одного подразделения/направления → `{org_node}/meetings/`, не сюда. Встреча дочерних узлов одной группировки → `{parent}/meetings/`.

**Вне scope.** Встречи, меняющие 02_strategy/ (vision, goal, plan, weekly_progress).

## Что лежит

- `YYYY-MM-DD_{topic}_summary.md` — выжимки L1 (создаёт orchestrator-meeting)
- `archive/` — транскрипты после обработки (`YYYY-MM-DD_{topic}_transcript.md`)

## Как обрабатывать

Скилл [orchestrator-meeting.md](../../../skills/meeting-analysis/orchestrator-meeting.md). Он вызывает L1 (entity extractor → выжимка) и L2 (обновление файлов проекта + Telegram-сводка). Руководитель подтверждает выжимку и обновления перед применением.

## Маршрутизация обновлений

Обновления из встречи НЕ дублируются — маршрутизируются по чеклисту [L2-procedure-scaffold-update.md](../../../skills/meeting-analysis/L2-procedure-scaffold-update.md) в файлы затронутых единиц (01_overview / 02_active / 03_progress / 04_decisions) и при необходимости в 02_strategy/06_decisions.md / 01_ceo/04_decisions.md.
