---
title: "Текущая инфраструктура svaib"
updated: 2025-12-11
version: 2.5
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
| `api.svaib.com`   | A     | 5.129.237.127     | VPS (зарезервировано) |
| `n8n.svaib.com`   | A     | 5.129.237.127     | VPS (зарезервировано) |
| `tools.svaib.com` | A     | 5.129.237.127     | VPS (зарезервировано) |
| `svaib.com`       | MX    | Cloudflare        | Email Routing         |
| `svaib.com`       | TXT   | SPF, DKIM         | Email Routing         |

***

## VPS

### Параметры

* **Провайдер:** Timeweb Cloud
* **Тариф:** 2 vCore / 4 GB RAM / 50 GB SSD
* **Локация:** Нидерланды
* **IP адрес:** 5.129.237.127
* **ОС:** Ubuntu 24.04 LTS
* **Стоимость:** ~~₽1150/мес (~~$12)

### Доступы

* **SSH порт:** 22
* **SSH ключ:** svaib\_imac\_ed25519 (хранится в KeePass)
* **Root доступ:** активен

### Установленное ПО

* Docker: 28.4.0
* Docker Compose: v2.39.4

### Безопасность

* ✅ Firewall (ufw): deny incoming, allow outgoing, OpenSSH разрешён
* ✅ SSH по ключам (пароль отключен)
* ⏳ TODO: создать sudo user вместо root
* ⏳ TODO: сменить SSH порт с 22
* ⏳ TODO: установить Fail2ban

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

### n8n Cloud

* **URL:** [https://svaib-app.app.n8n.cloud](https://svaib-app.app.n8n.cloud)
* **Аккаунт:** svaib.app@gmail.com
* **Тариф:** Starter ($24/мес)
* **Статус:** ✅ работает
* **Credentials:** Supabase, OpenAI подключены
* **API Key:** хранится в KeePass (срок: 90 дней, до ~11.03.2026)

### Recall.ai

* **Аккаунт:** app@svaib.com
* **API Key:** хранится в KeePass
* **Статус:** ✅ зарегистрирован

### Soniox

* **Console:** [https://console.soniox.com](https://console.soniox.com)
* **Аккаунт:** svaib.app@gmail.com
* **Project ID:** 8be55c77-a65d-43e6-aa0e-69dbb5955a9c
* **Project Name:** svaib-app
* **Region:** United States
* **API Key:** хранится в KeePass
* **Статус:** ✅ зарегистрирован

***

## Среда разработки

### VS Code

* **Версия:** 1.105.1
* **Расширения:** Prettier, Live Server, GitLens, Claude Code v2.0.22

### Claude Code

* **Тип:** VS Code Extension
* **Авторизация:** через Claude Max подписка ($100/мес)

### MCP-серверы (подключены 11.12.2025)

| MCP | Назначение | Токен | Срок действия |
|-----|------------|-------|---------------|
| **n8n-mcp** | Создание/редактирование workflow | KeePass | 90 дней (~11.03.2026) |
| **supabase** | SQL, таблицы, миграции | KeePass | 30 дней (~10.01.2026) |

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
| VPS Timeweb   | ₽1150 (~$12)  | 2 vCore / 4GB RAM |
| n8n Cloud     | $24           | Starter plan      |
| OpenAI API    | $5-10         | лимит $10         |
| Google Gemini | $0            | бесплатный тариф  |
| Supabase      | $0            | Free tier         |
| Cloudflare    | $0            | Free tier         |
| Домен         | ~₽100 (~$1)   | ₽1200/год         |
| **ИТОГО**     | **~$47/мес**  |                   |

***

## Что НЕ развёрнуто (но запланировано)

Следующие компоненты описаны в `architecture.md`, но ещё не развёрнуты:

* Telegram Bot
* Google OAuth для клиентов

***

**Принцип обновления:** Добавляем только то, что реально есть и работает. Архитектура — в `architecture.md`.