---
title: "Операционный слой arscontexta: три хука покрывают цикл orient → validate → persist"
source: "https://github.com/agenticnotetaking/arscontexta"
source_type: research
status: processed
added: 2026-03-06
updated: 2026-03-06
review_by: 2026-06-06
tags: [skill-graph, arscontexta, hooks, session-orient, write-validate]
publish: false
version: 1
---

# Hooks и Sessions — операционный слой arscontexta

## Кратко

Три хука в hooks.json покрывают полный операционный цикл: session-orient (при старте — инжекция контекста), write-validate (при записи — проверка YAML), auto-commit (при записи — сохранение). Хуки — enforcement, не intelligence: проверяют и сигнализируют, не принимают решения.

## hooks.json — полная конфигурация

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/session-orient.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/write-validate.sh",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/auto-commit.sh",
            "timeout": 5,
            "async": true
          }
        ]
      }
    ]
  }
}
```

## session-orient.sh — точный порядок инжекции

Верифицировано по коду (2026-03-05). Порядок принципиален — goals первым:

1. **Session tracking** — сохраняет session_id в ops/sessions/current.json, архивирует предыдущую
2. **Goals** — self/goals.md (или ops/goals.md если self-space выключен). Первым — агент сначала знает ЗАЧЕМ он здесь
3. **Identity** — self/identity.md + self/methodology.md. Потом — КТО он
4. **Methodology learnings** — 5 последних файлов из ops/methodology/ (только заголовки). Что узнал недавно
5. **Previous session** — ops/sessions/current.json. Чем закончил прошлый раз
6. **Workspace tree** — `tree -L 3 -P '*.md'`. ЧТО есть в пространстве
7. **Maintenance signals** (condition-based):
   - observations ≥ 10 → "suggest /rethink"
   - tensions ≥ 5 → "suggest /rethink"
   - sessions ≥ 5 → "suggest /remember --mine-sessions"
   - inbox ≥ 3 → "suggest /reduce"
   - methodology staleness ≥ 30 дней → "suggest update"

Timeout: 10 секунд.

## write-validate.sh — что проверяет

PostToolUse hook на Write. Проверяет файлы в notes/:

- Наличие YAML frontmatter (открывающие и закрывающие `---`)
- Наличие поля `description`
- Наличие поля `topics`

Non-blocking: предупреждает через additionalContext, не блокирует запись.

## auto-commit.sh

Async hook — автокоммит после каждой записи в vault. Не блокирует работу агента.

## Связанные файлы

- [architecture.md](architecture.md) — архитектурный контекст хуков (Three-Space, Progressive Disclosure)
- [kernel-primitives.md](kernel-primitives.md) — примитивы `session-rhythm` и `session-capture`, которые хуки реализуют
- [arscontexta-file-examples.md](arscontexta-file-examples.md) — как выглядят goals.md и identity.md, которые session-orient инжектирует
