---
title: "Архитектуры памяти AI-агентов — обзорная карта"
source: "https://arxiv.org/abs/2602.05665"
source_type: article
status: processed
added: 2026-02-16
updated: 2026-02-16
review_by: 2026-05-16
tags: [agent-memory, knowledge-graph, temporal-graph, hypergraph, retrieval, benchmarks]
publish: false
version: 1
---

# Архитектуры памяти AI-агентов — обзорная карта

## Кратко

Систематизация подходов к памяти AI-агентов на основе survey "Graph-based Agent Memory: Taxonomy, Techniques, and Applications" (arxiv 2602.05665, февраль 2026). Четыре фазы жизненного цикла памяти: extraction → storage → retrieval → evolution. Пять архитектур хранения: Knowledge Graph, Hierarchical, Temporal Graph, Hypergraph, Hybrid. Каталог работ по теме: [Awesome-GraphMemory](https://github.com/DEEP-PolyU/Awesome-GraphMemory).

Для deep dive по temporal graphs (Graphiti, Hindsight) → [temporal-graphs.md](temporal-graphs.md).

---

## Жизненный цикл памяти агента

```
Extraction → Storage → Retrieval → Evolution
(что запомнить)  (как хранить)  (как найти)   (как обновлять)
```

---

## 1. Extraction — что запоминать

Три типа источников:

| Тип | Что извлекается |
|-----|----------------|
| **Textual** | Сущности, факты, отношения из текста |
| **Sequential** | Последовательности событий с учётом порядка |
| **Multimodal** | Интеграция текста + изображений + аудио |

---

## 2. Storage — как хранить (пять архитектур)

| Архитектура | Суть | Когда применять | Примеры систем |
|---|---|---|---|
| **Knowledge Graph** | Граф (entity → relation → entity). Явные семантические связи | Фактические отношения, справочники, structured knowledge | MemLLM, AriGraph, G-Mem |
| **Hierarchical** | Многоуровневая организация: детали внизу, обобщения наверху | Zoom in/out — от стратегии до конкретной задачи | HiAgent, TiMem |
| **Temporal Graph** | Узлы и связи с временными метками. Инвалидация устаревшего | Когда критичен порядок событий, "что актуально сейчас" | Graphiti/Zep, MemoTime, MAGMA |
| **Hypergraph** | Одна связь на 3+ узлов. Групповые взаимодействия | Совещания, многосторонние отношения | HyperGraph-RAG |
| **Hybrid** | Комбинация нескольких парадигм | Сложные системы, где один тип не хватает | MAGMA (multi-graph), OPTIMUS |

### Примечательные системы

**AriGraph** — объединяет knowledge graph + episodic memory (воспоминания о действиях агента). Semantic facts + что делал и что получилось.

**MAGMA** — мульти-граф: одна информация представлена параллельно в semantic, temporal, causal и entity графах. Каждое измерение отвечает за свой тип запросов.

**Zep/Graphiti** — трёхуровневая иерархия: episode subgraph (что произошло) → semantic entity subgraph (факты о сущностях) → community subgraph (кластеры). Подробнее → [temporal-graphs.md](temporal-graphs.md).

**TiMem** — temporal-hierarchical: консолидация памяти слоями, как в нейронауке (working memory → episodic → semantic).

---

## 3. Retrieval — как искать в памяти

От простых к продвинутым:

| Стратегия | Описание |
|---|---|
| **Similarity-based** | Классический RAG: embeddings + nearest neighbor |
| **Rule-based** | Логические запросы, предопределённые паттерны (SPARQL) |
| **Graph-based** | Обход графа по связям (traversal) |
| **Temporal-based** | Поиск по временным меткам и отношениям (до/после/в период) |
| **RL-based** | Reinforcement learning: агент учится что вспоминать |
| **Agent-based** | Отдельный агент-поисковик решает что извлекать |
| **Multi-round** | Итеративный поиск с уточнением |
| **Post-retrieval** | Ранжирование и фильтрация после извлечения |
| **Multi-source** | Комбинация из нескольких хранилищ |

---

## 4. Evolution — как память обновляется

| Тип | Описание |
|---|---|
| **Internal self-evolving** | Агент сам пересматривает память: рефлексия, суммаризация, поиск паттернов, удаление устаревшего. Аналог Hindsight "Reflect" |
| **External self-exploration** | Обучение через взаимодействие со средой: агент исследует, набирает опыт, адаптирует память на основе feedback |

---

## 5. Бенчмарки — как оценивать память агентов

| Benchmark | Что оценивает | Данные |
|---|---|---|
| **LoCoMo** | Long conversational memory | Text + Image, multi-session |
| **LongMemEval** | Долгосрочное запоминание и recall | Interactive sequences |
| **MemoryAgentBench** | Память в multi-turn взаимодействиях | Multi-turn agent tasks |
| **MEMTRACK** | Память в технических средах | Code + Logs |
| **MADial-Bench** | Memory-augmented диалоги | Dialogue systems |
| **MemSim** | Байесовская симуляция когнитивной памяти | Cognitive modeling |
| **MMRC** | Мультимодальные разговоры | Text + Image |

---

## 6. Области применения

- Персональные ассистенты (multi-session chat, proactive interaction)
- Анализ документов и knowledge work
- Робототехника (long-horizon планирование)
- Multi-agent координация
- Gaming и simulation (open-world)
- Финансы, здравоохранение (domain-specific long-term memory)

---

## Ключевой инсайт

Графовая память превосходит flat storage (обычный RAG) за счёт: структурированных связей (не "похожий текст", а явные отношения), temporal reasoning (причинно-следственные цепочки), hierarchical organization (zoom in/out), causal tracking (что привело к чему).

---

## Источники

- [Survey: Graph-based Agent Memory (arxiv 2602.05665)](https://arxiv.org/abs/2602.05665)
- [Awesome-GraphMemory (GitHub)](https://github.com/DEEP-PolyU/Awesome-GraphMemory) — каталог papers, бенчмарков, инструментов по теме
- Пост Константина Доронина (@kdoronin_blog) — рекомендация survey

## Связанные файлы

- [temporal-graphs.md](temporal-graphs.md) — deep dive по Temporal Graph: Graphiti, Hindsight, bi-temporal model
- [temporal-graphs-doronin.md](temporal-graphs-doronin.md) — Graphiti на практике (опыт @kdoronin_blog)
- [!context.md](!context.md) — сводка по Context Engineering, RAG, Memory
- [../agents/!agents.md](../agents/!agents.md) — агентные системы (Memory как компонент)
- [../agents/feedback-loop-evolution.md](../agents/feedback-loop-evolution.md) — пересекается с Memory Evolution
