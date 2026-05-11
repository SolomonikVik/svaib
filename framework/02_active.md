---
title: "Framework — актуальное"
updated: 2026-05-06
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

Финальный проход по `methodology/scaffold/` 

### Что прочитать в новом чате

**Канон и контекст (SOT, не правим):**
- [02_file-spec.md](methodology/scaffold/02_file-spec.md) — канон md-файла
- [02_folder-spec.md](methodology/scaffold/02_folder-spec.md) — канон папки
- [02_readme-spec.md](methodology/scaffold/02_readme-spec.md) — канон README
- [01_architecture.md](methodology/scaffold/01_architecture.md) — модель контуров
- [README.md](methodology/scaffold/README.md) — карта контура
- [03_contours.md](methodology/scaffold/03_contours.md) — обвязка под канон 06.05 + досверка анатомии контуров
- [deployment.md](methodology/scaffold/deployment.md) — обвязка под канон 06.05
- [open-questions.md](methodology/scaffold/open-questions.md) — обвязка + что закрылось
- [03_node-files](methodology/scaffold/03_node-files.md)

**Клиентский scaffold (для досверки):**
- [framework/scaffold/README.md](scaffold/README.md)
- структура контуров `01_ceo/`, `02_strategy/`, `03_team/`, `04_company/`, `05_metrics/`, `product/`, `projects/`, `clients/`, `knowledge/`, `processes/` — пробежать (`ls`), читать конкретные файлы по ходу досверки

Спроси у Виктора - что делать

---

## ✅ Активные задачи

### Порядок в scaffold v3

#### Методология scaffold выверена
- [x] file folder-spec
- [x] file file-spec
- [x] file readme-spec
- [x] file architecture
	- [x] выносим узлы в folder-spec
	- [x] даем общее описание архитектуры
	- [x] выверяем
	- [x] после прочтения темпейтс - надо что-то менять?
- [x] folder-tamplates
- [x] file-tamplates
- [ ] deployment
- [ ] open questions
- [x] переименовать tamplates 02 -> 03
---
- [x] переименовать zz_archive
- [x] решить нужен ли docs на верхнем уровне
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
- [ ] Возможно сперва нужно сделать какую-то единую сводную задачу и сперва навести порядок методологии, а потом вернуться к клиенту (подумать)
- [ ] **Клиент-1 на живой базе** — intake-form + ответы → Cowork-тест на боевом

- Детали — [_inbox/metrics-scaffold/plan.md](_inbox/metrics-scaffold/plan.md) и [methodology/metrics/open-questions.md](methodology/metrics/open-questions.md) (секция «Что спросить у первого клиента до Б.2»)
- [ ] Определить технику внедрения канонического ID метрики в Excel-таблицу (колонка между B и C, видимая или скрытая, требования к заполнению).

**Реорганизация metrics завершена 2026-04-30.** Методология вертикали собрана в `methodology/metrics/`, skill-папка очищена, стандарт `extractors/` зафиксирован, smoke-test пройден, Codex-ревью отработан. Подробнее — [`03_progress.md`](03_progress.md) запись 30.04 (вторая за день).

**Next — двинуть клиентскую задачу.** Дать клиенту [`intake-form.md`](methodology/metrics/intake-form.md) + дополнительные вопросы из [`open-questions.md`](methodology/metrics/open-questions.md) секция «Что спросить у первого клиента до Б.2» → получить ответы → начать тестировать на его живой базе через Cowork (см. [`COWORK-TEST.md`](_inbox/metrics-scaffold/cowork-test/COWORK-TEST.md) как готовый pack).

Цель к концу следующей недели — pipeline работает на боевых данных клиента в его Cowork-окружении.

Точка входа в вертикаль для нового чата — [`methodology/metrics/README.md`](methodology/metrics/README.md).


### Помощники


## ⁉️ Открытые вопросы

-
