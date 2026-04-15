---
title: "AI-инструменты и платформы автоматизации — сводка"
status: processed
added: 2026-01-30
review_by: 2026-04-30
tags: [tools, automation, platforms, index]
publish: false
version: 14
updated: 2026-04-15
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

Agent platform Anthropic для не-разработчиков. Формат плагинов идентичен Claude Code — готовый delivery mechanism для модели подписки SVAIB. → [cowork.md](cowork.md)

### Web Scraping APIs

Прокси-сервисы для обхода anti-bot защиты. Нужны когда AI-агент не может достать веб-страницу. Firecrawl, scrape.do, Apify. → [web-scraping-apis.md](web-scraping-apis.md)

### Запись и транскрибация встреч

Дерево решений по сценариям: онлайн (Granola, Fireflies, Krisp, Fellow, Circleback), офлайн (MacWhisper, Vibe, Plaud Note Pro), real-time (Groq API + Whisper Turbo), звонки (Plaud VCS, iOS 18.1, Cube ACR), приватность (локальный Whisper/GigaAM). Автоматизация: Zoom webhook, Контур Толк API/F5AI, Plaud AutoFlow/Zapier, наш MacWhisper-скилл. MCP-серверы у 6 из 9 инструментов. Ключевое: ни один софт не закрывает все сценарии — комбинация софт + Plaud покрывает 95%. → [meeting-transcription.md](meeting-transcription.md)

### STT-модели для русского языка

Сравнение движков распознавания русской речи по WER-бенчмаркам. GigaAM-v3 (Сбер, MIT) доминирует с двукратным отрывом от Whisper (~8% vs ~16% средний WER). На зашумлённом аудио (дальний микрофон) разрыв 4x. Три бэкенда исполнения Whisper: C++ (GGML, универсальный), WhisperKit (Apple Silicon, ANE-оптимизация), Parakeet v3 (NVIDIA, скорость). Для повседневной диктовки на русском — Whisper Turbo через Groq API (надёжно, $0). Облачные: Groq (real-time, free), Soniox (WER 6,2%, code-switching), ElevenLabs Scribe v2, Yandex SpeechKit. → [russian-stt-models.md](russian-stt-models.md)

### n8n — платформа автоматизации

Open-source платформа для построения workflow-автоматизаций (self-hosted и cloud). Для SVAIB — основная платформа автоматизации. Разработка n8n workflow через Claude Code (MCP-серверы, скиллы, паттерны) → [coding/n8n-claude-code.md](../coding/n8n-claude-code.md). n8n также поддерживает Instance-Level MCP (v1.76+) — workflow становятся MCP-тулами для AI-клиентов. Нативный AI Workflow Builder — cloud-only beta.

### Автономные агенты (готовые продукты)

Готовые AI-агенты, которым делегируешь задачу (в отличие от оболочек, В которых работаешь). Выполняют многошаговые задачи в фоне: браузер, код, файлы, отчёты. Работают через мессенджеры и веб-интерфейс. Про архитектуру и разработку агентов → agents/.

- **OpenClaw** (ex-Clawdbot) — open-source self-hosted. Архитектура Gateway-Agent-Skills-Memory. Мессенджеры (WhatsApp, Telegram, Slack, Discord, Signal, iMessage). Peter Steinberger (→ OpenAI). → [openclaw.md](openclaw.md)
- **Manus** — коммерческий (Meta). Multi-agent архитектура. Skills + Connectors (Notion, Calendar, Drive). Telegram-бот (февраль 2026), планируют WhatsApp, LINE, Slack. → [manus.md](manus.md)

### Презентации с AI

Два подхода: markdown-first и визуальные AI-генераторы. Markdown-first — это Marp и Slidev: оба конвертируют .md в слайды, живут в git, редактируются AI напрямую, но делают разные ставки. **Marp** — статический рендер, минимум окружения (standalone binary или CLI), чистый Markdown + CSS, низкая кривая входа; выбираем когда нужны быстрые рабочие презентации без возни. **Slidev** — Vite + Vue 3 компоненты, интерактив, Monaco, Magic Move, Presenter View, запись с камерой; выбираем для технических демо и конференционных докладов. Ключевое структурное различие: у **Slidev есть официальный Agent Skill** от самих авторов (`npx skills add slidevjs/slidev`) + выделенная страница «Work with AI» в документации; у Marp — зоопарк community-скиллов разного качества. Оба вписываются в file-first философию продукта. Визуальные генераторы (Lovable, Gamma, NotebookLM, Slider AI) — альтернатива для быстрого результата без дизайн-навыков, но ценой потери git-workflow и AI-редактирования. → [presentations.md](presentations.md)
