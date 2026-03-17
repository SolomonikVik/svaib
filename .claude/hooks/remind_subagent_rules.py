#!/usr/bin/env python3
"""
PreToolUse hook for Agent tool: remind the coordinator about subagent rules.

This hook does not configure the subagent itself. It injects a short checklist
into the coordinator's context right before Agent tool execution.

Source of truth: lab/subagent-rules.md (section "Правила координатора").
If coordinator-facing launch rules change there, update COORDINATOR_CHECKLIST
here too.
"""

import json
import sys


COORDINATOR_CHECKLIST = """\
Перед запуском субагента проверь 4 вещи:

1. Задача ограничена одним куском работы — без скрытой координации и без оркестрации вниз.
2. Если субагенту понадобится Bash, в prompt есть явная строка:
   "Use only simple, single bash commands - no &&, no ||, no pipes, no ;, no redirects."
3. Если нужен файл-результат, ты заранее создал папку и указал точный путь внутри _inbox/subagents/.
4. Ты запускаешь субагента в foreground и заберёшь результат через путь к артефакту, а не через перечитывание содержимого.

Источник: lab/subagent-rules.md\
"""


def main():
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, IOError):
        sys.exit(0)

    if hook_input.get("tool_name") != "Agent":
        sys.exit(0)

    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": COORDINATOR_CHECKLIST,
        }
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
