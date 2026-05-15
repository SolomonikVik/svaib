---
title: "Framework — бэклог"
updated: 2026-05-15
version: 11
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

# 🔵 Горизонталь (общие слои)

## 🔸 Scaffold

### Связность scaffold

Проверить, что обновлённый scaffold не противоречит онтологии и методологии. Чтобы агенты не сыпались на устаревших связях.
- [ ] Связность с [memory/](memory/), [ontology/](ontology/), [methodology/](methodology/)

### Применить канон к самому `framework/svaib` (живой пример)

- [ ] `framework/00_product.md` → `framework/profile.md` (переименовать)
- [ ] Поправить ссылки: [README.md](README.md), [01_overview.md](01_overview.md), [architecture.md](architecture.md), [../meta/management/01_vision.md](../meta/management/01_vision.md)
- [ ] Проверить тело `profile.md` — блок «Стадия и горизонт» (операционка) — переехать в overview
- [ ] [01_overview.md](01_overview.md) — выровнять под 5 блоков

### Закрыть  открытые вопросы 

Открытые вопросы, перенесённые в [methodology/scaffold/open-questions.md](methodology/scaffold/open-questions.md):
Пересмотреть те, что ниже
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


- [ ] Посмотреть архитектуры Максима:
      [_inbox/scaffold/ARCHITECTURE_maxim.md](_inbox/scaffold/ARCHITECTURE_maxim.md) **Идея Maxim'а — connecting tree: 
      Aim                    (зачем компания вообще существует) ─ Strategy Goal   (стратегическая цель) -> Objective     (что должны сделать) -> Key Result    (как поймём что сделали) -> Initiative    (что делаем чтобы получить KR) -> Task          (конкретное действие)


## 🔸 Память v1

- [ ] **Полный вынос общих механизмов из [methodology/metrics/architecture.md](methodology/metrics/architecture.md) в `memory/`** — snapshot, версионирование сущностей, trace ответа, semantic layer как паттерн, маршрут + думающая ветка, границы ответа. Это горизонтальные контракты слоёв, не часть metrics. Источник — [04_decisions.md](04_decisions.md), решение №4 (2026-04-27)
- [ ] Inline-даты на volatile-данных: добавить в [memory/file_spec.md](memory/file_spec.md) (секция маркеров, рядом с `[SOURCE]`/`[REF:]`) и в [methodology/meeting_analysis.md](methodology/meeting_analysis.md) (требование к надстройке дельт). Формат — в `clients/_inbox/_todo_meeting_processor.md` секция «Требования к дельтам»
- [ ] QMD — локальный семантический поиск по markdown (MCP для Claude Code). 19k stars, Tobi Lütke. Установить, протестировать на нашем репо (570+ файлов), оценить качество vs grep. Если работает — часть онбординга клиента. Детали: [../lab/_inbox/qmd-research.md](../lab/_inbox/qmd-research.md)
- [ ] **Enforcement против раздувания стержневых файлов.** Текстовые правила («бритва Оккама», «экономь токены» в CLAUDE.md / file_spec) не работают как фильтр в момент генерации — подтверждено живым кейсом 2026-05-01 (idea.md раздут в 5 раз вопреки всем правилам). Нужны хуки/inline-правила: лимит строк на stem-файлах, правило «копируй не интерпретируй», pre-Write пауза, канон стержневого файла. Источник: [_inbox/2026-05-01_llm-bloat-pattern.md](_inbox/2026-05-01_llm-bloat-pattern.md) — 5 причин + 5 предложений по реализации

## 🔸 Помощники (Skills) — общее

- [ ] Telegram-бот / аккаунт AI для асинхронной коммуникации с клиентом (идея АС). Общий канал, не привязан к одной вертикали — могут пушить ритуалы любой вертикали
- [ ] **Вынести `send_telegram.sh` в `framework/skills/channels/telegram/`.** Сейчас скрипт лежит внутри `framework/skills/meeting-analysis/send_telegram.sh` — но используется из других скиллов (email-assistant, потенциально новые). Создать `framework/skills/channels/telegram/` (SKILL.md + скрипт), привести к канону дубль `.claude/skills/send-telegram/`. Обновить ссылки во всех скиллах и операциях (`setup_telegram_bot.md`, `setup_email_assistant.md`, `meeting-analysis/orchestrator-*`). Обнаружено при разработке email-assistant 30.04
- [ ] **Баг в send_telegram.sh:37** — `curl -d text="..."` ломает HTML при наличии `&` в тексте (пример: `Vivo&amp;Jolly` → Telegram получает `<b>` без пары). Лечится заменой `-d text="$1"` на `--data-urlencode "text=$1"`. Обход через curl с urlencode сработал

## 🔸 Мета (архитектура / онтология / методология)

- [ ] **Карта храма: definition of done для Second AI Brain.** Взять vision + architecture, приземлить на реальность: что конкретно должно существовать в готовом продукте. Результат — чеклист готовности, по которому можно оценивать направление. Без этого статус — счёт кирпичей без чертежа
- [ ] Композиции Человек и Проект — раскрыть состав частей в [ontology/entities.md](ontology/entities.md) (A.13). Человек → my_profile.md + team.md. Проект → весь фреймворк вокруг проектов/подпроектов
- [ ] [architecture.md](architecture.md) «Сборки» — определить из каких сущностей состоят генерируемые файлы (A.16). При реализации понадобится маппинг
- [ ] vision стратегического помощника на основе созвона АС — заготовка к будущей вертикали strategy. Источник — [../clients/_inbox/subagents/sm-vision-product-synthesis.md](../clients/_inbox/subagents/sm-vision-product-synthesis.md).

---

# 🔵 Вертикали (управленческие циклы)

## 🔸 meeting (аналитик встреч)

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
- [ ] Разобрать обратную связь от Опилкина по аналитику
- [ ] Сборка скиллов meeting-analysis: обернуть рабочие промпты в SKILL.md формат
- [ ] FRAME-скоринг: приоритизация сущностей по значимости (отложен)
- [ ] **Runtime-скиллы meeting-analysis не самодостаточны.** `L2-prompt-protocol-telegram.md` ссылается на `../../ontology/protocol_format.md` и `L2-prompt-protocol-full.md`; `L2-procedure-scaffold-update.md` — на `L2-procedure-client-update.md`. При копировании клиенту ссылки ломаются. Правило: runtime-скиллы должны быть самодостаточны — только ссылки на клиентские папки и другие runtime-скиллы. Обнаружено при миграции клиента 14.04, у клиента почищено вручную
- [ ] **Оркестратор встреч в Шаге 0** спрашивает путь транскрипта вручную — логично чтобы он сам дёргал `macwhisper-transcript --list` и находил
- [ ] L1/L2: различать "подумаю" vs "решил" — агент превращает размышление в задачу (кейс Паши у КЛ2, встреча 17.04). Нужен фильтр reflective vs committed при извлечении задач/решений
- [ ] Telegram-бот шлет вместо плюс пробел: Скрипт [send_telegram.sh:37](vscode-webview://02914pishrsn5pihe9dqlt249vcpu4d54q3kj7dhjjv070c597ft/svaib/framework/skills/meeting-analysis/send_telegram.sh#L37) шлёт текст через curl `-d text="$1"`. Флаг `-d` использует `application/x-www-form-urlencoded`, а в этом формате `+` означает пробел (стандарт RFC 3986). curl сам не кодирует — отправляет байты как есть, и сервер Telegram честно расшифровывает `+` как пробел.

## 🔸 metrics

**Состояние (25.04 вечер):** Архитектура метрик зафиксирована — [methodology/metrics/architecture.md](methodology/metrics/architecture.md) v3. 6 слоёв + процессы, метки [СЕЙЧАС]/[ПОЗЖЕ] на каждом слое, секция «Минимальный комплект первой стадии». Research-опора — [knowledge/metrics/!metrics.md](../knowledge/metrics/!metrics.md). Закрыты три драматичных гэпа (версионирование паспортов, валидация SQL, состояние разговора), 4 паспорта свернуты в семантический слой + ритуалы.

### Встраиваем метрики у клиента (тестируем простые способы)

- [ ] Задача в [02_active](02_active.md)
- [ ] Читаем https://novasapiens.ru/prompt/2604.25149

### Глубокая верификация архитектуры метрик с фреймворком целиком.

- [ ] Читаем [metrics.md](methodology/metrics/architecture.md) v3 (база) + [knowledge/metrics/!metrics.md](../knowledge/metrics/!metrics.md) (research).
- [ ] Проходит по всеми фреймворку и проверяет согласованность метрик с нашими файлами: [00_product.md](00_product.md) — управленческие циклы как ядро (метрики поддерживают циклы или живут параллельно?); [architecture.md](architecture.md) — три слоя (данные/память/помощники); куда ложатся 6 слоёв метрик; [ontology/entities.md](ontology/entities.md) и [ontology/rituals.md](ontology/rituals.md) — нужны ли новые сущности (метрика, маршрут, ритуал-метрик), как соотносится слой 5 с существующим каталогом ритуалов; [scaffold/clients/](scaffold/clients/) — где у клиента физически живут описание таблиц / метрики / маршруты
    - [ ] (общие механизмы метрик — snapshot, версионирование, trace, semantic layer — переезжают в `memory/`, см. горизонталь → Память v1)

### встраиваем метрики в архитектуру (бета версия)

- [ ] **Подключение источника метрик у клиентов (Excel/GoogleTabs)** — как физически данные попадают в scaffold клиента. Под KR декады 1: «метрики бизнеса живут в scaffold, подтягиваются из источника, план/факт виден» ([01_overview.md](01_overview.md))
- [ ] **Паспорта метрик в scaffold клиента** — где живут (папка, формат), как связаны с ритуалами и маршрутами. Опирается на результаты архитектурной верификации [methodology/metrics/architecture.md](methodology/metrics/architecture.md) v3 ↔ фреймворк (см. [02_active.md](02_active.md), задача 1)
- [ ] **Ритуал «разбор отклонений»** — где живёт, кто запускает, входы/выходы. Под KR декады 1: «разбор отклонений как процесс»
- [ ] **Бриф перед встречей (ритуал слоя 5 metrics)** — горящие метрики, риски, открытые вопросы. Триггер, шаблон сообщения, 3–5 маршрутов (см. [methodology/metrics/architecture.md](methodology/metrics/architecture.md), минимальный комплект первой стадии). Под KR декады 1: «метрики попадают в контекст встреч через scaffold»

## 🔸 strategy (не активна, заготовка к декаде 2)

- [ ] **Vision стратегического помощника (sidetrack)** — материал-заготовка к будущей вертикали strategy. Не задача декады 1, делается параллельно по возможности. Источник: [clients/_inbox/subagents/sm-vision-product-synthesis.md](../clients/_inbox/subagents/sm-vision-product-synthesis.md) (синтез по созвону АС). При активации вертикали strategy в декаде 2 — этот материал станет первым входом

---
