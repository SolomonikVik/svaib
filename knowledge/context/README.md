# Context — Context Engineering, RAG, Memory

Управление информацией для AI: RAG, память, контекстное окно, стратегии против context rot.

**Границы:** Сюда — КАК обеспечить AI нужной информацией. НЕ сюда: КАК сформулировать запрос (-> prompting/), конкретная структура knowledge/ (-> knowledge/README.md).

## Файлы

- [!context.md](!context.md) — сводка знаний
- [agent-memory.md](agent-memory.md) — обзорная карта: 5 архитектур хранения, 9 стратегий поиска, бенчмарки (survey arxiv 2602.05665)
- [temporal-graphs.md](temporal-graphs.md) — deep dive: Graphiti, Hindsight, bi-temporal model
- [temporal-graphs-doronin.md](temporal-graphs-doronin.md) — Graphiti на практике: метрики, кейсы, оптимизация (опыт @kdoronin_blog)

- [context-graphs.md](context-graphs.md) — Context Graphs: decision traces, траектории агентов, институциональная память (Foundation Capital)

**Как файлы связаны:** agent-memory.md — широкая карта всех подходов к памяти агентов. temporal-graphs.md — глубокое погружение в один конкретный подход (Temporal Graph). temporal-graphs-doronin.md — практика работы с Graphiti. context-graphs.md — бизнес-концепция: зачем организации нужна память решений, открытый вопрос темпоральности решается через temporal-graphs.
