---
title: "Spec-Driven Development — спецификация как источник истины в эпоху AI-кодинга"
source: "multiple (см. Источники) + industry research 2026-07-17"
source_type: research
status: processed
added: 2026-02-21
updated: 2026-07-18
review_by: 2026-10-18
tags: [ai-coding, methodology, spec-driven, sdd, specification, agents, engineering, contract-testing, agent-contracts]
publish: false
version: 3
---

# Spec-Driven Development

## Кратко

Spec-Driven Development (SDD) — парадигма, в которой спецификация (не код) является главным артефактом. Код — производный результат, генерируемый по спецификации. Академический первоисточник: Ostroff & Paige, XP 2004 — синтез TDD и Design by Contract. AI-ренессанс с 2025: vibe coding обнажил проблему (AI плохо угадывает намерения), спецификация решает её. Инструменты: GitHub Spec Kit, Amazon Kiro, Tessl, OpenSpec, BMAD. Четыре фазы: Specify → Plan → Tasks → Implement. К 2026 индустрия реально работает только на уровне **spec-first** — spec-as-source (Tessl) остаётся нишевой ставкой. Для контрактов между узлами графа (не только «спека для фичи») актуальны schema-first-подход и академическая рамка Agent Contracts.

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

**OpenSpec / BMAD / GSD** — сравнительный ландшафт 2026 ([Reenbit](https://reenbit.com/bmad-vs-spec-kit-vs-openspec-choosing-your-spec-driven-ai-framework/), [dev.to](https://dev.to/willtorber/spec-kit-vs-bmad-vs-openspec-choosing-an-sdd-framework-in-2026-d3j)): **OpenSpec** сильнее всего на brownfield и change-approval (спецификация изменения поверх существующей системы, не с нуля); **BMAD** — full-lifecycle с встроенным adversarial reviewer, но дорогой вход и рассчитан на enterprise; **GSD** — облегчённый вариант для соло/малой команды. Устоявшийся консенсус выбора: solo/малая команда → GSD или OpenSpec, мультикомандный enterprise → BMAD или полный Spec Kit.

---

## Контракты узлов: schema-first и Agent Contracts

Отдельная ветка SDD — не спека фичи, а контракт узла в графе агентных пайплайнов ([tianpan.co](https://tianpan.co/blog/2026-04-20-contract-testing-ai-pipelines)):

- Сбои агентных пайплайнов чаще происходят из-за **schema drift**, чем из-за качества модели — «контракт существует только в коде, который парсит выход» означает тихие отказы при малейшем изменении формата.
- Схема выхода фиксируется **в общем месте до написания промпта** (JSON Schema / Pydantic / Zod), а не выводится из промпта постфактум.
- Для LLM-выходов проверяются **структурные гарантии, не точное совпадение значений**: поля присутствуют, типы верны, ограничения соблюдены.
- **Consumer-driven contract testing**: даунстрим-узел декларирует, что ему нужно от входа; апстрим-узел проверяется, что отдаёт ровно это. Provider-тесты гоняют несколько (5–10) сэмплов — статистическую проверку, не единичный прогон.
- `schema_version` (и `prompt_version`) — обязательное поле в каждом артефакте; изменение схемы = breaking change с инкрементом версии и обязательным обновлением консюмера до деплоя.
- Constrained decoding (structured outputs у провайдеров) превращает схему из «просьбы в промпте» в жёсткую гарантию на уровне генерации, а не постобработки.

**Agent Contracts** ([arXiv 2601.08815](https://arxiv.org/html/2601.08815v1)) — академическая формализация контракта именно для автономного узла: `C = (I, O, S, R, T, Φ, Ψ)` — Inputs (схема + валидация), Outputs (схема + пороги качества), Skills (разрешённые способности узла), Resources (бюджеты — токены/вызовы/итерации/стоимость), Temporal (TTL), Φ Success criteria (измеримые, взвешенные критерии успеха), Ψ Termination (события остановки независимо от прогресса задачи). При делегации дочерним узлам действует правило: сумма бюджетов детей ≤ бюджет родителя. Заявленные результаты (исследовательская работа, не готовый продукт): до 90% экономии токенов и в 525 раз меньшая дисперсия результата в итеративных циклах при жёстком контрактном ограничении по сравнению с неограниченным циклом. Ценность рамки для практики — не готовый фреймворк, а полный словарь полей: чек-лист, по которому проверять, что спека узла ничего не забыла.

Это дополняет более общий вопрос «граф детерминированного кода vs автономный агент внутри узла» (Anthropic «Building Effective Agents», 12-factor-agents Factor 8 «own your control flow») — паттерны выбора между workflow-first и agent-first в целом → [../agents/workflow-automation.md](../agents/workflow-automation.md), [../agents/!agents.md](../agents/!agents.md).

---

## Формат и размер спеки

Независимо от инструмента, практики 2026 сходятся на конкретных числах и структуре ([Addy Osmani](https://addyosmani.com/blog/good-spec/), [Joshua McDonald](https://joshmcdonald.medium.com/running-a-small-team-on-a-big-project-spec-driven-development-with-claude-code-9a1b97f58551), [Augment Code](https://www.augmentcode.com/guides/ai-spec-template)):

- **Размер:** для отдельной задачи — 10–30 строк (Osmani; меньше 10 — теряются ограничения, больше 50 — переспецификация реализации, ~5–10 минут написания). Для фичи (McDonald) — до 4 страниц; длиннее означает, что это несколько спек, а не одна.
- **«Curse of instructions»:** качество исполнения агентом падает с ростом числа директив в спеке — агенту нужно кормить только релевантные секции, а не весь документ целиком.
- **Структура, которая работает:** контекст/проблема → **data contracts до описания поведения** («форма данных ограничивает поведение, а не наоборот» — McDonald) → поведение по тестируемым подсекциям → **обязательные failure modes** (невалидный вход, недоступный сервис, частичный сбой) → явный out-of-scope (агенты достраивают невысказанные требования и ломают рабочее) → границы трёх уровней: always do / ask first / never touch (Osmani).
- **Acceptance criteria:** бинарные, тестируемые, по одному аспекту на критерий, machine-verifiable с числовыми порогами. Декларативные требования («что» + ограничения) дают лучшее поведение агента, чем прескриптивные шаги «как».
- **PLANS.md** ([OpenAI Cookbook](https://developers.openai.com/cookbook/articles/codex_exec_plans)) — паттерн для многочасовой автономной работы: живой документ = спека + чекпоинты. Секции: Purpose (наблюдаемые исходы + как проверить), Progress (чеклист с таймстемпами, обновляется на каждой остановке), Surprises & Discoveries, Decision Log, Concrete Steps (точные команды и ожидаемый вывод). Критерии — наблюдаемое поведение («GET /health возвращает 200»), не внутренняя реализация. Спека + код должны быть самодостаточны для человека без внешнего контекста (self-containment).

---

## Кейс малой команды: 4 инженера + Claude Code

Наиболее близкий к команде из 1–2 человек задокументированный кейс ([Joshua McDonald](https://joshmcdonald.medium.com/running-a-small-team-on-a-big-project-spec-driven-development-with-claude-code-9a1b97f58551)): 4 инженера, 14 фич за квартал, 2–3x throughput за год без роста штата.

- **Три уровня работ**: vibe coding (мелочь, без спеки) / SDD (обычная фича) / design-driven parallelism (мультиагентная работа на крупную фичу).
- **5 скиллов**: `/spec-new` (из шаблона + регистрация в `specs/INDEX.md`), `/spec-review` (аудит двусмысленностей отдельным субагентом — сама спека при этом не правится), `/spec-decompose` (разбивка на 5–10 мини-спек), `/spec-implement` (исполнение в изолированном worktree), `/spec-verify` (проверка покрытия acceptance criteria тестами).
- **Детерминизм — через hooks, не через промпты**: spec gate (PreToolUse блокирует запись в код без активной спеки), test runner (PostToolUse), completion check (Stop-хук, дешёвый вызов «закончил ли»), session-start loader. Обоснование: «Skills — это руководство, которое модель может проигнорировать на любом ходу. Hooks выполняются детерминированным путём, который модель не видит и не может переписать».
- **4-слойное ревью**, важнейший слой — spec-aware review: сверка результата не «хорош ли он вообще», а именно с текстом спеки. Ловит самый дорогой класс дефектов — «реализация технически корректна, проходит тесты и тихо делает не то, что описала спека» (faithful-but-wrong).
- **Декомпозиция на мини-спеки не автоматизируется**: ~45 минут ручной работы с coupling review перед стартом; итоговое распределение труда — примерно 60% агентам, 40% человеку.
- **Staged adoption**: не ставить весь процесс сразу — начать с CLAUDE.md, добавлять по одному скиллу в ответ на реальный сбой, hooks — последними.

---

## Критика и ограничения

Böckeler (на martinfowler.com) провела детальный анализ трёх инструментов:

- **Overkill для малых задач.** Kiro превратила фикс бага в 4 user stories с 16 acceptance criteria. Spec Kit для задачи на 3-5 SP создал столько markdown, что ревью дольше прямой реализации
- **Агент не всегда следует спецификации** даже с большими контекстными окнами — может проигнорировать часть инструкций или следовать слишком буквально
- **Brownfield-проблема.** Инструменты лучше работают с greenfield. Встраивание SDD в существующую кодовую базу — нерешённая задача
- **Нет гибкости по масштабу.** Нужны разные workflow для однострочного фикса и новой подсистемы. Текущие инструменты этого не делают
- **"Waterfall?"** — SDD-сообщество: спецификации итеративны и эволюционируют, не каменные скрижали

**Spec drift — главная нерешённая проблема.** Даже при живой спеке она расходится с реализацией по ходу правок: «мельчайшая фича требует сложной манипуляции спекой», регенерация из изменённой спеки недетерминирована, практики бросают синхронизацию, и спека с кодом «дрейфуют до дублей и противоречий» ([HN «The Waterfall Strikes Back»](https://news.ycombinator.com/item?id=45935763)). Подходы к смягчению: **bidirectional sync** — агент обновляет спеку в том же коммите, человек ревьюит только contract-level изменения ([arXiv 2606.27045](https://arxiv.org/html/2606.27045v1)); «living specs» вместо статичных документов. Для малой команды дешевле не спец-тулинг, а простое правило: спека обновляется тем же PR/коммитом, что и код, плюс периодический аудит.

---

## Связанные файлы

- [ai-dev-practices.md](ai-dev-practices.md) — синтез 3 принципов проектирования среды для AI-разработки (SDD = принцип 1 "Spec First")
- [engineering-harness.md](engineering-harness.md) — Harness Engineering (комплементарный подход)
- [testing.md](testing.md) — тестирование AI-generated кода. SDD и тестирование пересекаются: specs → acceptance criteria → tests
- [../agents/workflow-automation.md](../agents/workflow-automation.md) — workflow-first vs agent-first: более общая рамка для «граф vs автономный агент», за пределами спек конкретного узла
- [../evals/eval-tooling.md](../evals/eval-tooling.md), [../evals/!evals.md](../evals/!evals.md) — prompts-as-code и eval-гейты в CI дополняют SDD-цикл проверкой качества, не только формы
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
- HN — "The Waterfall Strikes Back" (критика SDD, спека-код drift). [HN](https://news.ycombinator.com/item?id=45935763)

### Контракты, форматы спек и малые команды (ресерч 2026-07-17)

- Reenbit — "BMAD vs Spec Kit vs OpenSpec". [Reenbit](https://reenbit.com/bmad-vs-spec-kit-vs-openspec-choosing-your-spec-driven-ai-framework/)
- dev.to (Will Torber) — "Spec Kit vs BMAD vs OpenSpec". [dev.to](https://dev.to/willtorber/spec-kit-vs-bmad-vs-openspec-choosing-an-sdd-framework-in-2026-d3j)
- tianpan.co — "Contract testing for AI pipelines". [tianpan.co](https://tianpan.co/blog/2026-04-20-contract-testing-ai-pipelines)
- arXiv 2601.08815 — "Agent Contracts" (формализация I/O/S/R/T/Φ/Ψ). [arXiv](https://arxiv.org/html/2601.08815v1)
- arXiv 2606.27045 — "Spec Growth Engine" (bidirectional sync против spec drift). [arXiv](https://arxiv.org/html/2606.27045v1)
- Addy Osmani — "How to write a good spec for AI agents". [Osmani](https://addyosmani.com/blog/good-spec/)
- Augment Code — "AI spec template". [Augment](https://www.augmentcode.com/guides/ai-spec-template)
- OpenAI Cookbook — "PLANS.md для многочасовой автономии агентов Codex". [OpenAI Cookbook](https://developers.openai.com/cookbook/articles/codex_exec_plans)
- Joshua McDonald — "Running a small team on a big project: SDD with Claude Code" (кейс 4 инженера, 2–3x throughput). [Medium](https://joshmcdonald.medium.com/running-a-small-team-on-a-big-project-spec-driven-development-with-claude-code-9a1b97f58551)
