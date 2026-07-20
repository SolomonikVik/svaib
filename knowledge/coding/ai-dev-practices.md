---
title: "AI Development Practices — принципы проектирования среды для AI-разработки"
source: "multiple (см. Первоисточники) + industry research 2026-07-17"
source_type: article
status: processed
added: 2026-02-21
updated: 2026-07-18
review_by: 2026-10-18
tags: [ai-coding, methodology, best-practices, spec-driven, harness, delegation, engineering, review-bottleneck, cross-model-review, metr]
publish: false
version: 7
---

# AI Development Practices

## Кратко

Синтез принципов AI-first разработки из индустриальных источников: OpenAI, Anthropic, Mitchell Hashimoto, практики микро-команд (Boris Cherny, Simon Willison, Addy Osmani). Ключевой сдвиг: роль инженера — не "писать код", а "проектировать среду, в которой агенты пишут код надёжно". Три принципа проектирования среды: Spec First (ЧТО агент должен сделать), Context Architecture (ГДЕ агент работает и что знает), Harness Engineering (КАК среда контролирует качество). Практика 2026 добавляет устойчивый вывод: пропускная способность команды упирается в ревью, а не в число агентов — параллельность без градации ревью по риску съедает весь выигрыш.

---

## Ключевой сдвиг

> "Writing code" → "Designing the environment where agents write code reliably"

Не метафора. OpenAI за 5 месяцев написали ~1M строк кода через Codex, 0 строк вручную. Anthropic зафиксировали +67% merged PRs на инженера. Spotify сообщают, что лучшие разработчики не пишут код с декабря 2025.

Инженер становится архитектором среды: спецификации, правила, тесты, верификация. Код — побочный продукт правильно спроектированной среды.

---

## Принципы

### 1. Spec First — ЧТО агент должен сделать

**Суть:** Спецификация до кода. План в файл. Агент реализует по пунктам. После реализации — сверка с планом пункт за пунктом.

**Почему:** Без спецификации агент угадывает намерение. С хорошей спецификацией уверенный мидл (а современные модели — это мидл) справляется.

**Как:**
- Сгенерировать или написать спецификацию задачи (что делаем, какие модули затронуты, критерии готовности)
- Агент формирует план реализации, закрывает пробелы, задаёт вопросы
- Зафиксировать план в .md файл — ориентир для реализации и верификации
- Реализация = последовательное выполнение пунктов плана
- **Верификация** = сверка реализации с оригинальным планом по пунктам, отчёт по каждому

**Откуда:** OpenAI SDLC Planning phase, Hashimoto (шаг 2: планирование отдельно от исполнения)

**Правило №1 практика.** Boris Cherny (создатель Claude Code): не давать агенту писать код, пока письменный план не одобрен — «разделение планирования и исполнения — самое важное, что я делаю». Почти каждая сессия начинается в plan mode; план итерируется с моделью, затем правится инлайн-заметками в редакторе, и только после одобрения включается auto-accept — обычно с одного захода. Официальные best practices Anthropic смягчают правило для мелочи: если дифф описывается одним предложением — план можно пропустить, это оверхед.

**Детали:** [spec-driven-dev.md](spec-driven-dev.md) — SDD как парадигма, первоисточник (Ostroff/Paige 2004), инструменты, критика

### 2. Context Architecture — ГДЕ агент работает и что знает

**Суть:** Правильный контекст важнее мощной модели. Давай агенту карту, а не энциклопедию.

**Почему:** Контекст — scarce resource. Гигантский instruction file вытесняет задачу и код из контекстного окна.

**Как:**
- **Прогрев сверху-вниз:** архитектура → подсистемы → конкретный модуль. Не кидать агента сразу в баг 500-й строки
- **AGENTS.md / CLAUDE.md:** файлы с описанием архитектуры и правил проекта — постоянный контекст (Hashimoto, [Ghostty AGENTS.md](https://github.com/ghostty-org/ghostty/blob/ca07f8c3f775fe437d46722db80a755c2b6e6399/src/inspector/AGENTS.md))
- **Memory Bank** (Cline/Roo Code ecosystem): структурированная система markdown-файлов для сохранения контекста между сессиями. Популяризировано через Cline, адаптировано для Cursor, Amazon Kiro ("Steering")
- **Узкий фокус:** после общего понимания — сузить на конкретный модуль задачи
- **Документация как ToC:** оглавление + структурированная docs/, а не монолитная простыня

**Откуда:** Hashimoto (AGENTS.md), OpenAI ("give the agent a map, not a 1000-page manual"), Memory Bank (Cline community)

### 3. Harness Engineering — КАК среда контролирует качество

**Суть:** Среда, в которой агент не может ошибаться систематически. Два режима: реактивный (ошибка → правило) и проактивный (непрерывная гигиена кодовой базы).

**Почему:** Агент не учится между сессиями. Его "обучение" — это изменение среды вокруг него.

**Реактивный harness:**
- **Implicit prompting (AGENTS.md):** правила и запреты в текстовом файле. Каждая строка = предотвращённая ошибка
- **Programmed tools:** скрипты верификации, линтеры, structural tests. Агент может запустить и проверить себя
- **Verification tools:** тесты, linters, скриншоты, multi-agent review — всё это инструменты верификации, часть harness. Источники говорят о широкой "верификации", не только о тестах

**Проактивный harness (Garbage Collection):**
- "Golden principles" — механические, обязательные правила legibility, закодированные прямо в репо
- Примеры: "prefer shared utility packages over hand-rolled helpers", "не проверять данные YOLO-style — использовать typed SDKs"
- Фоновые Codex-задачи сканируют код, обновляют quality grades, открывают PR с рефакторингом
- Нарушения исправляются автоматически, без участия инженера

**Парадигма:** "Humans steer. Agents execute." (OpenAI)

**Критика:** Böckeler (ThoughtWorks) отмечает: OpenAI фокусируется на structural linters, мало говорит о functional/behavioral testing. Harness без behavioral tests рискует ловить только стилистические проблемы.

**Откуда:** Hashimoto (термин, 6-шаговый путь), OpenAI (масштабное применение, garbage collection). Böckeler: [martinfowler.com](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html)

**Детали:** [engineering-harness.md](engineering-harness.md)

---

## Практические заметки

**Скорость vs. осторожность.** В системе, где throughput агентов значительно превышает внимание человека, исправления дешевле ожидания: *"corrections are cheap, and waiting is expensive"* (OpenAI). Инвестируй в быстрые циклы обратной связи (тесты, CI), а не в длительные согласования перед запуском.

**Парадокс надзора и формирование навыков.** Эффективный надзор за AI требует навыков, которые атрофируются от чрезмерного делегирования (*"I worry much more about the oversight and supervision problem"* — инженер Anthropic). Частичный ответ — осознанно воспроизводить работу агента вручную для критичных областей: *"I literally did the work twice"* (Hashimoto). Навыки продолжают формироваться для задач, которые делаешь сам. Полного решения нет — открытая tension.

**Делегирование.** Не всё стоит делегировать. OpenAI использует фреймворк Delegate / Review / Own: механическое и повторяемое — delegate, фичи и рефакторинг — review, архитектура и security — own. Anthropic описывает характеристики задач для делегирования: легко проверяемое, self-contained, low-stakes, рутинное. Fully delegate можно только 0-20% работы, остальное требует активного надзора. End-of-Day Agents (Hashimoto) — тактика для задач, результат которых нужен на следующее утро: deep research, issue triage, прояснение unknowns → "тёплый старт" вместо холодного входа.

**Ревью — узкое место команды, не число агентов.** Пропускная способность упирается в ревью: норма середины 2026 — 4-8 параллельных worktrees на разработчика, выше — «bottleneck on review», не на возможности модели (Simon Willison: мержу одно значимое изменение за раз). Кризис объёма при массовом делегировании: код x4 при росте продуктивности ~12%, длительность ревью +441.5%, мержи без ревью +31.3%, AI-код несёт в 1.7 раза больше проблем, агентские PR в среднем на 51% больше человеческих — маленький дифф становится требованием к агенту, а не пожеланием (Addy Osmani, Agentic Code Review). Ревью по blast radius: низкий риск (конфиги, boilerplate) — линтер + беглый взгляд; высокий риск (платежи, auth) — типы + тесты + два разных AI-ревьюера + доменный эксперт-человек.

**Кросс-модельное ревью асимметрично.** Одно исследование (Cross-Model LLM Code Review, осторожно — одна работа): ревью Claude поднимало pass rate черновиков Codex с 71.6% до 89.7%, обратное направление ухудшало результат с 91.4% до 82.8% — сильная модель ревьюит, направление имеет значение. Из четырёх AI-ревью-инструментов в одном сравнении 93.4% находок ловились ровно одним инструментом — гетерогенность ревьюеров ценнее дублирования одного и того же. Ревьюеру-агенту нужно явно ограничивать периметр: «только gaps по корректности и заявленным требованиям, не стиль» — иначе он находит пробелы всегда и становится генератором over-engineering.

**Anti-slop.** Маленькие диффы — требование, не пожелание; CI-гейты (тесты, coverage, дубли хелперов) — неторгуемые; отдельно следить, когда агент переписывает assertions под сломанное поведение вместо починки кода (самый коварный slop); после двух неудачных поправок подряд — `/clear` и новый промпт, а не третья правка. Беклог как markdown в репо — паттерн Backlog.md: 1 задача = 1 файл (описание + acceptance criteria + DoD-чеклист) = 1 контекст-окно = 1 PR; диффы остаются читабельными, git — трекер без отдельной доски.

**Экономика мультиагентности.** Мультиагентная оркестрация стоит ~15x токенов одиночной сессии (данные Anthropic по своей research-системе); большинство команд уходит в multi-agent слишком рано. Для микро-команды достаточно двух паттернов — Writer/Reviewer (две сессии, свежий контекст ревьюера убирает bias к собственному коду) и Architect/Implementer (план итерируется отдельно, исполняют свежие инстансы); полноценный оркестратор оправдан для read-heavy исследований (параллельный сбор), не для конкурентных правок кода.

---

## Индустриальные данные

### OpenAI (февраль 2026)
- Пустой репо → ~1M строк за 5 месяцев через Codex
- 1500 PR, 0 строк написаны вручную
- Маленькая команда: в среднем 3.5 PR на инженера в день
- Оценка: 1/10 времени ручной разработки
- Сложность задач агентов удваивается каждые 7 месяцев
- Отчёт по внутреннему использованию Codex (данные к маю 2026): только 10.7% сотрудников ведут один воркфлоу за раз, 28.6% — пять и более параллельно; режим работы описан как «delegate, monitor, review, coordinate», не чат. 80.6% пользователей ставили задачи, эквивалентные более чем 30 минутам человеческой работы; топ-1% генерирует свыше 60 часов агентских прогонов в день

Источник: [Harness engineering](https://openai.com/index/harness-engineering/), [Building AI-Native Team](https://developers.openai.com/codex/guides/build-ai-native-engineering-team/), [The Shift to Agentic AI: Evidence from Codex (PDF)](https://cdn.openai.com/pdf/5d1e1489-21c0-43e4-9d42-f87efdbf0082/the-shift-to-agentic-ai-evidence-from-codex.pdf)

### METR (2025–2026)
- 2025: 16 опытных мейнтейнеров, 246 реальных задач в зрелых репозиториях (~1M+ LOC) — с AI на 19% медленнее; при этом до эксперимента разработчики ожидали ускорение +24%, после — были уверены, что получили +20% (самооценка ускорения врёт в обе стороны)
- 2026 update: точечные оценки развернулись к ускорению (~18% у исходной когорты), но METR прямо называет новые данные ненадёжными — разработчики, не готовые работать без AI, отсеивались из выборки; 30–50% участников признались, что прятали задачи, которые не хотели делать руками
- Устойчивый паттерн независимо от метода измерения: рутинные задачи ускоряются сильно (~46%), сложные — почти нет (<10%)
- Вывод: ускорение достаётся там, где задачи хорошо специфицированы, есть автоматическая верификация и ревью не стало узким горлом; условия METR-2025 (плохо специфицированные задачи в зрелом коде с неявным контекстом) — ровно обратный случай

Источник: [METR 2025](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/), [METR 2026 update](https://metr.org/blog/2026-02-24-uplift-update/)

### Anthropic (февраль 2026)
- Использование Claude: 28% → 60% рабочего времени за год
- Продуктивность: +20% → +50%
- +67% merged PRs на инженера в день
- 27% работы — задачи, которые вообще бы не делались без AI
- Автономность Claude Code: ~10 → ~21 последовательных действий (+116%)
- Бэкенд-инженеры стали "full-stack" благодаря AI

Источник: [How AI is transforming work at Anthropic](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic)

### Spotify (февраль 2026)
- Лучшие разработчики не пишут код с декабря 2025
- Используют Claude Code + внутренний инструмент Honk

Источник: [TechCrunch](https://techcrunch.com/2026/02/12/spotify-says-its-best-developers-havent-written-a-line-of-code-since-december-thanks-to-ai/)

---

## 7-фазная трансформация SDLC (OpenAI)

OpenAI описывает как AI меняет каждую фазу цикла разработки:

| Фаза | Агент делает | Инженер делает |
|------|-------------|----------------|
| **Planning** | Читает спеки, трейсит код, разбивает на подзадачи, оценивает сложность | Приоритизация, продуктовое направление, валидация |
| **Design** | Скаффолдинг, конвертация макетов в код, accessibility | Архитектурные паттерны, UX-флоу, альтернативы |
| **Build** | Генерация фич end-to-end (модели, API, UI, тесты, доки) | Уточнение поведения, ревью архитектурных решений |
| **Testing** | Генерация тест-кейсов, edge cases, синхронизация тестов | Определение качественных тестов, adversarial thinking |
| **Code Review** | Трейсинг логики, поиск P0/P1 багов, high-signal фидбек | Архитектурное соответствие, merge-ответственность |
| **Documentation** | Суммаризация из кода, диаграммы, release notes | Структура, стратегический контекст, шаблоны |
| **Deploy** | Парсинг логов, поиск аномалий, предложение hotfixes | Валидация root cause, resilient fixes, превентивные меры |

Источник: [Building an AI-Native Engineering Team](https://developers.openai.com/codex/guides/build-ai-native-engineering-team/)

---

## Связанные файлы

- [ai-ready-architecture.md](ai-ready-architecture.md) — **структура кода** под AI-агентов (sinks vs pipes, честные интерфейсы, progressive disclosure). Этот файл — про процесс, ai-ready-architecture — про структуру самого кода. Взаимодополняют
- [spec-driven-dev.md](spec-driven-dev.md) — детали принципа 1 "Spec First": SDD как парадигма, первоисточник (Ostroff/Paige 2004), инструменты, критика
- [engineering-harness.md](engineering-harness.md) — детали принципа 3 "Harness Engineering" (Hashimoto + OpenAI)
- [testing.md](testing.md) — тестирование AI-generated кода: failure modes, TDD+AI, mutation testing, multi-layer verification. Углубляет фазу Testing из SDLC и критику Böckeler
- [!coding.md](!coding.md) — сводка по AI-кодингу
- [../agents/!agents.md](../agents/!agents.md) — агентные паттерны
- [../skills/superpowers.md](../skills/superpowers.md) — библиотека скиллов (TDD, debugging, subagent patterns)

## Первоисточники

- [Mitchell Hashimoto: My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey) — 5 февраля 2026
- [OpenAI: Harness engineering](https://openai.com/index/harness-engineering/) — 13 февраля 2026
- [OpenAI: Building an AI-Native Engineering Team](https://developers.openai.com/codex/guides/build-ai-native-engineering-team/)
- [OpenAI: The Shift to Agentic AI — Evidence from Codex (PDF)](https://cdn.openai.com/pdf/5d1e1489-21c0-43e4-9d42-f87efdbf0082/the-shift-to-agentic-ai-evidence-from-codex.pdf)
- [Anthropic: How AI is transforming work](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic) — февраль 2026
- [Anthropic: Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [Anthropic: 2026 Agentic Coding Trends Report (PDF)](https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf)
- [TechCrunch: Spotify AI coding](https://techcrunch.com/2026/02/12/spotify-says-its-best-developers-havent-written-a-line-of-code-since-december-thanks-to-ai/) — 12 февраля 2026
- [Birgitta Böckeler: Harness Engineering](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html) — 17 февраля 2026
- [Boris Cherny — How I use Claude Code (X thread)](https://x.com/bcherny/status/2007179832300581177)
- [Simon Willison — Embracing the parallel coding agent lifestyle](https://simonw.substack.com/p/embracing-the-parallel-coding-agent)
- [Addy Osmani — Agentic Code Review](https://addyosmani.com/blog/agentic-code-review/)
- [METR 2025 — Early-2025 AI on experienced OS developers](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)
- [METR 2026 — Changing our experiment design](https://metr.org/blog/2026-02-24-uplift-update/)
- [ResearchGate — Cross-Model LLM Code Review](https://www.researchgate.net/publication/407032793_Cross-Model_LLM_Code_Review_Should_you_use_Claude_to_review_Codex_or_vice_versa)
- [Backlog.md — markdown-беклог для людей и агентов](https://github.com/MrLesk/Backlog.md)

## Вторичные источники

- [Habr: 6 советов от практиков AI coding](https://habr.com/ru/articles/997098/) — популяризация тех же принципов на русском (Хахалев/Киселёв, 16 февраля 2026)

