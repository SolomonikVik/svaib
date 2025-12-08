---
title: "Текущая инфраструктура svaib"
updated: 2025-12-08
version: 2.2
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
| n8n | svaib-app | _(при создании)_ |
| Recall.ai | svaib-app | _(при регистрации)_ |
| Soniox | svaib-app | _(при регистрации)_ |

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
* **DNS-серверы:** REG.RU
* **TTL:** 3600 секунд

### DNS записи

| Запись          | Тип               | Назначение            |
| --------------- | ----------------- | --------------------- |
| `svaib.com`     | A → 216.198.79.1  | Vercel (лендинг)      |
| `www.svaib.com` | CNAME → Vercel    | Редирект на основной  |
| `n8n.svaib.com` | A → 5.129.237.127 | VPS (зарезервировано) |
| `api.svaib.com` | A → 5.129.237.127 | VPS (зарезервировано) |
| `lab.svaib.com` | A → 5.129.237.127 | VPS (зарезервировано) |

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

***

## Среда разработки

### VS Code

* **Версия:** 1.105.1
* **Расширения:** Prettier, Live Server, GitLens, Claude Code v2.0.22

### Claude Code

* **Тип:** VS Code Extension
* **Авторизация:** через Claude Max подписку

### Git

* **Версия:** 2.47.0
* **Локальный репозиторий:** `/Users/viktorsolomonik/Projects/svaib/`

***

## Стоимость (текущая)

| Сервис        | Стоимость/мес | Примечание        |
| ------------- | ------------- | ----------------- |
| VPS Timeweb   | ₽1150 (\~$12) | 2 vCore / 4GB RAM |
| OpenAI API    | $5-10         | лимит $10         |
| Google Gemini | $0            | бесплатный тариф  |
| Supabase      | $0            | Free tier         |
| Домен         | ~~₽100 (~~$1) | ₽1200/год         |
| **ИТОГО**     | **\~$23/мес** |                   |

***

## Что НЕ развёрнуто (но запланировано)

Следующие компоненты описаны в `architecture.md`, но ещё не развёрнуты:

* n8n (Cloud или self-hosted)
* Recall.ai интеграция
* Soniox интеграция
* Telegram Bot
* Google OAuth для клиентов

***

**Принцип обновления:** Добавляем только то, что реально есть и работает. Архитектура — в `architecture.md`.