---
title: "Текущая инфраструктура svaib"
updated: 2025-12-29
version: 2.14
scope: "implementation"
priority: high
---

# Текущая инфраструктура svaib

## Кратко

Инвентаризация реальных ресурсов проекта: серверы, домены, API-ключи, доступы, Google Cloud OAuth. Только факты — что есть и работает прямо сейчас. Архитектурные решения и целевой стек — см. `architecture.md`.

## Правила именования

**Единое название проекта во всех сервисах:** `svaib-app`

| Сервис | Название | ID/URL |
|--------|----------|--------|
| Google Cloud | svaib | Project ID: `svaib-app` |
| Supabase | svaib-app | Project ID: `cfukwleykhntybwgdltr` |
| n8n | svaib-app | svaib-app.app.n8n.cloud |
| Cloudflare | svaib.com | DNS + Email Routing |
| Recall.ai | svaib-app | app@svaib.com |
| Soniox | svaib-app | console.soniox.com |

**Проектный аккаунт для всех сервисов:** `svaib.app@gmail.com`

## Связанные файлы

- architecture.md — архитектурный контракт (целевая архитектура)
- workflows.md — реализация: data flow, структура workflows, контракты промптов
- data_model.md — модель данных Supabase (структура таблиц БД)
- product_sprint.md — текущий спринт MVP (использует эти ресурсы)

***

## Домен и DNS

### Основной домен

* **Домен:** svaib.com
* **Регистратор:** reg.ru
* **Срок оплаты до:** 30.05.2026
* **DNS-серверы:** Cloudflare (tate.ns.cloudflare.com, vita.ns.cloudflare.com)
* **DNS-управление:** Cloudflare Dashboard

### DNS записи (Cloudflare)

| Запись            | Тип   | Значение          | Назначение            |
| ----------------- | ----- | ----------------- | --------------------- |
| `svaib.com`       | A     | 216.198.79.1      | Vercel (лендинг)      |
| `www.svaib.com`   | CNAME | Vercel            | Редирект на основной  |
| `api.svaib.com`   | A     | 5.129.237.127     | ⚠️ VPS отключен, IP не существует |
| `n8n.svaib.com`   | A     | 5.129.237.127     | ⚠️ VPS отключен, IP не существует |
| `tools.svaib.com` | A     | 5.129.237.127     | ⚠️ VPS отключен, IP не существует |
| `svaib.com`       | MX    | Cloudflare        | Email Routing         |
| `svaib.com`       | TXT   | SPF, DKIM         | Email Routing         |

***

## VPS

### Статус: ⏸️ ОТКЛЮЧЕН (17.12.2025)

**Причина:** Не используется для MVP. Все сервисы работают в облаке (n8n Cloud, Supabase Cloud, Vercel).

**Аккаунт Timeweb Cloud:** сохранён, можно создать новый VPS при необходимости.

**DNS записи в Cloudflare:** api/n8n/tools.svaib.com пока указывают на старый IP (5.129.237.127) — обновить при создании нового VPS.

### Когда понадобится

* Self-hosted n8n (при масштабировании, 100+ клиентов)
* Свои сервисы (API gateway, кастомные решения)

### Последняя конфигурация (для справки)

* **Провайдер:** Timeweb Cloud
* **Тариф:** 2 vCore / 4 GB RAM / 50 GB SSD
* **Локация:** Нидерланды
* **ОС:** Ubuntu 24.04 LTS
* **Docker:** 28.4.0, Docker Compose v2.39.4

***

## Vercel (Deployment)

* **URL проекта:** [https://vercel.com/solomonikvik/svaib](https://vercel.com/solomonikvik/svaib)
* **Production URL:** [https://svaib.com](https://svaib.com)
* **Root Directory:** `dev/src`
* **Автодеплой:** ✅ активен (push в main → deploy)
* **SSL:** автоматический сертификат

***

## GitHub

* **Репозиторий:** [https://github.com/SolomonikVik/svaib](https://github.com/SolomonikVik/svaib)
* **Ветка:** main
* **Статус:** ✅ подключен к Vercel

***

## Cloudflare

* **Аккаунт:** svaib.app@gmail.com
* **Тариф:** Free
* **Статус:** ✅ Active

### Сервисы

| Сервис        | Назначение                                  |
| ------------- | ------------------------------------------- |
| DNS           | Управление всеми записями svaib.com         |
| Email Routing | app@svaib.com → svaib.app@gmail.com         |

***

## Email-инфраструктура

### Текущая схема (MVP)

| Адрес               | Назначение                           | Примечание                                         |
| ------------------- | ------------------------------------ | -------------------------------------------------- |
| svaib.app@gmail.com | Основной аккаунт всех сервисов       | Google Cloud, Supabase, n8n, Cloudflare            |
| app@svaib.com       | Корпоративный адрес для Recall.ai    | Форвард → svaib.app@gmail.com                      |

### Почему две почты

**Проблема:** Recall.ai не принимает регистрацию с @gmail.com — требует корпоративный домен.

**Решение (09.12.2025):** Настроили Cloudflare Email Routing. Адрес `app@svaib.com` пересылает всё на `svaib.app@gmail.com`. Фактически одна почта, технически две.

**Ограничение:** Отправлять письма ОТ app@svaib.com нельзя (только получать). Для Recall.ai достаточно — им важен домен при регистрации.

**При масштабировании:** Переход на Google Workspace с полноценными ящиками.

***

## API-ключи и сервисы

### Проектный аккаунт

* **Email:** [svaib.app@gmail.com](mailto:svaib.app@gmail.com)
* **Credentials:** KeePass

### Google Cloud

* **Project name:** svaib
* **Project ID:** svaib-app
* **Project number:** 32423183870
* **Аккаунт:** [svaib.app@gmail.com](mailto:svaib.app@gmail.com)

#### APIs (enabled)

* Google Drive API ✅
* Google Sheets API ✅
* Google Slides API ✅
* Google Calendar API ✅

#### OAuth

* **Consent Screen:** External, Testing mode
* **Client ID for Web application:**
  * **Name:** svaib _(используется только в консоли, не показывается пользователям)_
  * **Client ID:** `32423183870-hm60s6fg2ngcv0utci1s60pmqvj3oe24.apps.googleusercontent.com`
* **Credentials:** KeePass

### OpenAI

* **Project:** svaib
* **API Key:** хранится в KeePass
* **Лимит расходов:** $10/мес
* **Статус:** ✅ работает

### Google Gemini

* **Project number:** 974967270075
* **API Key:** хранится в KeePass
* **Статус:** ✅ подключен

### Supabase

* **Organization:** svaib
* **Project:** svaib-app
* **Project ID:** cfukwleykhntybwgdltr
* **URL:** [https://cfukwleykhntybwgdltr.supabase.co](https://cfukwleykhntybwgdltr.supabase.co)
* **Регион:** EU Central (Frankfurt)
* **Аккаунт:** [svaib.app@gmail.com](mailto:svaib.app@gmail.com)
* **Тариф:** Free (планируется Pro для MVP)
* **Anon Key:** хранится в KeePass
* **Service Role Key:** хранится в KeePass
* **Database Password:** хранится в KeePass
* **Статус:** ✅ работает
* **Таблицы:** clients, team_members, oauth_tokens, meetings, transcripts, tasks, pipeline_runs
* **RLS:** включен, anon/authenticated заблокированы
* **Миграции (17.12.2025):** `clients_telegram_chat_id_unique` — UNIQUE constraint на telegram_chat_id

### n8n Cloud

* **URL:** [https://svaib-app.app.n8n.cloud](https://svaib-app.app.n8n.cloud)
* **Аккаунт:** svaib.app@gmail.com
* **Тариф:** Starter ($24/мес)
* **Версия:** 2.0 (декабрь 2025)
* **Статус:** ✅ работает
* **API Key:** хранится в KeePass (срок: 90 дней, до ~11.03.2026)
* **Project ID:** `9JhFwkoFVBxpUd8P` (проект svaib-app)

#### MCP-ограничение

n8n API не поддерживает создание workflow напрямую в проекте — только в personal.
**Рабочий процесс:** MCP создаёт workflow → Виктор переносит в проект через UI → MCP редактирует по ID.

#### Credentials (обновлено 17.12.2025)

| Credential | Тип | ID | Статус |
|------------|-----|-----|--------|
| Supabase account | Supabase API | `9AoqdQKbnc7fRFVq` | ✅ |
| Supabase Postgres | PostgreSQL | `hsHQlDm7rm2EsEGu` | ✅ |
| OpenAi account | OpenAI API | `5QtuGFTAdv2v9S7V` | ✅ |
| Recall.ai | Header Auth | `5KV81RaV9Gn79hUo` | ✅ |
| Soniox | Header Auth | `UlRllRLpPr7ylsXa` | ✅ |
| Telegram svaib | Telegram API | `thIFX3ToFrZky7ka` | ✅ |

**Supabase Postgres (Session Pooler):**
- Host: `aws-1-eu-central-1.pooler.supabase.com`
- Port: `5432`
- Database: `postgres`
- User: `postgres.cfukwleykhntybwgdltr`
- SSL: Disable (для Session Pooler)

**Примечание:** ID нужны для создания нод через MCP API. Брать из этой таблицы, не выдумывать.

#### Workflows (обновлено 29.12.2025)

> **Детали реализации:** См. [workflows.md](workflows.md)

| ID | Название | Назначение | Статус |
|----|----------|------------|--------|
| kG4emaP9j50nZoGu | meeting_create_bot | Telegram → Client + Meeting → Recall.ai | ✅ active (9 nodes) |
| 4v1G30AX1eHfRQjF | recall_webhook_receiver | Webhook Recall.ai → audio_mixed → Soniox transcribe | ✅ active (11 nodes) |
| 51ZGGJZp5sINBsQy | soniox_webhook_receiver | Webhook Soniox → транскрипт → Supabase → trigger process | ✅ active (11 nodes) |
| uZpjaRlzrSb4mBtV | meeting_process_transcript | AI Pipeline: 4 промпта → протокол → Telegram | ✅ active (20 nodes) |
| vO3W2eWVBCMwuLTi | test_supabase_connection | Тест подключения к Supabase | ✅ active |

**Soniox Webhook URL:** `https://svaib-app.app.n8n.cloud/webhook/soniox-transcript`

### Recall.ai

* **Аккаунт:** app@svaib.com
* **API Base URL:** `https://us-west-2.recall.ai`
* **API Key:** хранится в KeePass
* **Статус:** ✅ зарегистрирован

#### Audio Formats (найдено 16.12.2025)

| Опция | Формат | Совместимость с Soniox |
|-------|--------|------------------------|
| `audio_separate_raw` | Raw PCM (16kHz, 16-bit, mono, S16LE) | ❌ Не поддерживается |
| `audio_separate_mp3` | MP3 с заголовками | ✅ Поддерживается |

**✅ Текущая конфигурация:** `audio_mixed_mp3` (изменено 18.12.2025)

**Raw PCM параметры (если нужна конвертация):**
- Sample rate: 16 kHz
- Bit depth: 16-bit
- Encoding: Signed little-endian PCM (S16LE)
- Channels: Mono

#### Webhook (создан 15.12.2025, обновлён 16.12.2025)

* **Endpoint ID:** `ep_36sqxrncczNRgMnf6SJxaloBweD`
* **URL:** `https://svaib-app.app.n8n.cloud/webhook/5daad788-6e14-46e4-8ca2-69ff10ffa638`
* **Signing Secret:** хранится в KeePass
* **Events (17 штук):**
  * `audio_mixed.done`
  * `audio_separate.done`
  * `audio_separate.failed`
  * `audio_separate.processing`
  * `bot.breakout_room_closed`
  * `bot.breakout_room_entered`
  * `bot.breakout_room_left`
  * `bot.breakout_room_opened`
  * `bot.call_ended`
  * `bot.done`
  * `bot.fatal`
  * `bot.in_call_not_recording`
  * `bot.in_call_recording`
  * `bot.in_waiting_room`
  * `bot.joining_call`
  * `bot.recording_permission_allowed`
  * `bot.recording_permission_denied`

### Soniox

* **Console:** [https://console.soniox.com](https://console.soniox.com)
* **Аккаунт:** svaib.app@gmail.com
* **Project ID:** 8be55c77-a65d-43e6-aa0e-69dbb5955a9c
* **Project Name:** svaib-app
* **Region:** United States
* **API Key:** хранится в KeePass
* **Статус:** ✅ зарегистрирован

#### API Reference (найдено 16.12.2025)

**Async Transcription:**
* **URL:** `https://api.soniox.com/v1/transcriptions`
* **Method:** POST
* **Auth:** Header `Authorization: Bearer <API_KEY>`
* **Body:**
  ```json
  {
    "model": "stt-async-v3",
    "audio_url": "<URL>",
    "enable_speaker_diarization": true
  }
  ```
* **Response:** `{ "id": "<job_id>", "status": "pending", ... }`

**⚠️ Важно:** Endpoint БЕЗ `/async` — асинхронный режим включается параметром `model: 'stt-async-v3'`. Context7 выдаёт устаревший endpoint `/transcriptions/async` — он не работает (404).

### Telegram Bot (создан 15.12.2025)

* **Name:** svaib telegram bot
* **Username:** @svaib_bot
* **Token:** хранится в KeePass
* **Статус:** ✅ создан, подключен к n8n

***

## Среда разработки

### VS Code

* **Версия:** 1.105.1
* **Расширения:** Prettier, Live Server, GitLens, Claude Code v2.0.22

### Claude Code

* **Тип:** VS Code Extension
* **Авторизация:** через Claude Max подписка ($100/мес)

### MCP-серверы (подключены 11.12.2025, обновлено 15.12.2025)

| MCP | Назначение | Токен | Срок действия |
|-----|------------|-------|---------------|
| **n8n-mcp** | Создание/редактирование workflow | KeePass | 90 дней (~11.03.2026) |
| **supabase** | SQL, таблицы, миграции | KeePass | 30 дней (~10.01.2026) |
| **context7** | Документация (Recall.ai, Soniox, n8n) | — | Бессрочно |

**Хранение:** MCP конфигурация в `~/.claude.json` (user-level, не в репозитории)

**При истечении токена:**
1. Создать новый токен в соответствующем сервисе
2. `claude mcp remove <name> -s local`
3. `claude mcp add <name> ...` с новым токеном

### Git

* **Версия:** 2.47.0
* **Локальный репозиторий:** `/Users/viktorsolomonik/Projects/svaib/`

***

## Стоимость (текущая)

| Сервис        | Стоимость/мес | Примечание        |
| ------------- | ------------- | ----------------- |
| n8n Cloud     | $24           | Starter plan      |
| OpenAI API    | $5-10         | лимит $10         |
| Google Gemini | $0            | бесплатный тариф  |
| Supabase      | $0            | Free tier         |
| Cloudflare    | $0            | Free tier         |
| Домен         | ~₽100 (~$1)   | ₽1200/год         |
| **ИТОГО**     | **~$35/мес**  |                   |

*VPS Timeweb отключен 17.12.2025 — экономия ~$12/мес*

***

## Что НЕ развёрнуто (но запланировано)

Следующие компоненты описаны в `architecture.md`, но ещё не развёрнуты:

* Google OAuth для клиентов (flow для подключения Google Drive/Sheets)

***

**Принцип обновления:** Добавляем только то, что реально есть и работает. Архитектура — в `architecture.md`.