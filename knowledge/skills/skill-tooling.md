---
title: "Инструменты и паттерны для жизненного цикла скиллов — линтинг, валидация, маршрутизация, автогенерация"
source: "https://github.com/agent-sh/agnix, https://github.com/DaronVee/ccgg-skills-factory, https://github.com/ChrisWiles/claude-code-showcase, https://github.com/shanraisshan/claude-code-best-practice, https://github.com/AAddrickM/claude-pipeline, https://github.com/nicekid1/claudeception"
source_type: repo
status: processed
added: 2026-03-05
updated: 2026-03-05
review_by: 2026-06-05
tags: [skills, tooling, linting, validation, routing, quality-gates, automation]
publish: false
version: 1
---

# Инструменты и паттерны для жизненного цикла скиллов

## Кратко

Экосистема скиллов богата инструментами, но они разрозненны — каждый решает один аспект lifecycle. Этот файл собирает инструменты, усиливающие конкретные шаги: статический анализ SKILL.md (agnix), валидация структуры (ccgg-skills-factory), детерминированная маршрутизация вместо LLM routing (claude-code-showcase, claude-pipeline), архитектурные паттерны организации (shanraisshan), автоматическое извлечение скиллов (Claudeception), quality gates в production (levnikolaevich). Это не альтернативные методологии, а инструменты, усиливающие отдельные шаги процесса.

---

## Статический анализ

### agnix (agent-sh/agnix)

Линтер и LSP для SKILL.md, CLAUDE.md и hooks. Превращает текстовые quality gates в исполняемый код.

**Что делает:**
- 230+ правил валидации (формат `CC-SK-012`, `CC-MD-005`, `CC-HK-003`)
- Автофикс для большинства правил
- Интеграция: CLI, CI (GitHub Actions), IDE через LSP
- Правила покрывают: YAML frontmatter, structure, naming conventions, description quality

**Примеры правил:**
- `CC-SK-012` — `argument-hint` без `$ARGUMENTS` в body (бесполезная подсказка)
- Проверка длины description (budget awareness)
- Валидация kebab-case в name
- Проверка структуры директории

**Ценность для нас:** Шаг 4 (Build) в [todo-skill.md](../../lab/todo-skill.md) содержит 13-item чеклист — agnix автоматизирует большинство этих проверок. Можно встроить в CI или pre-commit hook.

**Репо:** [github.com/agent-sh/agnix](https://github.com/agent-sh/agnix)

---

## Валидация

### ccgg-skills-factory (DaronVee/ccgg-skills-factory)

Meta-skill + Python-валидатор. Двухуровневый подход: скилл учит создавать скиллы, скрипт валидирует результат.

**Что делает:**
- `comprehensive_validate.py` (514 строк) — 12+ автоматических проверок:
  - YAML frontmatter (обязательные поля, типы)
  - Progressive disclosure (длина body, глубина ссылок на references/)
  - Структура директории (наличие SKILL.md, допустимые поддиректории)
  - Description quality (длина, наличие trigger phrases)
- Meta-skill — скилл, который учит Claude создавать другие скиллы (аналог writing-skills в Superpowers)

**Ценность для нас:** Валидатор можно использовать как часть Шага 5 (Validate). В отличие от agnix (линтинг) проверяет семантику: progressive disclosure compliance, глубина ссылок.

**Репо:** [github.com/DaronVee/ccgg-skills-factory](https://github.com/DaronVee/ccgg-skills-factory)

---

## Маршрутизация

Проблема: LLM routing даёт ~20% базовой активации ([skill-activation.md](skill-activation.md)). Два инструментальных подхода к решению.

### claude-code-showcase (ChrisWiles/claude-code-showcase)

Rule-based skill routing через UserPromptSubmit hook. Детерминированная альтернатива LLM-маршрутизации.

**Как работает:**
- `skill-eval.js` — хук на UserPromptSubmit, оценивает каждый промпт пользователя
- `skill-rules.json` — правила маршрутизации для каждого скилла
- Типы паттернов: keywords, regex, glob (по файлам), intent patterns
- Confidence scoring: keyword=2pts, pattern=3pts, path=4pts, directory=5pts
- Приоритеты между скиллами при конфликте

**Отличие от forced eval hook:** Eval hook заставляет Claude оценить скиллы (всё ещё LLM, ~84%). Showcase заменяет LLM scoring на детерминированный rule engine — предсказуемо, без latency LLM reasoning.

**Компромисс:** Надёжнее для известных паттернов, но требует ручного описания правил для каждого скилла. Не работает на неожиданных формулировках.

### claude-pipeline (aaddrick/claude-pipeline)

SessionStart hook — инжектирует `using-skills` скилл в начало каждой сессии.

**Как работает:**
- При старте сессии хук загружает скилл `using-skills`
- Этот скилл содержит инструкцию: "Перед каждым ответом проверь, есть ли подходящий скилл"
- Claude получает reminder на каждый ход — не может "забыть" про скиллы

**Отличие от forced eval hook:** Eval hook работает через UserPromptSubmit (каждый промпт). Pipeline — через SessionStart (один раз при старте), но создаёт persistent instruction в контексте.

**Репо:** [github.com/AAddrickM/claude-pipeline](https://github.com/AAddrickM/claude-pipeline)

---

## Архитектурные паттерны

### Command → Agent → Skill (shanraisshan/claude-code-best-practice)

Паттерн разделения ответственности между тремя уровнями Claude Code.

**Суть:**
- **Command** — оркестратор. Определяет workflow, вызывает агентов. Пользователь запускает через `/name`
- **Agent** — исполнитель с preloaded skills. Работает в изолированном контексте, скиллы загружены при старте (решает проблему активации)
- **Skill** — независимая инструкция. Работает и сам по себе, и как часть агента

**"Исполнительный контракт":** Agent получает список скиллов при создании — это гарантирует 100% активацию (скиллы в контексте с первого хода). Нет зависимости от LLM routing.

**Ценность для нас:** Паттерн уже используется в svaib (commands → agents → skills). Shanraisshan формализовал его и показал, что preloaded skills в агенте — самый надёжный способ активации. Связано с нашим [skill-activation.md](skill-activation.md): стратегия "Subagent с preloaded skills".

**Репо:** [github.com/shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice)

---

## Автогенерация

### Claudeception (blader)

Принципиально иной подход: скиллы не проектируются top-down, а извлекаются bottom-up — Claude автоматически создаёт скилл когда обнаруживает нетривиальное решение.

**Как работает:**
- Hooks инжектируют evaluation reminders в процесс работы
- Claude оценивает: "Я только что нашёл решение, которое не очевидно — стоит ли сохранить как скилл?"
- Quality filter: "не просто documentation lookup, реально протестировано, поможет кому-то через 6 месяцев"
- Автоматически генерирует SKILL.md с description, trigger phrases, steps

**Философия:** Top-down (наш [todo-skill.md](../../lab/todo-skill.md)) — от боли к скиллу. Bottom-up (Claudeception) — от открытия к скиллу. Оба подхода дополняют друг друга: top-down для запланированных скиллов, bottom-up для emergent patterns.

**Ценность для нас:** Паттерн "скилл создаётся из практики" — можно адаптировать для лаборатории. Когда координатор решает нетривиальную задачу, хук предлагает: "Стоит ли сохранить как скилл?"

**Репо:** автор — blader (GitHub)

---

## Quality Gates в production

### levnikolaevich/claude-code-skills

Крупнейшая коллекция production-скиллов с формализованными quality gates.

**Масштаб:** 102 скилла, покрывающих полный Agile lifecycle (planning → development → review → deployment).

**4-level quality gates:**

| Уровень | Значение | Действие |
|---------|----------|----------|
| PASS | Всё ок | Продолжить |
| CONCERNS | Мелкие замечания | Продолжить с пометкой |
| REWORK | Существенные проблемы | Вернуть на доработку |
| FAIL | Критические ошибки | Блокировать |

**Multi-model cross-checking:** Claude + Codex + Gemini запускают параллельные ревью одного артефакта. Разногласия между моделями — сигнал для human review.

**Ценность для нас:** Модель quality gates (4 уровня) применима к Шагу 5 (Validate) в todo-skill.md. Сейчас у нас бинарная оценка (pass/fail триггеринг тестов) — 4 уровня дают более гранулярную обратную связь. Multi-model review — паттерн для сложных скиллов.

**Репо:** [github.com/levnikolaevich/claude-code-skills](https://github.com/levnikolaevich/claude-code-skills)

---

## Карта: инструменты по шагам lifecycle

| Шаг процесса | Инструмент | Что автоматизирует |
|-------------|-----------|-------------------|
| Проектирование | shanraisshan (паттерн C→A→S) | Выбор архитектуры: command, agent, или skill |
| Сборка | agnix (линтер) | Статические проверки YAML, naming, structure |
| Сборка | ccgg-skills-factory (валидатор) | Семантические проверки: progressive disclosure, description quality |
| Валидация | levnikolaevich (quality gates) | 4-level оценка вместо бинарной |
| Активация | claude-code-showcase (rule engine) | Детерминированная маршрутизация вместо LLM |
| Активация | claude-pipeline (SessionStart hook) | Persistent reminder о скиллах |
| Активация | shanraisshan (preloaded skills) | 100% через agent с preloaded skills |
| Создание | Claudeception (bottom-up) | Автоматическое извлечение из практики |

---

## Источники

- GPT Deep Research (март 2026): конкурентный анализ подходов к созданию скиллов
- Верификация Claude (март 2026): все репо проверены на GitHub, описания корректны
- Compass-артифакт (март 2026): обзор экосистемы и конкурентных подходов

## Связанные файлы

- [!skills.md](!skills.md) — сводка знаний о скиллах (формат, принципы, экосистема)
- [skill-activation.md](skill-activation.md) — механика активации и проблема надёжности ~20%, к которой tooling даёт конкретные решения
- [superpowers.md](superpowers.md) — библиотека Superpowers: TDD-подход к скиллам (complementary к tooling)
- [context/skill-graphs/arscontexta-skill-anatomy.md](../context/skill-graphs/arscontexta-skill-anatomy.md) — 7 паттернов проектирования (design-level, tooling — build/validate-level)
