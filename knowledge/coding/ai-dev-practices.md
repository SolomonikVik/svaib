---
title: "AI Development Practices — принципы проектирования среды для AI-разработки"
source: "multiple (см. Первоисточники)"
source_type: article
status: processed
added: 2026-02-21
updated: 2026-02-28
review_by: 2026-05-28
tags: [ai-coding, methodology, best-practices, spec-driven, harness, delegation, engineering]
publish: false
version: 6
---

# AI Development Practices

## Кратко

Синтез принципов AI-first разработки из индустриальных источников: OpenAI, Anthropic, Mitchell Hashimoto. Ключевой сдвиг: роль инженера — не "писать код", а "проектировать среду, в которой агенты пишут код надёжно". Три принципа проектирования среды: Spec First (ЧТО агент должен сделать), Context Architecture (ГДЕ агент работает и что знает), Harness Engineering (КАК среда контролирует качество).

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

---

## Индустриальные данные

### OpenAI (февраль 2026)
- Пустой репо → ~1M строк за 5 месяцев через Codex
- 1500 PR, 0 строк написаны вручную
- Маленькая команда: в среднем 3.5 PR на инженера в день
- Оценка: 1/10 времени ручной разработки
- Сложность задач агентов удваивается каждые 7 месяцев

Источник: [Harness engineering](https://openai.com/index/harness-engineering/), [Building AI-Native Team](https://developers.openai.com/codex/guides/build-ai-native-engineering-team/)

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
- [Anthropic: How AI is transforming work](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic) — февраль 2026
- [TechCrunch: Spotify AI coding](https://techcrunch.com/2026/02/12/spotify-says-its-best-developers-havent-written-a-line-of-code-since-december-thanks-to-ai/) — 12 февраля 2026
- [Birgitta Böckeler: Harness Engineering](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html) — 17 февраля 2026

## Вторичные источники

- [Habr: 6 советов от практиков AI coding](https://habr.com/ru/articles/997098/) — популяризация тех же принципов на русском (Хахалев/Киселёв, 16 февраля 2026)

