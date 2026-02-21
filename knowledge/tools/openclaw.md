---
title: "OpenClaw (ex-Clawdbot/Moltbot) — open-source self-hosted AI-агент с архитектурой Gateway-Agent-Skills-Memory"
source: "https://github.com/moltbot/moltbot"
source_type: repo
status: processed
added: 2026-01-31
updated: 2026-02-16
review_by: 2026-04-30
tags: [agents, skills, memory, self-hosted, open-source, architecture-patterns]
aliases: [Clawdbot, CloudBot, Moltbot, Claude Bot, клодбот]
publish: false
version: 3
---

# OpenClaw (ex-Clawdbot → Moltbot)

## Кратко

Также известен как: Clawdbot, CloudBot, Moltbot, Claude Bot, клодбот. Open-source self-hosted AI-агент (Peter Steinberger / @steipete, основатель PSPDFKit, MIT лицензия). Не чат-бот, а автономный ассистент, который выполняет действия: shell-команды, браузер, файлы, календарь, smart home. Подключается к мессенджерам как точки входа. Архитектура из 4 компонентов (Gateway, Agent, Skills, Memory). Один из самых быстрорастущих open-source AI-проектов (январь 2026). Cloudflare сделал managed-версию (Moltworker). В феврале 2026 Sam Altman переманил Peter Steinberger в OpenAI — проект теперь развивается под крылом OpenAI.

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

Два уровня: сессионный и персистентный.

**Сессионный:** Каждый чат = сессия с логом (`sessions_history` tool). Сжатие через `/compact`. Pruning (автоочистка). Per-session state: thinking level, модель, политика ответов.

**Персистентный (MD-файлы):** Долгосрочная память через набор Markdown-файлов:
- **user.md** — факты о человеке (из онбординга + из разговоров). Статичная часть, устаревает
- **identity.md** — характер и имя бота (задаётся при онбординге)
- **soul.md** — системный промпт, определяющий "душу" ассистента. Редактируемый пользователем
- **memory.md** — динамическая память: факты, таск-лист, контекст из разговоров. Растёт с каждой сессией — вставляется в каждый запрос → рост токенов → рост стоимости
- **bootstrap.md** — онбординг-промпт, который самоудаляется после прохождения (паттерн: одноразовая инструкция)

**Heartbeat:** Каждые 30 минут агент проверяет сессию — есть ли что сохранить в memory.md. Аналог Memory в ChatGPT, но файловый.

**Ограничения:** Нет knowledge graph или темпоральности. Memory.md — плоский файл, растёт неограниченно, что приводит к взрывному росту стоимости. О подходах к темпоральной памяти (Graphiti, Hindsight) см. [../context/temporal-graphs.md](../context/temporal-graphs.md).

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

## Стоимость

По умолчанию Opus для всех задач (включая тривиальные). $3+ за одну демо-сессию. Кейс: юзер потратил $4000/мес. Memory растёт → контекст каждого запроса растёт → экспоненциальный рост стоимости. Heartbeat каждые 30 мин добавляет. Рекомендация: переключить heartbeat и простые задачи на дешёвые модели (QwQ, Haiku).

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

## Стратегическое значение

**Переход в OpenAI (февраль 2026).** Sam Altman переманил Peter Steinberger в OpenAI. До этого Anthropic пыталась заблокировать проект юридическими письмами (имя "ClawdBot" слишком похоже на Claude), что привело к ребрендингу. Вместо защиты экосистемы — потеряли ключевого разработчика конкуренту. Peter уже получил доступ к OpenAI Aardvark (инструмент поиска security-уязвимостей).

**Почему это важно (@llm_under_hood).** Проект "показывает принципиальное направление движения отрасли на будущий год". Несмотря на критику половины AI-экспертов ("ерунду банальную и небезопасную сделали"), другая половина мира — люди, впервые получившие реально работающий self-hosted AI-агент — ответила массовым хайпом и движухой. Безопасность — дело наживное, а вот продуктовый паттерн (персональный автономный агент в мессенджере) оказался востребованным.

**Для SVAIB:** OpenClaw подтверждает жизнеспособность архитектуры Skills + Memory на Markdown + Gateway к мессенджерам. Наш framework/scaffold/ — по сути та же идея, но со структурированной онтологией вместо плоского memory.md.

---

## Ссылки

- Repo: https://github.com/moltbot/moltbot
- Skills: https://github.com/VoltAgent/awesome-moltbot-skills
- Cloudflare Moltworker: https://github.com/cloudflare/moltworker
- Сайт: https://clawd.bot/
- Автор: Peter Steinberger (@steipete)

## Связанные файлы

- [manus.md](manus.md) — Manus: коммерческий автономный агент (Meta), аналогичный класс продукта
- [../agents/mcp.md](../agents/mcp.md) — MCP как протокол интеграции (OpenClaw использует MCP)
- [../agents/subagents.md](../agents/subagents.md) — субагентные паттерны (supervisor-specialist из OpenClaw)
- [../agents/!agents.md](../agents/!agents.md) — сводка по агентным системам
- [../context/context-graphs.md](../context/context-graphs.md) — Context Graphs (Foundation Capital): decision traces и траектории агентов — связь с Memory-компонентом OpenClaw
