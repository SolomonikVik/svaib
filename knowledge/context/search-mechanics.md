---
title: "Как Claude Code, Cursor и Claude Projects ищут файлы: механики поиска"
source: "consolidated research (ChatGPT, Gemini, Claude Opus 4.6)"
source_type: article
status: processed
added: 2026-02-17
updated: 2026-02-18
review_by: 2026-05-18
tags: [claude-code, cursor, claude-projects, chatgpt, search, grep, rag, embeddings]
publish: false
version: 5
---

# Как AI-инструменты ищут файлы: Claude Code, Cursor, Projects

## Кратко

Справочник по механикам поиска файлов в основных AI-инструментах. Claude Code — агентный grep без индекса. Cursor — облачный семантический индекс. Claude Projects — full context (<200K) или автоматический RAG (>200K). ChatGPT Projects — всегда RAG. Имя файла — единственная оптимизация, работающая везде. Claude Code "ходит" по ссылкам, Cursor "сканирует" по смыслу.

---

## 1. Claude Code — агентный grep без индекса

**Механизм:** Автономный агент в цикле ReAct: задача → решение что искать → инструмент → результат → следующий шаг. Каждый поиск — live-запрос через ripgrep к файловой системе. Нет предварительного индекса.

**Цикл поиска:** Glob/LS (сориентироваться) → Grep (найти по содержимому, результаты отсортированы по дате модификации) → Read (прочитать файл) → переход по ссылкам в найденных файлах → повтор.

**Ключевые инсайты:**
- **Пробовали RAG — отказались.** Ранние версии использовали Voyage embeddings. Агентный grep "outperformed everything else by a lot" (Boris Cherny, создатель Claude Code).
- **"Everything is the model"** — поиск улучшается с каждым поколением модели без изменений инфраструктуры.
- **Ведёт себя как разработчик:** если файл A ссылается на файл B — перейдёт. Если ссылки нет — может не догадаться искать дальше.
- **CLAUDE.md** загружается при старте, направляет первый шаг поиска. Иерархия: Enterprise policy → `./CLAUDE.md` → `~/.claude/CLAUDE.md` → `.CLAUDE.local.md` → child dirs on demand. Поддерживает `@path/to/import`.

**Ограничения:**
- Grep failure rate ~50% в ряде сценариев: OR-операторы в regex и сложные glob-паттерны (GitHub issue #5256).
- Нет индекса = больше токенов на каждый поиск (несколько раундов grep для одного вопроса).

---

## 2. Cursor — облачный семантический индекс

**Механизм:** При открытии проекта: tree-sitter парсит AST → чанки ~500 токенов (для неподдерживаемых языков: regex + indentation heuristics) → embedding кастомной моделью → облачная векторная БД (Turbopuffer на S3). Сырой код удаляется после embedding. При запросе (@Codebase): vector search + keyword grep → rerank (~20 фрагментов) → reason (план) → generate (топ-5 в контексте LLM). Латентность: warm ~10ms, cold ~500ms.

**Ключевые инсайты:**
- **Кастомная embedding-модель:** обучена на реальных interaction traces (не off-the-shelf), +12.5% accuracy в code retrieval.
- **Гибрид:** semantic search для концептуальных запросов + Instant Grep (v2.1) для точных паттернов. Агент сам выбирает стратегию.
- **Re-indexing через Merkle tree каждые 5-10 минут** — возможен stale data.
- **`.cursorignore` критичен:** исключение `node_modules` → индексация 5 мин → 30 сек, CPU -56%, запросы +61%. Целиться в <1000 файлов.
- **`.cursor/rules/*.mdc` НЕ влияют на индексирование** — только на поведение AI. Scope discovery контролируется через `.cursorignore` и `.gitignore`.

---

## 3. Claude Projects — full context или RAG

**Механизм:** Два режима. <200K токенов → все документы загружаются целиком в каждый разговор (идеал: нет chunking artifacts, нет retrieval misses). >200K → автоматический RAG. Ёмкость ~2M токенов (~5000 стр), файлы до 30MB.

**RAG под капотом:** Anthropic Contextual Retrieval (сентябрь 2024) — чанки ~800 токенов, каждый обогащается контекстом (50-100 токенов summary от Claude Haiku), затем hybrid semantic embeddings + BM25. Результат: **-49% ошибок поиска**, **-67% с reranking**. Семантический поиск находит статьи по теме, даже если ключевое слово отсутствует в имени файла.

### Три уровня доступа к данным

| Уровень | Видит при старте | Чтение целиком | Поиск (RAG) |
|:--------|:-----------------|:---------------|:------------|
| **System Prompt** | да, всегда в памяти | всегда целиком | — |
| **Project Files** | да, видит названия | да, `view` (до ~16K символов) | да |
| **Project Knowledge** | нет, даже названий | нет, только чанками | да |

**Project Files** — загрузка вручную, лежат в `/mnt/project/`. **Project Knowledge** — подключённые источники (GitHub и др.), попадают только в RAG-индекс.

**Ключевые инсайты:**
- В RAG-индексе Project Files и Project Knowledge **идентичны**. Разница: Project Files можно ещё и открыть целиком через `view`.
- `view` для Project Knowledge → "Path not found" (файл не существует в ФС, только чанки в индексе).
- **RAG хорош для точечных вопросов** ("какой Project ID?"), но не для целостного анализа ("проанализируй всю архитектуру").
- Google Docs — снимок на момент загрузки. Изменил документ — перезагрузи.

Источник: эксперимент Виктора Соломоника, февраль 2026.

---

## 4. ChatGPT Projects — всегда RAG

**Механизм:** Всегда RAG, нет режима full context. При загрузке файла: парсинг → чанки (800 токенов, overlap 400) → embedding через text-embedding-3-large → Vector Store. При запросе: hybrid search (semantic + keyword) через Reciprocal Rank Fusion, reranking, до 20 чанков в контекст.

**Ключевые инсайты:**
- **Project Instructions** = системный промпт, лимит **1500 символов** (~750-900 токенов). Единственное, что модель знает без поиска.
- **Модель приоритизирует обученные знания** над загруженными файлами — без явной отсылки к файлу может его проигнорировать.
- **Project Memory — не RAG, а pre-computed профиль:** модель автоматически извлекает "важные моменты" из чатов и инжектирует в системный промпт. Три режима: Default, Project-only (изолированная, необратимо), No Memory.
- Не показывает, какие файлы использовала при ответе.
- Лимит файлов: 20 (Plus) / 40 (Pro/Business/Enterprise). Макс. размер файла: 512 MB.

---

## 5. Сравнительная таблица

| Характеристика | Claude Code | Cursor | Claude Projects | ChatGPT Projects |
|:---------------|:------------|:-------|:----------------|:-----------------|
| **Тип поиска** | Агентный grep (live) | Semantic + grep (hybrid) | Full context или RAG (auto) | Hybrid RAG (semantic + keyword) |
| **Индексация** | Нет | Облачная, инкрементальная | Нет (full) / Да (RAG) | Да, при загрузке |
| **Точные термины** | ★★★★★ | ★★★★ | ★★★★ | ★★★★ |
| **Концептуальный поиск** | ★★ | ★★★★★ | ★★★★ | ★★★★ |
| **Навигация по ссылкам** | ★★★★★ | ★★ | ★★ | ★ |
| **Stale data** | Невозможно | Возможно (5-10 мин) | Невозможно | Невозможно |
| **Privacy** | Всё локально | Облако (код удаляется) | Anthropic | OpenAI |

---

## 6. Практические выводы для организации файлов

### Работает везде

| Приём | Почему работает |
|:------|:---------------|
| **Имя файла = поисковый запрос** | Grep находит по имени, embedding создаёт чёткий вектор |
| **Сильные первые 20-40 строк** (summary + keywords) | Первый чанк при RAG; первое, что читает агент |
| **Самоописывающие заголовки** | Границы чанков для RAG; грепабельные якоря для Claude Code |
| **Повторение субъекта в каждой секции** | Чанк самодостаточен при RAG; grep находит термин |
| **Консистентная терминология** | Grep не найдёт "Budget" если в файле "Cost estimation" |

### Claude Code

| Приём | Зачем |
|:------|:------|
| **Уникальные маркеры** (`[GOAL-123]`, `PROJECT-ALPHA`) | Grep находит со 100% гарантией |
| **Явные ссылки между файлами** | Агент "ходит" по ссылкам — без них может не найти |
| **Навигационный блок в начале файла** | "Детали бюджета см. в [[alpha_budget.md]]" |
| **Anchor-комментарии в коде** | `// AUTH: Main flow` — грепабельные landmarks |
| **Подсказки в CLAUDE.md** | "Auth logic is in `src/auth/`" — направляет первый шаг |

### Cursor

| Приём | Зачем |
|:------|:------|
| **Синонимы в summary/заголовках** | Embedding "мостит" между формулировками |
| **Агрессивный .cursorignore** | Меньше шума = точнее результаты |
| **Плотность информации в чанке** | Reranker оставит "Бюджет маркетинга Q3: 5000", выкинет "Бюджет: 5000" |

### Claude Projects

| Приём | Зачем |
|:------|:------|
| **System Prompt — максимум ценности** | Всё, что Claude должен знать без поиска |
| **Критичные файлы → Project Files** | Нужно чтение целиком — загружай вручную, не через GitHub |
| **Навигационный файл → Project Files** | Карта проекта, иначе Claude не увидит при старте |

### ChatGPT Projects

| Приём | Зачем |
|:------|:------|
| **Instructions — 1500 символов, каждый на счету** | Единственное без поиска |
| **Явные ссылки на файлы в запросе** | Иначе модель приоритизирует обученные знания |
| **Меньше файлов = точнее** | Full context нет, только RAG |

### Что может не сработать

- Файл в `.gitignore` / `.cursorignore` → Cursor не проиндексирует
- Только "смысловой" запрос → Claude Code через grep не зацепится
- Много YAML вверху → Claude Code выигрывает от человеческих фраз в теле
- `![[transclusion]]` и block references → невидимы для RAG

---

## Ключевое резюме

> **Cursor "сканирует" (RAG), Claude Code "ходит" (agentic browsing), Projects "знает всё" (full context) или "ищет" (RAG). Оптимизируй файлы под grep И embedding одновременно: ясные имена, ясные заголовки, явные ссылки, консистентные термины.**

---

## Связанные файлы

- [markdown-for-llm.md](markdown-for-llm.md) — как писать markdown для LLM+RAG; пара: здесь КАК ищут, там КАК писать
- [!context.md](!context.md) — сводка знаний: context engineering, RAG, memory
- [agent-memory.md](agent-memory.md) — 5 архитектур хранения, 9 стратегий поиска
- [../coding/claude-code.md](../coding/claude-code.md) — Claude Code как инструмент (функциональность, плагины)

---

## Источники

- Boris Cherny (создатель Claude Code) — Latent Space podcast + HN: отказ от RAG в пользу агентного grep
- Cursor security & codebase indexing docs — Merkle tree, embedding pipeline, Turbopuffer, .cursorignore
- Anthropic "Contextual Retrieval" (сентябрь 2024) — hybrid semantic + BM25
- Claude Code system prompt analysis — tools, two-model architecture
- Claude Projects documentation — dual-mode, 200K threshold
- Cursor v2.1 release — Instant Grep
- GitHub issue #5256 — Claude Code grep reliability
- Community benchmarks — .cursorignore impact
- Эксперимент Виктора Соломоника (февраль 2026) — Claude Projects: уровни доступа
- OpenAI docs — Vector Store, chunking, text-embedding-3-large, hybrid search
- OpenAI Help Center — ChatGPT Projects: files, instructions, memory modes
- Reverse engineering ChatGPT memory (Embrace The Red, LLMRefs)
