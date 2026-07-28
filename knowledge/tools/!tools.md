---
title: "AI-инструменты и платформы автоматизации — сводка"
status: processed
added: 2026-01-30
review_by: 2026-10-21
tags: [tools, automation, platforms, index]
publish: false
updated: 2026-07-27
---

# Tools — AI-инструменты и платформы

## Кратко

Платформы автоматизации и AI-инструменты, НЕ связанные с написанием кода. Готовые агентные продукты (Manus, OpenClaw) — тоже здесь. Не путать с: coding/ (IDE, кодинг-ассистенты) и agents/ (разработка агентов — протоколы, SDK, паттерны).

---

## Темы

### AI-оболочки

Среды, через которые пользователь работает с AI. Для SVAIB это интерфейс клиента: мы наполняем оболочку содержимым. Каталог: Claude Code, Claude Project, Cowork, OpenCode, Codex, Kojori, ValeDesk, VS Code. → [ai-workspaces.md](ai-workspaces.md)

### Claude Project

Веб-интерфейс Claude (claude.ai) с подключением данных. Основной runtime для клиентов SVAIB: руководитель в браузере, данные в Google Docs, AI читает через Drive Fetch. Google Workspace коннекторы (Drive Search + Drive Fetch), три уровня доступа (System Prompt / Project Files / Project Knowledge). Ключевое: Drive Fetch даёт актуальную версию, RAG отстаёт на 2+ часа. → [claude-project.md](claude-project.md)

### Cowork и плагины

Agent platform Anthropic для не-разработчиков. Формат плагинов идентичен Claude Code, **кроме hooks** — они молча не срабатывают в sandboxed VM Cowork (открытый баг Anthropic), значит enforcement-логика на хуках для этого канала delivery не годится. → [cowork.md](cowork.md)

### Buildin — клиентское no-code пространство

Китайский аналог Notion, доступен в РФ. Используется командами как замена Notion, отрезанного из РФ — и значит регулярно встречается у клиентов SVAIB как уже существующее хранилище контрактов, реестров, баз сотрудников. Три пути забрать данные: REST API (`api.buildin.ai/v1`, JSON block tree, конвертация в md на нашей стороне), hosted MCP (`mcp.buildin.ai/message?token=...`, подключается одной строкой в `.mcp.json`, но список tools не документирован), UI-экспорт страницы в Markdown/PDF/CSV/Word. Ключевое: API и MCP — только с тарифа Plus (платный), Free даёт лишь UI-экспорт. Database = страница с `parent.database_id`, row БД — обычная page; permission плагина выдаётся поштучно на page (наследование с БД не подтверждено документально). Community вокруг SDK почти отсутствует — на чужие грабли опереться не получится. → [buildin.md](buildin.md)

### Obsidian — md-платформа с командной коллаборацией

Локальный редактор базы знаний на обычных .md-файлах (данные у пользователя, кросс-девайс). Для SVAIB — альтернативный слой хранения/рантайма к Google Drive + Claude Project, закрывающий то, что у Drive болит: командную коллаборацию с приватными/общими зонами и одновременную запись — через плагин **Relay** (real-time на Yjs/CRDT, слияние правок без конфликтов, шаринг отдельных папок, роли). Agent-writable — через **Obsidian MCP** (read/write в vault, правка frontmatter). CRDT-движок Relay (Yjs) — open-source, тот же класс лежит в OSS-альтернативах (Nextcloud Text, HedgeDoc). → [obsidian.md](obsidian.md)

### OpenKnowledge (Inkeep) — AI-native md IDE / LLM-wiki

Открытый (GPL-3.0) редактор базы знаний от Inkeep: WYSIWYG над обычными .md/.mdx, которые агент (Claude, Codex, Cursor, OpenClaw и др.) правит **нативно через MCP + skills**, без облака. Продуктовая реализация паттерна LLM Wiki (Карпатый) с фокусом «company/second brain» — то же направление, что SVAIB. Dual-observer Yjs/CRDT синхронит WYSIWYG↔сырой md **локально** (человек↔агент↔файл, не мультиплеер); командный шаринг — через git/GitHub auto-sync; поиск — Orama (гибрид). Local-first. Смотреть на copyleft GPL-3.0 и свежесть проекта. → [openknowledge.md](openknowledge.md)

### Командные контентные платформы с AI

Класс, к которому клиент приходит с вопросом «где команде хранить данные, с которыми работает AI». Два устройства рынка: интегрированный контур, где документы, пространства, поиск и AI живут внутри одной платформы (Microsoft 365, Google Workspace, Box, Notion, Nextcloud), и AI-слой поверх чужих систем, подчиняющийся их правам (Atlassian Rovo, Glean). Зрелость определяется не качеством чата, а синхронизацией прав, аудитом и контролем действий агента. Три вещи, которые важно знать заранее: (1) **приватность от организации не даёт ни одна централизованная платформа** — owner в Notion находит приватные страницы через Content Search, Google super admin и Vault экспортируют данные, Box Content Manager открывает контент managed users; это обратная сторона offboarding и legal hold; (2) чтение агентом контролируется отдельно от скачивания — Box исключает классифицированный контент из чтения/поиска AI, Slack запрещает AI отдельные каналы; (3) политика владельца данных меняется росчерком пера — Salesforce ограничил Slack API до «query-by-query», выбив Slack-данные из индексов сторонних AI-платформ. Выход наружу без копирования файлов — через MCP (Box MCP Server с admin-guardrails, инструменты Nextcloud). → [team-content-platforms.md](team-content-platforms.md)

### Web Scraping APIs

Прокси-сервисы для обхода anti-bot защиты. Нужны когда AI-агент не может достать веб-страницу. Firecrawl, scrape.do, Apify. → [web-scraping-apis.md](web-scraping-apis.md)

### Запись и транскрибация встреч

Выбор идёт не по сценарию записи, а по **контуру данных**: может ли аудио покидать периметр → отдаёт ли ВКС клиента машинный транскрипт сама (Teams Graph, Zoom webhook) → чем записывать → тест русского. Второй ключ отбора — **машинный доступ без ручного копирования**, в трёх классах: автоматический push (webhook, watch folder), управляемый pull (API, MCP, CLI, чтение локальной базы) и только ручной UI-экспорт — не проходит лишь третий. MCP при этом не доказывает автоматизацию: это чтение по запросу, а не доставка. Канонический артефакт — сырой транскрипт со спикерами, не саммари вендора. Кандидаты на пилот: зарубежное облако — Krisp Core ($8, botless, Mac/Win/mobile, webhook), российское — mymeet.ai либо нативные Толк/Телемост/MTS Link, локально — MacWhisper (€64) / Vibe, без ноутбука — Plaud. Circleback — премиум-альтернатива Krisp втрое дороже без доказанной дельты. Всё собрано по документации вендоров; живьём проверены только MacWhisper и Plaud, качество русского не измерено ни у кого — отсюда приёмочный тест в файле. → [meeting-transcription.md](meeting-transcription.md)

### STT-модели для русского языка

Сравнение движков распознавания русской речи. В бенчмарке AlphaCephei (11 датасетов, 13 моделей) GigaAM-v3 (Сбер, MIT) — лидер с двукратным отрывом от Whisper (~8% vs ~16% средний WER), на зашумлённом аудио разрыв 4x. Важно: WER сопоставим только внутри одного замера — цифры из разных источников (fine-tuned antony66, облачные API, заявления вендоров) сравнивать с этой таблицей нельзя. Три бэкенда исполнения Whisper: C++ (GGML, универсальный), WhisperKit (Apple Silicon, ANE), Parakeet v3 (NVIDIA, скорость). Облачные: Groq (быстрый и бесплатный, но это инфраструктурный STT-слой, а не продукт для руководителя), Soniox (code-switching рус+англ), ElevenLabs Scribe v2, Yandex SpeechKit. → [russian-stt-models.md](russian-stt-models.md)

### n8n — платформа автоматизации

Open-source платформа для построения workflow-автоматизаций (self-hosted и cloud). Для SVAIB — основная платформа автоматизации. Разработка n8n workflow через Claude Code (MCP-серверы, скиллы, паттерны) → [coding/n8n-claude-code.md](../coding/n8n-claude-code.md). n8n также поддерживает Instance-Level MCP (v1.76+) — workflow становятся MCP-тулами для AI-клиентов. Нативный AI Workflow Builder — cloud-only beta. Когда вообще выбирать workflow, а когда агента (и гибрид «агент пишет workflow») → [agents/workflow-automation.md](../agents/workflow-automation.md).

### Автономные агенты (готовые продукты)

Готовые AI-агенты, которым делегируешь задачу (в отличие от оболочек, В которых работаешь). Выполняют многошаговые задачи в фоне: браузер, код, файлы, отчёты. Работают через мессенджеры и веб-интерфейс. Про архитектуру и разработку агентов → agents/.

- **OpenClaw** (ex-Clawdbot) — open-source self-hosted. Архитектура Gateway-Agent-Skills-Memory. Мессенджеры (WhatsApp, Telegram, Slack, Discord, Signal, iMessage). Peter Steinberger (→ OpenAI). → [openclaw.md](openclaw.md)
- **Manus** — коммерческий (Meta). Multi-agent архитектура. Skills + Connectors (Notion, Calendar, Drive). Telegram-бот (февраль 2026), планируют WhatsApp, LINE, Slack. → [manus.md](manus.md)

Уровнем выше одиночных агентов — **оркестратор «AI-компании»**: не один бот, а команда агентов с org chart, ролями, бюджетами и governance.

- **Paperclip** — open-source (MIT), self-hosted. Node.js + React-дашборд, embedded Postgres. Agent-agnostic («если принимает heartbeat — нанят»), делегирование по org chart, hard-stop по бюджету, владелец = совет директоров. Фрейм: «OpenClaw — сотрудник, Paperclip — компания». Прямо резонирует с вижном SVAIB (AI-компания для руководителя). → [paperclip.md](paperclip.md)

### Презентации с AI

Два подхода: markdown-first и визуальные AI-генераторы. Markdown-first — это Marp и Slidev: оба конвертируют .md в слайды, живут в git, редактируются AI напрямую, но делают разные ставки. **Marp** — статический рендер, минимум окружения (standalone binary или CLI), чистый Markdown + CSS, низкая кривая входа; выбираем когда нужны быстрые рабочие презентации без возни. **Slidev** — Vite + Vue 3 компоненты, интерактив, Monaco, Magic Move, Presenter View, запись с камерой; выбираем для технических демо и конференционных докладов. Ключевое структурное различие: у **Slidev есть официальный Agent Skill** от самих авторов (`npx skills add slidevjs/slidev`) + выделенная страница «Work with AI» в документации; у Marp — зоопарк community-скиллов разного качества. Оба вписываются в file-first философию продукта. Визуальные генераторы (Lovable, Gamma, NotebookLM, Slider AI) — альтернатива для быстрого результата без дизайн-навыков, но ценой потери git-workflow и AI-редактирования. → [presentations.md](presentations.md)

### HTML как слой вывода AI

Приём: AI отдаёт результат человеку не «стеной markdown», а как самодостаточный **HTML-артефакт** (отчёт, дашборд, дек, схема). Два слоя: данные **хранятся** в markdown/БД, наружу **рендерятся** в HTML по требованию (рендер одноразовый, в `.gitignore`). Эвристика: читатель-человек → HTML, читатель-модель → markdown. Рабочая практика, не гипотеза — HTML-вывод плотнее и нагляднее текста; издержка — дороже генерить, поэтому лениво. Ядро ниши — **скиллы-роутеры**: детект формы вывода → шаблон под форму → валидация → один `.html` (html-artifact, claude-design, build-dashboard; theme-factory — слой темизации). Платформы: Claude Artifacts/Live Artifacts (живые дашборды из коннекторов), Thesys C1 / Vercel AI SDK / Tambo (generative UI в продукт), Gamma (деки; свой бренд-тема, но без pixel-control шаблона). Брендирование: design-токены + `DESIGN.md` + шаблон-оболочка — AI заполняет контент, не сочиняет стиль. Доставка не-технику — self-contained `.html`. Презентации ([presentations.md](presentations.md)) — частный случай. → [html-output.md](html-output.md)
