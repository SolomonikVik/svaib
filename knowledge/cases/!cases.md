---
title: "Кейсы применения AI — сводка знаний"
status: processed
added: 2026-01-30
updated: 2026-09-09
review_by: 2026-05-21
tags: [cases, index, second-brain, skill-graph, coman-os, okr, enforcement]
publish: false
---

# Cases — Кейсы применения

## Кратко

Конкретные примеры использования AI: свои эксперименты, чужие истории успеха и неудач, разборы решений. Привязка теории к практике. Как компания X внедрила AI-ассистента, какие результаты получила, что пошло не так.

## Кейсы: Second Brain / Knowledge Systems

### arscontexta — Second Brain как Claude Code плагин

Heinrich (@arscontexta) построил Claude Code плагин, который через разговор генерирует персональную knowledge system. 249 связанных markdown-файлов (skill graph), three-space model (self/notes/ops), 6Rs processing pipeline. Движется в том же направлении: markdown, данные у пользователя, AI навигирует структуру. Подробный разбор: [arscontexta.md](arscontexta.md).

### CoMan OS — управленческая ОС и помощник руководителя в плагине

Максим О. построил трёхслойную архитектуру управления (Knowledge → Skills с механизмом согласования → AI-агенты) поверх причинной иерархии Advanced OKR, где каждый объект домена знает, какому Key Result служит. Публичная часть — поставка «Иван»: помощник руководителя двумя сборками, под Claude Code / Cowork и под Codex / ChatGPT Work, с 18 правилами поведения и обвязкой качества из 11 хуков. Продаётся не исполнительность, а сопротивление: возражение до старта, названная цена идеи, отказ соглашаться молча.

Переносимого в архитектуре мало — почти все рамки заимствованы (обратимость решений у Bezos, петля in/on/out из supervisory control, премортем у Klein, сикофантия из исследования Anthropic). Ценность — в доведении рамок до исполняемого кода с честно названной ценой каждого правила: [coman-os.md](coman-os.md), методология enforcement — [../skills/rule-enforcement.md](../skills/rule-enforcement.md).

Показательный разрыв кейса: доставка всех правил построена на `SessionStart`-хуке — единственном событии, которого в Cowork нет, при том что остальные плагинные хуки там работают. Поставка приезжает без правил, хотя обещает обратное.

## Связанные файлы

- [../context/skill-graphs/](../context/skill-graphs/) — Skill Graphs: архитектурный паттерн, на котором построен arscontexta
- [../plugins/!plugins.md](../plugins/!plugins.md) — Плагины Claude Code: формат, в котором доставляются обе системы, и разрыв канала Cowork
- [../skills/rule-enforcement.md](../skills/rule-enforcement.md) — методология enforcement, собранная из практики CoMan OS
