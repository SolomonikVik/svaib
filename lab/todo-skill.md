---
title: "Последовательность создания Skill"
version: v8
updated: 2026-03-05
verified: false
---

# Создание Skill — пошаговая инструкция

> **Статус: этот файл надо переделать.**
>
> 2026-03-05: первое реальное применение (скилл `presentation`) показало, что todo-skill.md не работает как процесс. Координатор прочитал файл, формально прошёл по шагам и получил 6.5/10 — хуже, чем Виктор делал без всякого процесса (~8.5-9).
>
> Что пошло не так:
> - **Шаг 2 (исследование) пропущен** — координатор знал про `document-skills:pptx`, но не залез внутрь, не исследовал best practices. Изобрёл слабый шаблон с нуля. Это второй `process-step-skip` — первый был 2026-02-27, текстовый guardrail не помог.
> - **Шаг 4a (skill-creator) проигнорирован** — прямо написано "рекомендуется для новых скиллов", координатор пошёл вручную (4b). Ещё один пропуск в том же процессе.
> - **Артефакт-gate добавлен** (после шага 2), но корневая проблема глубже: текстовая инструкция не работает как механизм принуждения. Claude читает markdown как контекст, а не как исполняемый код. Может пропустить любой шаг — и пропускает.
>
> **Вывод:** нужно менять архитектуру — либо сделать `document-skills:skill-creator` обязательным runtime (не "рекомендуется", а единственный путь), либо превратить шаги в исполняемые проверки (hook/скрипт), а не текстовые пожелания.

Выполняй шаги по порядку. Справочник по формату — в конце файла. Выбор типа инструмента → `tooling.md`.

---

## Шаг 1. Понять боль

Разговор с Виктором: что отнимает время? Как часто? Что на входе, что на выходе?

**Критерий:** можешь в одном предложении сформулировать: "Скилл делает X когда Y".

---

## Шаг 2. Поиск аналогов + проверка конфликтов

Два действия параллельно (независимы друг от друга):

**a) Поиск аналогов — проверь каталоги по специализации:**

| Каталог | Специализация | Установка |
|---------|--------------|-----------|
| [Superpowers](https://github.com/obra/superpowers) (~14 шт.) | Методологии разработки: TDD, дебаг, planning, code review | `/plugin marketplace add obra/superpowers-marketplace` |
| [anthropics/skills](https://github.com/anthropics/skills) | Документы (PDF/DOCX/PPTX/XLSX), MCP, брендинг, skill-creator | `/plugin marketplace add anthropics/skills` |
| [antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) (968+) | Кураторский список: business (GTM, CRO, pricing), security, architecture | `npx antigravity-awesome-skills` |
| [HashiCorp](https://github.com/hashicorp/agent-skills) | Только Terraform + Packer (DevOps/IaC) | `npx skills add hashicorp/agent-skills` |
| [add-skill.org](https://add-skill.org) (Vercel Labs) | Team workflow: Linear, Notion, Jira, release notes | `npx add-skill vercel-labs/agent-skills` |
| [skills.sh](https://skills.sh) (80K+) | Массовый каталог: dev, design, cloud, marketing. Нужна ручная проверка качества | `npx skillsadd owner/repo` |
| [SkillHub](https://www.skillhub.club/) (22K+) | Массовый каталог с AI-грейдингом (S/A-rank) | `npx @skill-hub/cli install name` |

Если не нашёл в каталогах — веб-поиск: "claude code skill [задача]".

Также проверь **bundled skills** Claude Code — может задача уже решена: `/simplify` (код-ревью, 3 параллельных агента), `/batch` (массовые изменения с worktree и PR), `/debug` (дебаг сессии).

**b) Проверка конфликтов:**
- Glob `.claude/skills/` и `.claude/commands/` — нет ли скилла с похожим триггером или пересечением
- **Важно:** commands и skills объединены. Если есть `.claude/commands/review.md` и ты создашь `.claude/skills/review/SKILL.md` — skill перекроет command

**Критерий:** ответ "аналогов нет, строим сами" или "нашёл X, адаптируем" + конфликтов нет (или обсуждён с Виктором).

**Артефакт шага 2 (обязательный).** Перед переходом к шагу 3 — покажи Виктору краткий отчёт:
- Найденные аналоги (или "не найдены" с указанием где искал и что проверил)
- Best practices: что нашёл в knowledge/, каталогах, веб-поиске. Если аналог существует — что внутри него делает результат хорошим
- Решение: строим сами / адаптируем X / используем Y как основу

**Без этого артефакта шаг 3 не начинается.** (Добавлено после повторного process-step-skip, 2026-03-05)

---

## Шаг 3. Спроектировать

Определи и покажи Виктору:

| Параметр | Что указать |
|----------|-------------|
| Тип | **Reference** — conventions, guidelines. **Task** — step-by-step процедура |
| `name` | kebab-case, ≤64 символа |
| Триггер | Когда скилл активируется (точные фразы пользователя). Пиши "навязчиво" (pushy) — Claude склонен НЕ триггерить, перечисляй больше ситуаций |
| Анти-триггеры | Когда НЕ активируется |
| Входы | Что получает (аргументы, контекст) |
| Логика | Шаги выполнения |
| Выходы | Что создаёт/меняет |
| Контекст | **Основной** (видит историю разговора) или **fork** (изолированный субагент, не видит историю). Дефолт: основной |
| Видимость | **Авто** (Claude видит description, может триггерить сам, ~20%) или **Только ручной** (`disable-model-invocation: true` — только `/name`, Виктор не сможет вызвать фразой). Дефолт: авто |
| Формат frontmatter | **Стандарт** (`name` + `description`) или **Расширенный** (+ `allowed-tools`, `model`, `context` и др.). См. справочник |

> Автоактивация скиллов ~20%. Если нужна надёжная активация — см. справочник, секция "Повышение надёжности активации". Для `disable-model-invocation: true` — неактуально.

**Паттерны проектирования (arscontexta):** 7 паттернов, проверенных в production (arscontexta v0.8.0, 26 скиллов, MIT, 2K+ stars). Применимы к любому скиллу — от простого reader до сложного навигатора. Подробности и примеры: `knowledge/skills/skill-graphs/arscontexta-skill-anatomy.md`.

| Паттерн | Суть | Когда применять |
|---------|------|-----------------|
| **EXECUTE NOW** | Императивный старт: "Parse $ARGUMENTS → начинай сейчас". Надёжнее чем "Usage: вот что можно" | Любой скилл. `$ARGUMENTS` — встроенная переменная Claude Code |
| **Фазовая архитектура** | Последовательные фазы с конкретными bash-командами (простые операции) или вызовами scripts/ (сложная логика) | Любой скилл с >1 шагом. Bash в SKILL.md дополняет scripts/, не заменяет |
| **Edge Cases** | Секция "что делать когда условия неидеальны" — graceful degradation, не просто Limitations | Любой скилл. Чем больше edge cases — тем реже падает без объяснения |
| **Quality Gates** | Чеклист "готово ли" перед отдачей результата. Для сложных — полный (evidence, risk, steps). Для простых — "output must include X, Y, Z" | Сложные скиллы — полный. Простые — упрощённый |
| **Runtime Config (Step 0)** | "Прочитай конфиг перед работой" — скилл адаптируется к контексту | Plugin для клиентов — обязательно. Внутренние — если работает с разными папками |
| **Articulation Test** | Каждая ссылка: "A связан с B потому что [причина]". Голое "see also" — нет | Любой скилл в Related Skills |
| **Vocabulary Templating** | `{vocabulary.notes}` — параметризация для разных доменов | Только plugin для клиентов |

**Покажи Виктору. Получи одобрение. Только после этого — строить.**

---

## Шаг 4. Построить

Два варианта:

**a) Через `document-skills:skill-creator`** (рекомендуется для новых скиллов):
- Запусти через Skill tool: `skill: "document-skills:skill-creator"`
- Что он делает: интервью (use cases, триггеры) → планирование ресурсов (scripts/, references/, assets/) → `init_skill.py` (генерация каркаса) → помощь с description → `package_skill.py` (валидация)
- Он создаёт каркас (~40% работы): структуру, шаблон SKILL.md, примеры файлов. Наполнение содержанием — на координаторе
- **Обязательные секции SKILL.md** (Superpowers, `knowledge/skills/!skills.md`): Iron Law (одно нерушимое правило), Core Process (фазы пошагово). Рекомендуемые: Red Flags (признаки нарушения), Common Rationalizations (отговорки AI → почему неправильно)

**b) Вручную** — если скилл простой или адаптируешь существующий.

**Куда класть:**

| Уровень | Путь | Когда |
|---------|------|-------|
| Project | `.claude/skills/<name>/SKILL.md` | Скилл для этого проекта |
| Personal | `~/.claude/skills/<name>/SKILL.md` | Скилл для всех проектов |
| Plugin | `framework/plugin/skills/<name>/SKILL.md` | Скилл для продукта (клиентам) |

Чеклист перед сохранением:

- [ ] `name`: kebab-case, ≤64 символа, не `claude-*`/`anthropic-*`
- [ ] `description`: что делает + когда использовать. Trigger-фразы конкретные. Экономь бюджет (~16K на ВСЕ скиллы)
- [ ] Anti-triggers в description: "Do NOT use when..."
- [ ] SKILL.md ≤500 строк; детали → `references/`
- [ ] Нет XML-тегов в frontmatter
- [ ] Информация — либо в SKILL.md, либо в references (не дублировать)
- [ ] Есть хотя бы 1 пример вход→выход (Claude учится на примерах лучше чем на правилах)
- [ ] Есть секция Edge Cases (что делать при нештатных ситуациях — не Limitations)
- [ ] Related Skills: каждая ссылка с причиной ("A для B потому что..."), не голое "see also"
- [ ] Для скиллов с side effects: настрой permission rules (`Skill(name)` в `/permissions`)

### Блокер во время строительства

Если во время шага 4 план ломается (API недоступен, аналог не работает как ожидалось, архитектура не складывается) — **СТОП**. Не решай проблему самостоятельно, не перестраивай на альтернативный подход. Это стратегическое решение, не техническое.

**Действие:** вернись к шагу 3. Покажи Виктору что сломалось, предложи варианты (включая "не делать"), получи новое одобрение.

---

## Шаг 5. Валидировать

**a) Triggering тесты** — запусти на реальном примере:

- [ ] 5 промптов где ДОЛЖЕН сработать — порог: минимум 4/5
- [ ] 5 промптов где НЕ должен — порог: 5/5 (ложные срабатывания недопустимы)
- [ ] Тестировать в отдельных сессиях (новый чат на каждый промпт)
- [ ] Скилл видим в `/context`
- [ ] Не конфликтует с существующими

**b) Скоринг через skill-creator** — запусти `document-skills:skill-creator` на готовом скилле для оценки:
- Качество description и trigger-фраз
- Структура SKILL.md (секции, progressive disclosure)
- Best practices (Iron Law, self-contained, composability)
- Рекомендации по улучшению

**Troubleshooting:**

| Проблема | Решение |
|----------|---------|
| Не триггерится | Description слишком абстрактный. Добавь точные trigger-фразы. **Debug:** спроси Claude "When would you use the [skill-name] skill?" — он процитирует description, видно что не хватает |
| Триггерится лишний раз | Добавь anti-triggers: "Do NOT use when..." |
| Не видим в `/context` | Проверь: SKILL.md (регистрозависимо!), структура директории, бюджет описаний |
| Ошибки при вызове | Нет real-time валидации YAML; проверь синтаксис вручную |

---
---

# Справочник: формат Skill

> Дистилляция из knowledge/skills/ (4 файла), context7, внешних ссылок (code.claude.com/docs, agentskills.io/spec, блоги). Дата: 2026-03-02.

## Структура директории

```
my-skill/
├── SKILL.md              # Основной файл (обязательный, регистрозависимо)
├── references/           # (опц.) Справочные — загружаются on demand
├── scripts/              # (опц.) Утилиты — запускаются без чтения в контекст (token efficient)
└── assets/               # (опц.) Медиа, шаблоны
```

Для простого скилла достаточно одного `SKILL.md`. Поддиректории — по необходимости.

## YAML frontmatter

### Стандарт (agentskills.io — переносимый формат)

По спецификации Agent Skills и skill-creator от Anthropic — в frontmatter SKILL.md **только два поля:**

| Атрибут | Описание |
|---------|----------|
| `name` | kebab-case, ≤64 символа. Fallback: имя директории |
| `description` | Что делает + когда использовать. Trigger-фразы конкретные. ≤1024 символов. Fallback: 1-й абзац markdown |

**Примеры description:**
- Хорошо: `"Analyzes Figma design files and generates handoff documentation. Use when user uploads .fig files, asks for 'design specs' or 'design-to-code handoff'."`
- Плохо: `"Helps with projects."` / `"Creates sophisticated multi-page documentation systems."` — нет триггеров, непонятно КОГДА

### Расширения Claude Code (работают только в Claude Code)

Эти атрибуты НЕ часть стандарта agentskills.io, но поддерживаются Claude Code:

**Управление вызовом:**

| Атрибут | Значение | Эффект |
|---------|----------|--------|
| (default) | — | description в контексте, full skill при вызове |
| `disable-model-invocation` | `true` | description НЕ в контексте. Только ручной вызов через `/name` |
| `user-invocable` | `false` | скрыт из `/` меню, но description в контексте — Claude вызывает сам |

**Опциональные атрибуты:**

| Атрибут | Описание |
|---------|----------|
| `allowed-tools` | Ограничение инструментов. Comma или space-delimited. Примеры: `Read, Grep, Glob` или `Read Bash(git:*)` |
| `model` | Модель: `sonnet`, `haiku`, `opus` |
| `argument-hint` | Подсказка аргументов: `[filename] [format]` |
| `context` | `fork` — запуск в изолированном субагенте. SKILL.md body становится промптом субагента. Субагент НЕ видит историю разговора. Не подходит для скиллов-guidelines без конкретной задачи |
| `agent` | Тип субагента при context: fork (`Explore`, `Plan`, `general-purpose`, кастомный из `.claude/agents/`) |
| `hooks` | Хуки жизненного цикла скилла. Формат: см. [CC docs: Hooks in skills and agents](https://code.claude.com/docs/en/hooks#hooks-in-skills-and-agents) |

**Мета-информация (Agent Skills spec — для дистрибуции плагина):**

| Атрибут | Описание |
|---------|----------|
| `version` | Семантическая версия |
| `license`, `compatibility`, `metadata` | Нужны при публикации в каталоги |

## Тело SKILL.md

Markdown инструкции для Claude. Рекомендуется императивный стиль: "To accomplish X, do Y".

Типичные секции: Overview, Iron Law, When to Use / When NOT, Core Process, Red Flags, Quick Reference, Related Skills.

### Динамические возможности

| Механизм | Синтаксис | Что делает |
|----------|-----------|-----------|
| Аргументы | `$ARGUMENTS`, `$ARGUMENTS[0]`, `$1`, `$2` | Подстановка аргументов пользователя. Если `$ARGUMENTS` нет в контенте — аргументы добавляются в конец как `ARGUMENTS: <value>` |
| Session ID | `${CLAUDE_SESSION_ID}` | ID текущей сессии |
| Shell preprocessing | `` !`command` `` | Выполняет shell-команду ДО отправки Claude, output подставляется |
| Extended thinking | слово `ultrathink` в контенте | Включает extended thinking |

## Архитектурные ограничения

- **Бюджет описаний:** 2% от context window (fallback ~16K символов). Env: `SLASH_COMMAND_TOOL_CHAR_BUDGET`. Проверка: `/context`
- **Активация:** LLM-based routing по description. Базовая надёжность ~20%. С forced eval hook ~84%
- **Progressive disclosure:** metadata (~100 токенов) → SKILL.md body (≤500 строк) → references (on demand)
- **Нет real-time валидации** — ошибки в YAML видны только при вызове
- **Имена:** не `claude-*`, не `anthropic-*` (зарезервированы). Нет XML-тегов в frontmatter
- **Приоритет при конфликте:** enterprise > personal > project. Skill > command при совпадении имён

## Повышение надёжности активации

Базовая надёжность автоматической активации — ~20%. Это архитектурное ограничение LLM routing. Подробности: `knowledge/skills/skill-activation.md`.

| Стратегия | Надёжность | Плюсы | Минусы |
|-----------|-----------|-------|--------|
| Только description | ~20% | Ничего не стоит | 4 из 5 раз не сработает |
| Forced eval hook | ~84% | Системное решение | Latency к каждому ответу, инжект в контекст при КАЖДОМ сообщении, overhead растёт с числом скиллов. Создание: `todo-hook.md` |
| Триггеры в CLAUDE.md | высокая | Всегда в контексте, нулевая latency | Раздувает CLAUDE.md |
| Subagent с preloaded skills | высокая | Полный SKILL.md при старте | Только для субагентов |

> Сравнение Skill vs Command vs Agent vs Hook → `tooling.md`
