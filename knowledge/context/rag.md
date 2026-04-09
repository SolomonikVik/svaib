---
title: "RAG — Retrieval-Augmented Generation: подходы, реализации, бенчмарки"
source: "https://langwatch.ai/blog/the-ultimate-rag-blueprint-everything-you-need-to-know-about-rag-in-2025-2026"
source_type: article
status: processed
added: 2026-04-09
updated: 2026-04-09
review_by: 2026-07-09
tags: [rag, hybrid-search, vector-search, bm25, reranking, graphrag, agentic-rag, chunking, benchmarks]
publish: false
version: 1
---

# RAG — Retrieval-Augmented Generation

## Кратко

Паттерн подачи AI релевантной информации из внешнего хранилища: нарезать документы на куски (чанкинг) → превратить в числовые представления (эмбеддинги) → сохранить в базу → при запросе найти похожие куски → подать LLM для генерации ответа. Стандартный RAG (один вектор, cosine similarity) устарел для статичных корпусов < 1M токенов — там long context дешевле. Но для динамичных данных (100+ файлов, постоянное обновление) RAG остаётся ключевой технологией. 71% компаний, начавших с context-stuffing, добавили vector retrieval в течение 12 месяцев (Gartner Q4 2025).

Для SVAIB: RAG — реализация неструктурированного поиска в контекстной архитектуре (workbench блок 0). Когда агент не знает маршрут — ищет по смыслу.

---

## RAG vs Long Context

С появлением контекстных окон в 1M+ токенов (Claude, Gemini) вопрос "нужен ли RAG" стал центральным.

| Параметр | Long Context (1M) | RAG |
|---|---|---|
| Стоимость | Квадратичный рост attention | 50-200x меньше токенов на запрос |
| «Потерялось в середине» | Да, при >100K токенов | Нет — подаются только релевантные куски |
| Динамичные данные | Каждый раз всё заново | Инкрементальный update |
| Точность retrieval | ~90% | 95%+ с гибридным поиском |
| Латентность | 20-30с first token | 200-500мс + retrieval |

**Консенсус 2026:** гибрид — RAG для retrieval из большого корпуса, long context для reasoning по найденным документам. Не "или-или", а "и-и".

---

## Что реально работает (best practices 2026)

### Гибридный поиск

Одного vector search недостаточно. Работающий пайплайн:

1. **BM25 (sparse)** — поиск по ключевым словам. Ловит точные совпадения, которые vector search пропускает
2. **Vector search (dense)** — поиск по смыслу через эмбеддинги. Ловит семантическую близость
3. **RRF fusion** — объединение результатов (Reciprocal Rank Fusion, k=60). Не требует нормализации скоров
4. **Cross-encoder reranker** — перечитывает найденные куски, переупорядочивает по релевантности. Самый большой single gain по precision. +80мс латентности

Реализации: QMD (все 4 шага, локально), Weaviate (hybrid mode), Elasticsearch + vector plugin.

### Чанкинг

Как нарезать документы — критично для качества:

- **Семантический сплит** > фиксированная длина. Разрыв по смысловым границам (абзацы, заголовки)
- **Small-to-big:** ищем по маленьким чанкам (точнее retrieval), подаём LLM родительский документ (больше контекста)
- **QA-пары как чанки** — набирает популярность. Один обмен вопрос-ответ = один чанк. Подход Karpathy/QMD
- **Contextual retrieval (Anthropic):** добавление контекста документа перед каждым чанком при эмбеддинге. Снижает ошибки retrieval на 67%

### Эмбеддинги и реранкеры

| Компонент | Актуальные модели |
|---|---|
| Эмбеддинги | E5-large-v2, all-MiniLM-L6-v2 (лёгкая), Cohere embed-v3 |
| Реранкеры | bge-reranker-v2-m3, Cohere Rerank, qwen3-reranker-0.6b (локальный) |
| Расширение запросов | Fine-tuned LLM (QMD использует qmd-query-expansion-1.7B) |

---

## Направления эволюции

### Agentic RAG

Агент сам решает: что искать, какие инструменты вызвать, когда проверить результат, нужен ли повторный поиск. Не фиксированный пайплайн, а цикл решений.

Паттерны: reflection (агент оценивает качество найденного), planning (разбивает сложный вопрос на подзапросы), tool use (выбирает между grep, vector search, API), multi-agent (разные агенты для разных задач).

Фреймворки: LangGraph, CrewAI, Pydantic AI, DSPy.

**Для SVAIB:** это ближе всего к нашей архитектуре — агент-координатор поверх retrieval. Наш "структурированный режим" (скилл → маршрут) + "неструктурированный режим" (агент ищет сам) = по сути Agentic RAG.

### GraphRAG (Microsoft)

Извлекает сущности + связи из документов → строит knowledge graph → создаёт иерархические community summaries. При запросе: ищет не по чанкам, а по графу связей.

- Comprehensiveness 72-83% vs baseline RAG (не может ответить на вопросы, требующие связей)
- 97% меньше токенов для root-level summaries
- Open source, доступен через Azure (Microsoft Discovery)
- GraphRAG-Bench принят на ICLR 2026

**Для SVAIB:** потенциально ценен для связей между знаниями руководителя (решения → люди → направления → встречи). Но сложен в maintenance. Присмотреться, не внедрять сейчас.

### Подход Karpathy (LLM Wiki)

LLM читает сырые материалы → пишет wiki-статьи (человекочитаемые) → при запросе читает индекс → подтягивает нужные статьи. Обходит проблему чанкинга: статьи сохраняют полный контекст. По сути это то, что делает QMD — гибридный поиск по markdown-файлам.

Подробнее → [llm-wiki.md](llm-wiki.md)

---

## Конкретные реализации

### QMD (приоритетный кандидат)

Локальный семантический поиск по markdown. Автор — Tobi Lütke (основатель Shopify). Гибридный пайплайн: query expansion (LLM) → BM25 + vector параллельно → RRF fusion → LLM reranking. Всё локально, три GGUF-модели (~2 ГБ). MCP-сервер для Claude Code.

Подробный research → [../../lab/_inbox/qmd-research.md](../../lab/_inbox/qmd-research.md)

**Почему приоритетный:** проверенный автор, полный гибридный пайплайн, работает поверх файловой системы (не нужна отдельная БД), MCP-интеграция, рекомендован Karpathy.

### MemPalace (хайп-проект, исследован 2026-04-09)

Open source (MIT), заявлено 96.6% на LongMemEval. Verbatim storage в ChromaDB + метадатная фильтрация ("дворец": wings/halls/rooms). Авторы — актриса Milla Jovovich (лицо проекта, 7 коммитов) и Ben Sigman (CEO крипто-компании). В первые 24 часа — pump-and-dump крипто-токена.

**Что в коде vs что заявлено:** hybrid scoring и reranking существуют только в бенчмарк-скриптах, не в продукте. Продукт = голый ChromaDB vector search. Независимый тест — 17% accuracy в реальном использовании. При добавлении system prompt accuracy падает с 89.8% до 1.0% (issue #333). 96 открытых issues.

**Инсайт верный:** verbatim storage + хороший поиск конкурентоспособен с LLM-extraction. Реализация ненадёжная.

### Другие

- **Graphiti (Zep)** — temporal knowledge graph на Neo4j. Зрелый, облачный. $25+/мес. Подробнее → [temporal-graphs.md](temporal-graphs.md)
- **LlamaIndex** — фреймворк для RAG-пайплайнов. Много интеграций, но тяжёлый
- **LangChain** — оркестрация. Широко используется, но критикуется за overengineering
- **ChromaDB** — простейшая vector DB. Хорошо для прототипов, слабо для production (HNSW bloat)
- **Weaviate, Qdrant, Pinecone** — production-grade vector DB с hybrid search

---

## Бенчмарки

| Бенчмарк | Что измеряет | Статус (2026) |
|---|---|---|
| **LongMemEval** | Recall фактов из долгих диалогов | Широко используется, 500 вопросов |
| **LoCoMo** | Multi-hop reasoning по разговорам | 1986 QA пар |
| **mtRAG** (IBM) | Multi-turn RAG, 842 задачи | SemEval 2026, зрелый |
| **RAGBench** | Retrieval + generation, 100K примеров | Широко используется |
| **GraphRAG-Bench** | Когда графы нужны в RAG | ICLR 2026 |
| **CRAG** | Contextual relevance + grounding | Академический стандарт |

Метрики: faithfulness (не придумывает), relevancy (отвечает на вопрос), completeness (не пропускает), naturalness (читабельно). Измерение: LLM-as-judge + human annotation.

---

## Связь с архитектурой SVAIB

В контекстной архитектуре Second AI Brain (→ [workbench.md](../../framework/_inbox/context-memory/workbench.md)) RAG занимает позицию **неструктурированного поиска** — когда агент не знает маршрут и ищет по смыслу. Два режима:

1. **Структурированный** (ICM) — задача понятна, маршрут известен, агент идёт по рельсам. RAG не нужен
2. **Неструктурированный** — вопрос открытый, агент ищет. RAG = основной инструмент

Наш паттерн ближе всего к Agentic RAG: агент решает когда искать (а не ищет всегда), комбинирует grep + RAG + чтение файлов, останавливается по достаточности.

Приоритетная реализация для тестирования: QMD (→ [lab/_inbox/qmd-research.md](../../lab/_inbox/qmd-research.md)).

---

## Источники

- [The Ultimate RAG Blueprint 2025/2026](https://langwatch.ai/blog/the-ultimate-rag-blueprint-everything-you-need-to-know-about-rag-in-2025-2026) — LangWatch
- [RAG vs Long Context](https://www.mindstudio.ai/blog/1m-token-context-window-vs-rag-claude) — MindStudio
- [Standard RAG Is Dead: Architecture Split in 2026](https://ucstrategies.com/news/standard-rag-is-dead-why-ai-architecture-split-in-2026/)
- [Hybrid Search & Production Hardening](https://aboullaite.me/rag-revisited-2026/)
- [mtRAG Benchmark](https://research.ibm.com/blog/conversational-RAG-benchmark) — IBM Research
- [Agentic RAG Survey](https://arxiv.org/abs/2501.09136) — arxiv
- [GraphRAG-Bench (ICLR 2026)](https://github.com/GraphRAG-Bench/GraphRAG-Benchmark)
- [Karpathy LLM Knowledge Base](https://ghost.codersera.com/blog/karpathy-llm-knowledge-base-second-brain/) — codersera
- [ColBERT Late Interaction](https://weaviate.io/blog/late-interaction-overview) — Weaviate
- [From RAG to Context](https://ragflow.io/blog/rag-review-2025-from-rag-to-context) — RAGFlow
- [RAG is Dead, Long Live RAG](https://lighton.ai/lighton-blogs/rag-is-dead-long-live-rag-retrieval-in-the-age-of-agents) — LightOn

## Связанные файлы

- [!context.md](!context.md) — сводка по context engineering (RAG как одно из направлений)
- [agent-memory.md](agent-memory.md) — архитектуры памяти AI-агентов (RAG = одна из стратегий retrieval)
- [llm-wiki.md](llm-wiki.md) — подход Karpathy к персональной памяти
- [search-mechanics.md](search-mechanics.md) — как AI-инструменты ищут файлы на практике
- [temporal-graphs.md](temporal-graphs.md) — Graphiti, Hindsight (альтернатива RAG для темпоральных данных)
- [../../lab/_inbox/qmd-research.md](../../lab/_inbox/qmd-research.md) — QMD research и план внедрения
