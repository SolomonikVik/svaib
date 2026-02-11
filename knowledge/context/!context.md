---
title: "Context Engineering, RAG, Memory — сводка знаний"
status: processed
added: 2026-01-30
updated: 2026-02-11
review_by: 2026-05-11
tags: [context-engineering, rag, memory, temporal-graphs, index]
publish: false
version: 3
---

# Context — Context Engineering, RAG, Memory

## Кратко

Дисциплина управления информацией, которую получает AI. Context Engineering — эволюция промптинга: не просто "как спросить", а "какой набор информации даст нужный результат". Включает: RAG (Retrieval-Augmented Generation — подтягивание релевантных документов), управление памятью, работу с контекстным окном, стратегии против "context rot" (деградация качества при перегрузке контекста). Ключевой принцип: контекстное окно — ограниченный ресурс, каждый токен должен быть полезен.

Знания о context engineering, RAG и memory — рабочий материал для продукта SVAIB (см. product_vision.md).

## Ключевые направления

### RAG (Retrieval-Augmented Generation)
Подтягивание релевантных документов в контекст AI перед генерацией ответа. Базовый подход: vector store + embeddings + similarity search. Ограничение: не понимает время — все chunks равнозначны.

### Temporal Knowledge Graphs — память с пониманием времени
Продвинутый подход к памяти AI-агентов, решающий ключевое ограничение обычного RAG — отсутствие темпоральности. Каждый факт/отношение имеет временные метки, конфликты разрешаются через invalidation. Bi-temporal model различает "когда произошло" и "когда узнали". Критично для продукта SVAIB: решения на встречах обновляются, AI должен знать что актуально сейчас. Два живых фреймворка: Graphiti (Zep, Neo4j, MCP-сервер) и Hindsight (Vectorize.io, PostgreSQL, биомиметическая память). Подробнее → [temporal-graphs.md](temporal-graphs.md). Практический опыт работы с Graphiti (метрики, кейсы, оптимизация) → [temporal-graphs-doronin.md](temporal-graphs-doronin.md)

### Context Window Management
Управление ограниченным контекстным окном: что включить, что опустить, когда сжимать. Стратегии: progressive summarization, context rotation, priority-based selection.

### Context Rot
Деградация качества ответов при перегрузке контекста нерелевантной информацией. Больше контекста ≠ лучше. Нужна фильтрация и приоритизация.

## Связанные файлы

- [temporal-graphs.md](temporal-graphs.md) — Temporal Knowledge Graphs: Graphiti, Hindsight, bi-temporal model
- [temporal-graphs-doronin.md](temporal-graphs-doronin.md) — Graphiti на практике (опыт @kdoronin_blog)
- [../agents/!agents.md](../agents/!agents.md) — агентные системы (Memory как компонент)
- [../agents/openclaw.md](../agents/openclaw.md) — пример архитектуры с Memory-компонентом (слабая темпоральность)
