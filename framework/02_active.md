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

### ⭕️ Порядок в scaffold v4

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

### ⭕️ Метрики у клиента

**Цель.** Первый слой metrics-вертикали — AI-аналитик контура базовых target metrics CEO. Полноценный собеседник по этому контуру: понимает речь CEO, читает семантику метрик, идёт в источник, считает, анализирует, отвечает в формате, который подходит вопросу.

**Что умеет.**

- **Ad-hoc вопросы CEO** своими словами: «растём или нет?», «что просело в марте?», «почему MRR не вырос?», «покажи динамику за квартал», «сравни с прошлым годом», «где разрыв план/факт».
- **Анализ:** сравнивает периоды и годы, считает дельты, видит динамику, подсвечивает аномалии, формулирует управленческий вывод — а не сырое число.
- **Подача:** число / narrative / таблица / HTML с графиком — выбирает по вопросу.
- **Регулярные ритуалы** — если CEO просит: недельная сводка в Telegram, утренний бриф к понедельнику, отчёт на C-level встречу. 

**На чём работает.**

- Один канонический список метрик контура (базовые target metrics, как их называет CEO в речи и в xlsx).
- Один главный источник (xlsx/Sheets клиента) с месячной/годовой динамикой и планом/фактом, где они есть в источнике.

**Принцип масштабируемости.**

Единица расширения = **domain** (соответствует канону имён в [`methodology/metrics/architecture.md`](methodology/metrics/architecture.md), раздел «Канонические имена domain-файлов»). Domain = канонический список метрик одного управленческого фокуса CEO + его источник + аналитические функции над ними.

Сейчас domain один — базовый `business-metrics.md` (то, что у CEO держится в голове как «весь бизнес одной картинкой»).

С первого дня мы строим не «единичный пример», а архитектурный шаблон domain, которым потом наращивается весь бизнес.

**Принцип реализации.** Помощник детерминирован в данных (не считает в голове, всё через инструмент), свободен в подаче (формат ответа выбирает под вопрос). Знание + думание + инструменты + подача.

---

**DoD.**
- У Клиента 1 в scaffold лежит `business-metrics.md` со списком его target metrics.
- В источнике есть привязка, по которой помощник детерминированно находит данные метрики (служебная колонка с каноническими именами; контракт — [`methodology/metrics/metrics-spec.md`](methodology/metrics/metrics-spec.md)).
- Системный промпт оркестратора metrics настроен под думающую аналитику базового domain.
- Помощник отвечает содержательно на 3–5 типовых вопросов CEO («растём или нет», «что просело в марте», «динамика за квартал», «сравни с прошлым годом», «где разрыв план/факт»).

#### Этап 1 — верифицировать и докрутить семантический слой

- [x] [`methodology/metrics/metrics-spec.md`](methodology/metrics/metrics-spec.md) — внутренняя логика (раскладка, поля метрики, контракт привязки, формулировки). 
	- [x] Соответствие [`methodology/scaffold/02_file-spec.md`](methodology/scaffold/02_file-spec.md) (YAML минимум, шапка, H1-формула — где разумно применить без зацементирования драфтной спеки scaffold).
- [x] [`scaffold/05_metrics/business-metrics.md`](scaffold/05_metrics/business-metrics.md) — исправить на основании спеки
- [x] Клиентский `business-metrics.md` под Клиента 1 — целиком, формат и содержание. Доводка до отправляемого артефакта.


#### Этап 2 — отправка клиенту

Артефакты к отправке готовы в [`clients/private/lebedev/docs/`](../clients/private/lebedev/docs/):
- [`business-metrics.md`](../clients/private/lebedev/docs/business-metrics.md) — черновик клиента по новой спеке.
- [`metrics-intake-prompt.md`](../clients/private/lebedev/docs/metrics-intake-prompt.md) — промпт-помощник, чистый текст для копирования в LLM-сессию Жени.

Черновик письма Жене — в чате прошлой сессии (4 блока: что строим / зачем семантический слой / три шага / что прислать обратно).

- [x] **Промпт-помощник** занесён в систему: [`skills/metrics-analysis/business-metrics-intake.md`](skills/metrics-analysis/business-metrics-intake.md), README skill-папки обновлён.
	- [ ] Упоминание в [`methodology/metrics/rollout.md`](methodology/metrics/rollout.md) / карте вертикали — отложено до Этапа 3 (переписывание методологии).
- [x] Отправить письмо + два файла CEO Клиента 1.
- [ ] Получить обратно заполненный `business-metrics.md` + ссылку на xlsx со служебной колонкой.
- [ ] Зафиксировать финальный артефакт в папке клиента.

#### Этап 3 — переписать методологию

Контекст: `metrics-spec.md` — свежий, актуальный канон. `architecture.md`, `rollout.md`, `HOWTO.md`, `README.md`, `intake-form.md` — старые, рассинхронизированы.

Под пересмотр:
- [`methodology/metrics/architecture.md`](methodology/metrics/architecture.md) — структурный пересмотр. Не косметика: переосмысление, что вообще в этом документе должно лежать. Сейчас смешана старая 6-слойная модель и свежий каркас. Решить: что остаётся, что выносится, как стыкуется со спекой.
- [`methodology/metrics/rollout.md`](methodology/metrics/rollout.md), [`HOWTO.md`](methodology/metrics/HOWTO.md), [`README.md`](methodology/metrics/README.md), [`intake-form.md`](methodology/metrics/intake-form.md) — содержат старую формулировку «помощник по колонке достаёт число», битые ссылки на удалённый `first-layer.md`, упоминания шифра `L1/L2`, поля `version` у метрики, описания таблиц с синонимами/хешом схемы. Переписать под AI-аналитик target metrics + текущую спеку.
- [`scaffold/05_metrics/template-domain.md`](scaffold/05_metrics/template-domain.md), [`scaffold/05_metrics/01_metrics.md`](scaffold/05_metrics/01_metrics.md) витрина — под пересмотр в логике «функциональный domain = тот же формат, что базовый, шире охват».
- Спека функциональных domain в `metrics-spec.md` — сейчас минимальная (унаследование от базового). Если по факту работы у клиентов появятся расширенные поля паспорта — донести в спеку.

**Точка входа в вертикаль:** [`methodology/metrics/README.md`](methodology/metrics/README.md) → [`methodology/metrics/architecture.md`](methodology/metrics/architecture.md) → [`methodology/metrics/metrics-spec.md`](methodology/metrics/metrics-spec.md).

#### Этап 4 — переписать методологию
Строим помощника для клиента

### ⭕️ Помощники


## ⁉️ Открытые вопросы

-
