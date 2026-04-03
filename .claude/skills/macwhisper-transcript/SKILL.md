---
name: macwhisper-transcript
description: "Extract transcript from MacWhisper SQLite into _transcript.md. Use when: 'подтяни транскрипт', 'вытащи транскрипт', 'pull transcript', 'что есть в MacWhisper', or meeting processing needs transcript."
---

# MacWhisper Transcript Extractor

Вытаскивает транскрипт из локальной базы MacWhisper (SQLite) и кладёт в `_transcript.md` клиента. Ноль токенов в контексте — всё через bash.

## Скрипт

```
.claude/skills/macwhisper-transcript/scripts/macwhisper_transcript.sh
```

## Команды

### Показать сегодняшние сессии

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/macwhisper_transcript.sh --list
```

Выводит: название, AI-заголовок, время, длительность, AI summary.

### Показать сессии за дату

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/macwhisper_transcript.sh --list 2026-04-03
```

### Вытащить транскрипт в файл клиента

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/macwhisper_transcript.sh "Название сессии" clients/{name}/meetings/_transcript.md
```

Метаданные (спикеры, длительность, AI summary) выводятся в stdout — использовать для Шага 0 оркестратора.

## Связь с оркестратором

Этот скрипт заменяет ручной ввод на Шаге 0 orchestrator-client-meeting.md:
- **Кто** — из спикеров MacWhisper
- **О чём** — из AI summary
- **Когда** — из даты сессии
- **Транскрипт** — уже в `_transcript.md`
