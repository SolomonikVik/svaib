# Context — Context Engineering, RAG, Memory

Управление информацией для AI: RAG, память, контекстное окно, стратегии против context rot.

**Границы:** Сюда — КАК обеспечить AI нужной информацией. НЕ сюда: КАК сформулировать запрос (-> prompting/), конкретная структура knowledge/ (-> knowledge/README.md).

## Файлы

- [!context.md](!context.md) — сводка знаний
- [agent-memory.md](agent-memory.md) — обзорная карта: 5 архитектур хранения, 9 стратегий поиска, бенчмарки (survey arxiv 2602.05665)
- [temporal-graphs.md](temporal-graphs.md) — deep dive: Graphiti, Hindsight, bi-temporal model
- [temporal-graphs-doronin.md](temporal-graphs-doronin.md) — Graphiti на практике: метрики, кейсы, оптимизация (опыт @kdoronin_blog)

- [context-graphs.md](context-graphs.md) — Context Graphs: decision traces, траектории агентов, институциональная память (Foundation Capital)
- [markdown-for-llm.md](markdown-for-llm.md) — Анатомия Markdown-файла для человека + LLM + RAG: YAML, структура, чанкинг, связи (консолидация 3 исследований)
- [search-mechanics.md](search-mechanics.md) — Как Claude Code, Cursor, Claude Projects и ChatGPT Projects ищут файлы: механики поиска, уровни доступа, практические выводы

- [ai-system-files.md](ai-system-files.md) — AI System Files: карта конфигурационных файлов для AI-ассистентов (CLAUDE.md, AGENTS.md, soul.md), стандартизация AAIF, best practices, архитектура памяти через файлы

**Кросс-ссылки:**
- [../skills/skill-graphs/](../skills/skill-graphs/) — Skill Graphs (arscontexta): навигация агента по знаниям, progressive disclosure, wikilinks. Живёт в skills/, но контент на 85%+ про context engineering

**Как файлы связаны:** agent-memory.md — широкая карта всех подходов к памяти агентов. temporal-graphs.md — глубокое погружение в один конкретный подход (Temporal Graph). temporal-graphs-doronin.md — практика работы с Graphiti. context-graphs.md — бизнес-концепция: зачем организации нужна память решений, открытый вопрос темпоральности решается через temporal-graphs. markdown-for-llm.md и search-mechanics.md — пара: первый про КАК писать файлы, второй про КАК их находят AI-инструменты. ai-system-files.md — карта самих файлов (CLAUDE.md, AGENTS.md и др.): какие инструменты что читают, стандарт AGENTS.md, паттерн персоны (soul.md).
