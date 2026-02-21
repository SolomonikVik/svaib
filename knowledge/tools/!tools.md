---
title: "AI-инструменты и платформы автоматизации — сводка"
status: processed
added: 2026-01-30
review_by: 2026-04-30
tags: [tools, automation, platforms, index]
publish: false
version: 10
updated: 2026-02-21
---

# Tools — AI-инструменты и платформы

## Кратко

Платформы автоматизации и AI-инструменты, НЕ связанные с написанием кода. Готовые агентные продукты (Manus, OpenClaw) — тоже здесь. Не путать с: coding/ (IDE, кодинг-ассистенты) и agents/ (разработка агентов — протоколы, SDK, паттерны).

---

## Темы

### AI-оболочки

Среды, через которые пользователь работает с AI. Для SVAIB это интерфейс клиента: мы наполняем оболочку содержимым. Каталог: Claude Code, Cowork, OpenCode, Codex, Kojori, ValeDesk, VS Code. → [ai-workspaces.md](ai-workspaces.md)

### Cowork и плагины

Agent platform Anthropic для не-разработчиков. Формат плагинов идентичен Claude Code — готовый delivery mechanism для модели подписки SVAIB. → [cowork.md](cowork.md)

### Web Scraping APIs

Прокси-сервисы для обхода anti-bot защиты. Нужны когда AI-агент не может достать веб-страницу. Firecrawl, scrape.do, Apify. → [web-scraping-apis.md](web-scraping-apis.md)

### Запись и транскрибация встреч

Конкурентный ландшафт и технологический стек для продукта SVAIB. Коммерческие (Granola, Bluedot, Otter, Fireflies) и open-source (Hyprnote, Sherpa-ONNX, T-one). → [meeting-transcription.md](meeting-transcription.md)

### n8n — платформа автоматизации

Open-source платформа для построения workflow-автоматизаций (self-hosted и cloud). Для SVAIB — основная платформа автоматизации. Разработка n8n workflow через Claude Code (MCP-серверы, скиллы, паттерны) → [coding/n8n-claude-code.md](../coding/n8n-claude-code.md). n8n также поддерживает Instance-Level MCP (v1.76+) — workflow становятся MCP-тулами для AI-клиентов. Нативный AI Workflow Builder — cloud-only beta.

### Автономные агенты (готовые продукты)

Готовые AI-агенты, которым делегируешь задачу (в отличие от оболочек, В которых работаешь). Выполняют многошаговые задачи в фоне: браузер, код, файлы, отчёты. Работают через мессенджеры и веб-интерфейс. Про архитектуру и разработку агентов → agents/.

- **OpenClaw** (ex-Clawdbot) — open-source self-hosted. Архитектура Gateway-Agent-Skills-Memory. Мессенджеры (WhatsApp, Telegram, Slack, Discord, Signal, iMessage). Peter Steinberger (→ OpenAI). → [openclaw.md](openclaw.md)
- **Manus** — коммерческий (Meta). Multi-agent архитектура. Skills + Connectors (Notion, Calendar, Drive). Telegram-бот (февраль 2026), планируют WhatsApp, LINE, Slack. → [manus.md](manus.md)

### Презентации с AI

Два подхода: markdown-first (Slidev — Git, Agent Skill, hackable) и визуальные AI-генераторы (Lovable, Slider AI — быстрый результат без дизайн-навыков). Slidev вписывается в file-first философию продукта. → [presentations.md](presentations.md)
