---
title: "last30days-skill — кейс: Python-heavy архитектура скилла с code-enforced gates"
source: "https://github.com/mvanhorn/last30days"
source_type: repo
status: processed
added: 2026-03-07
updated: 2026-03-07
review_by: 2026-06-07
tags: [skills, architecture, patterns, python, research, fallback, code-enforcement]
publish: false
version: 1
---

# last30days-skill — Python-heavy Research Skill

## Кратко

Скилл для Claude Code, собирающий свежие новости по теме за 30 дней с 8 платформ параллельно. Архитектурно противоположен prompt-heavy подходу (Superpowers): критичная логика вынесена в Python-скрипт (~1800 строк), SKILL.md (~400 строк) отвечает только за синтез и презентацию. Ценность для нас: паттерны code-enforced phases, fallback chains, strict output template, two-phase search — применимы к любому скиллу с многошаговым процессом.

---

## Архитектура

### Два модуля, разделение ответственности

| Модуль | Что делает | Что НЕ делает |
|--------|-----------|---------------|
| `scripts/research.py` (~1800 строк) | Сбор данных, scoring, dedupe, fallback | Синтез, форматирование вывода |
| `SKILL.md` (~400 строк) | Синтез из собранных данных, презентация | Сбор, scoring, выбор источников |

Граница жёсткая: Python возвращает JSON-структуру, Claude работает только с ней. Claude не может "решить" пропустить фазу сбора — без данных от скрипта ему нечего синтезировать.

### Shell preprocessing

SKILL.md использует `` !`command` `` — shell preprocessing Claude Code. Скрипт выполняется ДО отправки промпта Claude, результат подставляется в контекст. Claude получает уже собранные данные, не решает как их собирать.

### Платформы (8 источников)

Reddit, Hacker News, X/Twitter, YouTube, GitHub, Product Hunt, Web (general), Academic (arxiv/papers). Каждый — отдельный модуль в скрипте с собственной логикой сбора и fallback.

---

## Паттерны (ценность для нас)

### 1. Code-Enforced Phases

**Проблема:** Текстовые инструкции "сначала исследуй, потом строй" — AI пропускает шаги.

**Решение last30days:** Фазы обеспечены архитектурой кода:
- Phase 1 (discovery) → entity extraction → Phase 2 (drill-down) → scoring → rendering
- Каждая фаза возвращает data structure, следующая принимает как input
- Пропустить невозможно — следующая фаза упадёт без входных данных

**Принцип:** Если шаг критичен — вынеси его в код (скрипт, hook), не в промпт. Код детерминирован, промпт — нет.

**Связь:** Принцип "Degrees of Freedom" из [!skills.md](!skills.md) — "для критичных валидаций — bundled scripts".

### 2. Fallback Chains

**Проблема:** Один источник недоступен → весь процесс застревает.

**Решение last30days:** Каждый источник имеет цепочку fallback:
- Reddit: ScrapeCreators API → OpenAI API → skip
- X/Twitter: Bird CLI → xAI Grok API → skip
- Web: Parallel fetch → Brave Search → OpenRouter → Claude WebSearch
- Финальный fallback всегда `skip` — один пропуск не блокирует результат

**Принцип:** Primary → Fallback 1 → Fallback 2 → Skip (с пометкой что пропущено). Graceful degradation вместо hard failure.

### 3. Strict Output Template

**Проблема:** AI добавляет лишнее — "а ещё заметил", "попутно поправил".

**Решение last30days:** Формат вывода жёстко шаблонизирован:
```
Title → "What I learned" (synthesis) → Stats block (tree + emoji per source) → Invitation to discuss
```
В шаблоне нет секции "дополнительные наблюдения" — Claude не может её добавить.

**Принцип:** Scope ограничивается форматом вывода, а не запретами. Нет места в шаблоне = нет действия.

### 4. Two-Phase Search

**Проблема:** Одноразовый поиск даёт поверхностные результаты.

**Решение last30days:**
- Phase 1: Широкий поиск по всем платформам → извлечение key entities (люди, проекты, компании)
- Phase 2: Целевой поиск по извлечённым entities → глубокие результаты
- Между фазами — entity extraction (NLP), не просто передача ссылок

**Принцип:** Broad → Extract → Targeted. Второй проход знает что искать.

### 5. Engagement Scoring с log1p

**Проблема:** Вирусный контент задавливает нишевый но ценный.

**Решение last30days:** `log1p(metric)` для всех engagement-метрик (upvotes, comments, stars). Логарифмическое сглаживание: разница между 10 и 100 upvotes значима, между 10K и 100K — нет.

### 6. Deduplication

Cross-platform dedupe: одна новость на Reddit, HN и Twitter → один результат с пометкой всех источников. Без дедупликации топ-10 = одна и та же новость 5 раз.

---

## Сравнение с Superpowers

| Аспект | last30days | Superpowers |
|--------|-----------|-------------|
| Подход | Python-heavy (логика в коде) | Prompt-heavy (логика в тексте) |
| SKILL.md | ~400 строк (синтез) | ~200-500 строк (полный процесс) |
| Scripts | ~1800 строк Python | Нет скриптов |
| Phase enforcement | Код (data dependency) | Текст (Iron Law + Red Flags) |
| Scope control | Output template (нет места) | Pressure tests (антитела) |
| Когда лучше | Детерминированные шаги, внешние API | Творческие задачи, code review |

**Вывод:** Два полюса skill-архитектуры. Выбор зависит от задачи: если шаги детерминированы и хрупки → код. Если нужна гибкость и адаптация → промпт.

---

## Качество и ограничения

**Качество:** Крупный проект, MIT лицензия, активная разработка. Хорошо документирован. Встроенная система benchmarking (60+ файлов blinded comparisons для оценки качества синтеза).

**Ограничения:**
- Требует API-ключи для нескольких платформ (Reddit, X, YouTube и др.)
- Python-зависимость (не все среды поддерживают)
- Скрипт ~1800 строк — сложно модифицировать без понимания архитектуры

---

## Связанные файлы

- [!skills.md](!skills.md) — сводка знаний (формат, принципы, экосистема)
- [superpowers.md](superpowers.md) — Superpowers: prompt-heavy подход (контраст)
- [skill-tooling.md](skill-tooling.md) — инструменты lifecycle
- [../../.claude/lab/inbox-last30days-patterns.md](../../.claude/lab/inbox-last30days-patterns.md) — план применения паттернов к нашим проблемам из rescue-log
