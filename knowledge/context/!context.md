---
title: "Context Engineering, RAG, Memory — сводка знаний"
status: processed
added: 2026-01-30
updated: 2026-04-09
review_by: 2026-06-20
tags: [context-engineering, rag, memory, temporal-graphs, extraction, ai-dotfiles, index, progressive-disclosure, google-drive, integrations, icm, hybrid-search, agentic-rag, graphrag]
publish: false
version: 17
---

# Context — Context Engineering, RAG, Memory

## Кратко

Дисциплина управления информацией, которую получает AI. Context Engineering — эволюция промптинга: не просто "как спросить", а "какой набор информации даст нужный результат". Включает: RAG (Retrieval-Augmented Generation — подтягивание релевантных документов), управление памятью, работу с контекстным окном, стратегии против "context rot" (деградация качества при перегрузке контекста). Ключевой принцип: контекстное окно — ограниченный ресурс, каждый токен должен быть полезен.

Знания о context engineering, RAG и memory — рабочий материал для продукта SVAIB (см. product_vision.md).

**Профайл:** Методологическая карта — концепции, архитектуры, принципы. Сюда: теория и классификации (что такое RAG, какие бывают архитектуры памяти, что такое context rot). Как это реализовано в конкретных продуктах (Claude Code, Cursor, Projects, ChatGPT) → [search-mechanics.md](search-mechanics.md).

## Ключевые направления

### Архитектуры памяти AI-агентов — широкая карта

Память агента можно организовать по-разному. Пять основных архитектур хранения: Knowledge Graph (явные связи между сущностями), Hierarchical (слои от деталей к обобщениям), Temporal Graph (факты с временными метками), Hypergraph (связи на 3+ узлов — групповые взаимодействия), Hybrid (комбинация). Жизненный цикл: extraction → storage → retrieval → evolution. Подробная карта архитектур, стратегий поиска, эволюции памяти и бенчмарков → [agent-memory.md](agent-memory.md).

### RAG (Retrieval-Augmented Generation)
Паттерн подачи AI релевантной информации из внешнего хранилища: чанкинг → эмбеддинги → vector store → retrieval → LLM. Стандартный RAG (один вектор) устарел — работающий пайплайн 2026: гибридный поиск (BM25 + vector + RRF fusion + cross-encoder reranker). Три направления эволюции: Agentic RAG (агент решает что искать), GraphRAG (поиск по графу связей), подход Karpathy (wiki-статьи вместо чанков). Для SVAIB: RAG = реализация неструктурированного поиска в контекстной архитектуре. Подробная карта подходов, реализаций (QMD, MemPalace, GraphRAG), бенчмарков → [rag.md](rag.md).

### Extraction — извлечение сущностей из текста

Шаг extraction в жизненном цикле памяти: unstructured text → structured entities. Задача: взять документ (протокол, заметку, отчёт) и вытащить конкретные сущности (цели, решения, люди, задачи) в структурированном формате.

**[langextract](https://github.com/google/langextract)** (Google, Apache 2.0) — Python-библиотека для LLM-based extraction. Chunking + параллельная обработка + multi-pass для длинных документов. Source grounding — каждый извлечённый факт привязан к позиции в тексте. Адаптация под домен через few-shot примеры, без fine-tuning. Поддержка: Gemini (основной), OpenAI, Ollama. Устанавливается через pip, можно интегрировать в скилл или субагент. Для SVAIB: кандидат на extraction-слой при массовой обработке документов клиента по онтологии.

### Temporal Knowledge Graphs — память с пониманием времени
Одна из пяти архитектур хранения памяти агентов (→ [agent-memory.md](agent-memory.md)). Решает ключевое ограничение обычного RAG — отсутствие темпоральности. Каждый факт/отношение имеет временные метки, конфликты разрешаются через invalidation. Bi-temporal model различает "когда произошло" и "когда узнали". Критично для продукта SVAIB: решения на встречах обновляются, AI должен знать что актуально сейчас. Два живых фреймворка: Graphiti (Zep, Neo4j, MCP-сервер) и Hindsight (Vectorize.io, PostgreSQL, биомиметическая память). Подробнее → [temporal-graphs.md](temporal-graphs.md). Практический опыт работы с Graphiti (метрики, кейсы, оптимизация) → [temporal-graphs-doronin.md](temporal-graphs-doronin.md)

### AI System Files — конфигурационные файлы для AI-ассистентов

Каждый AI coding-ассистент использует конфигурационные файлы двух типов: **инструкции** (CLAUDE.md, AGENTS.md, GEMINI.md — "как работать с проектом") и **персона/память** (soul.md, identity.md, memory.md — "кто ты и что помнишь"). Все сходятся на Markdown и иерархической загрузке по директориям. AGENTS.md движется к кросс-платформенному стандарту через AAIF (Linux Foundation, основатели: Anthropic, OpenAI, Block). Подробная карта 13 инструментов, кросс-чтение файлов, best practices, anti-patterns и лимиты → [ai-system-files.md](ai-system-files.md).

### File-based Memory (MD-файлы как память)

Файлы — «нулевой уровень» памяти агента (аудируемость, git-diff, ручная правка). Спектр уровней: 0 — статические инструкции (CLAUDE.md) → 1 — авто-память (MEMORY.md) → 2 — файлы + семантический поиск (OpenClaw memsearch) → 3 — внешние API (Mem0) → 4 — темпоральные графы (Graphiti/Zep). Индексация и графы — надстройки, но source of truth остаётся в редактируемых файлах. Подробнее о спектре → [ai-system-files.md](ai-system-files.md).

Паттерн персоны из OpenClaw: soul.md (ядро личности), identity.md (внешняя подача), user.md (контекст пользователя), memory.md (накопленные факты). Разделение «кто агент» от «что агент делает» — архитектурный паттерн, позволяющий ревьюить изменения в «душе» отдельно от «памяти». → [../tools/openclaw.md](../tools/openclaw.md)

### LLM Wiki — вики, поддерживаемая LLM

Паттерн (Karpathy, 2026): вместо RAG по сырым источникам — LLM инкрементально компилирует markdown-вики. Три операции: **Ingest** (обработать источник → обновить 10-15 страниц), **Query** (ответ на вопрос становится страницей вики — знание компаундится), **Lint** (периодический аудит целостности: противоречия, устаревшие факты, осиротевшие страницы). Ключевой инсайт: LLM отлично справляется с бухгалтерией знаний (кросс-ссылки, консистентность), от которой человек отказывается из-за экспоненциального роста maintenance burden. Паттерн работает на уровнях 0-1 спектра (markdown + git, без БД). Вызвал волну реализаций: llm-wiki-kit (MCP), sage-wiki, memex, atomic-knowledge. Подробнее → [llm-wiki.md](llm-wiki.md)

### Context Graphs — институциональная память решений

Концепция Foundation Capital (Ashu Garg, январь 2026): context graph = живая карта того, КАК организация принимает решения. "Decision traces" — записи reasoning за решениями (какие исключения, какой прецедент, кто одобрил). Модели commoditize, а decision traces — компаундящий proprietary актив. Агенты создают traces автоматически: траектория агента по системам = decision trace. Со временем из траекторий возникает мировая модель организации. Открытые вопросы: темпоральность (→ решается через [temporal-graphs.md](temporal-graphs.md)), governance, где хранить граф. Для SVAIB: наш framework/ontology — по сути context graph для CEO. Подробнее → [context-graphs.md](context-graphs.md).

### Реализация в приложениях

Теория выше описывает механизмы (RAG, temporal graphs, file-based memory). Как это реализовано в конкретных AI-инструментах (Claude Code, Cursor, Claude Projects, ChatGPT Projects) — механики поиска, уровни доступа, практические выводы для организации файлов → [search-mechanics.md](search-mechanics.md).

### Интеграция Google Drive + Claude Projects + Cowork

Тестирование (март 2026) выявило ключевой зазор в экосистеме Anthropic: что Cowork умеет писать (.docx, .md) — Claude в Projects не видит автоматически. Что Claude видит автоматически (нативные Google Docs) — Cowork не умеет писать. Целевая архитектура для клиентов SVAIB: клиент пишет в Google Docs → скрипт синхронизации → GitHub-репо (markdown) → Claude Project видит через RAG. Матрица совместимости форматов, варианты мостов → [claude_integrations_gdrive.md](claude_integrations_gdrive.md).

### Оптимизация Markdown-файлов для LLM и RAG

Консолидированное исследование (3 модели, февраль 2026) выявило ключевые принципы написания файлов, которые одинаково хорошо работают для человека, LLM и RAG-систем. Семь главных находок (все — консенсус или подтверждены бенчмарками): `description` в YAML — самое ценное одиночное улучшение для discovery; "summary first" из-за Lost in the Middle (-20%+ точности в середине контекста); каждая H2-секция — автономный чанк с повторением субъекта (-35% ошибок поиска, Anthropic Contextual Retrieval); структурный чанкинг по заголовкам превосходит семантический (70.5% vs 63.8%); YAML обрабатывается LLM как текст, не как структурированные данные; <300 строк, таблицы <20 строк, вложенность ≤2. Подробнее → [markdown-for-llm.md](markdown-for-llm.md).

### Механики поиска AI-инструментов

Консолидированное исследование (3 модели, февраль 2026) по тому, как три основных инструмента технически находят файлы. Claude Code — агентный grep без индекса (Boris Cherny: "outperformed everything else by a lot"). Cursor — облачный semantic index (tree-sitter → Turbopuffer). Claude Projects — full context (<200K) или автоматический RAG (>200K, предположительно Contextual Retrieval). Главный вывод: имя файла — единственная оптимизация, работающая везде; Claude Code "ходит" по ссылкам, Cursor "сканирует" по смыслу. Оптимизировать файлы нужно под grep И embedding одновременно. Подробнее → [search-mechanics.md](search-mechanics.md).

### ICM — оркестрация через файловую структуру

ICM (Van Clief, McDermott, 2026) — методология, где файловая система заменяет code-level оркестрацию агентов. Порядок папок = последовательность этапов, содержимое папки = контекст этапа. Пять принципов (one stage one job, plain text interface, layered context loading, every output is an edit surface, configure the factory not the product) и пятислойная иерархия контекста (Layer 0-4: identity → routing → stage contract → reference → working). Ключевые инсайты: разделение reference (стабильные правила, internalize) vs working (per-run данные, transform) — разное когнитивное задание для модели; stage contracts как декларативный критерий достаточности контекста; токен-бюджеты ~5k vs ~42k показывают что staged loading в разы эффективнее монолитного. Работает для sequential workflows с human review; не работает для динамической навигации по произвольным задачам. Подробнее → [icm.md](icm.md)

### Navigation & Progressive Disclosure — как агент навигирует знания

Паттерны послойной навигации по файлам знаний: агент начинает с дешёвых операций (file tree, YAML descriptions) и углубляется только по необходимости (MOC hierarchy → wiki-link traversal → full content). Результат: минимум контекста при максимуме пользы. Навигация отвязана от файловой структуры — файлы находятся по связям, а не по путям. Формализовано как "skill graph" (Heinrich/@arscontexta, 2026) — по сути context engineering, хотя название отсылает к skills. Архитектура, элементы, верифицированная реализация → [skill-graphs/](skill-graphs/).

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
- [../tools/openclaw.md](../tools/openclaw.md) — пример архитектуры с Memory-компонентом (слабая темпоральность)
- [markdown-for-llm.md](markdown-for-llm.md) — анатомия Markdown-файла для человека + LLM + RAG (YAML, структура, чанкинг, связи)
- [search-mechanics.md](search-mechanics.md) — как Claude Code, Cursor, Claude Projects и ChatGPT ищут файлы (механики поиска, уровни доступа)
- [ai-system-files.md](ai-system-files.md) — карта конфигурационных файлов для AI-ассистентов: 13 инструментов, AGENTS.md стандарт, паттерн персоны, best practices
- [skill-graphs/skill-graphs.md](skill-graphs/skill-graphs.md) — Skill Graphs: навигация по знаниям, progressive disclosure, wikilinks (arscontexta)
- [skill-graphs/architecture.md](skill-graphs/architecture.md) — архитектура: Three-Space, 6Rs pipeline, hooks, верифицированный progressive disclosure
- [icm.md](icm.md) — ICM (Van Clief, 2026): оркестрация агентов через файловую структуру, 5 слоёв контекста, stage contracts, reference vs working
- [llm-wiki.md](llm-wiki.md) — LLM Wiki (Karpathy): паттерн инкрементальной вики — Ingest/Query/Lint, комьюнити-реализации, связь с arscontexta и ICM
- [claude_integrations_gdrive.md](claude_integrations_gdrive.md) — Google Drive + Claude Projects + Cowork: матрица совместимости, зазоры чтения/записи, мосты, целевая архитектура для клиентов
