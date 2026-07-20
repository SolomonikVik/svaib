---
title: "Eval tooling — карта фреймворков и критерии выбора"
source: "internal synthesis (industry research 2026-07-17)"
source_type: docs
status: processed
added: 2026-07-18
updated: 2026-07-18
review_by: 2026-10-18
tags: [evals, tooling, promptfoo, deepeval]
publish: false
version: 3
---

# Eval tooling

## Кратко

Карта eval-инструментов и устойчивые критерии, по которым команда выбирает между самописным харнесом и готовым фреймворком. Конкретные цены, тарифные лимиты и версии нужно проверять в официальной документации перед выбором.

## Консолидация рынка 2026

- OpenAI объявила о приобретении promptfoo 09.03.2026 и будущей интеграции его технологии в OpenAI Frontier; на дату проверки сделка в официальном анонсе описана как ещё не завершённая. Open-source CLI и библиотека продолжают развиваться.
- Собственная hosted-платформа OpenAI Evals — deprecated: read-only с 31.10.2026, полное отключение 30.11.2026; официальная миграция — на promptfoo. Репозиторий `openai/simple-evals` не обновляется с июля 2025.
- Langfuse с января 2026 — часть ClickHouse; W&B Weave — под CoreWeave после сделки 2025.

## Стандартный цикл сравнения (EDD)

Индустриальный паттерн раннеров типа promptfoo: зафиксировать baseline прогона → внести изменение (промпт/модель/пайплайн) → прогнать снова → сравнить с baseline (`eval --compare` или аналог) → получить точный список регрессий (pass→fail) и побед (fail→pass), а не агрегированный процент. Детерминированные ассерты (regex/contains/is-json/счётчики) идут первыми — быстрые и бесплатные; model-graded ассерты (llm-rubric/factuality) — точечно, там, где код не может проверить сам.

## Карта инструментов

| Инструмент | Что это | Модель развёртывания | Для кого |
|---|---|---|---|
| **promptfoo** | CLI + YAML, регресс-эвалы, red-teaming | Open-source CLI; облачные возможности | Промпт-регрессы, CI, сравнение моделей |
| **DeepEval** | pytest-style Python, готовые и кастомные метрики | Open-source библиотека; облачная платформа Confident AI | Python-команды, CI-гейты |
| **Braintrust** | Платформа полного цикла: evals, мониторинг, аннотация | Hosted | Команды с нетехническими стейкхолдерами |
| **LangSmith** | Трейсинг + evals, LangChain-центричный | Hosted | Команды на стеке LangChain |
| **Langfuse** | Трейсы, датасеты, эксперименты, аннотация | Open source, self-host и cloud | Малые команды, приоритет владения данными |
| **Arize Phoenix** | Self-hosted observability + evals | Elastic License 2.0 (не OSI) | Команды, для которых наблюдаемость первична |
| **W&B Weave** | Трейсинг агентов, MCP auto-logging | Под CoreWeave | Уже живущие в экосистеме W&B |

## Паттерн «два инструмента»

Распространённая архитектура — лёгкий CI-фреймворк для регресс-гейтов (DeepEval/promptfoo) плюс опциональная платформа для аннотации, истории и дашбордов (Braintrust/LangSmith/Langfuse). Для небольшой инженерной команды без внешних аннотаторов отдельная платформа может быть избыточна.

## Контр-позиция: самописный тулинг как инвестиция

Hamel Husain аргументирует, что самописные annotation-инструменты могут быть особенно ценной инвестицией благодаря видимости доменного контекста, недоступной универсальному UI. Это контр-позиция к покупке полной платформы, а не универсальное правило; промпты при таком подходе версионируются рядом с кодом продукта.

## Сигналы, что пора брать готовый инструмент

- Нужен UI для просмотра/аннотации трейсов человеком не из инженерной команды.
- Нужна история прогонов и тренды между сессиями, не только последний результат.
- Golden set вырос до десятков кейсов и прогоны стали регулярными (CI/nightly), а не разовыми.
- Поддержка самописного харнеса начала требовать заметного времени в месяц сверх собственно eval-работы.

## Итоговая рамка выбора

Выбор не обязан быть бинарным: open-source-раннер может отвечать за кастомные рубрики и CI-гейты, а платформа — добавляться только при потребности в масштабе, истории или UI для аннотаторов. Между runner-библиотеками выбирают по формату кейсов, требуемым грейдерам, интеграции с CI и языку основной кодовой базы.

## Источники

- [OpenAI — OpenAI to acquire promptfoo](https://openai.com/index/openai-to-acquire-promptfoo/)
- [OpenAI Evals platform deprecation notice (June 2026)](https://codex.danielvaughan.com/2026/06/04/openai-june-2026-platform-deprecations-evals-agent-builder-prompts-codex-cli-migration/)
- [promptfoo — expected outputs / eval --compare](https://www.promptfoo.dev/docs/configuration/expected-outputs/)
- [DeepEval (GitHub)](https://github.com/confident-ai/deepeval)
- [Langfuse (GitHub)](https://github.com/langfuse/langfuse)
- [Hamel Husain — LLM Evals FAQ](https://hamel.dev/blog/posts/evals-faq/)
- [Helicone — Buy vs build LLM observability](https://www.helicone.ai/blog/buy-vs-build-llm-observability)
- [FutureAGI — When is building your LLM evals actually worth it](https://futureagi.substack.com/p/when-is-building-your-llm-evals-actually)
