---
title: "Framework — актуальное"
updated: 2026-05-12
scope: product_core
priority: high
type: plan
---

# Framework — актуальное

## Кратко

Операционный хаб направления: контекст передачи между чатами (Session Handoff), активные задачи, открытые вопросы. Всё, что требует внимания сейчас — в одном месте. State-файл: перезаписывается, не растёт. Вся история — в [03_progress.md](03_progress.md).

**Работа с файлом:** Что сюда: текущие задачи направления, блокеры, открытые вопросы. Что НЕ сюда: что за продукт и зачем (→ [00_product.md](00_product.md)), как устроен внутри (→ [architecture.md](architecture.md)), состояние реализации (→ [01_overview.md](01_overview.md)), задачи на будущее (→ [02_backlog.md](02_backlog.md)), история (→ [03_progress.md](03_progress.md)), продуктовые решения (→ [04_decisions.md](04_decisions.md)), входящее на разбор (→ [_inbox/01_inbox.md](_inbox/01_inbox.md)).

---

## Session Handoff

### Что делаем

Интеграция матричной модели scaffold в канон методологии. Старая модель Аспект>Домен (`01_ceo / 02_strategy / 03_team / 04_company / 05_metrics`) заменена на матрицу (`00_ceo / 01_company / домены`). ADR с обоснованием, корневой раскладкой, распределительным принципом (владелец > НОП) и планом работ — в [00_dilemma.md](methodology/scaffold/00_dilemma.md).

### Что прочитать в новом чате

**ОБЯЗАТЕЛЬНО первым — ADR:**
- [methodology/scaffold/00_dilemma.md](methodology/scaffold/00_dilemma.md) — дилемма, варианты, выбор матрицы, раскладка `01_company/` и домена, что считается доменом, распределительный принцип, план трансформации канона

**Канон (старая модель, будет переписан в этом сеансе):**
- [01_architecture.md](methodology/scaffold/01_architecture.md)
- [02_folder-spec.md](methodology/scaffold/02_folder-spec.md)
- [02_file-spec.md](methodology/scaffold/02_file-spec.md)
- [02_readme-spec.md](methodology/scaffold/02_readme-spec.md)
- [03_node-files.md](methodology/scaffold/03_node-files.md)
- [03_contours.md](methodology/scaffold/03_contours.md)
- [deployment.md](methodology/scaffold/deployment.md)
- [open-questions.md](methodology/scaffold/open-questions.md)
- [README.md](methodology/scaffold/README.md)

### Что делать

По плану 00_dilemma § План трансформации канона, Трек 1, шаг 1: переписать [01_architecture.md](methodology/scaffold/01_architecture.md) — корневая модель под матрицу, определение домена, распределительный принцип, стадии развёртывания. Дальше — по цепочке (02_folder-spec → 03_node-files → 03_contours → deployment → open-questions → README), ломать порядок нельзя.

Параллельные треки (после канона): связанные слои (Трек 2 — `.claude/commands/svaib-scaffold.md`, `framework/README.md`, `memory/`, `ontology/`, ТЗ strategy redesign) и миграция клиентского `framework/scaffold/` v1 → v2 (Трек 3).

---

## ✅ Активные задачи

### Порядок в scaffold v4

#### Методология scaffold выверена
- [ ] обновляем все в связи с диллемой
- [ ] file architecture
	- [ ] нужно ли ее пересмотреть в целом теперь
- [ ] file folder-spec
- [ ] file file-spec
- [ ] file readme-spec
- [ ] folder-tamplates - как его теперь называть?
- [ ] file-tamplates - как их теперь называть
- [ ] deployment
- [ ] open questions
---
- [ ] решить глоссарий и словарь терминов (например каноническое название метрики) 
	- [ ] в т.ч. для нас
- [ ] решить про стратегию - маркетинговую, продуктовую, конкурентную
- [ ] решить вопрос а где вообще все про маркетинг - в компании, в процессе, в папочке маркетинг или например финансы - чтобы там все и процессы и метрики и т.д. и может сделать статус управленческий цикл - чтобы можно было в т.ч. собирать файлы папки или делать домен? как в архитектура арк-контекста - именно доменные файлы собираются в единый индекс или и то и другое. 
- [ ] может быть разворот файла выглядеть в виде списка файлов - как в маркетинге, а не как папка - чтобы не плодить кучу папок - как это разводить? Какой канон?
- [ ] а может быть разворачивание из узла в контуры (например у маркетинга есть своя стратегия, своя команда, свои метрики, свои )
- [ ] проставить файлам - статус final
- [ ] 
- [ ] формируем план ниже


#### Канон каждого базового файла scaffold

Для каждого — миссия файла + миссия канонических блоков внутри. То же, что сделали для overview в этой сессии, — по остальным.

- [ ] `README.md` - 
- [ ] `01_overview.md`
	- [ ] АС предлагаем - Overview содержит KP/KR с текущими значениями (не только цели). Альтернатива: только цели — отвергли.
	- [ ] - `scaffold/product/01_overview.md` — пересобрать под 5 блоков канона.
	- [ ] `scaffold/projects/{name}/01_overview.md` — пересобрать под 5 блоков; паспортную часть вынести в `profile.md`.
- [ ] `profile.md`
- [ ] `02_active.md`
- [ ] `02_backlog.md` — **Направление (Track) и Задача (Task). Подзадача = задача внутри задачи, глубина вложенности любая**
- [ ] `03_progress.md`
- [ ] `04_decisions.md`
- [ ] **Глоссарий**

#### Канон файлов и папок внутри направлений (от общего к частному)

Внутри типов сущностей scaffold (`04_company/{org_node}/`, `product/`, `projects/{name}/`) — цепочки файлов конкретных типов сущностей и их связки.

- [ ] **Глоссарий — где должен быть**
- [ ] **Папка [scaffold/clients/](scaffold/clients/)** — чёткое определение Setup: что это, зачем, для чего настройка папок
- [ ] **Определиться с папкой `docs/`** для доп-доков в направлениях
- [ ] **Определиться с папкой `wiki/`** по методу Karpathy (можно позже)

#### Канон README

Содержательный шаблон `README.md` по типам папок (глубже разграничения README ↔ overview, зафиксированного в [methodology/scaffold/02_readme-spec.md](methodology/scaffold/02_readme-spec.md)).

#### Что забираем из контекстной архитектуры и чужих архитектурных документов

Внимательно прочитать [memory/01_context_memory.md](memory/01_context_memory.md) и решить, что взять в scaffold на первый заход: YAML / front-matter, правила, хуки и т.д.

- [ ] Посмотреть какие инсайты можно взять из [ARCHITECTURE_maxim](_inbox/scaffold/ARCHITECTURE_maxim.md) при ревизии scaffold
- [ ] [memory/file_spec.md](memory/file_spec.md) — формат файла

#### Обновить файлы scaffold под Шаг 6

Применить решения по контекстной архитектуре (YAML, хуки, правила) к шаблонам scaffold.
- [ ] удалить файлы из клиентского 


#### Применить канон 5 блоков overview к шаблонам scaffold

- [ ] `scaffold/product/01_overview.md` — пересобрать под 5 блоков
- [ ] `scaffold/projects/{name}/01_overview.md` — пересобрать, паспорт вынести в `profile.md`
- [ ] `scaffold/04_company/{org_node}/01_overview.md` — пересобрать
- [ ] Добавить отсутствующий `scaffold/04_company/{org_node}/README.md`
- [ ] Однострочный README в архивных/служебных подпапках
- [ ] `scaffold/projects/{name}/README.md` — вынести методологию проекта в `principles.md` / `methodology.md`
- [ ] `scaffold/05_metrics/` — оставить отдельной парадигмой, но сверить терминологию

### Метрики у клиента

**Цель сессии 2026-05-12.** Запустить первый слой metrics-вертикали у Клиента 1: каноническое имя метрики, колонка с этим именем в его xlsx, помощник по колонке. Без extractor, без narrative, без compound — это второй слой, разворачивается по живому триггеру.

**Статус (после сессии 2026-05-12).**

Методология первого слоя сведена в канон:
- [x] [`methodology/metrics/first-layer.md`](methodology/metrics/first-layer.md) — рамка, DoD, формат `canonical_metrics.md`, граница со вторым слоем.
- [x] [`methodology/metrics/rollout.md`](methodology/metrics/rollout.md) — playbook (6 шагов вместо 12-шагового pilot).
- [x] [`methodology/metrics/HOWTO.md`](methodology/metrics/HOWTO.md) — сценарий «вопрос → каноническое имя → число из xlsx».
- [x] [`methodology/metrics/README.md`](methodology/metrics/README.md) — карта без статусности, точка входа теперь `first-layer.md`.
- [x] [`methodology/metrics/intake-form.md`](methodology/metrics/intake-form.md) — понижен до внутреннего чек-листа координатора.
- [x] [`scaffold/05_metrics/canonical_metrics.md`](scaffold/05_metrics/canonical_metrics.md) — шаблон под клиента.
- [x] [`scaffold/05_metrics/README.md`](scaffold/05_metrics/README.md) — `canonical_metrics.md` отмечен как стартовая точка.
- [x] [`methodology/metrics/architecture.md`](methodology/metrics/architecture.md) — маяк на `first-layer.md` в «Кратко», остальное не переписывалось.

**Клиентский трек (вне framework, идёт параллельно).** 2026-05-12: подготовлен черновик `clients/private/lebedev/docs/canonical_metrics_ssp.md` и бриф для CEO. Отправлен на правки. До возвращения правок колонку в xlsx и помощника не делаем — каноническое имя может измениться.

**Ближайшие шаги.**
- [ ] Получить правки CEO по черновику `canonical_metrics_ssp.md`.
- [ ] Внести колонку с каноническими названиями в главный лист xlsx (правило: пустое поле = метрика для помощника не существует).
- [ ] Положить финализированный `canonical_metrics.md` в scaffold клиента (точное место — по текущему канону scaffold).
- [ ] Smoke-test: 2–3 типовых вопроса CEO → помощник идёт в xlsx через каноническую колонку → возвращает число.

**Что не делаем в этом цикле (явно).** Per-client extractor, narrative composer, паспорта с `direction`/synonyms/antonyms, OKR-проекция, compound route, regular loop, история по месяцам, weekly metrics-ритуал, open-question #1 «narrative.py vs LLM-сборка». Все они — второй и третий слои; включаются по живому триггеру (см. [`methodology/metrics/first-layer.md`](methodology/metrics/first-layer.md), раздел «Триггеры перехода ко второму слою»).

**Точка входа в вертикаль:** [`methodology/metrics/README.md`](methodology/metrics/README.md) → [`methodology/metrics/first-layer.md`](methodology/metrics/first-layer.md).


### Помощники


## ⁉️ Открытые вопросы

-
