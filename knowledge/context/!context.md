---
title: "Context Engineering, RAG, Memory — сводка знаний"
status: processed
added: 2026-01-30
updated: 2026-02-16
review_by: 2026-05-11
tags: [context-engineering, rag, memory, temporal-graphs, index]
publish: false
version: 6
---

# Context — Context Engineering, RAG, Memory

## Кратко

Дисциплина управления информацией, которую получает AI. Context Engineering — эволюция промптинга: не просто "как спросить", а "какой набор информации даст нужный результат". Включает: RAG (Retrieval-Augmented Generation — подтягивание релевантных документов), управление памятью, работу с контекстным окном, стратегии против "context rot" (деградация качества при перегрузке контекста). Ключевой принцип: контекстное окно — ограниченный ресурс, каждый токен должен быть полезен.

Знания о context engineering, RAG и memory — рабочий материал для продукта SVAIB (см. product_vision.md).

## Ключевые направления

### Архитектуры памяти AI-агентов — широкая карта

Память агента можно организовать по-разному. Пять основных архитектур хранения: Knowledge Graph (явные связи между сущностями), Hierarchical (слои от деталей к обобщениям), Temporal Graph (факты с временными метками), Hypergraph (связи на 3+ узлов — групповые взаимодействия), Hybrid (комбинация). Жизненный цикл: extraction → storage → retrieval → evolution. Подробная карта архитектур, стратегий поиска, эволюции памяти и бенчмарков → [agent-memory.md](agent-memory.md).

### RAG (Retrieval-Augmented Generation)
Подтягивание релевантных документов в контекст AI перед генерацией ответа. Базовый подход: vector store + embeddings + similarity search. Ограничение: не понимает время — все chunks равнозначны. В таксономии памяти агентов RAG — это similarity-based retrieval, простейшая из девяти стратегий поиска (→ [agent-memory.md](agent-memory.md)).

### Temporal Knowledge Graphs — память с пониманием времени
Одна из пяти архитектур хранения памяти агентов (→ [agent-memory.md](agent-memory.md)). Решает ключевое ограничение обычного RAG — отсутствие темпоральности. Каждый факт/отношение имеет временные метки, конфликты разрешаются через invalidation. Bi-temporal model различает "когда произошло" и "когда узнали". Критично для продукта SVAIB: решения на встречах обновляются, AI должен знать что актуально сейчас. Два живых фреймворка: Graphiti (Zep, Neo4j, MCP-сервер) и Hindsight (Vectorize.io, PostgreSQL, биомиметическая память). Подробнее → [temporal-graphs.md](temporal-graphs.md). Практический опыт работы с Graphiti (метрики, кейсы, оптимизация) → [temporal-graphs-doronin.md](temporal-graphs-doronin.md)

### File-based Memory (MD-файлы как память)

Простейший подход к персистентной памяти агента: набор Markdown-файлов с разными ролями. Паттерн из OpenClaw (Clawdbot): user.md (факты о человеке), identity.md (характер бота), soul.md (системный промпт), memory.md (динамические факты + таски), bootstrap.md (онбординг, самоудаляется). Файлы вставляются в каждый запрос к LLM.

**Плюсы:** Прозрачность (можно открыть и прочитать), редактируемость, Git-friendly, не требует инфраструктуры.
**Минусы:** Растёт линейно → рост токенов → рост стоимости. Нет темпоральности (старые факты не "протухают"). Нет приоритизации — всё вставляется целиком.

Подход близок к тому, как устроены CLAUDE.md и memory в Claude Code. По сути наш framework/scaffold/ — это тот же паттерн, но структурированный через онтологию. → [../agents/openclaw.md](../agents/openclaw.md)

### Context Graphs — институциональная память решений

Концепция Foundation Capital (Ashu Garg, январь 2026): context graph = живая карта того, КАК организация принимает решения. "Decision traces" — записи reasoning за решениями (какие исключения, какой прецедент, кто одобрил). Модели commoditize, а decision traces — компаундящий proprietary актив. Агенты создают traces автоматически: траектория агента по системам = decision trace. Со временем из траекторий возникает мировая модель организации. Открытые вопросы: темпоральность (→ решается через [temporal-graphs.md](temporal-graphs.md)), governance, где хранить граф. Для SVAIB: наш framework/ontology — по сути context graph для CEO. Подробнее → [context-graphs.md](context-graphs.md).

### Context Window Management
Управление ограниченным контекстным окном: что включить, что опустить, когда сжимать. Стратегии: progressive summarization, context rotation, priority-based selection.

### Context Rot
Деградация качества ответов при перегрузке контекста нерелевантной информацией. Больше контекста ≠ лучше. Нужна фильтрация и приоритизация.

## Связанные файлы

- [agent-memory.md](agent-memory.md) — обзорная карта архитектур памяти AI-агентов (5 типов storage, 9 стратегий retrieval, бенчмарки)
- [temporal-graphs.md](temporal-graphs.md) — Temporal Knowledge Graphs: Graphiti, Hindsight, bi-temporal model
- [temporal-graphs-doronin.md](temporal-graphs-doronin.md) — Graphiti на практике (опыт @kdoronin_blog)
- [../agents/!agents.md](../agents/!agents.md) — агентные системы (Memory как компонент)
- [context-graphs.md](context-graphs.md) — Context Graphs: decision traces, траектории агентов (Foundation Capital)
- [../agents/openclaw.md](../agents/openclaw.md) — пример архитектуры с Memory-компонентом (слабая темпоральность)
