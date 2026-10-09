---
title: "file-specs — спецификации канонических файлов"
updated: 2026-10-06
status: draft
---

# file-specs — спецификации канонических файлов

Перечень канонических файлов пространства и их спецификаций. Канонический файл — файл из этого перечня: у него есть имя, миссия и спецификация.

Перед записью в канонический файл агент читает [общий файл](00_general.md), затем спецификацию этого файла. Какую брать, видно по имени файла, а где имя меняется под предмет — по месту.

## Содержимое папки

- [00_general.md](00_general.md) — общий файл: что верно для любого канонического файла.
- [overview.md](overview.md) — `01_overview.md`, обзор узла.
- [active.md](active.md) — `02_active.md`, текущая работа.
- [backlog.md](backlog.md) — `03_backlog.md`, будущая работа.
- [progress.md](progress.md) — `04_progress.md`, хроника.
- [decisions.md](decisions.md) — `05_decisions.md`, журнал решений.
- [meeting-summary.md](meeting-summary.md) — `summary.md` в папке встречи, выжимка встречи: где она лежит; форму задаёт спецификация разбора встречи.
- [reference.md](reference.md) — `person.md`, `profile.md`, `architecture.md`, `setup.md`, `glossary.md`, `speech-aliases.md`: одна спецификация на шесть справочных файлов.
