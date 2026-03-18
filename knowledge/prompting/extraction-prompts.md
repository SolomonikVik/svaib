---
title: "Best practices для extraction-промптов: извлечение сущностей и поведенческих паттернов из текстов"
source_type: research
status: processed
added: 2026-03-14
updated: 2026-03-18
review_by: 2026-06-18
tags: [prompting, extraction, meeting-analysis, anti-hallucination, behavioral-analysis, NVC]
publish: false
version: 2
---

# Extraction prompts — best practices

## Кратко

Сводка исследований и production-практик по проектированию LLM-промптов для извлечения структурированных данных из неструктурированного текста. Два фокуса: entity extraction (бизнес-сущности) и behavioral extraction (поведенческие паттерны). Применимо к meeting transcripts, интервью, документам.

---

## Архитектура extraction-промпта

**Оптимальная структура:**
```
Role/Task → Iron Law → Принципы → Вход → Каталог (reference) → Процесс → Формат выхода → Anti-patterns
```

**Iron Law** — один нерушимый принцип на промпт, выделенный отдельно перед всем остальным. Не прячется в списке из 5 принципов. AI рационализирует нарушение размытых правил при давлении — одно чёткое правило сложнее обойти. Источник: паттерн из production skills, подтверждён на практике svaib.

**Принципы вместо правил.** Умная модель при хорошей оптике сделает лучше, чем средняя модель с 50 правилами. 4-5 принципов, из которых правила следуют, не микроменеджмент.

---

## Entity extraction

### Quote-first extraction

Самая эффективная анти-галлюцинационная техника (Anthropic docs). Порядок: **сначала найди цитату → потом определи тип сущности**. Не наоборот. Меняет когнитивный режим модели: работает от текста, а не от схемы.

Источник: [Anthropic — Reduce Hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations)

### Structured decomposition > CoT > Direct

F1 scores из исследований:
- Structured decomposition: **79.8%**
- Few-shot: 75.2%
- Chain-of-thought: 74.1%
- Direct extraction: 70.1%

Практический паттерн: "определи основные темы → по каждой теме извлеки кандидатов". Лёгкое предварительное рассуждение без полноценного CoT. Полный CoT генерирует много reasoning-токенов без пропорционального роста точности.

Источник: [Structured Decomposition for LLM Reasoning](https://arxiv.org/pdf/2601.01609)

### Three-tier certainty

**Не просить числовой confidence** — ненадёжно (lowest accuracy across datasets). Вместо этого три категории, привязанные к лингвистическим маркерам:
- `certain` — explicit commitment ("решили", "договорились", "делаем")
- `likely` — strong implication ("может попробуем", "я думаю стоит")
- `unclear` — ambiguous context

Источник: [Sensible — Confidence Signals](https://www.sensible.so/blog/confidence-signals)

### Few-shot с edge cases

2-3 примера дают +5% F1 vs zero-shot. Главная ценность — показать пограничные случаи: "это выглядит как решение, но это идея" (нет commitment language). Модель учится границам быстрее через примеры, чем через правила.

### Flat schema

Точность извлечения падает с глубиной вложенности JSON. Для промежуточного выхода (между экстрактором и синтезатором) — плоская структура. Enum fields для классификации, не free-text.

Источник: [PARSE — Schema Optimization](https://arxiv.org/html/2510.08623v1)

### Phantom consensus — главный failure mode

LLM выдаёт обсуждение за решение. Митигация: require explicit commitment language. Нет "решили"/"договорились" → не Решение. В промпте как anti-pattern или в "Чего не делать".

---

## Behavioral extraction

### Camera test (NVC)

Из Nonviolent Communication (Marshall Rosenberg). Правило: может ли видеокамера записать то, что ты описываешь? "Участник сказал: 'рынок изменился'" — камера может. "Участник уходит от ответственности" — камера не может, это интерпретация.

Применение: встроить как Iron Law поведенческого экстрактора + как self-check перед выдачей каждого наблюдения.

Источник: [NVC Chapter 3 — Observing Without Evaluating](https://nonviolentcommunication.com/wp-content/uploads/2024/12/nvc3-chapter3.pdf)

### Vocabulary blocklist

Жёсткий запрет конкретных слов надёжнее мягкого "будь нейтральным". Модель не может сказать запрещённое.

Категории для блоклиста:
- Психологические термины: "защитный механизм", "избегание", "проекция", "компенсация"
- Оценки характера: "безответственный", "слабый лидер"
- Язык намерений: "пытается", "хочет", "стремится", "избегает"
- Генерализации: "всегда", "никогда", "типично", "склонен"

### Subject constraint

Подлежащее в наблюдении — всегда "высказывание" или "фраза", не "участник". "В высказывании причина отнесена к внешнему фактору" — не "участник переложил ответственность". Встраивается в Iron Law.

### Anti-pattern few-shot

Для behavioral extraction критичнее, чем для entity extraction — цена ошибки выше (клиент может закрыться). Примеры НЕПРАВИЛЬНОГО вывода с объяснением "почему ошибка" + правильный вариант. Модель учится границам через нарушения.

### "Возможная причина" — зона риска

Свободное поле для интерпретации причины поведения — именно та точка, где модель начинает "умничать". Исторический инцидент svaib: AI перешёл от наблюдений к диагнозу "defensive mechanism", клиент закрылся. Рекомендация: убрать или жёстко ограничить ("только если причина прямо названа в речи").

### Symmetry enforcement — trade-off

"Для каждого (-) ищи (+)" может породить ложноположительные наблюдения — противоречит принципу "лучше не отметить, чем приписать". Убрали из промпта svaib. Остаточный риск: негативный bias. Мониторить на тестах.

---

## Архитектура pipeline

### Монолит vs пайплайн: зависит от контекстного окна

При достаточном контексте модели (1M+ токенов, Opus 4.6) один промпт с методологией > цепочка специализированных агентов. Верифицировано: generic промпт из интернета (16.5/20) ≈ полная 4-агентная система (16/20), а один промпт с встроенной методологией — лучше обоих (17.5/20). Причина: "телефонная игра" — каждая передача между агентами теряет контекст и вносит искажения (гипотеза → факт, обсуждение → решение). Подробнее: `framework/_inbox/experiments/conclusions.md`. Источник: эксперимент svaib, март 2026.

**Следствие:** паттерн parallel extractors → synthesizer (ниже) остаётся релевантным для коротких контекстных окон и batch-обработки, но для моделей с 1M+ контекстом стоит начинать с одного промпта.

### Parallel extractors → Synthesizer

Proven production pattern (Microsoft, AssemblyAI, Deepchecks). Entity extractor + behavior extractor запускаются параллельно, synthesizer объединяет. Latency снижается ~50%.

### Tiered models

Дешёвые/быстрые модели (Sonnet, Haiku) на extraction. Мощные (Opus) на synthesis. Extractors делают recall-задачу, synthesizer — reasoning-задачу.

### Context separation

- **Контекст транскрипта** (глоссарий, участники, цель) → экстракторам. Для корректного чтения текста.
- **Контекст проекта** (досье, история) → только синтезатору. Иначе contamination: контекст подменяет то, что сказано.
- Two-phase approach: сначала извлечь без контекста проекта, потом обогатить.

### Chapter segmentation для длинных встреч

Для транскриптов 60+ минут: разбивать по темам (semantic chunking), не механически. Microsoft использует BERT-based text-tiling. "Lost in the middle" problem: LLM пропускает информацию в середине длинного контекста.

Источник: [Microsoft — Summaries, Highlights, and Action Items](https://arxiv.org/abs/2307.15793)

### Verification pass

Между extraction и synthesis — проверка: speaker attribution errors, phantom consensus, hallucinated quotes. Опционально для v1, рекомендуется для production.

---

## Общие паттерны

- **Temperature 0-0.2** для extraction tasks — factual precision, не creativity
- **Structured outputs API** (Anthropic) для программных пайплайнов — guaranteed schema compliance
- **Role через задачу** — "Твоя задача — извлечь..." лучше чем "Ты — экстрактор"
- **"После тебя будет редакция"** — снимает давление с extractor, усиливает recall
- **Не дублировать каталог** — дать как reference в промпте, не объяснять каждый тип

---

## Источники

- [Anthropic — Reduce Hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations)
- [Anthropic — Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Anthropic — Increase Output Consistency](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/increase-consistency)
- [Structured Decomposition for LLM Reasoning](https://arxiv.org/pdf/2601.01609)
- [PARSE — Schema Optimization for Entity Extraction](https://arxiv.org/html/2510.08623v1)
- [Microsoft — Summaries, Highlights, and Action Items (arXiv:2307.15793)](https://arxiv.org/abs/2307.15793)
- [Re-FRAME Meeting Summarization (arXiv:2509.15901)](https://www.arxiv.org/pdf/2509.15901)
- [NVC Chapter 3 — Observing Without Evaluating](https://nonviolentcommunication.com/wp-content/uploads/2024/12/nvc3-chapter3.pdf)
- [ICA Coach — Observation vs Evaluation](https://icacoach.com/coach-portfolios/power-tools/observation-vs-evaluation/)
- [Prompting to Reduce Social Bias (System 1/System 2)](https://arxiv.org/html/2404.17218v4)
- [Sensible — Confidence Signals](https://www.sensible.so/blog/confidence-signals)
- [Deepchecks — Multi-Step LLM Chains](https://deepchecks.com/orchestrating-multi-step-llm-chains-best-practices/)
- [Databricks — Batch Entity Extraction](https://community.databricks.com/t5/technical-blog/end-to-end-structured-extraction-with-llm-part-1-batch-entity/ba-p/98396)
- [Tensorlake — RAG Citations](https://www.tensorlake.ai/blog/rag-citations)
