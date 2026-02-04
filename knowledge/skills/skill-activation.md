---
title: "Механика активации скиллов в Claude Code — progressive disclosure, LLM routing, forced eval hooks"
source: "https://code.claude.com/docs/en/skills"
source_type: docs
status: processed
added: 2026-02-01
review_by: 2026-05-01
tags: [skills, claude-code, activation, hooks, reliability]
publish: false
version: 1
---

# Механика активации скиллов в Claude Code

## Кратко

Скиллы в Claude Code загружаются через progressive disclosure: при старте сессии — только description (~50 токенов), полный SKILL.md — только при вызове. Решение о вызове принимает LLM (чистый reasoning, без алгоритмического роутинга). Базовая надёжность автоматической активации — ~20%. Forced eval hook поднимает до ~84%. Это архитектурное ограничение, а не проблема конкретного скилла.

---

## Progressive disclosure — как скиллы загружаются в контекст

### Три уровня загрузки

```
Уровень 1: Старт сессии
  → Загружаются ТОЛЬКО description всех скиллов (~50 токенов каждый)
  → Claude видит список: "skill-name: Use when..."
  → Полное содержание SKILL.md НЕ в контексте

Уровень 2: Вызов скилла (автоматический или /skill-name)
  → Загружается полный SKILL.md
  → Инжектится как user message в контекст
  → Теперь все правила, Red Flags, Iron Law — в контексте

Уровень 3: Supporting files (reference.md, examples.md)
  → Загружаются только если SKILL.md на них ссылается и Claude решит их прочитать
```

**Ключевое следствие:** Пока скилл не вызван, Claude работает без его правил. Даже если правила идеально написаны (Iron Law, Common Rationalizations, Red Flags) — они не влияют на поведение, потому что не в контексте.

### Бюджет описаний

По умолчанию лимит — 15,000 символов на все description всех скиллов. Если скиллов много, часть будет исключена. Проверить: `/context` (покажет warning). Увеличить: переменная `SLASH_COMMAND_TOOL_CHAR_BUDGET`.

---

## LLM-based routing — как принимается решение о вызове

Активация скилла — **чистый LLM reasoning**. Никакого алгоритмического роутинга, классификатора, embedding-матчинга. Claude смотрит на описания доступных скиллов и решает — вызвать или нет.

Это значит:
- Качество description критично — оно единственный вход для решения
- Решение зависит от формулировки запроса пользователя
- Нет гарантии вызова, даже если ситуация точно подходит
- При сложных multi-skill сценариях надёжность падает ещё сильнее

### Description — как писать для лучшей активации

**Хорошо:** "Use when [конкретный триггер]. [Что происходит]."
```
"Use when the user shares a link, topic, or tool name that might be added
to the knowledge base. Ensures investigation before recording."
```

**Плохо:** "[Что делает скилл]." — не говорит КОГДА применять.
```
"A methodology for recording knowledge with 4 phases."
```

---

## Проблема надёжности — известное ограничение

### Тестирование (200+ промптов)

| Подход | Успешность | Стоимость/тест |
|--------|-----------|----------------|
| Просто description (без хука) | ~20% | $0.006 |
| Forced eval hook | ~84% | $0.007 |
| LLM eval hook | ~80% | $0.006 |

Источник: [Scott Spence, тестирование skill activation](https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably)

**~20% базовая успешность** — это не баг, а характеристика LLM routing. В 4 из 5 случаев скилл не активируется автоматически, даже с хорошим description.

---

## Forced eval hook — решение проблемы

### Что это

Хук на `UserPromptSubmit`, который перед каждым ответом заставляет Claude:
1. Перечислить все доступные скиллы
2. Оценить каждый: YES/NO с обоснованием
3. Только после этого отвечать

Создаёт **commitment mechanism** — Claude не может "забыть" про скилл, потому что обязан его явно оценить.

### Как настроить

Добавить в `.claude/settings.json` хук типа `UserPromptSubmit`. Скрипт хука инжектит в контекст требование оценить все скиллы перед ответом. Доступен через `claude-code-toolkit` (plugin marketplace) или ручная настройка.

### Ограничения

- Добавляет latency к каждому ответу (оценка всех скиллов)
- При большом количестве скиллов — значительный overhead
- 84% — не 100%, всё ещё есть пропуски
- На complex multi-skill сценариях LLM eval может давать 0%

---

## Управление вызовом — frontmatter поля

| Поле | Эффект |
|------|--------|
| (по умолчанию) | И пользователь (/name), и Claude могут вызвать |
| `disable-model-invocation: true` | Только пользователь. Description НЕ загружается в контекст |
| `user-invocable: false` | Только Claude. Скрыт из меню `/` |

**Влияние на контекст:**

| Настройка | Description в контексте | Полный скилл |
|-----------|------------------------|-------------|
| По умолчанию | Да (всегда) | При вызове |
| `disable-model-invocation: true` | Нет | При вызове пользователем |
| `user-invocable: false` | Да (всегда) | При вызове Claude |

---

## context: fork — запуск в субагенте

`context: fork` в frontmatter запускает скилл в изолированном контексте (субагент). Содержание SKILL.md становится промптом для субагента.

```yaml
---
name: deep-research
context: fork
agent: Explore
---
```

Поле `agent` определяет тип субагента: `Explore`, `Plan`, `general-purpose` или кастомный из `.claude/agents/`.

**Важно:** `context: fork` имеет смысл только для скиллов с конкретной задачей. Скилл с guidelines ("используй эти API-конвенции") без задачи — субагент получит guidelines, но без actionable prompt, и вернёт пустоту.

---

## Практические выводы

### Почему скилл может "не работать"

1. **Не вызван** → правила не в контексте → Claude работает по общему разумению
2. **Description не матчится** → LLM не решает вызвать
3. **Бюджет описаний исчерпан** → скилл исключён из списка
4. **Multi-skill сценарий** → надёжность падает

### Стратегии повышения надёжности

| Стратегия | Плюсы | Минусы |
|-----------|-------|--------|
| **Forced eval hook** | Системное решение, ~84% | Latency, overhead |
| **Критичные правила в CLAUDE.md** | Всегда в контексте | Раздувает CLAUDE.md |
| **Дублирование в commands** | Правила загружаются с командой | Нарушает DRY |
| **Subagent с preloaded skills** | Полный SKILL.md при старте | Только для субагентов |

### Для скиллов-процессов (типа knowledge-research)

Скилл-процесс (Фазы 1-4, Iron Law, Red Flags) работает **только если загружен в контекст**. Без загрузки — Claude следует "духу" описания, но не букве правил. Для таких скиллов forced eval hook или явный вызов через команду — обязательны.

---

## Ссылки

- Официальная документация: https://code.claude.com/docs/en/skills
- Scott Spence, тестирование: https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably
- Skills explained (Anthropic blog): https://claude.com/blog/skills-explained
- Agent Skills deep dive: https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/
- Agent Skills open standard: https://agentskills.io
