---
title: "Автономный режим — полный доступ для ночной работы"
updated: 2026-03-07
---

# Автономный режим

Когда Виктор уходит и даёт задачу на автономную работу — переключить permissions одной операцией.

## Включить (полный доступ)

Заменить блок `permissions` в `.claude/settings.json` на:

```json
"permissions": {
  "allow": [
    "Read", "Write", "Edit",
    "Bash(*)"
  ],
  "ask": [
    "Bash(git push*)",
    "Bash(git reset --hard*)"
  ]
}
```

## Выключить (стандартный режим)

Вернуть блок `permissions` в `.claude/settings.json` к:

```json
"permissions": {
  "allow": [
    "Bash(git *)",
    "Bash(ls *)", "Bash(find *)",
    "Bash(mkdir *)", "Bash(mv *)", "Bash(cp *)",
    "Bash(npm *)", "Bash(npx *)",
    "Bash(python3 *)",
    "Bash(echo *)", "Bash(cat *)",
    "Bash(curl *)", "Bash(which *)",
    "Bash(cd *)", "Bash(pwd)", "Bash(date *)",
    "Bash(chmod *)", "Bash(touch *)",
    "Bash(gh *)",
    "Bash(uv run *)",
    "Bash(NODE_PATH=* node *)",
    "Bash(node *)",
    "Bash(soffice *)",
    "Bash(pdftoppm *)",
    "Bash(open *)"
  ],
  "ask": [
    "Bash(git push*)",
    "Bash(git reset*)",
    "Bash(git checkout -- *)",
    "Bash(rm *)"
  ]
}
```

## Важно

- Блок `hooks` в settings.json НЕ трогать — он остаётся одинаковым в обоих режимах
- После отката проверить: `Read .claude/settings.json`
- `git push` и `git reset --hard` всегда требуют подтверждения в обоих режимах
