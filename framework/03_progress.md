---
title: "Framework — хроника"
updated: 2026-05-12
scope: product_core
type: log
---

# Framework — хроника

## Кратко

Журнал сделанного по направлению. Завершённые задачи, ключевые сдвиги, значимые релизы частей фреймворка. Не дублирует [02_active.md](02_active.md) (текущая работа и Session Handoff) и не дублирует meta `session-log.md` (процесс работы с Claude). Даёт **результат** в домене — что было готово когда.

**Работа с файлом:** log — дописывать при завершении значимой задачи по направлению или релизе части фреймворка. Не менять старые записи. Формат: дата → 1-3 строки (что сделано, ссылка на артефакт если есть).

## Связанные файлы

- [01_overview.md](01_overview.md) — состояние реализации шести частей, roadmap декады, модель поставки
- [02_active.md](02_active.md) — что в работе сейчас, Session Handoff
- [02_backlog.md](02_backlog.md) — задачи направления на будущее
- [../meta/management/04_weekly_progress.md](../meta/management/04_weekly_progress.md) — агрегатор по всем направлениям

---
## 2026-05-12 · Methodology scaffold финализирована: единый канон шести файлов

Шесть файлов методологии scaffold ([01_architecture.md](methodology/scaffold/01_architecture.md), [02_file-spec.md](methodology/scaffold/02_file-spec.md), [02_folder-spec.md](methodology/scaffold/02_folder-spec.md), [02_readme-spec.md](methodology/scaffold/02_readme-spec.md), [03_node-files.md](methodology/scaffold/03_node-files.md), [03_contours.md](methodology/scaffold/03_contours.md)) сведены в единый согласованный непротиворечивый канон. `03_contours.md` (v4) — 10 контуров в единой форме («Что это» + дерево + контурно-специфичные миссии), 14 контурно-специфичных файлов вынесены в SOT этого файла. По `person.md` принят Вариант 3: рамка (миссия + 6 канонических разделов) остаётся в `03_node-files.md`, имена и контекст применения распределены по контурам — `01_ceo/01_my-profile.md`, `03_team/{person}.md`, `clients/{client}/{person}.md`. Аудит трёх независимых субагентов (консистентность между файлами, внутренние ошибки, dogfood самим каноном) — драм не нашёл.

---
## 2026-05-12 · Добавлен 9-й управленческий цикл — finance

Финансы выделены из metrics как отдельный предметный контур: финмодель, бюджет, кэш, юнит-экономика, сценарии. Финансовые метрики (revenue, gross margin, CAC, runway) остаются в metrics, бюджет и финмодель — в finance. Обновлены [ontology/management_cycles.md](ontology/management_cycles.md) (v3), [architecture.md](architecture.md) (v13), [01_overview.md](01_overview.md) (v10, цель экватора: 7 циклов в бете), [methodology/scaffold/open-questions.md](methodology/scaffold/open-questions.md) (v5 — где finance живёт в scaffold, отложено до первого клиента). На сайте `dev/src/public/second-ai-brain-overview.html` карта продукта и блоки циклов обновлены до 9.

---
## 2026-05-11 · Methodology scaffold: 01_architecture финален + ревью пятёрки применено

[01_architecture.md](methodology/scaffold/01_architecture.md) переработан как обзорный слой (v4) — 7 H2-секций, дубли с spec убраны. Параллельно прошли два ревью (Claude × 4 субагента + Codex), сведены в action items, применены P1+P2: триплет AGENTS/CLAUDE в методологической папке, `archive/`→`zz_archive/`, инвариант «сущность ↔ файл, узел ↔ папка», унифицирована «служебная папка» с root-level, разведены H1 и аннотация в readme-spec. Коммит `dd1d780`.

---
## 2026-05-06 · Methodology scaffold v6: file-templates и folder-spec

Переписаны [03_node-files.md](methodology/scaffold/03_node-files.md) (v3, с примерами аннотаций для каждого канонического файла) и [02_folder-spec.md](methodology/scaffold/02_folder-spec.md) (v3, упрощены типы узлов, README под новый канон). Параллельно Кодекс отработал замену «зона»→«контур» в methodology/scaffold/ и architecture.md.

---
## 2026-05-06 · Methodology scaffold v5: file-spec и readme-spec упрощены

Сжали обвязку md-файла. В [02_file-spec.md](methodology/scaffold/02_file-spec.md) (v3, 315→238 строк) выкинуты «Миссия файла», обязательные «Кратко» и «Связанные файлы», поля `type`/`scope`/`priority`/`status`/`tags`/`source`, маркеры `[SOURCE]`/`[REF:]`, секции «Анатомия», «Уровни соответствия», «Чеклист», «Антипаттерны». Добавлены § «Title и H1» (формула, лимит ≤120), § «Лид» (опц.), § «Summary» (опц., для больших файлов), § «Правило файла / Правило блока» с enforcement через хук Rule Injection ([memory/01_context_memory.md § 5.5](memory/01_context_memory.md)).

В [02_readme-spec.md](methodology/scaffold/02_readme-spec.md) переработан YAML (минимум: `title`, `description`, `created`, `updated`; убран `version`); `description` сформулирован как «дешёвая карточка релевантности», не миссия. Добавлен раздел «README — место описания миссии файлов внутри папки» (миссия каждого файла теперь живёт в колонке таблицы `## Что лежит` README, а не внутри файлов). Каркас README обновлён: `## Назначение` (миссия папки) + `## Что лежит` с колонкой «Миссия» + `## Маршруты` (опц.) + `## Связи` (обязательный для README). Добавлен § «Доставка README агенту» — триплет `README.md` + `AGENTS.md` + `CLAUDE.md` (последние два — pointer-only на `@README.md`) для гарантии доставки агенту.

Закрыт open-question про `claude/agents/gemini` в каждой папке: канон триплета зафиксирован в [02_readme-spec.md](methodology/scaffold/02_readme-spec.md). CLAUDE.md — временный костыль до нативной поддержки AGENTS.md в Claude Code.

---
## 2026-05-06 · Methodology scaffold v4

10 open-questions закрыты, миграции `04_company` и `05_metrics` выполнены.

---
## 2026-05-05 · Первая чистая архитектура scaffold

Из 20+ разрозненных черновиков собрали первую чистую архитектуру в одном файле — [methodology/scaffold/01_architecture.md](methodology/scaffold/01_architecture.md). До этого scaffold был кусочным, агенты путались, единой опоры не было — теперь есть базовый source of truth для всего scaffold-направления. Закрытие одного из узких мест декады 1 (см. [01_overview.md](01_overview.md) → Фокус).

---
## 2026-05-05 · Каркас methodology/scaffold/ из 8 файлов

Переутверждена структура папки (8 скелетов: 01_architecture + 4 spec'а + deployment + open-questions + README); 

---
## 2026-05-04 · L2-prompt-protocol-telegram переведён на эмодзи-маркеры задач

Telegram-сводка теперь использует ⭕️ / ✅ вместо markdown-чекбоксов `- [ ]` / `- [x]` — Telegram их режет, задачи читались куце. Добавлено правило отступов между задачами. Версия 3 → 4. [L2-prompt-protocol-telegram.md](skills/meeting-analysis/L2-prompt-protocol-telegram.md)

## 2026-05-01 · Фазы 3-4 fern-модели scaffold завершены, бэклог переструктурирован

Получены 4 внешних ревью fern-модели от нейросетей, синтезированы во внутренний draft с 10 открытыми вопросами + раздел «Фундаментальное напряжение». На его основе собран клиентский структурный draft + HTML-презентация для предстоящих встреч. Раздел `## Scaffold` в [02_backlog.md](02_backlog.md) переструктурирован: 12 шагов финального плана (старые 7 пунктов поглощены, добавлены пропущенные: канон развёртывания у клиента, цепочки файлов внутри направлений, profile.md в каноне базовых файлов, контекстная архитектура как отдельный шаг, 10 концептуальных открытых вопросов).

## 2026-05-01 · Клиентское intro для metrics-вертикали

Создан client-facing документ для CEO с запросом на metrics: почему «загрузить xlsx в LLM» не работает. HTML-презентация в фирменном стиле svaib (тёмная тема, для 5-минутного показа). Хранится в локальном `_inbox/` клиента, готов к выдаче.

## 2026-05-01 · Сформулированы 5 принципиальных требований к scaffold

Зафиксирован стержень scaffold-направления: двусторонняя читаемость, управленческая модель CEO, универсальность+адаптивность, целостность, самоподдерживаемость. Позже перенесено в [methodology/scaffold/01_architecture.md](methodology/scaffold/01_architecture.md) как рабочий канон scaffold.

## 2026-04-30 · Реорганизация metrics-вертикали в одно место

Методология вертикали собрана в новую папку `methodology/metrics/` (README — карта вертикали, architecture, HOWTO, rollout, intake-form, open-questions). В `skills/metrics-analysis/` остался только skill: orchestrator + черновик `narrative.py` (DRAFT, open-question #1). Зафиксирован стандарт `metrics/extractors/` у клиента (без подчёркивания) + новый [`scaffold/metrics/extractors/README.md`](scaffold/metrics/extractors/README.md). Канон 8 имён domain-файлов — единый источник правды в [`methodology/metrics/architecture.md`](methodology/metrics/architecture.md), копии в scaffold/orchestrator со ссылкой. Subagent-аудит decisions ↔ methodology: дыр нет (отчёт — [`_inbox/subagents/metrics-decisions-audit/report.md`](_inbox/subagents/metrics-decisions-audit/report.md)). Smoke-test sandbox после переименования: extractor → narrative pipeline работает, числа сходятся с Б.1.

## 2026-04-30 · Впервые потрогали управленческий цикл metrics на живых клиентских данных

Стратегический переход: до этого metrics жили как методология и канон шаблонов. В Б.1 впервые прогнали полный pipeline на реальной таблице клиента в sandbox — AI собрал ответ на «что у меня по OKR1?» с числами, сходящимися с фактами клиента. Параллельно поймали 5 первых дыр (главная — отсутствие атрибута направления у метрик), зашили в канон. Документы под расширение на следующих клиентов: [`HOWTO.md`](methodology/metrics/HOWTO.md), [`rollout.md`](methodology/metrics/rollout.md), [`intake-form.md`](methodology/metrics/intake-form.md), [`open-questions.md`](methodology/metrics/open-questions.md).

## 2026-04-28 · Канон базовых сущностей scaffold

Зафиксирован канон четырёх ключевых сущностей scaffold: миссия и 5 блоков 01_overview.md (Суть / Цели и КР / Команда / Фокус / Дорожная карта), опциональный profile.md как паспорт-доктрина рядом, разграничение README (вход в папку, для AI-агента) ↔ overview (вход в сущность), G/Y/R-светофор как универсальный сигнальный примитив.

## 2026-04-28 · Цели и overview переразложены под вертикали управленческих циклов

Продолжение архитектурного сдвига [27.04](#2026-04-27--введены-вертикали-управленческих-циклов): применили новую оптику сверху вниз через цепочку vision → goal → overview → backlog. Цель экватора и декады 1 по продукту переписаны через управленческие циклы (от принципа «циклы как ядро»). К экватору — все 8 циклов представлены в бете (strategy, team, metrics, meeting, product, marketing, sales, projects), sales и marketing опционально по тяге клиентов. К 22.05 — 2 цикла (meeting, metrics) на уровне early-adopter beta у 2-3 клиентов; выбор циклов — pull от запросов СМ и ЛБ через клиентского субагента. Зафиксирован принцип иерархии: goal — короткая рамка, overview — детальная развёртка. Overview пересобран под канон 5 блоков (Суть/Цели/Команда/Фокус/Roadmap)

## 2026-04-27 · Введены вертикали управленческих циклов

В архитектуру продукта добавлен третий разрез — вертикаль управленческого цикла, проходящая через 3 слоя продукта и 6 частей framework. Предыстория: methodology/metrics/architecture.md (v3) не помещалась в текущую модель — наполняет все три слоя одновременно. Решение: вертикаль = управленческий цикл (опора на принцип из 00_product), не «domain pack»; общие механизмы (snapshot, trace, semantic layer) — горизонтальные контракты слоёв; зависимости вертикалей — только через горизонталь по стабильным ID; вертикаль ≠ скилл; лимит 5–7. Зафиксировано: [04_decisions.md](04_decisions.md) №4, новый файл [ontology/management_cycles.md](ontology/management_cycles.md), правки в 8 связанных файлах; [02_backlog.md](02_backlog.md) переструктурирован под две оси. Аудит: Claude (general-purpose субагент) + Codex.

## 2026-04-25 · Появилась архитектура встраивания метрик в Second AI Brain

В фреймворке не было методологии работы с бизнес-метриками — собрали с нуля за сутки: индустриальный синтез по теме положили в [knowledge/metrics/!metrics.md](../knowledge/metrics/!metrics.md) (новая категория), первую архитектуру — в [methodology/metrics/architecture.md](methodology/metrics/architecture.md) (6 слоёв + процессы, паспорта свернуты в семантический слой, метки [СЕЙЧАС]/[ПОЗЖЕ], секция «Минимальный комплект первой стадии» под «1-2 клиента, Cowork»)

## 2026-04-22 · Канонизация `scaffold/product/` под клиента

Опциональная папка `scaffold/product/` имела только старый README (февраль 2025)/ Установлен канонический каркас: 7 файлов-шаблонов (`product`, `architecture`, `01_overview`, `02_active`, `02_backlog`, `03_progress`, `04_decisions`) + `README.md` с навигацией, правилами развёртывания и связями с `../02_strategy/` (3 связи: vision→product, goal→overview, progress→weekly). Структура зеркалит модель framework-уровня (наш продукт)

## 2026-04-21 · Канонизация продуктового контура

Продуктовое видение Second AI Brain было размазано по всему репо без общего канона. Установлена каноническая модель «framework = продукт»: одна точка правды о продукте.

Движение сверху вниз: vision проекта (куда идём) → product (какой продукт и для кого) → architecture (как устроен внутри) → 01_overview (где мы в стройке) → 02_active (что горит сейчас) → 02_backlog (что дальше) → 03_progress (что сделано) + 04_decisions (почему так решили).

## 2026-04-21 · Шаблон scaffold/projects/ 
В scaffold (каркас, который клиент разворачивает у себя) появился готовый шаблон "проект клиента" — папка для именованного проекта с командой, метриками, задачами, решениями и хроникой встреч. Overview → backlog → active → progress → decisions.
Это другая природа, чем "подразделения" в scaffold: проекты живут параллельно и могут пересекать оргструктуру.

## 2026-04-15 · Создан слой memory/ (6-я часть фреймворка)

Перенесён workbench контекстной памяти → `01_context_memory.md`. `file_spec.md` переехал из `ontology/` в `memory/`. Обновлены `architecture.md` v8, `README.md` v7 («шесть частей» + memory в диаграмме и таблице), 5 сервисных файлов.
