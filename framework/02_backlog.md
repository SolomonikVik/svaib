---
title: "Framework — бэклог"
updated: 2026-05-01
version: 10
scope: product_core
type: plan
---

# Framework — бэклог

## Кратко

Полный список задач направления на будущее. Источник для плана недели (weekly-planning). Задачи уже разобраны (из inbox) и ожидают выполнения.

Структура — по двум осям архитектуры (decision №4, 2026-04-27): **горизонталь** (общие слои) и **вертикали** (управленческие циклы). Скиллы и прочее — отдельно.

**Работа с файлом:** plan — дописывать по мере появления задач (из `_inbox/01_inbox.md` при разборе, из встреч, из инсайтов). Выполненная задача — `[x]` + перенос в [03_progress.md](03_progress.md). Задача пишется с достаточным контекстом: понятно что делать без открытия других файлов. Что сюда: конкретные задачи развития direction'а. Что НЕ сюда: сырое на разбор (→ [_inbox/01_inbox.md](_inbox/01_inbox.md)), то что делаем сейчас (→ [02_active.md](02_active.md)), архитектурные решения (→ [04_decisions.md](04_decisions.md)).

## Связанные файлы

- [01_overview.md](01_overview.md) — состояние реализации, roadmap декады
- [02_active.md](02_active.md) — что делаем сейчас
- [03_progress.md](03_progress.md) — хроника сделанного
- [04_decisions.md](04_decisions.md) — архитектурные решения (см. №4 — вертикали)
- [_inbox/01_inbox.md](_inbox/01_inbox.md) — входящее на разбор

---

# Горизонталь (общие слои)

## Scaffold

Финальный список задач после Фазы 3-4 fern-модели (внешний review + внутренний синтез сделаны 1.05). Источник — [_inbox/scaffold/2026-05-01_scaffold-model-draft.md](_inbox/scaffold/2026-05-01_scaffold-model-draft.md). Полный список черновиков по fern — в _inbox/scaffold/.

### Шаг 1. Обсудить scaffold-draft-v1 с клиентами

Презентовать [_inbox/scaffold/2026-05-01_scaffold-draft-v1.md](_inbox/scaffold/2026-05-01_scaffold-draft-v1.md) и [_inbox/scaffold/2026-05-01_scaffold-draft-v1.html](_inbox/scaffold/2026-05-01_scaffold-draft-v1.html) на предстоящих встречах. Собрать обратную связь — что зашло, что ломается, что переоформить.

### Шаг 2. Фаза 6: принять решения и собрать всё в единый канон

#### 2.1. Принять решения по форме канона

- [ ] **Где живёт канон**: `principles.md` / `MODEL.md` / отдельный `canon.md` / папка `canon/`
- [ ] **Имя корневой обязательной папки** — `04_management/` → `04_company/` (или иное)
- [ ] **Место CEO** — `01_ceo/` отдельно или узел `03_team/`

#### 2.2. Интегрировать в единый канон ВСЕ источники

Стержневые рабочие файлы scaffold:
- [scaffold/idea.md](scaffold/idea.md) — 5 требований, стержень
- [scaffold/principles.md](scaffold/principles.md) — 9 принципов проектирования
- [scaffold/MODEL.md](scaffold/MODEL.md) — текущая прескриптивная модель
- [scaffold/README.md](scaffold/README.md) — клиентский вход

Главный артефакт fern:
- [scaffold/fern-model-draft.md](scaffold/fern-model-draft.md) — гипотеза, 5 стадий, 14 открытых вопросов (α-ξ + κ-λ-μ)

Черновики из `_inbox/scaffold/`:
- [2026-04-28_overview-canon-draft.md](_inbox/scaffold/2026-04-28_overview-canon-draft.md) — 5 блоков overview, profile, README, светофор
- [2026-04-30_fern-scaffold-growth.html](_inbox/scaffold/2026-04-30_fern-scaffold-growth.html) — визуализация роста по стадиям
- [2026-05-01_fern-external-review-request.md](_inbox/scaffold/2026-05-01_fern-external-review-request.md) — внешний запрос
- [2026-05-01_scaffold-model-draft.md](_inbox/scaffold/2026-05-01_scaffold-model-draft.md) — синтез 4 ревью, 10 открытых вопросов
- [2026-05-01_scaffold-draft-v1.md](_inbox/scaffold/2026-05-01_scaffold-draft-v1.md) + [.html](_inbox/scaffold/2026-05-01_scaffold-draft-v1.html) — клиентский драфт

Опорные чужие архитектуры:
- [_inbox/scaffold/ARCHITECTURE_maxim.md](_inbox/scaffold/ARCHITECTURE_maxim.md)
- [_inbox/scaffold/ARCHITECTURE_rinat.md](_inbox/scaffold/ARCHITECTURE_rinat.md)

Соседние слои framework — что взять в scaffold:
- [memory/01_context_memory.md](memory/01_context_memory.md) — протоколы памяти, хуки, Rule Injection, [SOURCE]/[REF:]
- [memory/file_spec.md](memory/file_spec.md) — формат файла, YAML, секции
- [ontology/entities.md](ontology/entities.md) — каталог сущностей (композиции человека и проекта)
- [ontology/ontology.md](ontology/ontology.md) — связи сущностей
- [methodology/methodology.md](methodology/methodology.md) — протоколы и decision frames

Уже применённые подагентские ревью (источник для архива):
- `_inbox/subagents/2026-04-30-fern-model-review/report.md` — ревью fern-модели на самодостаточность

#### 2.3. Перевести зафиксированный канон из `_inbox/scaffold/` в `scaffold/`

Архивировать черновики, поглощённые каноном. Оставить только живые источники.

### Шаг 3. Канон каждого базового файла scaffold

Для каждого — миссия файла + миссия канонических блоков внутри. То же, что сделали для overview в этой сессии, — по остальным.

- [ ] `README.md`
- [ ] `01_overview.md` (5 блоков уже зафиксированы в [_inbox/scaffold/2026-04-28_overview-canon-draft.md](_inbox/scaffold/2026-04-28_overview-canon-draft.md))
- [ ] `profile.md`
- [ ] `02_active.md`
- [ ] `02_backlog.md` — **Направление (Track) и Задача (Task). Подзадача = задача внутри задачи, глубина вложенности любая**
- [ ] `03_progress.md`
- [ ] `04_decisions.md`
- [ ] **Глоссарий**

### Шаг 4. Канон файлов и папок внутри направлений (от общего к частному)

Внутри типов сущностей scaffold (`04_management/{org_node}/`, `product/`, `projects/{name}/`) — цепочки файлов конкретных типов сущностей и их связки.

- [ ] **Глоссарий — где должен быть**
- [ ] **Папка [scaffold/clients/](scaffold/clients/)** — чёткое определение Setup: что это, зачем, для чего настройка папок
- [ ] **Определиться с папкой `docs/`** для доп-доков в направлениях
- [ ] **Определиться с папкой `wiki/`** по методу Karpathy (можно позже)

### Шаг 5. Канон README

Содержательный шаблон `README.md` по типам папок (глубже разграничения README ↔ overview из § 3 принятых решений в overview-canon-draft).

### Шаг 6. Что забираем из контекстной архитектуры и чужих архитектурных документов

Внимательно прочитать [memory/01_context_memory.md](memory/01_context_memory.md) и решить, что взять в scaffold на первый заход: YAML / front-matter, правила, хуки и т.д.

- [ ] Посмотреть какие инсайты можно взять из [ARCHITECTURE_maxim](_inbox/scaffold/ARCHITECTURE_maxim.md) и [ARCHITECTURE_rinat](_inbox/scaffold/ARCHITECTURE_rinat.md) (материалы в [_inbox/scaffold/](_inbox/scaffold/)) при ревизии scaffold
- [ ] [memory/file_spec.md](memory/file_spec.md) — формат файла

### Шаг 7. Обновить файлы scaffold под Шаг 6

Применить решения по контекстной архитектуре (YAML, хуки, правила) к шаблонам scaffold.

### Шаг 8. Применить канон 5 блоков overview к шаблонам scaffold

- [ ] `scaffold/product/01_overview.md` — пересобрать под 5 блоков
- [ ] `scaffold/projects/{name}/01_overview.md` — пересобрать, паспорт вынести в `profile.md`
- [ ] `scaffold/04_management/{org_node}/01_overview.md` — пересобрать
- [ ] Добавить отсутствующий `scaffold/04_management/{org_node}/README.md`
- [ ] Однострочный README в архивных/служебных подпапках
- [ ] `scaffold/projects/{name}/README.md` — вынести методологию проекта в `principles.md` / `methodology.md`
- [ ] `scaffold/metrics/` — оставить отдельной парадигмой, но сверить терминологию

### Шаг 9. Применить канон к самому `framework/svaib` (живой пример)

- [ ] `framework/00_product.md` → `framework/profile.md` (переименовать)
- [ ] Поправить ссылки: [README.md](README.md), [01_overview.md](01_overview.md), [architecture.md](architecture.md), [../meta/management/01_vision.md](../meta/management/01_vision.md)
- [ ] Проверить тело `profile.md` — блок «Стадия и горизонт» (операционка) — переехать в overview
- [ ] [01_overview.md](01_overview.md) — выровнять под 5 блоков

### Шаг 10. Канон развёртывания у клиента

Как scaffold разворачивается: что обязательно, что опционально, в каком порядке, где зафиксировано как канон (чтобы не забывалось при онбординге).

### Шаг 11. Связность scaffold

Проверить, что обновлённый scaffold не противоречит онтологии и методологии. Чтобы агенты не сыпались на устаревших связях.

- [ ] **Решить про слияние [scaffold/principles.md](scaffold/principles.md) → [scaffold/MODEL.md](scaffold/MODEL.md)**: где они должны лежать — в `scaffold/` или в `methodology/`. Плюс файл [scaffold/idea.md](scaffold/idea.md) (ЧТО — 5 требований, стержень) → `principles.md` (КАК принимать решения о структуре) → `MODEL.md` (КАК выглядит развёртываемая модель). **ПОДУМАТЬ ОБСУДИТЬ РЕШИТЬ**
- [ ] Связность с [memory/](memory/), [ontology/](ontology/), [methodology/](methodology/)

### Шаг 12. Закрыть 10 концептуальных открытых вопросов

Из [_inbox/scaffold/2026-05-01_scaffold-model-draft.md](_inbox/scaffold/2026-05-01_scaffold-model-draft.md):

1. **Identity сущности** — явный `id` в frontmatter или `[SOURCE]/[REF:]` + Rename Guard
2. **Природа vs стадия** — маркетинг-как-файл и маркетинг-как-проект: одна сущность на разных стадиях или две разные
3. **Lifecycle архивации** — формальные операции `archive / pause / merge / split` для умерших / слившихся / разделившихся сущностей
4. **Триггеры стадий** — нужны ли жёсткие чек-листы для переходов 1→2, 2→3, 3→4
5. **Место CEO** — `01_ceo/` отдельно или узел внутри `03_team/` (часть 2.1)
6. **Композитные сущности** — клиент = profile + company + project: особый случай или общий механизм
7. **Knowledge по подразделениям** — распределённая или одна плоская wiki
8. **Технические ссылки при rename** — якорные `#section`, внешние от клиента — покрывает ли Rename Guard
9. **Стратегия — fern или каноническая зона** — где граница между 6 фиксированными файлами и прогрессивным разворотом
10. **Темпоральность** — когда сущность считать «холодной»

## Память v1

- [ ] **Полный вынос общих механизмов из [methodology/metrics/architecture.md](methodology/metrics/architecture.md) в `memory/`** — snapshot, версионирование сущностей, trace ответа, semantic layer как паттерн, маршрут + думающая ветка, границы ответа. Это горизонтальные контракты слоёв, не часть metrics. Источник — [04_decisions.md](04_decisions.md), решение №4 (2026-04-27)
- [ ] Inline-даты на volatile-данных: добавить в [memory/file_spec.md](memory/file_spec.md) (секция маркеров, рядом с `[SOURCE]`/`[REF:]`) и в [methodology/meeting_analysis.md](methodology/meeting_analysis.md) (требование к надстройке дельт). Формат — в `clients/_inbox/_todo_meeting_processor.md` секция «Требования к дельтам»
- [ ] QMD — локальный семантический поиск по markdown (MCP для Claude Code). 19k stars, Tobi Lütke. Установить, протестировать на нашем репо (570+ файлов), оценить качество vs grep. Если работает — часть онбординга клиента. Детали: [../lab/_inbox/qmd-research.md](../lab/_inbox/qmd-research.md)
- [ ] **Enforcement против раздувания стержневых файлов.** Текстовые правила («бритва Оккама», «экономь токены» в CLAUDE.md / file_spec) не работают как фильтр в момент генерации — подтверждено живым кейсом 2026-05-01 (idea.md раздут в 5 раз вопреки всем правилам). Нужны хуки/inline-правила: лимит строк на stem-файлах, правило «копируй не интерпретируй», pre-Write пауза, канон стержневого файла. Источник: [_inbox/2026-05-01_llm-bloat-pattern.md](_inbox/2026-05-01_llm-bloat-pattern.md) — 5 причин + 5 предложений по реализации

## Помощники (Skills) — общее

- [ ] Telegram-бот / аккаунт AI для асинхронной коммуникации с клиентом (идея АС). Общий канал, не привязан к одной вертикали — могут пушить ритуалы любой вертикали
- [ ] **Вынести `send_telegram.sh` в `framework/skills/channels/telegram/`.** Сейчас скрипт лежит внутри `framework/skills/meeting-analysis/send_telegram.sh` — но используется из других скиллов (email-assistant, потенциально новые). Создать `framework/skills/channels/telegram/` (SKILL.md + скрипт), привести к канону дубль `.claude/skills/send-telegram/`. Обновить ссылки во всех скиллах и операциях (`setup_telegram_bot.md`, `setup_email_assistant.md`, `meeting-analysis/orchestrator-*`). Обнаружено при разработке email-assistant 30.04

## Мета (архитектура / онтология / методология)

- [ ] **Карта храма: definition of done для Second AI Brain.** Взять vision + architecture, приземлить на реальность: что конкретно должно существовать в готовом продукте. Результат — чеклист готовности, по которому можно оценивать направление. Без этого статус — счёт кирпичей без чертежа
- [ ] Композиции Человек и Проект — раскрыть состав частей в [ontology/entities.md](ontology/entities.md) (A.13). Человек → my_profile.md + team.md. Проект → весь фреймворк вокруг проектов/подпроектов
- [ ] [architecture.md](architecture.md) «Сборки» — определить из каких сущностей состоят генерируемые файлы (A.16). При реализации понадобится маппинг
- [ ] vision стратегического помощника на основе созвона АС — заготовка к будущей вертикали strategy. Источник — [../clients/_inbox/subagents/sm-vision-product-synthesis.md](../clients/_inbox/subagents/sm-vision-product-synthesis.md).

---

# Вертикали (управленческие циклы)

## meeting (аналитик встреч)

Первая задача разобрать все задачи ниже и собрать из них единый план действий

### 2. ИСПРАВЛЕНИЕ АНАЛИТИКА ВСТРЕЧ

**Состояние (22.04 вечер):** проблема meeting-analysis переразложена. Единый вход для нового чата — бриф.

- [_inbox/meeting-analysis/2026-04-22_meeting-analysis-brief.md](_inbox/meeting-analysis/2026-04-22_meeting-analysis-brief.md) v2 — главный вход. Постановка проблемы + 5 гипотез + список что читать / не читать.
- [_inbox/meeting-analysis/2026-04-22_research-requests.md](_inbox/meeting-analysis/2026-04-22_research-requests.md) — два запроса research (targeted + open-ended) в GPT и Claude. Виктор положит туда ссылки на 4 ответа.

**Что делает новый чат:**

1. Читает [бриф](_inbox/meeting-analysis/2026-04-22_meeting-analysis-brief.md) — только список «обязательно».
2. Когда Виктор приложит 4 ссылки на ответы research — читает их (если суммарно >50 страниц, каждый через субагента, возвращающего карту находок).
3. Делает синтез на 1-2 страницы по 4 ответам + первый industry-research [_inbox/meeting-analysis/2026-04-22_meeting-analysis-industry-research.md](_inbox/meeting-analysis/2026-04-22_meeting-analysis-industry-research.md) как пятый источник (что повторилось / что расходится / неочевидное), кладёт отдельным файлом в `_inbox/`.
4. Делает архитектурное предложение по новому пайплайну: какие гипотезы из брифа подтверждены/опровергнуты синтезом, какая декомпозиция (что добавить, что изменить), поэтапный план. Обсуждает с Виктором → понимание проблемы и направления решения. **На этом задача чата закрывается.**
5. Надо обсудить с Виктором - есть бэклог фреймворка - там много задач на аналитика надо собрать все воедино

- в т.ч. новый кейс - [ ] [2026-04-24_judges-cascade-hypothesis.md](_inbox/meeting-analysis/2026-04-24_judges-cascade-hypothesis.md) — полевая гипотеза: каскад судей (общий критик + оппозиционный критик + задачный верификатор) как L1.5-слой между L1 и L2. Проверено на одной встрече (АС, 24.04). 5 гипотез — требуют повтора на ≥3-5 встречах, прежде чем встраивать в пайплайн
- а также **второй полевой прогон** — [_inbox/meeting-analysis/2026-04-24_L1-false-decision-case.md](_inbox/meeting-analysis/2026-04-24_L1-false-decision-case.md) — клиент Л, 24.04. L1 + общий критик пропустили две галлюцинации: "предложение без принятия → Решение" и "закрытый вопрос → Открытый вопрос". Узкий верификатор с цитатами нашёл за 100 сек. **Новая категория ошибки L1** (потеря диалектики диалога) + усиление Г2/Г4 первого документа
- Починить L2-раскидку: разваливает нарративы, фиксирует откровенную мелочь. Материал кейса — [_inbox/meeting-analysis/2026-04-22_L2-narrative-spec-dispersal-case.md](_inbox/meeting-analysis/2026-04-22_L2-narrative-spec-dispersal-case.md). Паттерн воспроизводится на разных клиентах (жалоба Виктора), не только на одной встрече. Трогает `skills/meeting-analysis/L2-procedure-client-update.md` + возможно `orchestrator-client-meeting.md` (2026-04-22)
- Починить утечку профайла в L1: оркестратор передаёт коучинг-лог участника в L1 на 1-on-1, L1 подменяет цитаты транскрипта готовыми формулировками. Материал кейса — [_inbox/meeting-analysis/2026-04-22_L1-profile-leak-seleznev-case.md](_inbox/meeting-analysis/2026-04-22_L1-profile-leak-seleznev-case.md). Клиентский эксперимент (первый клиент) фактически валидировал fix by reducing context. Готовы правки A/B/C: `skills/meeting-analysis/orchestrator-meeting.md` (шаг 0, минимум L1-контекста), `L1-prompt-entity-extractor.md` (опора — цитата транскрипта, не контекста), `L2-procedure-scaffold-update.md` (изоляция коучинг-лога от L1). (2026-04-22)
- [ ] Верифицировать автообновление `team/` из результатов встречи — на этапе анализа, не по отдельной команде (идея, согласована с АС): `org_structure.md`, `glossary.md` и т.д. — создавать записи о людях, которых раньше не было
- [ ] Behavioral extractor: определиться v1 vs v2, протестировать на 2+ транскриптах, подключить к оркестратору
- [ ] Оптимизация пайплайна: L1 по ссылкам (не inline) + L2 ревизия-first (не append-only). Детали: [_inbox/meeting-analysis/task-pipeline-optimization.md](_inbox/meeting-analysis/task-pipeline-optimization.md)
- [ ] **Баг в send_telegram.sh:37** — `curl -d text="..."` ломает HTML при наличии `&` в тексте (пример: `Vivo&amp;Jolly` → Telegram получает `<b>` без пары). Лечится заменой `-d text="$1"` на `--data-urlencode "text=$1"`. Обход через curl с urlencode сработал
- [ ] Разобрать обратную связь от Опилкина по аналитику
- [ ] Сборка скиллов meeting-analysis: обернуть рабочие промпты в SKILL.md формат
- [ ] FRAME-скоринг: приоритизация сущностей по значимости (отложен)
- [ ] **Runtime-скиллы meeting-analysis не самодостаточны.** `L2-prompt-protocol-telegram.md` ссылается на `../../ontology/protocol_format.md` и `L2-prompt-protocol-full.md`; `L2-procedure-scaffold-update.md` — на `L2-procedure-client-update.md`. При копировании клиенту ссылки ломаются. Правило: runtime-скиллы должны быть самодостаточны — только ссылки на клиентские папки и другие runtime-скиллы. Обнаружено при миграции клиента 14.04, у клиента почищено вручную
- [ ] **Оркестратор встреч в Шаге 0** спрашивает путь транскрипта вручную — логично чтобы он сам дёргал `macwhisper-transcript --list` и находил
- [ ] L1/L2: различать "подумаю" vs "решил" — агент превращает размышление в задачу (кейс Паши у КЛ2, встреча 17.04). Нужен фильтр reflective vs committed при извлечении задач/решений

## metrics

**Состояние (25.04 вечер):** Архитектура метрик зафиксирована — [methodology/metrics/architecture.md](methodology/metrics/architecture.md) v3. 6 слоёв + процессы, метки [СЕЙЧАС]/[ПОЗЖЕ] на каждом слое, секция «Минимальный комплект первой стадии». Research-опора — [knowledge/metrics/!metrics.md](../knowledge/metrics/!metrics.md). Закрыты три драматичных гэпа (версионирование паспортов, валидация SQL, состояние разговора), 4 паспорта свернуты в семантический слой + ритуалы.

### Встраиваем метрики у клиента (тестируем простые способы)

- [ ] Задача в актив

### Глубокая верификация архитектуры метрик с фреймворком целиком.

- [ ] Читаем [metrics.md](methodology/metrics/architecture.md) v3 (база) + [knowledge/metrics/!metrics.md](../knowledge/metrics/!metrics.md) (research).
- [ ] Проходит по всеми фреймворку и проверяет согласованность метрик с нашими файлами: [00_product.md](00_product.md) — управленческие циклы как ядро (метрики поддерживают циклы или живут параллельно?); [architecture.md](architecture.md) — три слоя (данные/память/помощники); куда ложатся 6 слоёв метрик; [ontology/entities.md](ontology/entities.md) и [ontology/rituals.md](ontology/rituals.md) — нужны ли новые сущности (метрика, маршрут, ритуал-метрик), как соотносится слой 5 с существующим каталогом ритуалов; [scaffold/clients/](scaffold/clients/) — где у клиента физически живут описание таблиц / метрики / маршруты
    - [ ] (общие механизмы метрик — snapshot, версионирование, trace, semantic layer — переезжают в `memory/`, см. горизонталь → Память v1)

### встраиваем метрики в архитектуру (бета версия)

- [ ] **Подключение источника метрик у клиентов (Excel/GoogleTabs)** — как физически данные попадают в scaffold клиента. Под KR декады 1: «метрики бизнеса живут в scaffold, подтягиваются из источника, план/факт виден» ([01_overview.md](01_overview.md))
- [ ] **Паспорта метрик в scaffold клиента** — где живут (папка, формат), как связаны с ритуалами и маршрутами. Опирается на результаты архитектурной верификации [methodology/metrics/architecture.md](methodology/metrics/architecture.md) v3 ↔ фреймворк (см. [02_active.md](02_active.md), задача 1)
- [ ] **Ритуал «разбор отклонений»** — где живёт, кто запускает, входы/выходы. Под KR декады 1: «разбор отклонений как процесс»
- [ ] **Бриф перед встречей (ритуал слоя 5 metrics)** — горящие метрики, риски, открытые вопросы. Триггер, шаблон сообщения, 3–5 маршрутов (см. [methodology/metrics/architecture.md](methodology/metrics/architecture.md), минимальный комплект первой стадии). Под KR декады 1: «метрики попадают в контекст встреч через scaffold»

## strategy (не активна, заготовка к декаде 2)

- [ ] **Vision стратегического помощника (sidetrack)** — материал-заготовка к будущей вертикали strategy. Не задача декады 1, делается параллельно по возможности. Источник: [clients/_inbox/subagents/sm-vision-product-synthesis.md](../clients/_inbox/subagents/sm-vision-product-synthesis.md) (синтез по созвону АС). При активации вертикали strategy в декаде 2 — этот материал станет первым входом

---

# Прочее

- (свободная зона для задач, не вписывающихся в горизонталь/вертикаль)