---
title: "Текущая инфраструктура svaib"
updated: 2025-11-28
version: 2.0
scope: "operations"
priority: high
---

# Текущая инфраструктура svaib

## Кратко

Инвентаризация реальных ресурсов проекта: серверы, домены, API-ключи, доступы. Только факты — что есть и работает прямо сейчас. Архитектурные решения и целевой стек — см. `architecture.md`.

---

## Домен и DNS

### Основной домен
- **Домен:** svaib.com
- **Регистратор:** reg.ru
- **Срок оплаты до:** 30.05.2026
- **DNS-серверы:** REG.RU
- **TTL:** 3600 секунд

### DNS записи

| Запись | Тип | Назначение |
|--------|-----|------------|
| `svaib.com` | A → 216.198.79.1 | Vercel (лендинг) |
| `www.svaib.com` | CNAME → Vercel | Редирект на основной |
| `n8n.svaib.com` | A → 5.129.237.127 | VPS (зарезервировано) |
| `api.svaib.com` | A → 5.129.237.127 | VPS (зарезервировано) |
| `lab.svaib.com` | A → 5.129.237.127 | VPS (зарезервировано) |

---

## VPS

### Параметры
- **Провайдер:** Timeweb Cloud
- **Тариф:** 2 vCore / 4 GB RAM / 50 GB SSD
- **Локация:** Нидерланды
- **IP адрес:** 5.129.237.127
- **ОС:** Ubuntu 24.04 LTS
- **Стоимость:** ~₽1150/мес (~$12)

### Доступы
- **SSH порт:** 22
- **SSH ключ:** svaib_imac_ed25519 (хранится в KeePass)
- **Root доступ:** активен

### Установленное ПО
- Docker: 28.4.0
- Docker Compose: v2.39.4

### Безопасность
- ✅ Firewall (ufw): deny incoming, allow outgoing, OpenSSH разрешён
- ✅ SSH по ключам (пароль отключен)
- ⏳ TODO: создать sudo user вместо root
- ⏳ TODO: сменить SSH порт с 22
- ⏳ TODO: установить Fail2ban

---

## Vercel (Deployment)

- **URL проекта:** https://vercel.com/solomonikvik/svaib
- **Production URL:** https://svaib.com
- **Root Directory:** `dev/src`
- **Автодеплой:** ✅ активен (push в main → deploy)
- **SSL:** автоматический сертификат

---

## GitHub

- **Репозиторий:** https://github.com/SolomonikVik/svaib
- **Ветка:** main
- **Статус:** ✅ подключен к Vercel

---

## API-ключи и сервисы

### OpenAI
- **Project:** svaib
- **API Key:** хранится в KeePass
- **Лимит расходов:** $10/мес
- **Статус:** ✅ работает

### Google Gemini
- **Project number:** 974967270075
- **API Key:** хранится в KeePass
- **Статус:** ✅ подключен

### Supabase
- **Organization:** svaib
- **Тариф:** Free (планируется Pro для MVP)
- **Project:** svaib_vectors
- **Project ID:** yysxediaamhpqhxpbdko
- **URL:** https://yysxediaamhpqhxpbdko.supabase.co
- **Регион:** EU West (Frankfurt)
- **Anon Key:** хранится в KeePass
- **Service Role Key:** хранится в KeePass
- **Статус:** зарегистрирован, активно не используется

---

## Среда разработки

### VS Code
- **Версия:** 1.105.1
- **Расширения:** Prettier, Live Server, GitLens, Claude Code v2.0.22

### Claude Code
- **Тип:** VS Code Extension
- **Авторизация:** через Claude Max подписку

### Git
- **Версия:** 2.47.0
- **Локальный репозиторий:** `/Users/viktorsolomonik/Projects/svaib/`

---

## Стоимость (текущая)

| Сервис | Стоимость/мес | Примечание |
|--------|---------------|------------|
| VPS Timeweb | ₽1150 (~$12) | 2 vCore / 4GB RAM |
| OpenAI API | $5-10 | лимит $10 |
| Google Gemini | $0 | бесплатный тариф |
| Supabase | $0 | Free tier |
| Домен | ~₽100 (~$1) | ₽1200/год |
| **ИТОГО** | **~$23/мес** | |

---

## Что НЕ развёрнуто (но запланировано)

Следующие компоненты описаны в `architecture.md`, но ещё не развёрнуты:

- n8n (Cloud или self-hosted)
- Recall.ai интеграция
- Soniox интеграция
- Telegram Bot
- Google OAuth для клиентов

---

## История изменений

| Версия | Дата | Изменения |
|--------|------|-----------|
| 2.0 | 2025-11-28 | Полная переработка: только факты, убраны архитектурные рассуждения, Dify, гипотезы |
| 1.0 | 2025-10-15 | Радикальное упрощение: только факты |
| 0.x | 2025-09-24 | Первые версии с архитектурными планами |

---

**Принцип обновления:** Добавляем только то, что реально есть и работает. Архитектура — в `architecture.md`.
