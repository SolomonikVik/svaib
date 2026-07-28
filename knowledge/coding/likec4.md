---
title: "LikeC4 — DSL для архитектуры-как-код, синтаксис и фильтрация views"
source: "https://likec4.dev"
source_type: docs
status: processed
added: 2026-07-21
updated: 2026-07-21
review_by: 2026-10-21
tags: [likec4, diagramming-as-code, c4-model, dsl, mcp, architecture-docs]
publish: false
---

# LikeC4 — DSL для архитектуры-как-код

## Кратко

LikeC4 — open-source DSL-инструмент «architecture as code»: одна текстовая модель (`.c4`-файлы) → множество интерактивных диаграмм (structural + dynamic views), валидация, MCP-сервер для агентного доступа. MIT license, активная разработка с 2023, поддерживается doubleSlash. Альтернатива Structurizr DSL / Mermaid C4 / PlantUML C4 / D2 для проектов, где архитектурная документация должна жить в git и обновляться теми же LLM-агентами, что пишут код.

## Что это и для кого

Модель описывается один раз (элементы + связи + метаданные), views — это projections/фильтры поверх неё, а не отдельные диаграммы для каждого уровня зума. Ключевое отличие от «просто DSL для рисования» (Mermaid, D2 без слоя модели): элементы типизируются свободно (`element pipeline`, `element orchestrator` — свой домен, не обязательно software-компоненты), поэтому ложится и на процессные/агентные схемы, не только на классический software C4.

Целевая аудитория — архитекторы и разработчики, которые хотят единый источник правды для диаграмм, версионируемый как код.

## Экосистема

- **CLI** (`npx likec4` или `@likec4/cli`) — `validate` (синтаксис + layout drift), `build` (статический интерактивный сайт), `export` (PNG/JPEG — требует Playwright, JSON, DrawIO, Mermaid/Dot/D2/PlantUML), `start`/`serve` (dev-сервер с live reload).
- **VS Code extension** — редактирование с подсветкой/автодополнением; при установке автоматически регистрирует MCP-сервер через нативную MCP-поддержку VS Code (stdio).
- **MCP-сервер** (`@likec4/mcp`) — 18 инструментов (проверено эмпирически на 1.59.1 через `tools/list`, не только по доке): 17 read-only query-инструментов для агента (`list-projects`, `read-project-summary`, `read-element`, `read-view`, `search-element`, `query-by-tags`/`query-by-tag-pattern`/`query-by-metadata`, `query-graph`, `find-relationships`, `find-relationship-paths` (BFS), `query-incomers-graph`/`query-outgoers-graph`, `batch-read-elements`, `subgraph-summary`, `element-diff`, `read-deployment`) + один write-инструмент `apply-semantic-layout` (меняет layout view — единственный не read-only/idempotent в наборе). Запуск: `likec4 mcp` (stdio) или `likec4 mcp --http [--port N]` (streamable HTTP, порт 33335 по умолчанию). Ограничение: через VS Code extension сервер активен только пока расширение включено.

**Проверено вживую (2026-07-21).** Протокол и данные надёжны: handshake + 4 tool-вызова (`list-projects`/`query-by-tags`/`find-relationships`/`read-view`) через сырой JSON-RPC вернули корректные структурированные данные с точным `sourceLocation` (файл+строка). **Но задокументированная команда интеграции с Claude Code сломана:** `claude mcp add likec4 -- npx -y @likec4/mcp` (именно так рекомендует likec4.dev) регистрируется, но health-check даёт `✘ Failed to connect` — пакет `@likec4/mcp@1.59.1` на npm падает через `npx -y @likec4/mcp` с `ERR_MODULE_NOT_FOUND: Cannot find package 'lodash-es'` (недостающая транзитивная зависимость, воспроизведено дважды). **Рабочий обходной путь** — регистрировать через основной CLI-пакет вместо отдельного: `claude mcp add likec4 -- npx -y likec4 mcp .` → подключается (`✔ Connected`). Не проверено — агентный сценарий использования (Claude сам решает, когда вызывать эти тулы в реальной работе, не прямой запрос).
- **File discovery** — CLI рекурсивно ищет `*.c4`/`*.likec4` от текущей папки, конфигурация не обязательна; multi-project (несколько независимых моделей в одном репозитории) поддерживается через `--project`/явный конфиг проекта.
- Дополнительно: Vite plugin, React-компоненты, Web Components — для встраивания диаграмм в свои сайты/доки.

## Синтаксис — ключевое

- `specification { element <kind> ... tag <name> ... }` — типы элементов и теги заводятся свободно под свой домен.
- `model { }` — элементы + связи (`a -> b 'label'`), вложенность контуров через `{ }`.
- `views { view <name> { include *; exclude ...; } }` — structural views, multi-scale zoom реализуется несколькими views с разной глубиной раскрытия одного и того же контура (не автоматический semantic zoom — каждый view поддерживается вручную).
- `dynamic view` — сценарии/процессы с `alt { when '...' { } else '...' { } }` — реальные ветвления, не только статические связи.
- Многострочный `description` — только через `"""..."""`, не через одинарные кавычки с переносами.

## Фильтрация views (чтобы не захламлять схему)

Прямой ответ на задачу «оставить только важное»:

- **Wildcard/scope:** `cloud.*` (только прямые дети) · `cloud.**` (все вложенные + их связи) · `cloud._` (только дети, у которых есть связи с уже видимыми элементами).
- **По тегам:** `exclude element.tag = #draft` / `include element.tag != #experimental` — прямой способ скрыть черновики/экспериментальные ветки одной строкой, если теги уже заведены в модели.
- **По kind:** `include element.kind != system`.
- **`where`-условия** — комбинация по kind/tag/metadata: `include cloud.* where kind is microservice`, `exclude * where tag is #deprecated`, `include * where metadata.critical is true`.
- **Фильтрация связей** — по направлению и по metadata источника/цели: `include -> backend` (только входящие), `exclude * -> * where target.metadata.environment is "staging"`.
- **Приглушение вместо удаления** (элемент остаётся для контекста, но не доминирует): `style * { color muted; opacity 10% }`, `style deprecated element.tag = #deprecated { color muted }`.
- **`predicateGroup`** — переиспользуемый набор фильтров, объявляется в `global`, подключается в любом view одной строкой (`global predicate microservices`) — снижает трудоёмкость ручной поддержки `include`/`exclude` на масштабе.
- Порядок предикатов важен; `exclude` работает только на уже включённые элементы; `where` идёт перед `with`.

Источник синтаксиса: [likec4.dev/dsl/views](https://likec4.dev/dsl/views/), [likec4.dev/tooling/ai-tools](https://likec4.dev/tooling/ai-tools/), [likec4.dev/tooling/cli](https://likec4.dev/tooling/cli/) — дока живая, при сомнениях сверяться с ней, а не с этим файлом.

## Найденные шероховатости DSL (эмпирика, не в доке)

Молодой проект — ошибки парсера не всегда указывают на реальную причину:

- `summary` — зарезервированное слово (используется под metadata), нельзя называть так идентификатор элемента. Ошибка валидации указывала на строку на 15+ ниже настоящей причины.
- `#tag-with-hyphen` не работает — дефис конфликтует с токенизацией `->`/`<-`. Нужен camelCase/snake_case.
- Экспорт в PNG/JPEG требует Playwright (CLI сам предложит установить).
- **Bare `*` — всегда прямые дети, никогда не рекурсивно.** И в несвязанном top-level `view { include * }`, и в `view of <scope> { include * }` — `*` даёт только один уровень вниз от текущего scope (root или `<scope>` соответственно), не всё дерево. Если модель обёрнута в один корневой элемент (`company { ... }` на весь файл) — top-level `include *` без scope даёт **один узел** (сам корень), не его детей; нужен явный `include root.*` (уровень) или `root.**` (вся глубина). Если корневых элементов в модели несколько (как в первом пилоте: `lead`, `meetingAnalysis`, ... на одном уровне) — эффект не проявляется, `*` уже указывает туда, куда нужно. Проверять на `npx likec4 export json` (`nodes.length` по каждому view), не на глаз.

## Альтернативы — когда что выбирать

| Инструмент | Сильная сторона | Слабое место |
|---|---|---|
| **LikeC4** | Единая модель → много views, свободная типизация под нестандартный домен (процессы/агенты, не только software), MCP из коробки | Молодой DSL, шероховатости парсера, views поддерживаются вручную |
| **Structurizr DSL** | Строже дисциплинирует классический C4, зрелее (тоже поддерживает custom elements/archetypes/properties) | Каноническая C4-рамка менее естественна для гибридных доменов |
| **D2** | Сильнее для отдельных выразительных схем и презентаций (layers/scenarios/steps) | Слабее как общий семантический реестр архитектуры |
| **Mermaid C4** | Уже везде, где есть Mermaid (GitHub, доки) | Реализация C4 официально experimental, модель дублируется по диаграммам |
| **PlantUML C4** | Зрелый рендеринг | Многословный синтаксис, ручное сопровождение views хуже для LLM-first работы |

Практический вывод: не «один инструмент для всех схем» — LikeC4 для устойчивой архитектурной модели с несколькими связанными views, обычный Mermaid для локальных объясняющих схем внутри markdown, D2 только под отдельный выразительный визуальный артефакт.

## Наш опыт (svaib)

Пилот #1 LikeC4 на реальном контуре `meeting-analysis` — техвалидация (`validate`/`build`/`export json`) прошла на всех пяти критериях ресерча. Независимое ревью (`codex exec`) отметило: MCP и человеческая навигация не протестированы, найден дрейф модель↔реальность, воспроизводимость через `npx` без lockfile — риски и полный справочник фильтрации задокументированы в самом пилоте, решение по принятию инструмента ещё не принято. Детали: lab/_inbox/likec4-pilot-meeting-analysis/README.md.

Пилот #2 — другой домен (не product-пайплайн, а процесс/методология): схема разработки через eval (`product/evals` → `lab/eval-methodology` → `dev/evals`), вложенные контуры, dynamic view с реальным бизнес-ветвлением, тег-фильтрация на 25 узлах (два фильтра — для инженера и для продукта). Дал находку про глубину wildcard (см. «Синтаксис» выше). Детали: lab/_inbox/likec4-pilot-eval-process/README.md.

## Связанные материалы

- [ai-ready-architecture.md](ai-ready-architecture.md) — «C4-подобная иерархия» как принцип структуры кода под AI-агентов; LikeC4 — конкретный инструмент для этого слоя документации
- [ai-dev-practices.md](ai-dev-practices.md) — Documentation как одна из зон AI-ассистирования (диаграммы — часть этой зоны)
