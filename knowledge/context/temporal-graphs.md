---
title: "Temporal Knowledge Graphs — память AI-агентов с пониманием времени"
source: "https://github.com/getzep/graphiti, https://github.com/vectorize-io/hindsight"
source_type: repo
status: processed
added: 2026-02-11
updated: 2026-02-11
review_by: 2026-05-11
tags: [temporal-graphs, knowledge-graph, agent-memory, graphiti, hindsight, rag]
publish: false
version: 2
---

# Temporal Knowledge Graphs — память AI-агентов с пониманием времени

## Кратко

Temporal knowledge graphs — подход к памяти AI-агентов, где каждое знание имеет временнУю метку: когда произошло, когда записано, актуально ли ещё. В отличие от обычного RAG (vector store, где все куски равнозначны), темпоральный граф разрешает конфликты во времени: "решение от 15 января отменяет решение от 10 января". Два живых фреймворка: Graphiti (Zep, крупный проект, bi-temporal model на Neo4j) и Hindsight (Vectorize.io, растущий проект, биомиметическая память на PostgreSQL). Два мёртвых: DyG-RAG и HippoRAG — paper repos без развития.

## Связь с продуктом SVAIB

Темпоральные графы — ключевая техническая гипотеза продукта (см. product_vision.md). Для AI-помощника по встречам критично: решения обновляются, задачи переносятся, статусы меняются. AI должен знать что актуально СЕЙЧАС, а не выдавать устаревшие решения. Bi-temporal model Graphiti — прямое решение этой задачи.

---

## Концепция: зачем нужна темпоральность

**Проблема обычного RAG:** Vector store хранит chunks без понятия времени. Если в документах два противоречащих решения (от 10.01 и 15.01), RAG может вернуть устаревшее — ему всё равно.

**Решение — temporal graph:**
- Каждый факт/отношение имеет временные метки (когда произошло, когда записано)
- При конфликте — более поздний факт инвалидирует ранний (не удаляет — сохраняет историю)
- Поддержка point-in-time queries: "какие решения были актуальны на 15 января?"

**Bi-temporal model** (Graphiti): два времени для каждого ребра графа:
1. **Event time** — когда событие произошло в реальном мире
2. **Ingestion time** — когда система узнала об этом
Это позволяет различать "мы узнали поздно" от "это произошло поздно".

---

## Живые фреймворки

### Graphiti (Zep) — лидер

| Параметр | Значение |
|----------|----------|
| Repo | https://github.com/getzep/graphiti |
| Масштаб | Крупный проект, одна из самых популярных agent memory библиотек |
| Лицензия | Apache-2.0 |
| Arxiv | [2501.13956](https://arxiv.org/abs/2501.13956) — "Zep: A Temporal Knowledge Graph Architecture for Agent Memory" |
| Стек | Python 3.10+, Neo4j / FalkorDB / Kuzu / Neptune |
| LLM | OpenAI, Claude, Gemini, Groq, Azure OpenAI |
| MCP-сервер | Есть — Claude и Cursor работают с графом напрямую |
| Benchmark | 94.8% DMR (vs MemGPT 93.4%), P95 latency ~300ms |

**Ключевые возможности:**
- **Real-time incremental updates** — новые данные интегрируются сразу, без batch-перестроения всего графа
- **Bi-temporal model** — каждое ребро хранит event time + ingestion time + validity interval
- **Conflict resolution** — при конфликте Graphiti использует temporal metadata для invalidation (не удаления)
- **Hybrid search** — semantic embeddings + BM25 keyword + graph traversal
- **Custom entities** через Pydantic models
- **Episodes** — данные добавляются как "эпизоды" (текст или structured JSON)

**Архитектура:**
- `graphiti_core` — основная библиотека
- `server` — FastAPI REST-сервис
- `mcp_server` — MCP-протокол для AI-ассистентов

**Связь с Zep:** Graphiti = open-source ядро. Zep = коммерческая платформа поверх (user/conversation management, dashboards, enterprise features). Graphiti можно использовать отдельно.

**Установка:**
```bash
pip install graphiti-core
# С поддержкой разных БД:
pip install graphiti-core[falkordb]
pip install graphiti-core[kuzu]
# С LLM-провайдерами:
pip install graphiti-core[anthropic,groq,google-genai]
```

---

### Hindsight (Vectorize.io) — альтернатива

| Параметр | Значение |
|----------|----------|
| Repo | https://github.com/vectorize-io/hindsight |
| Масштаб | Растущий проект, используется в production Fortune 500 |
| Лицензия | MIT |
| Arxiv | [2512.12818](https://arxiv.org/abs/2512.12818) — "Hindsight is 20/20: Building Agent Memory that Retains, Recalls, and Reflects" |
| Стек | Python / Node.js, PostgreSQL, Docker/K8s |
| LLM | OpenAI, Claude, Gemini, Groq, Ollama, LM Studio |
| Production | Fortune 500, AI-стартапы |
| Benchmark | 91.4% LongMemEval (лучший результат на момент публикации) |

**Три операции:**
1. **Retain** — запомни: LLM извлекает факты, сущности, отношения, temporal data → нормализация в канонические entities
2. **Recall** — вспомни: TEMPR (4 параллельных поиска: semantic, BM25, graph traversal, temporal filter) → Reciprocal Rank Fusion → neural reranker
3. **Reflect** — осмысли: AI анализирует накопленные воспоминания, строит ментальные модели

**Биомиметическая память (три типа):**
- **World** — факты о мире (объективные)
- **Experiences** — опыт агента (субъективные)
- **Mental Models** — выученные обобщения (синтез)

**CARA** — Coherent Adaptive Reasoning Agents: настраиваемые параметры рассуждения (skepticism, literalism, empathy).

**Отличие от Graphiti:** Hindsight больше про "обучение" агента (reflect), Graphiti — про точные темпоральные запросы. Hindsight на PostgreSQL (проще инфраструктурно), Graphiti на graph DB (мощнее для графовых запросов).

**Установка:**
```bash
pip install hindsight-client -U
# или Node.js:
npm install @vectorize-io/hindsight-client
```

---

## Мёртвые фреймворки (не использовать)

### DyG-RAG
- Repo: https://github.com/RingBDStack/DyG-RAG
- Последний коммит: декабрь 2024, минимальная активность за всю жизнь проекта
- Arxiv: 2507.13396
- Идея: event-centric dynamic graph RAG с Dynamic Event Unit (DEU)
- **Вердикт:** Paper repo. Минимальное сообщество, разработка остановилась.

### HippoRAG
- Repo: https://github.com/OSU-NLP-Group/HippoRAG
- Последний коммит: декабрь 2024, код заморожен
- Arxiv: 2405.14831 (NeurIPS '24), 2502.14802 (ICML '25)
- Идея: RAG вдохновлённый гиппокампом, knowledge graphs + personalized PageRank
- **Вердикт:** Академически ценен (NeurIPS, ICML), но код заморожен. Нет активного development.

---

## Критерий оценки фреймворков (от практика)

Формула жизнеспособности проекта (из канала по теме):
1. **Теоретическая база** — arxiv paper с описанием подхода
2. **Практическая реализация** — github с рабочим кодом
3. **Регулярные обновления** — проект живёт и развивается

Если paper есть, но код не обновляется — это "paper repo", утопия для production. Graphiti и Hindsight проходят все три критерия. DyG-RAG и HippoRAG — нет.

**Пайплайн мониторинга темы:**
- Еженедельный поиск новых публикаций по "temporal graphs + agent memory"
- Оценка по заголовку и введению → глубокое изучение через NotebookLM
- Проверка github: есть ли код, активен ли
- Разворачивание и тестирование жизнеспособных решений

---

## Сравнительная таблица

| | Graphiti | Hindsight | DyG-RAG | HippoRAG |
|---|---|---|---|---|
| Масштаб | Крупный | Растущий | Микро | Средний (академический) |
| Статус | Активен | Активен | Мёртв | Мёртв |
| База | Neo4j/FalkorDB/Kuzu | PostgreSQL | nano-graphrag | Custom |
| Фокус | Точные темпоральные запросы | Обучение + рефлексия | Event-centric graph | Hippocampus-inspired |
| MCP | Есть | Нет | Нет | Нет |
| Arxiv | 2501.13956 | 2512.12818 | 2507.13396 | 2405.14831 |
| Лицензия | Apache-2.0 | MIT | — | — |

## Связанные файлы

- [temporal-graphs-doronin.md](temporal-graphs-doronin.md) — Graphiti на практике: метрики, кейсы, оптимизация (опыт @kdoronin_blog)
- [!context.md](!context.md) — сводка по Context Engineering, RAG, Memory
- [../agents/!agents.md](../agents/!agents.md) — агентные системы (Memory как компонент)
- [../agents/openclaw.md](../agents/openclaw.md) — отсутствие темпоральности как слабость
