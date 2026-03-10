---
title: "Последовательность создания Hook"
updated: 2026-03-02
verified: false
---

# Создание Hook — пошаговая инструкция

> **Статус: требует верификации и дистилляции.**
> Этот файл — черновик. Шаг 2 отправляет читать knowledge/coding/claude-code.md и skill-activation.md. Нужна дистилляция: выжимка по механике hooks (формат, события, settings.json) прямо в этот файл. Также формат hooks не верифицирован через актуальную документацию.
>
> **Что нужно сделать:** в отдельной сессии пройти документацию по hooks (knowledge/ + context7), дистиллировать выжимку в этот файл.

Hook — автореакция на событие (до/после действия). Выполняется автоматически, без участия человека. Используй когда нужна проверка, валидация или автоматическое действие при каждом срабатывании триггера.

---

## Шаг 1. Понять потребность

Разговор с Виктором: какое событие должно вызывать автоматическое действие? Что на входе (какой event)? Что на выходе (что делает hook)?

**Критерий:** можешь сформулировать: "При событии X автоматически делать Y".

---

## Шаг 2. Изучить knowledge/ и docs

1. `knowledge/coding/claude-code.md` — раздел про hooks: формат, типы событий, ограничения
2. `knowledge/skills/skill-activation.md` — может быть полезно для понимания механики триггеров
3. Проверь через context7 (`/anthropics/claude-code`): актуальный формат hooks, доступные события, настройка в settings.json

**Критерий:** знаешь формат, доступные events, ограничения.

---

## Шаг 3. Проверить конфликты

Просканируй `.claude/hooks/` — нет ли уже hook на это же событие? Проверь `settings.json` на существующие hooks.

**Критерий:** конфликтов нет.

---

## Шаг 4. Спроектировать

Определи: имя, событие-триггер, что делает, что проверяет, как обрабатывает ошибки.

**Покажи Виктору. Получи одобрение.**

---

## Шаг 5. Построить

Создай файл в `.claude/hooks/`. Добавь настройку в `settings.json` если нужно.

Проверь:
- [ ] Hook не блокирует основной workflow при ошибке
- [ ] Логирование понятное (что произошло, что сделано)
- [ ] Не конфликтует с существующими hooks

---

## Шаг 6. Валидировать

Запусти действие, которое должно триггернуть hook. Проверь что сработал правильно. Проверь edge cases (что если событие не то? что если ошибка?).

---

## Заметки по событиям

### Stop hook

**Не подходит для закрытия сессии.** Stop hook срабатывает на каждый ответ Claude (каждый API round-trip), а не при завершении сессии. Закрытие окна IDE не триггерит никакой hook — процесс просто завершается.

Три типа: shell command, prompt-based, agent-based. Exit code управляет поведением: 0 = разрешить остановку, 2 = заблокировать. Поле `stop_hook_active` предотвращает бесконечные циклы.

**Ограничение:** Stop hook не срабатывает пока висит permission prompt (Yes/No на Edit, Write, и т.д.). Permission prompt блокирует весь pipeline — hook дождётся только после того как пользователь ответит и все tool calls завершатся.

---

## Верифицированная механика (2026-03-10)

Проверено экспериментально на реальном транскрипте текущей сессии.

### Порядок выполнения

1. Claude генерирует ВЕСЬ ответ целиком (текст + tool_use блоки) за один API call
2. Ответ записывается в транскрипт как одна JSONL-запись
3. Tool calls выполняются последовательно: PreToolUse → permission check → выполнение → PostToolUse
4. После завершения ВСЕХ tool calls — срабатывает Stop hook

### Транскрипт (transcript.jsonl)

Формат записей:
- `"type": "user"` — сообщение пользователя, `message.content` — массив блоков
- `"type": "assistant"` — ответ Claude, `message.content` — массив блоков (`text`, `tool_use`)
- Другие типы: `progress`, `system`, `queue-operation`, `file-history-snapshot` — служебные

### Что видит каждый hook в транскрипте

| Hook | Текущий user msg | Текущий assistant msg |
|------|-----------------|----------------------|
| PreToolUse | **НЕТ** | **НЕТ** |
| Stop | Да | Да |

**Критично:** PreToolUse НЕ видит текущий ход. Транскрипт на момент PreToolUse содержит только предыдущие ходы. Это делает невозможным ловить паттерн "содержательный текст + tool call в одном ходе" через PreToolUse.

### Доступные события

`SessionStart`, `InstructionsLoaded`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `Notification`, `SubagentStart`, `SubagentStop`, `Stop`, `TeammateIdle`, `TaskCompleted`, `ConfigChange`, `WorktreeCreate`, `WorktreeRemove`, `PreCompact`, `SessionEnd`.

### Hook input (общие поля)

```json
{
  "session_id": "...",
  "transcript_path": "~/.claude/projects/.../session-id.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "PreToolUse|Stop|...",
  "tool_name": "Bash|Edit|...",      // только для PreToolUse/PostToolUse
  "tool_input": {},                   // только для PreToolUse/PostToolUse
  "stop_hook_active": true|false      // только для Stop
}
```

### Hook output

**Stop hook:** JSON на stdout: `{"decision": "block", "reason": "..."}`. Exit 0.
**PreToolUse:** JSON на stdout: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow|deny|ask", "permissionDecisionReason": "..."}}`. Exit 0. Или exit 2 + stderr для простого deny.
