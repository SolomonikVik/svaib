---
title: "Target Architecture — Second Value AI Brain"
created: 2026-07-06
updated: 2026-07-17
version: 0.2
status: draft
---

# Target Architecture — Second Value AI Brain

Рабочая целевая архитектура к Product Vision: как реализовать образ AI-партнёра руководителя, который живёт в каналах, держит целостный менеджмент, сам приносит важное, отвечает на вопросы и даёт проверяемые views.

Это **не канон** и не accepted-решение. Это рабочий мост между [Product Vision](01_product-vision.md), гипотезой semantic sidecar и будущими правками канона продукта.

## Для чего файл

Файл нужен для трёх задач:

1. Дать техническому исполнителю картину, что именно строим, не превращая Vision в инженерную спецификацию.
2. Связать product-вещи из Vision с реализационными слоями: scaffold, memory, sidecar, skills/plugin, runtime, views.
3. Зафиксировать открытые решения, которые нельзя замести красивой формулой "AI-партнёр".

## Источники

- [00_masterplan.md](00_masterplan.md) — состав работы и решения по Vision.
- [01_product-vision.md](01_product-vision.md) — целевое состояние продукта.
- [02_contours/01_strategy.md](02_contours/01_strategy.md) — стратегия как координатная система управления.
- ../_inbox/memory/memory-semantic-sidecar-views.md — scaffold + semantic sidecar + generated views.
- [../architecture.md](../architecture.md) — текущий канон `Данные → Память → Помощники`, который будем эволюционировать.
- [../methodology/scaffold/01_architecture.md](../methodology/scaffold/01_architecture.md) — composable management architecture.
- [../methodology/memory/01_context_memory.md](../methodology/memory/01_context_memory.md) — текущий протокол контекстной памяти.
- [../methodology/metrics/architecture.md](../methodology/metrics/architecture.md) — extractor, маршруты, snapshot, объяснимость.
- [../05_decisions.md](../05_decisions.md) — принятые продуктовые решения.
- ../_inbox/scaffold/2026-06-30-ai-memory-engineering-patterns.md — инженерные паттерны памяти.
- ../_inbox/scaffold/2026-06-30-ai-memory-market-landscape.md — рыночные паттерны context layer / work graph.
- ../meetings/zz_archive/2026-07-06_vision_transcript.md — обсуждение Vision и архитектурных развилок.

## Главный тезис

Текущая архитектурная формула сохраняется:

```text
Данные → Память → Помощники
```

Но для целевого продукта её нужно раскрыть точнее:

```text
Sources & Truth у клиента
        ↓ extraction / connectors / indexing
Machine Context / semantic sidecar
        ↓ role routing / skills / routes / tools
Agent Execution: один AI-партнёр в разных ролях
        ↓
Channels + Views: куда партнёр приносит результат и где его можно проверить
```

`Views` не становятся четвёртым source of truth. Это read models: собранные представления для человека поверх данных, памяти и помощников.

`Runtime` не становится ядром продукта. Но target architecture должна честно признать: runtime-agnostic не значит runtime-free. Партнёру нужен исполняющий слой, который умеет запускать skills/routes, подключать источники, собирать context, доставлять сигналы в каналы и показывать views.

## Что меняется относительно текущего канона

Текущий [architecture.md](../architecture.md) говорит: "интерфейс — не наше". Для target state это уже не так.

Новая формула:

- **runtime остаётся заменяемым**;
- **модель остаётся заменяемой**;
- **source-данные клиента остаются у клиента**;
- **но каналы и views становятся частью продуктовой поверхности svaib**, потому что именно через них клиент чувствует партнёра.

Это не значит "строим большую веб-платформу". Это значит: продукт должен уметь отдавать ценность не только текстом в чате, но и проверяемыми views, briefs, traces и рабочими пространствами под задачу.

## Клиентская форма продукта

Для клиента svaib не должен выглядеть как папка, плагин или набор скиллов.

Целевая форма:

1. **Один AI-партнёр** — с ним можно говорить в привычном канале.
2. **Подключённые рабочие потоки** — встречи, документы, календарь, задачи, таблицы, почта/чаты по явному доступу.
3. **Проверяемая база** — source и ключевые документы у клиента, в открытом и переносимом виде.
4. **Views под задачу** — стратегическая карта, prep к встрече, trace расчёта, прогресс проектов, досье человека.
5. **Слой доверия** — источники, provenance, статусы свежести, права, подтверждение изменений.

Клиент может воспринимать продукт как "контакт в Telegram", "AI в рабочем чате", "личный кабинет", "view по встрече" или "папку с документами". Это каналы и поверхности. Архитектурно продукт один.

## Целевые слои

### 1. Sources & Truth

Это всё, где живёт исходная и операционная правда клиента. Не один bucket, а несколько разных типов источников.

**Source / Authoring**

Scaffold markdown, стратегические документы, цели, решения, project cards, profiles, summaries, management briefs.

Роль:
- место человеческого смысла, авторства и принятой управленческой позиции;
- то, что клиент может открыть, проверить, отредактировать и забрать;
- human-facing канон.

**Raw Episodes**

Транскрипты встреч, meeting notes, письма, входящие документы, исходные выгрузки, сообщения, записи созвонов.

Роль:
- доказательная сырьевая база;
- вход для extraction;
- не основной контекст чтения по умолчанию, пока не обработан.

**Live Systems**

Sheets, CRM, BI, календарь, трекер задач, почта, мессенджеры, meeting tools.

Роль:
- authority для изменяющихся значений: статусы, даты, значения метрик, события;
- query-time источник, если копирование в память создаёт риск устаревания.

**Truth by field**

Правду нужно задавать не на уровне "всё в markdown" или "всё в базе", а на уровне поля.

| Поле | Source of truth |
|---|---|
| `goal.statement` | стратегический source / scaffold |
| `goal.rationale` | vision / strategy brief / decision log |
| `project.summary` | project card / source document |
| `project.status` | трекер, если есть; иначе scaffold |
| `task.status` | task system; fallback scaffold |
| `meeting.raw_transcript` | raw episode |
| `meeting.summary` | processed meeting summary |
| `decision.rationale` | meeting summary / decision log |
| `metric.definition` | metrics source file |
| `metric.value` | Sheets / BI / CRM / extractor |
| `edge.project_serves_goal` | canonical source или human-confirmed sidecar edge |
| `confidence`, `derived_from`, `valid_from`, `valid_to` | machine context |

### 2. Machine Context / Semantic Sidecar

Machine Context отвечает не за то, где человек пишет смысл, а за то, как партнёр быстро и проверяемо собирает нужный контекст.

Минимальные компоненты:

- stable IDs для ключевых сущностей;
- canonical entity map: язык клиента → сущность svaib → место source;
- индексы по решениям, задачам, встречам, людям, проектам, целям;
- semantic sidecar: entities, edges, references, timestamps, provenance, confidence;
- lexical + semantic search по source;
- pointers к live systems вместо копирования volatile-значений;
- permission/censor rules;
- freshness/conflict markers.

Sidecar производный. Он может пересобираться из source и raw episodes. Он не становится самостоятельной правдой без отдельного решения.

Граница данных:

- ID, ссылки, хэши, provenance, короткие производные факты и статусы связей могут жить в машинном слое.
- Chunks, embeddings и реконструируемый клиентский текст считаются клиентскими данными, пока не принято иное решение.
- Если машинный слой живёт у svaib, нужно отдельно решить, какие данные допустимо хранить вне клиентского контура.

### 3. Agent Execution / Один партнёр в ролях

Клиент видит одного партнёра. Внутри это маршрутизация ролей и workflows.

Базовые элементы:

- **Partner shell** — единая личность, тон, границы, управление диалогом.
- **Task classifier / router** — понимает задачу, scope, нужную роль и маршрут.
- **Domain roles** — Strategy, Meetings, Metrics, Projects, Team, Finance, Product, Marketing, Sales.
- **Routes** — проверенные пути "вопрос → контекст → инструменты → ответ".
- **Tools** — extractor, calculator, search, sidecar query, view builder, write-back proposal.
- **Guards** — права, censor, source freshness, no-silent-write, no-autonomous-irreversible-action.

Принцип:

```text
one partner outside
many bounded workflows inside
```

Роли не должны превращаться в маркетплейс помощников. "Стратег", "аналитик встреч", "метрик-аналитик" — это внутренние способы думать и действовать, а не отдельные персонажи для клиента.

### 4. Channels

Каналы — это органы чувств и доставки партнёра.

Кандидаты:

- Telegram / messenger;
- email;
- calendar;
- meeting tool;
- web / local dashboard;
- generated HTML view;
- voice later.

Открытая граница: доступ к каналу должен быть явным. Например, почта может подключаться не как "читай всё по умолчанию", а как "держу партнёра в копии" или "разрешаю читать выбранные треды/лейблы". Это продуктовая граница доверия, а не только техническая настройка.

Во всех каналах партнёр должен быть одним и тем же:

- помнить линию разговора;
- уважать права и видимость;
- не создавать отдельную правду в каждом канале;
- доставлять результат туда, где клиент живёт.

### 5. Views / Read Models

Views — это собранные под задачу представления для человека. Они используют source, sidecar и execution, но не являются source of truth.

Первые целевые views:

- **Strategic management map** — цели, метрики, инициативы, владельцы, встречи, решения, drift.
- **Meeting prep view** — повестка, предыдущие решения, открытые вопросы, связанные цели/проекты/люди.
- **Project progress view** — прогресс, блокеры, решения, связь с целями.
- **Metric trace view** — число, источник, расчёт, интерпретация, соседние решения/проекты.
- **Person / owner view** — ответственность, проекты, задачи, риски, история решений, доступный уровень чувствительности.
- **Decision trace** — что решили, почему, где источник, что это поменяло.

Требования к view:

- показывает source/provenance;
- показывает freshness/confidence, если вывод производный;
- не хранит самостоятельную правду;
- write-back идёт в source через подтверждённый маршрут;
- может быть статическим HTML на ранней стадии и интерактивным workspace позже.

## Управленческая онтология

Нужен не generic knowledge graph, а узкая executive ontology.

Первые сущности:

| Entity | Зачем нужна |
|---|---|
| `Goal / KR` | куда идём и чем проверяем движение |
| `Strategic Choice / Bet` | что выбрали делать и не делать |
| `Project / Initiative` | чем двигаем цели |
| `Task` | что должно быть сделано |
| `Meeting` | где обсуждали и что изменилось |
| `Decision` | что решили и почему |
| `Metric` | чем измеряем |
| `Person` | кто владеет и влияет |
| `Unit` | чем управляем |
| `Document / Episode / Chunk` | откуда взят факт |

Первые рёбра:

| Edge | Статус на старте |
|---|---|
| `goal_has_metric` | желательно canonical |
| `project_serves_goal` | human-confirmed или canonical |
| `task_belongs_to_project` | extracted / human-confirmed |
| `person_owns_project` | canonical / human-confirmed |
| `person_owns_metric` | canonical / human-confirmed |
| `meeting_mentions_entity` | extracted |
| `meeting_produces_decision` | extracted / human-confirmed |
| `decision_affects_goal` | human-confirmed |
| `decision_affects_metric` | human-confirmed |
| `project_has_meeting` | extracted |
| `unit_contains_project` | canonical |
| `source_supports_fact` | system-generated |

Статусы доверия для фактов и рёбер:

- `extracted` — вытащено из источника;
- `inferred` — машина предположила по контексту;
- `human-confirmed` — человек подтвердил;
- `canonical` — зафиксировано в source of truth;
- `invalidated` — раньше было актуально, но больше не действует.

Важное правило: vector/RAG может помочь найти похожее, но не доказывает управленческую связь. Связь требует source, подтверждения или явного статуса доверия.

## Strategy как spine

Strategy — первый сквозной контур, потому что он задаёт координатную систему.

Target architecture должна поддерживать стратегическую карту:

```text
vision / ценности / рамки
→ стратегический вызов
→ выборы / ставки / stop-doing
→ цели периода
→ KR / метрики
→ инициативы / проекты
→ владельцы / команда
→ ритмы встреч
→ решения
→ evidence / progress / drift
→ пересмотр курса
```

Для клиента это не "графовая база". Это стратегическая карта управления:

- что куда ведёт;
- чем проверяется;
- кто владеет;
- где обсуждается;
- что не связано;
- где drift.

Внутри Strategy может вызываться как роль из других workflows:

- meeting analysis зовёт Strategy, чтобы понять, какие решения/темы стратегически значимы;
- projects зовёт Strategy, чтобы проверить связь инициатив с целями;
- metrics зовёт Strategy, чтобы интерпретировать отклонение не только как число, но как drift;
- team зовёт Strategy, чтобы увидеть перегруз владельцев и зависимость целей от людей.

## Базовые потоки

### Поток 1. Обработка встречи

```text
raw transcript / meeting notes
→ extraction: topics, decisions, tasks, entities, candidate edges
→ role pass: meeting analyst + Strategy if needed
→ update proposal: summaries, decisions, tasks, edge candidates
→ view: meeting summary / prep / follow-up
→ write-back after confirmation
```

Принципы:

- raw transcript не становится памятью напрямую;
- важное извлекается в структурированный summary;
- candidate edges не становятся canonical без основания;
- sensitive people-analysis проходит через censor/permissions.

### Поток 2. Вопрос CEO

```text
question
→ task/scope/role classification
→ route exists?
    yes: run known route
    no: build plan
→ context assembly: source + sidecar + live systems
→ tool calls if needed
→ answer / view / trace
→ optional write-back proposal
```

Принципы:

- не грузить всё;
- если source не ясен, спросить;
- если live value нужен, идти в live system;
- если вывод важный, показать source/provenance.

### Поток 3. Проактивный сигнал

```text
schedule / event / threshold
→ route
→ source + sidecar + live check
→ signal with evidence
→ channel delivery
→ optional view
```

Примеры:

- "Стратегия заявлена приоритетом, но встреч по ней не было 6 недель."
- "Ключевая метрика стоит, а активных инициатив по ней нет."
- "Проект потерял связь с целью после стратсессии."
- "Расходы идут по бюджету, продажи отстают, cash horizon короче модели."

### Поток 4. View generation

```text
request / trigger
→ select view type
→ fetch sources and sidecar edges
→ fetch live values if needed
→ build HTML / brief / workspace
→ attach provenance and freshness markers
→ show to client
→ write-back only by explicit action
```

## Путь реализации

Это не roadmap по датам, а последовательность зрелости. Уровень включается по симптомам, а не по желанию построить "красивую архитектуру".

### Level 0. Scaffold discipline

Что есть / укрепляем:

- ясные source-файлы;
- README routes;
- стабильные имена и миссии файлов;
- у каждого факта одно каноническое место хранения;
- явные ссылки;
- базовые YAML/frontmatter поля.

Цель: агент может найти и прочитать нужное без хаоса.

### Level 1. Read models from files

Что строим первым:

- strategic management map из существующих файлов;
- meeting prep view;
- project progress view;
- simple "goal → initiatives" slice.

Технология может быть простой: чтение scaffold + генерация HTML/markdown view. Sidecar может быть ещё не базой, а простым индекс-файлом/JSON/локальной сборкой.

### Level 2. Connectors to live systems

Подключаем там, где truth быстро меняется:

- calendar;
- meeting transcripts;
- Sheets / metrics;
- task tracker;
- selective email/chat access.

Принцип: volatile values лучше брать query-time, чем копировать в память без freshness.

### Level 3. Semantic / lexical index

Когда чтение 5-6 файлов на каждый вопрос становится нормой, добавляем производный индекс:

- lexical search;
- semantic search;
- reranking;
- stable chunk references;
- provenance до source.

Индекс производный и пересобираемый.

### Level 4. Narrow executive graph

Когда появляются real multi-hop вопросы, добавляем граф сущностей и рёбер:

- goals;
- projects;
- tasks;
- meetings;
- decisions;
- metrics;
- people;
- units;
- documents/episodes.

Граф узкий. Не graph-everything. Строится из явных ссылок, frontmatter, extraction и human-confirmation.

### Level 5. Temporal memory

Добавляется при регулярных ошибках из-за устаревших фактов:

- valid_from / valid_to;
- invalidation вместо hard delete;
- point-in-time reasoning;
- conflict history.

Это важно для живого бизнеса, но не первый шаг.

## Что можно собрать к концу 2026

Рабочая цель на конец 2026: не полная autonomous company brain, а целостный читаемый продукт, где все элементы Vision уже видны.

Минимальная сильная версия:

1. **Один партнёр в канале** — базовая беседа, роль-роутинг, сохранение линии.
2. **Scaffold у клиента** — source/authoring слой, который можно открыть и забрать.
3. **Meeting pipeline** — обработка встреч, decisions/tasks, candidate edges.
4. **Strategic management map** — первый spine-view: цели, метрики, инициативы, владельцы, встречи, решения, drift.
5. **Project progress view** — инициативы и связь с целями.
6. **Metrics path** — extractor/calculator/analyst для ограниченного набора метрик.
7. **Simple machine context** — индексы, stable IDs, candidate edges, provenance.
8. **Channels** — Telegram/chat + generated HTML views; email/calendar/meeting tools по приоритету.
9. **Trust layer** — source links, freshness/confidence, approval for write-back, permissions/censor baseline.

Технически это может начинаться как plugin + локальные/простые сборки + generated views. Позже те же роли и контракты можно выносить в managed service или автономный runtime.

## Граница продукта и внешней инфраструктуры

svaib не должен конкурировать с каждым инструментом вглубь.

Не наша уникальность:

- лучший транскрибатор;
- лучший spreadsheet agent;
- лучший BI;
- лучший task tracker;
- лучшая CRM;
- лучшая LLM-модель.

Наша уникальность:

- управленческая онтология;
- связность между циклами;
- роль AI-партнёра по целостному менеджменту;
- маршруты и skills, которые превращают источники в управленческий вывод;
- memory/sidecar, который держит связи, provenance, freshness и права;
- views, которые показывают руководителю управленческую карту, а не просто данные.

Хороший внешний инструмент можно брать под капот, если он реализует роль лучше. Главное — не отдавать внешнему инструменту нашу продуктовую связность и source-of-truth contract.

## Принципы доверия

1. **Source first.** Каждый важный вывод должен вести к source.
2. **No silent truth.** Sidecar не знает лучше source; он показывает, откуда взял факт или связь.
3. **No silent write-back.** Изменения source идут через явное подтверждение, пока не принят bounded automation.
4. **Ask when unsure.** Если метрика, связь, owner или смысл неясны, партнёр спрашивает.
5. **Freshness matters.** Для живых значений нужен timestamp, snapshot или query-time fetch.
6. **Permissions are structural.** Права и censor не добавляются потом; они часть модели.
7. **Views are read models.** View помогает думать и действовать, но не становится второй правдой.
8. **Memory can be cleaned.** Устаревшие факты инвалидируются или удаляются по правилам, а не копятся бесконечно.

## Открытые решения

### Sidecar location

Где живёт machine context:

- рядом со scaffold у клиента;
- в локальном runtime;
- в self-hosted контейнере клиента;
- в сервисе svaib;
- у runtime-провайдера.

Решить вместе с политикой данных: что можно хранить вне клиентского контура, а что нельзя.

### Chunks / embeddings

Можно ли хранить chunks и embeddings вне клиентского контура?

Пока рабочая позиция: chunks, embeddings и реконструируемый клиентский контент считаются клиентскими данными.

### Каналы доступа

Как подключается почта и чаты:

- полный доступ;
- выбранные labels/folders;
- явное forward / CC партнёра;
- только материалы, приложенные к задаче;
- разные режимы для CEO и команды.

### Runtime и коммерческая упаковка

Нужно решить:

- клиент покупает модель сам или получает всё в комплекте;
- svaib поставляет plugin поверх чужого runtime или managed service;
- где проходит граница поддержки;
- как обновляются skills/routes/views.

### First implementation substrate

Кандидаты для первых экспериментов:

- files + generated indexes;
- JSON/SQLite sidecar;
- Postgres/Supabase;
- vector store;
- graph DB;
- готовые indexing tools.

Решать не идеологически, а от первого view и первых вопросов.

### Write-back scope

Уровни:

1. draft-only;
2. human approval;
3. bounded automation;
4. full autonomous actions.

Для текущего Vision принят только безопасный контур: готовит — человек подтверждает.

### Eval памяти

Нужно определить метрики качества:

- retrieval accuracy;
- relationship precision;
- freshness errors;
- duplicate-truth rate;
- citation/provenance quality;
- false links;
- time-to-context;
- answer explainability;
- user correction rate.

## Что важно не перепутать

- Target Architecture не заменяет текущий канон продукта.
- Views могут быть главным UX, но не являются truth.
- Semantic sidecar может стать value layer, но он производный.
- "Данные у клиента" не означает "у нас нет сервиса".
- Runtime-agnostic не означает "без runtime".
- Один партнёр снаружи не означает один монолитный агент внутри.
- Узкий executive graph не равен big-bang knowledge graph.
- Strategy первична как координатная система, но не отменяет остальные циклы.
- Каналы не являются управленческими циклами.

## Следующие шаги

1. Согласовать эту v0.1 как рабочую рамку или поправить развилки.
2. Выбрать первый target view: стратегическая карта управления или meeting prep.
3. Для выбранного view описать минимальные sources, entities, edges, route, output и write-back.
4. После проверки на живом материале оформить accepted/proposed решения в [../05_decisions.md](../05_decisions.md).
5. Только после этого переносить изменения в [../architecture.md](../architecture.md), `methodology/memory/` и specs.
