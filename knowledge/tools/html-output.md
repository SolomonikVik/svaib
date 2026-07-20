---
title: "HTML как слой вывода AI — формат доставки результата человеку (отчёт, дашборд, дек)"
source: "https://thariqs.github.io/html-effectiveness"
source_type: article
status: processed
added: 2026-06-14
updated: 2026-06-15
review_by: 2026-09-14
tags: [html, output, artifacts, presentation-layer, skills, generative-ui, design-tokens, dashboards, telegram]
publish: false
version: 3
---

# HTML как слой вывода AI

## Кратко

**HTML как слой вывода** — приём: AI отдаёт результат человеку не «стеной markdown», а как самодостаточный **HTML-артефакт** (отчёт, дашборд, презентация, схема, explainer). Данные **хранятся** в markdown/БД (под AI-чтение, git, поиск), а **наружу** рендерятся в HTML — под глаз человека и шеринг ссылкой. Ниша уже обросла инструментарием: скиллы-роутеры (детект формы → шаблон → один `.html`), платформы (Claude Artifacts, generative-UI сервисы) и приёмы брендирования (design-токены + `DESIGN.md` + шаблон-оболочка).

---

## Зачем HTML на выходе

HTML-артефакт сильнее «стены markdown», когда вывод смотрит **человек**:

- **Плотность.** Таблицы, CSS-вёрстка, SVG, код, интерактив, пространственные данные — в одном файле.
- **Визуальная навигация.** Табы, секции, иллюстрации, in-page навигация — длинный материал листается, а не читается подряд.
- **Шеринг.** Рендерится в браузере, отдаётся файлом или ссылкой → выше шанс, что реально посмотрят.
- **Интерактив.** Слайдеры, сортируемые таблицы, кнопка экспорта → двусторонняя петля с данными.

Лабораторных сравнений восприятия HTML и markdown не найдено — преимущество здесь оценивается как **практическое и наглядное** (презентация инвестору в HTML очевидно выигрывает у `.md`). Издержка: HTML **в несколько раз дороже** генерить (больше токенов и времени) — поэтому рендерим **лениво**, в момент выдачи.

---

## Два слоя: хранение и вывод

Markdown и HTML — не конкуренты, а **разные слои**.

- **Хранение = канонический источник.** Для документов это обычно markdown (дёшево, чисто в git-диффах, удобно AI). Для живых данных канон — БД/API.
- **Вывод = HTML.** Витрина: рендерится **по требованию** из источника под конкретного зрителя. Артефакт **одноразовый** — не источник правды, перегенерируется когда нужен свежий.

Аналогия: источник — база данных, HTML — отчёт, который из неё печатают. Рабочий паттерн: *канонический источник → HTML по требованию → рендер в `.gitignore`* (снимает шумные HTML-диффы, сохраняя плюсы для человека). Та же модель «текст-источник → богатый HTML-вид» давно живёт в MDX и Quarto/Pandoc.

---

## Когда HTML, когда markdown

- **HTML** — у вывода есть вёрстка, таблицы, SVG/диаграммы, сворачиваемые секции, интерактив; или его отдают человеку/стейкхолдеру.
- **Markdown** — это инструкция, будет переиспользовано моделью, живёт в git, важен бюджет токенов.

Короткая эвристика практиков: *читатель-человек → HTML; читатель-модель → markdown.*

---

## Типы артефактов вывода

Устойчивая таксономия «форм» (на ней строятся скиллы-роутеры):

- **report** — статусы, post-mortem, аудиты: график + таймлайн, «проскролил» → «прочитал».
- **data-viz / dashboard** — KPI-карточки, тренды, доли; фильтры и сортируемые таблицы.
- **deck** — листаемые слайды (`<section>` + немного JS) без Keynote.
- **diagram** — inline-SVG схемы, графы, карты связей.
- **prototype** — кликабельный прототип; движение/интеракцию нельзя описать, только почувствовать.
- **spec / explainer** — explainer со сворачиванием, табами кода, глоссарием.
- **editor** — одноразовый редактор под задачу, всегда с кнопкой экспорта (данные возвращаются агенту).

---

## Инструментарий: чем генерить

### Скиллы-роутеры (детект формы → шаблон → один .html)

Ядро ниши. Конвейер: *вход → детект формы → загрузка паттернов под форму → генерация → валидация в браузере → самодостаточный `.html`*.

- **[html-artifact](https://claudskills.com/skills/html-artifact/)** — главный универсальный роутер. Детектит ~8 форм (spec, code-review, prototype, report, editor, data-viz, diagram, deck), под каждую грузит свои паттерны. Несёт дизайн-систему (Birchline) + темы. Триггеры: «make HTML / as HTML», либо авто-инъекция роутером, когда вывод выигрывает от визуализации.
- **[claude-design-skill](https://github.com/jiji262/claude-design-skill)** — самый детально документированный (адаптация внутреннего дизайн-промпта Claude.ai), показательный пример «как устроен роутер». Формы: деки, design-canvas (сетка вариантов), прототипы (React+Babel), timeline-анимации, wireframes. Внутри — рабочие протоколы: **fact-verification до генерации** (WebSearch по названному продукту — экономит часы переделки), **Visual System Declaration** (цвета/типографика до пикселей), **Advisor Mode** (на размытый бриф предлагает 3 направления), **anti-slop** правила в коде, pinned-версии + integrity hashes против «тихих» поломок. `assets/` — готовые HTML-каркасы (`deck-stage.html`, `prototype-shell.html`), в которые льётся контент.
- **[theme-factory](https://github.com/anthropics/skills/blob/main/skills/theme-factory/SKILL.md)** (Anthropic, офиц.) — не генератор, а **слой темизации** поверх готового артефакта: палитра + парные шрифты, накатывается отдельным шагом с подтверждением. Воплощает «стиль отдельно от контента».
- **[web-artifacts-builder](https://github.com/anthropics/skills/blob/main/skills/web-artifacts-builder/SKILL.md)** (Anthropic, офиц.) — для **сложных** артефактов (state, routing, shadcn/ui): React+Vite+Tailwind → бандлится в один self-contained `bundle.html`. Водораздел: простой вывод → один `.html`; нужны состояние/роутинг → builder.
- **[build-dashboard](https://awesomeskill.ai/skill/anthropics-knowledge-work-plugins-build-dashboard)** (Anthropic knowledge-work) — узкая форма: данные (query/CSV/текст) → HTML-дашборд на Chart.js (данные встроены; сам Chart.js может грузиться с CDN — для офлайна инлайнить), KPI-карточки на CSS Grid, print-friendly.
- **[frontend-design](https://claude.com/blog/improving-frontend-design-through-skills)** (Anthropic) — не генератор, а **слой вкуса**: грузит контекст по осям (типографика, цвет, motion, фоны), борется с generic-дизайном.

**Общее:** `SKILL.md` + `references/` (паттерны под форму) + `assets/` (HTML-скелеты) + шаг валидации + результат = самодостаточный `.html`. **Отличаются** глубиной роутинга: html-artifact/claude-design детектят форму и грузят разные паттерны; theme-factory только темизирует; build-dashboard заточен под одну форму.

### Платформы

- **[Claude Artifacts / Live Artifacts](https://support.claude.com/en/articles/14729249-use-live-artifacts-in-claude-cowork)** — Artifacts: live-preview HTML/React рядом с чатом, скачивается как `.html`. **Live Artifacts** (в Cowork) — персистентная страница, **перезапрашивающая данные из коннекторов** (Sheets, Notion, CRM) при открытии: дашборды, трекеры.
- **[Thesys C1 / OpenUI](https://docs.thesys.dev/)** — OpenAI-совместимый эндпоинт, который **возвращает готовый UI вместо текста** (drop-in замена LLM-вызова), стримит компоненты, встроенная realtime-починка незавершённого ответа. Для встраивания generative-UI в свой продукт.
- **[Vercel v0 / AI SDK](https://vercel.com/blog/ai-sdk-3-generative-ui)** — generative UI: LLM-вывод привязан к реальным React-компонентам. v0 генерит **код, который ты владеешь**; AI SDK — компонент в рантайме.
- **[Tambo](https://medium.com/@akshaychame2/the-complete-guide-to-generative-ui-frameworks-in-2026-fde71c4fa8cc)** — агент выбирает из **твоих утверждённых** React-компонентов по интенту. Стиль зафиксирован архитектурно (важно для бренда).
- **[Gamma](https://gamma.app/explore/content/guides/what-is-gamma-and-how-does-it-use-ai-to-build-presentations)** — текст/аутлайн → презентация за ~минуту; поддерживает свои цвета/шрифты/лого (тема). Но без pixel-control layout и жёсткого энфорса корп-шаблона — для строгого бренда слабее, чем связка токены + шаблон-оболочка.

### Дешёвый брендированный markdown → HTML (недооценено)

- **[Marp / Slidev](presentations.md)** и **[Quarto/Pandoc](https://quarto.org/docs/presentations/revealjs/)** рендерят markdown → брендированный HTML (слайды, отчёты, сайты), где бренд зашит в CSS-тему, а AI пишет только контент. Marp даёт HTML заметно легче reveal.js. Зрелый non-AI слой «контент отдельно, стиль отдельно», в который LLM поставляет markdown. Презентации — частный случай этого слоя ([presentations.md](presentations.md)).

---

## Как генерить хорошо

**Работает:**
- **Форма до контента.** Сначала зафиксировать форму вывода и структуру данных, потом генерить (так устроены роутеры).
- **Декларация визуальной системы до пикселей** — цвета/типографика/spacing заранее.
- **Fact-verification** при упоминании реального продукта/бренда (WebSearch) — до генерации.
- **Структурированный вход/выход** (схемы, JSON-данные инлайн) надёжнее «уговоров промптом».
- **Валидация в реальном браузере** перед «готово»; pinned-зависимости + integrity hashes для React/Babel.

**Не работает (антипаттерны):**
- **Generic «AI-дизайн» (AI slop).** Anthropic зовёт это «distributional convergence»: без направления AI скатывается в шаблонное. Tells, которых избегать: затёртые шрифты (Inter, Roboto, system), клише-палитры (purple gradients on white), excessive centered layouts, uniform rounded corners, emoji-буллеты, CSS-силуэты вместо реальных продуктовых шотов.
- **Сломанный JS.** LLM выдаёт *правдоподобный*, не *корректный* код — уверенные вызовы несуществующих функций → ошибки. Лечится пост-валидацией/авто-починкой (error-resilience как у Thesys C1 — на уровне рендера, не промпта).
- **Token-bloat.** Голый HTML съедает на ~80–90% больше токенов, чем сам контент; не гнать тяжёлые бандлы.
- **LLM не исполняет JS.** Если контент «дорисовывается» рантайм-JS — для downstream-систем он невидим. Критичное держать в **статичном HTML**.

---

## Брендирование вывода

Главный принцип: **разделить структуру и стиль** — шаблон задаёт layout, токены задают вид, AI заполняет **контент**, а не сочиняет стиль. Рабочая комбинация:

1. **Design-токены (JSON/DTCG)** — точные значения цветов, типографики, spacing; агент *подставляет*, а не угадывает. [Design tokens with AI agents](https://www.mindstudio.ai/blog/design-tokens-ai-agents-consistent-brand-visuals)
2. **`DESIGN.md`** — несёт *суждение/правила*, чего JSON не может («primary использовать скупо», иерархия, тон); грузится в каждый проход. Относительно новая практика как **переносимый бренд-актив** (Google Stitch, реестры). [DESIGN.md vs tokens](https://wavespeed.ai/blog/posts/design-md-vs-design-tokens-ai-workflows/), [готовые системы — awesome-claude-design](https://github.com/VoltAgent/awesome-claude-design)
3. **Шаблон-оболочка** (assets-скелет) — готовый HTML-каркас, AI льёт контент внутрь границ.

Альтернатива — бренд **через компоненты** (Tambo: AI выбирает из утверждённых). Двухслойка «движок форм + слой бренд-темы» (html-artifact + theme-factory) — хороший паттерн для своего пайплайна.

---

## Доставка артефакта

- **Self-contained inlined `.html`** — весь JS/CSS/данные внутри, открывается в любом браузере офлайн, без аккаунта. Самый простой способ отдать не-технику (файл/почта). Минус: статично (нет live-данных).
- **Hosted share-link платформы** — Claude Artifacts публикуются с публичным URL. Удобно переслать; нюанс — часть share-link требует доступа к платформе у получателя. [share Claude artifact](https://www.shareduo.com/blog/claude-artifacts-not-working-for-others)
- **Внешний хостинг** — HTML как обычный сайт (домен, аналитика, формы). Полный контроль ценой лишнего сервиса.
- **Live-данные** → Live Artifact в Cowork (локальный, перезапрашивает коннекторы).

**Telegram rich messages (Bot API 10.1, июнь 2026)** — промежуточная ступень между markdown-стеной и полным HTML-артефактом: бот методом `sendRichMessage` шлёт document-grade сообщение **прямо в чат** (таблицы, заголовки, вложенные списки, формулы, сворачиваемые блоки, цитаты) без файла и без ссылки. Контент задаётся одним полем — `html` или `markdown` (GFM-подобный), Telegram сам парсит блоки. Цена: рендер нативным стилем Telegram — **нет бренда, CSS/SVG, интерактива**, и только внутри Telegram. Ниша — операционный/внутренний вывод (дайджесты, сводки), не брендированная клиентская поставка. [Bot API 10.1](https://core.telegram.org/bots/api#sendrichmessage).

**Безопасность (важно для клиентской поставки).** Самодостаточный `.html` означает «не зависит от внешних ресурсов», **но не равно «ничего не утекает»**: инлайн-JS всё равно может слать данные в сеть. Гарантия приватности — офлайн или CSP с блокировкой сети. Если рендеришь AI-HTML в доверенном/чужом контексте — изолируй: `sandbox="allow-scripts"` iframe (не вместе с `allow-same-origin`) + CSP, блокируй сеть по умолчанию, **вырезай внешние картинки** (классический канал утечки через инъекцию ``). Клиентский markdown — **недоверенный вход** (indirect prompt injection), не только выход.

---

## Живой vs одноразовый артефакт

Две независимые оси решают тип вывода:

- **Персистентность.** *Одноразовый* (рендерится, состояния нет, перегенерируется) ↔ *живой интерфейс* (подключён к данным, переспрашивает при открытии — Claude Live Artifacts).
- **Контроль над UI.** *Статичный* (ты владеешь шаблоном/компонентами, модель заполняет) → *декларативный* (модель отдаёт JSON-спеку UI) → *open-ended* (модель пишет весь HTML). Для брендированной клиентской поставки — статичный конец.

Решать по порядку: (1) нужно ли пережить сессию и отражать меняющиеся данные → одноразовый или живой; (2) сколько UI-власти отдать модели.

---

## Границы темы

- **HTML на ВЫХОДЕ ≠ HTML на ВХОДЕ.** Этот файл — про вывод человеку. Вопрос «в каком формате подавать таблицы в контекст модели» — другая ось (вход), и там HTML как универсально лучший формат таблиц спорен. Оба тезиса истинны одновременно.
- Парная тема про вход — markdown как формат для LLM/RAG: [../context/markdown-for-llm.md](../context/markdown-for-llm.md).

---

## Связь с svaib

У нас слой вывода уже частично реализован — фирменные спеки HTML-артефактов и бренд живут в `meta/marketing/brand/` (это наша реализация). Здесь — внешняя теория и инструментарий, на которые она опирается.

---

## Связанные файлы

- [../context/markdown-for-llm.md](../context/markdown-for-llm.md) — парная ось: markdown как формат на **входе** для LLM/RAG (этот файл — про **выход**)
- [presentations.md](presentations.md) — деки как частный случай слоя вывода (Marp/Slidev: markdown → слайды)
- [cowork.md](cowork.md) — среда генерации/превью HTML-артефактов для не-разработчиков
- [../coding/ui-design.md](../coding/ui-design.md) — соседняя ось: генерация **интерфейсов продукта** (Lovable/v0/Bolt) ≠ вывод **данных** как артефакт
- [../skills/!skills.md](../skills/!skills.md) — формат скиллов; здесь скиллы-роутеры как реализация слоя вывода
- [../metrics/!metrics.md](../metrics/!metrics.md) — граница: формат таблиц на входе в контекст (другая ось)

---

## Источники

- [Thariq Shihipar — Unreasonable Effectiveness of HTML](https://thariqs.github.io/html-effectiveness/) — галерея ~20 артефактов, 9 форм (первоисточник идеи)
- [html-artifact skill](https://claudskills.com/skills/html-artifact/) — shape-router + дизайн-система
- [claude-design-skill](https://github.com/jiji262/claude-design-skill) — детальный пример роутера, anti-slop протоколы
- [theme-factory](https://github.com/anthropics/skills/blob/main/skills/theme-factory/SKILL.md), [web-artifacts-builder](https://github.com/anthropics/skills/blob/main/skills/web-artifacts-builder/SKILL.md) — официальные скиллы Anthropic
- [Improving frontend design through Skills](https://claude.com/blog/improving-frontend-design-through-skills) — distributional convergence / anti-slop
- [Claude Live Artifacts](https://support.claude.com/en/articles/14729249-use-live-artifacts-in-claude-cowork), [Thesys C1](https://docs.thesys.dev/), [Vercel AI SDK](https://vercel.com/blog/ai-sdk-3-generative-ui) — платформы
- [DESIGN.md vs Design Tokens](https://wavespeed.ai/blog/posts/design-md-vs-design-tokens-ai-workflows/), [awesome-claude-design](https://github.com/VoltAgent/awesome-claude-design) — брендирование вывода
