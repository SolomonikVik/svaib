# Tools — AI-инструменты и платформы

Платформы автоматизации, AI-инструменты и готовые агентные продукты, НЕ связанные с написанием кода.

**Границы:** Сюда — платформы (n8n, Dify, Langflow), рабочие среды (Cowork), готовые агентные продукты (Manus, OpenClaw), инфра-сервисы. НЕ сюда: IDE и кодинг-ассистенты (→ coding/), разработка агентов — протоколы, SDK, паттерны (→ agents/).

**Гранулярность:** Один файл = одна категория инструментов, не один инструмент. Отдельный файл на инструмент — только если он ключевой и материала больше, чем на всю категорию.

## Файлы

- [!tools.md](!tools.md) — сводка знаний
- [cowork.md](cowork.md) — Cowork: агентная платформа Anthropic для knowledge workers
- [openclaw.md](openclaw.md) — OpenClaw: open-source self-hosted автономный агент
- [manus.md](manus.md) — Manus: автономный AI-агент (Meta), Telegram-бот
- [paperclip.md](paperclip.md) — Paperclip: open-source оркестратор AI-агентов как компании (org chart, бюджеты, governance) — слой над OpenClaw/Manus
- [ai-workspaces.md](ai-workspaces.md) — AI-оболочки: каталог сред для работы с AI
- [web-scraping-apis.md](web-scraping-apis.md) — Web Scraping APIs: прокси-сервисы для AI
- [meeting-transcription.md](meeting-transcription.md) — Запись и транскрибация встреч: дерево решений по сценариям, автоматизация, MCP-серверы
- [russian-stt-models.md](russian-stt-models.md) — STT-модели для русского: GigaAM-v3 vs Whisper vs T-one, WER-бенчмарки, рекомендации
- [presentations.md](presentations.md) — Презентации с AI: markdown-first (Marp, Slidev) vs визуальные генераторы (Lovable, Slider AI), сравнение, Agent Skills
- [html-output.md](html-output.md) — HTML как слой вывода AI: markdown для хранения, HTML-артефакт для показа человеку; скиллы-роутеры, инструментарий, брендирование, безопасность/доставка
- [claude-project.md](claude-project.md) — Claude Project: delivery-среда для клиентов SVAIB (Google Workspace коннекторы, ограничения Drive API)
- [buildin.md](buildin.md) — Buildin: китайский no-code workspace (аналог Notion), REST API + hosted MCP + UI-экспорт, тарифы и риски интеграции

## Связи

- [../coding/](../coding/) — при выборе «как автоматизировать»: сравнить код-путь (coding) и no-code-путь (tools)
- [../agents/](../agents/) — оценил готовый продукт (Manus, OpenClaw) и хочешь понять, как такое устроено/построить
- [../plugins/](../plugins/) — разворачиваешь Cowork и подбираешь плагины к нему
