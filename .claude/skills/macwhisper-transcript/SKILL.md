---
name: macwhisper-transcript
description: "Extract transcript from MacWhisper SQLite into _transcript.md. Use when: 'подтяни транскрипт', 'вытащи транскрипт', 'pull transcript', 'что есть в MacWhisper', or meeting processing needs transcript."
---

# MacWhisper Transcript Extractor

Двухшаговый доступ к локальной базе MacWhisper (SQLite). **Сначала ищем → подтверждаем → извлекаем.** Ноль токенов в контексте — всё через bash.

## Скрипт

```
.claude/skills/macwhisper-transcript/scripts/macwhisper_transcript.sh
```

## Контракт работы

**Всегда два шага: `--list` → подтверждение → `--extract`. Никогда не прыгать в extract без list.**

### Шаг 1. Найти встречу (`--list`)

Любой запрос про встречу (по дате / теме / участнику) — сначала ищем через `--list`.

Фильтры комбинируются:

```bash
# дефолт — сегодня
bash ${CLAUDE_SKILL_DIR}/scripts/macwhisper_transcript.sh --list

# конкретная дата
bash ${CLAUDE_SKILL_DIR}/scripts/macwhisper_transcript.sh --list 2026-04-23
bash ${CLAUDE_SKILL_DIR}/scripts/macwhisper_transcript.sh --list --date 2026-04-23

# полнотекстовый поиск (FTS5 по fullText + aiSummary + userChosenTitle), без ограничения дат
bash ${CLAUDE_SKILL_DIR}/scripts/macwhisper_transcript.sh --list --search "дивиденды"

# по спикеру
bash ${CLAUDE_SKILL_DIR}/scripts/macwhisper_transcript.sh --list --speaker Ефим

# комбинация
bash ${CLAUDE_SKILL_DIR}/scripts/macwhisper_transcript.sh --list --date 2026-04-23 --speaker Ефим
```

Вывод — блок на каждую сессию:
```
─── <id_short>  │  <date HH:MM>  │  <duration> min  │  <lines> lines / <chars> chars
    title     : <userChosenTitle>
    aiTitle   : <aiTitle>
    summary   : <aiSummaryShort>
    app       : <Zoom/...>  (calendar: <matchedCalendarTitle если отличается>)
    speakers  : <имена>
```

Показываются только merged-сессии (с `userChosenTitle`), не удалённые. Сырые дорожки (app-audio, mic-audio до diarization) скрыты.

### Шаг 2. Подтверждение

Показываем кандидатов из `--list`. Фраза: «**предполагаю — эта (id_short)**».
- Если кандидат один — достаточно сообщения «беру эту», ждать подтверждения не обязательно.
- Если несколько — ждём выбор.

### Шаг 3. Извлечение (`--extract`)

Только по `id_short` (8 hex-символов из `--list`). Никакого поиска по названию.

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/macwhisper_transcript.sh --extract <id_short> /path/to/_transcript.md
```

В stdout — метаданные (id, date, duration, app, model, language, diarized, summary, speakers).
В файл — построчный транскрипт в формате `**Спикер** [MM:SS]: текст` (подряд идущие реплики одного спикера склеены).
