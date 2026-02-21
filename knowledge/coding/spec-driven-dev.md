---
title: "Spec-Driven Development — спецификация как источник истины в эпоху AI-кодинга"
source: "multiple (см. Источники)"
source_type: research
status: processed
added: 2026-02-21
updated: 2026-02-21
review_by: 2026-05-21
tags: [ai-coding, methodology, spec-driven, sdd, specification, agents, engineering]
publish: false
version: 1
---

# Spec-Driven Development

## Кратко

Spec-Driven Development (SDD) — парадигма, в которой спецификация (не код) является главным артефактом. Код — производный результат, генерируемый по спецификации. Академический первоисточник: Ostroff & Paige, XP 2004 — синтез TDD и Design by Contract. AI-ренессанс с 2025: vibe coding обнажил проблему (AI плохо угадывает намерения), спецификация решает её. Инструменты: GitHub Spec Kit, Amazon Kiro, Tessl. Четыре фазы: Specify → Plan → Tasks → Implement.

---

## Первоисточник термина

Jonathan S. Ostroff и Richard F. Paige — "Agile Specification-Driven Development" (XP 2004, Garmisch-Partenkirchen). Ключевой тезис: TDD и Design by Contract — не конкуренты, а комплементарные типы спецификаций. SDD объединяет оба: тесты проверяют контракты, контракты расширяют покрытие тестов. [PDF](https://www.eecs.yorku.ca/~jonathan/publications/2004/xp2004.pdf)

Bertrand Meyer продолжил идею в "Contract-Driven Development" (FASE 2007) с автоматической генерацией тестов из контрактов. [Springer](https://link.springer.com/chapter/10.1007/978-3-540-71289-3_2)

## AI-ренессанс (2025)

LLM-агенты сделали SDD практически применимым. Спецификация перестала быть "документом, который никто не читает" — теперь её читает агент и генерирует код.

- **Февраль 2025:** Андрей Карпати вводит термин "vibe coding" — обозначая проблему расплывчатых промптов
- **Сентябрь 2025:** GitHub выпускает Spec Kit — open-source тулкит для SDD
- **Ноябрь 2025:** Amazon запускает Kiro — IDE со встроенным SDD-workflow

---

## Три уровня зрелости

Birgitta Böckeler (Thoughtworks / Martin Fowler blog):

**Spec-First** — спецификация пишется перед кодом для конкретной задачи. После реализации может быть отброшена. Базовое улучшение над vibe coding.

**Spec-Anchored** — спецификация как живой документ на протяжении жизненного цикла фичи. Используется для эволюции и поддержки.

**Spec-as-Source** — радикальный подход: спецификация — единственный поддерживаемый артефакт, код перегенерируется из неё. Человек никогда не редактирует код напрямую.

---

## Четырёхфазный workflow

Все основные инструменты сходятся:

1. **Specify** — что и зачем: user stories, acceptance criteria, ограничения, явные запреты ("что НЕ делать")
2. **Plan** — как на верхнем уровне: архитектура, стек, компоненты, паттерны
3. **Tasks** — декомпозиция: атомарные задачи с зависимостями и критериями готовности
4. **Implement** — исполнение и верификация: генерация кода → проверка против спецификации → human review

---

## Инструменты

**GitHub Spec Kit** (сентябрь 2025) — open-source CLI, самый популярный инструмент. Slash-команды: `/speckit.constitution` → `.specify` → `.plan` → `.tasks` → `.implement`. Агент-агностичный (Claude Code, Gemini CLI, Cursor, Copilot). `constitution.md` — неизменяемые принципы проекта (аналог CLAUDE.md). [GitHub](https://github.com/github/spec-kit)

**Amazon Kiro** (ноябрь 2025) — IDE со встроенным SDD: Requirements → Design → Tasks → Implement. "Steering" как memory bank (product.md, structure.md, tech.md). [kiro.dev](https://kiro.dev)

**Tessl** (сентябрь 2025) — радикальный spec-as-source. Спецификация — единственный артефакт, код полностью генерируется и перегенерируется. Человек работает только со спецификацией.

---

## Критика и ограничения

Böckeler (на martinfowler.com) провела детальный анализ трёх инструментов:

- **Overkill для малых задач.** Kiro превратила фикс бага в 4 user stories с 16 acceptance criteria. Spec Kit для задачи на 3-5 SP создал столько markdown, что ревью дольше прямой реализации
- **Агент не всегда следует спецификации** даже с большими контекстными окнами — может проигнорировать часть инструкций или следовать слишком буквально
- **Brownfield-проблема.** Инструменты лучше работают с greenfield. Встраивание SDD в существующую кодовую базу — нерешённая задача
- **Нет гибкости по масштабу.** Нужны разные workflow для однострочного фикса и новой подсистемы. Текущие инструменты этого не делают
- **"Waterfall?"** — SDD-сообщество: спецификации итеративны и эволюционируют, не каменные скрижали

---

## Связанные файлы

- [ai-dev-practices.md](ai-dev-practices.md) — синтез 3 принципов проектирования среды для AI-разработки (SDD = принцип 1 "Spec First")
- [engineering-harness.md](engineering-harness.md) — Harness Engineering (комплементарный подход)
- [!coding.md](!coding.md) — сводка по AI-кодингу

## Источники

### Академические

- Ostroff, Paige — "Agile Specification-Driven Development" (XP 2004). [PDF](https://www.eecs.yorku.ca/~jonathan/publications/2004/xp2004.pdf) — **первоисточник термина**
- Meyer — "Contract-Driven Development" (FASE 2007). [Springer](https://link.springer.com/chapter/10.1007/978-3-540-71289-3_2)
- Panaversity — "Spec-Driven Development with Claude Code" (февраль 2026). [arXiv](https://arxiv.org/html/2602.00180v1)

### Индустриальные

- ThoughtWorks (Liu Shangqi) — "Spec-driven development: Unpacking one of 2025's key new AI-assisted engineering practices" (декабрь 2025). [ThoughtWorks](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices)
- Böckeler (Martin Fowler blog) — "Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl" (октябрь 2025). [martinfowler.com](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- InfoQ — "Spec-Driven Development: When Architecture Becomes Executable" (январь 2026). [InfoQ](https://www.infoq.com/articles/spec-driven-development/)
- Microsoft (Den Delimarsky) — "Diving Into Spec-Driven Development With GitHub Spec Kit" (сентябрь 2025). [Microsoft](https://developer.microsoft.com/blog/spec-driven-development-spec-kit)

### Практические руководства

- Zencoder — "A Practical Guide to Spec-Driven Development". [Zencoder](https://docs.zencoder.ai/user-guides/tutorials/spec-driven-development-guide)
- Scalable Path — "Beyond Vibe-Coding: A Practical Guide" (ноябрь 2025). [Scalable Path](https://www.scalablepath.com/machine-learning/spec-driven-development-guide)
- Scott Logic (Colin Eberhardt) — "Putting Spec Kit Through Its Paces: Radical Idea or Reinvented Waterfall?" (ноябрь 2025). [Scott Logic](https://blog.scottlogic.com/2025/11/26/putting-spec-kit-through-its-paces-radical-idea-or-reinvented-waterfall.html)
