---
title: "Web Scraping APIs — прокси-сервисы для обхода anti-bot защиты"
source: "https://scrape.do"
source_type: docs
status: raw
added: 2026-02-01
review_by: 2026-05-01
tags: [tools, scraping, proxy, api, firecrawl, mcp]
publish: false
version: 1
---

# Web Scraping APIs

## Кратко

Прокси-сервисы, которые получают контент защищённых сайтов (LinkedIn, Reddit, Amazon и др.) за тебя. Отправляешь URL — получаешь HTML/markdown. Сервис берёт на себя: ротацию IP (десятки миллионов адресов), CAPTCHA, JavaScript-рендеринг, anti-bot обход. Нужны когда AI-агент (Claude Code, OpenClaw, любой другой) упирается в anti-bot защиту при попытке fetch-нуть веб-страницу. Без такого сервиса агент предложит "скопируй вручную" — это недопустимо в автоматизированном workflow.

---

## Как это работает

```bash
# Базовый запрос (scrape.do)
curl 'https://api.scrape.do/?token=TOKEN&url=https://linkedin.com/jobs/view/123'

# С markdown-выводом (удобно для AI)
curl 'https://api.scrape.do/?token=TOKEN&url=URL&output=markdown'

# С JS-рендерингом (SPA-сайты)
curl 'https://api.scrape.do/?token=TOKEN&url=URL&render=true'
```

Все сервисы работают по одному принципу: HTTP GET с API-ключом и целевым URL. Различаются ценой, пулом IP, поддержкой сложных сайтов.

---

## Сравнение сервисов

| Сервис | Free tier | От (платно) | Кредитов за $1 | MCP для Claude | Фокус |
|--------|-----------|-------------|----------------|----------------|-------|
| **Firecrawl** | Есть | $16/мес | — | Есть (официальный) | Markdown-вывод, оптимизирован для AI |
| **scrape.do** | 1000 кредитов | $29/мес | ~8600 | Через Composio | Дешёвый, 110M+ IP, pay-for-success |
| **ScraperAPI** | 5000 кредитов | $49/мес | — | Нет | LinkedIn = 30x кредитов (дорого) |
| **ScrapingBee** | Trial | $49/мес | — | Нет | Stealth proxy 75x (дорого) |
| **Apify** | Есть | $39/мес | — | Есть | Маркетплейс готовых скраперов |
| **Bright Data** | Нет | $499/мес | — | Нет | Enterprise, flat rate |

### Кредитные множители (scrape.do)

Базовый запрос = 1 кредит. Фичи увеличивают стоимость:

| Фича | Множитель |
|------|-----------|
| Стандартный запрос | 1x |
| JavaScript-рендеринг (`render=true`) | 5x |
| Premium/residential proxy (`super=true`) | 10x |
| Render + premium proxy | 25x |

Оплата только за успешные запросы (2xx). Ошибки и таймауты бесплатны.

---

## Интеграция с AI-агентами

### Firecrawl (рекомендация для Claude Code)

Есть готовый MCP-сервер. Устанавливается напрямую в Claude Code/Desktop. Вывод в markdown — оптимален для контекста AI. Документация: docs.firecrawl.dev/developer-guides/mcp-setup-guides/claude-code

### scrape.do

Нативного MCP нет. Интеграция:
- **Через curl в Bash** — простейший вариант, работает сразу
- **Через Composio** — MCP-коннектор (composio.dev), требует аккаунт Composio
- **Самописный MCP** — тонкая обёртка над API, десятки строк кода

### Apify

Есть MCP-интеграция. Маркетплейс готовых "актёров" (скраперов) для конкретных сайтов: LinkedIn, Twitter, Amazon. Не универсальный прокси, а готовые парсеры.

### Паттерн: кросс-модельный скрапинг

Из практик сообщества (январь 2026): Claude Code оркестрирует субагентов на Gemini CLI для fetch-задач. Claude не может зайти на сайт → запускает `gemini --model gemini-2.5-flash "Извлеки данные: [URL]"` через Bash. Gemini имеет свой веб-доступ. Бесплатно, но нестабильно.

---

## Когда что выбрать

- **Разовые задачи, интеграция с Claude Code** → Firecrawl (MCP, markdown, free tier)
- **Массовый скрапинг, бюджет** → scrape.do (дешевле всех, pay-for-success)
- **Конкретный сайт (LinkedIn, Amazon)** → Apify (готовые актёры)
- **Enterprise** → Bright Data
- **Бесплатно и грязно** → Gemini CLI как субагент

---

## Связанные материалы

- [coding/!coding.md](../coding/!coding.md) — AI-кодинг, субагенты, Task tool (используются для оркестрации скрапинга)
- [coding/swarm-mode.md](../coding/swarm-mode.md) — multi-agent паттерны (параллельный скрапинг через команду агентов)
