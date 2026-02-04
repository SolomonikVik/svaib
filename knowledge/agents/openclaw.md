---
title: "OpenClaw (ex-Clawdbot/Moltbot) — open-source self-hosted AI-агент с архитектурой Gateway-Agent-Skills-Memory"
source: "https://github.com/moltbot/moltbot"
source_type: repo
status: processed
added: 2026-01-31
review_by: 2026-04-30
tags: [agents, skills, memory, self-hosted, open-source, architecture-patterns]
publish: false
version: 1
---

# OpenClaw (ex-Clawdbot → Moltbot)

## Кратко

Open-source self-hosted AI-агент (Peter Steinberger, основатель PSPDFKit, MIT лицензия). Не чат-бот, а автономный ассистент, который выполняет действия: shell-команды, браузер, файлы, календарь, smart home. Подключается к мессенджерам как точки входа. Архитектура из 4 компонентов (Gateway, Agent, Skills, Memory). Один из самых быстрорастущих open-source AI-проектов (январь 2026). Cloudflare сделал managed-версию (Moltworker).

---

## Архитектура

Четыре компонента, каждый с чёткой ответственностью:

### 1. Gateway

WebSocket-сервер (порт 18789, localhost по умолчанию). Управляет подключениями к мессенджерам через отдельные библиотеки-коннекторы:

- WhatsApp → Baileys (reverse-engineered протокол, **не** официальный API — риск блокировки номера)
- Telegram → grammY (официальный Bot API)
- Slack → Bolt
- Discord → discord.js
- Signal → signal-cli
- iMessage → imsg (macOS-only, недокументированные API)
- Google Chat, Microsoft Teams, Matrix, Zalo, BlueBubbles — через extensions

Абстрагирует канал доставки от логики агента — агенту приходит унифицированный ввод независимо от мессенджера.

Удалённый доступ через Tailscale Serve/Funnel или SSH-туннели. При Tailscale Gateway привязывается к loopback.

### 2. Agent

Reasoning engine. Подключается к LLM-провайдеру:
- **Anthropic** — Claude Pro/Max (рекомендуют Opus 4.5 за "long-context strength и prompt-injection resistance")
- **OpenAI** — ChatGPT/Codex
- **Локальные модели** — поддерживаются

Конфиг минимальный: `~/.openclaw/openclaw.json`, ключевое поле `agent.model`. Есть model failover — ротация между провайдерами с fallback.

Поддерживает иерархию: supervisor-агент делегирует specialist-агентам. Кросс-сессионная координация через `sessions_list`, `sessions_history`, `sessions_send`.

Extended thinking через `/think <level>` (off → xhigh).

### 3. Skills

Скилл = Markdown-файл `SKILL.md` в `~/.openclaw/workspace/skills/<skill>/`. Агент читает файл как инструкцию и выполняет.

Три типа:
- **Bundled** — встроенные (браузер, shell, файлы, cron, smart home)
- **Managed** — из реестра ClawdHub
- **Workspace** — пользовательские, в локальной папке

ClawdHub — реестр скиллов. Агент может сам искать и подключать нужные скиллы. Также может создавать новые скиллы на лету.

В контекст агента инжектятся: AGENTS.md, SOUL.md, TOOLS.md.

### 4. Memory

Сессионная модель:
- Каждый чат = сессия с логом (доступен через `sessions_history` tool)
- Сжатие контекста через `/compact`
- Сессии можно pruning (автоочистка)
- Per-session state: thinking level, модель, политика ответов

**Ограничения:** Нет долгосрочной структурированной памяти, knowledge graph или темпоральности. Персистентность на уровне сессий, не на уровне знаний. Memory — самый слабый компонент архитектуры.

---

## Безопасность

- Gateway слушает только localhost по умолчанию
- **DM pairing** (по умолчанию): незнакомцы получают код, бот не обрабатывает их сообщения до одобрения (`openclaw pairing approve`)
- **Docker-песочница** для групповых чатов (`sandbox.mode: "non-main"`)
- **Elevated access** — доступ к root отдельно, включается per-session (`/elevated on|off`)
- `openclaw doctor` — диагностика рискованных конфигураций

**Риски:**
- Shell-доступ = потенциальное удаление файлов при ошибке агента
- Prompt injection через входящие документы/письма
- WhatsApp через Baileys — Meta может заблокировать номер
- При открытии Gateway наружу без auth — remote code execution

---

## Установка

```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon
```

Node ≥22, pnpm рекомендуется. macOS, Linux, Windows (WSL2). Визард проводит через настройку Gateway, каналов, скиллов. Устанавливает демон (launchd/systemd).

Каналы обновления: stable, beta, dev (`openclaw update --channel`).

---

## Проактивность

Агент не только отвечает, но и инициирует: напоминания, предупреждения, предложения. Работает через cron-скиллы и event hooks.

---

## Экосистема

- **Cloudflare Moltworker** — managed-версия, деплой на Cloudflare Workers без self-hosting
- **Tencent Cloud, Alibaba Cloud** — интегрировали simplified deployment
- **ClawdHub** — маркетплейс скиллов
- **Сообщество:** активное, крупный Discord, десятки контрибьюторов

---

## Ссылки

- Repo: https://github.com/moltbot/moltbot
- Skills: https://github.com/VoltAgent/awesome-moltbot-skills
- Cloudflare Moltworker: https://github.com/cloudflare/moltworker
- Сайт: https://clawd.bot/
- Автор: Peter Steinberger (@steipete)
