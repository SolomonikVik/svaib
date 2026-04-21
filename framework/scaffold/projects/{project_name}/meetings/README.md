# meetings/ — встречи проекта

Встречи по этому проекту: рабочие сессии команды, синки с заказчиком, ретроспективы по вехам. Кросс-проектные встречи — в `projects/meetings/` (если развёрнут) или в `04_management/meetings/`.

**Когда сюда.** По правилу наименьшей общей родительской папки ([../../README.md](../../README.md)). Встреча охватывает только этот проект → сюда. Встреча с участниками из других проектов или подразделений — смотри папку общего родителя.

## Что лежит

- `YYYY-MM-DD_{topic}_summary.md` — выжимки L1 (создаёт orchestrator-meeting)
- `archive/` — транскрипты после обработки (`YYYY-MM-DD_{topic}_transcript.md`)

## Как обрабатывать

Скилл [orchestrator-meeting.md](../../../../skills/meeting-analysis/orchestrator-meeting.md). Вызывает L1 (выжимка) и L2 (обновление файлов проекта + Telegram). Руководитель подтверждает перед применением.

## Маршрутизация обновлений

Обновления маршрутизируются через [L2-procedure-scaffold-update.md](../../../../skills/meeting-analysis/L2-procedure-scaffold-update.md) в файлы проекта (01_overview / 02_active / 02_backlog / 03_progress / 04_decisions).

> **Термины** (`L1`, `L2`, `summary`, `transcript`, `orchestrator-meeting`) и сам процесс обработки описаны в скилле `meeting-analysis` — это часть фреймворка, не часть шаблона проекта. Здесь — только правила хранения протоколов внутри папки.
