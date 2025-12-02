---
title: "Сравнительный анализ архитектурного стека MVP"
updated: 2025-12-02
version: 1
scope: "archive"
priority: low
---

# Архитектурный стек — справочник альтернатив

## Кратко

Справочник альтернативных решений для архитектурного стека MVP (оркестратор, БД, API). Использовать если текущий стек не подойдёт.


## 1. ОРКЕСТРАТОР — Сравнение вариантов

### Сводная таблица

| Платформа | Хостинг | Ценообразование | Google API | Сложные флоу | Стоимость 10 клиентов | Стоимость 100 клиентов | Ключевые ограничения |
|-----------|---------|-----------------|------------|--------------|---------------------|----------------------|---------------------|
| **n8n** | Self-host + Cloud | Per Execution | Хорошо (native nodes) | Отлично (code + visual) | €20/мес (Cloud Starter) | €50-120/мес (Pro/Business) | Multi-tenant требует workarounds; меньше готовых интеграций |
| **Make** | SaaS only | Per Operation | Отлично (1500+ apps) | Отлично (visual) | $9-16/мес | $200-500+/мес | Быстро дорожает; нет self-host; Dynamic connections только Enterprise |
| **Zapier** | SaaS only | Per Task | Лучший (8000+ apps) | Средне (нет циклов) | $20-50/мес | $407-815+/мес | Дорого; полный vendor lock-in; линейные workflow |
| **Pipedream** | SaaS only | Credit-based (compute) | Хорошо (code-first) | Отлично (full code) | $0-29/мес | $49-99+/мес | Требует dev-навыков; меньше готовых интеграций; нет visual builder |
| **Activepieces** | Self-host + Cloud | "Unlimited tasks" | Средне | Хорошо (visual + code) | $25/мес (Cloud Plus) | $150/мес | Молодая платформа; меньше battle-tested |

### Детальное сравнение

#### n8n — РЕКОМЕНДАЦИЯ

**Плюсы:**
- **Execution-based pricing** — платишь за запуск workflow, не за шаги. Сценарий с 200 шагами = 1 execution. Критично для AI-флоу
- **Self-hosted опция** — zero vendor lock-in, open-source (Community Edition бесплатен)
- **Баланс low-code/high-code** — визуальный builder + JavaScript/Python code nodes
- **Масштабируется предсказуемо** — от Cloud Starter €20/мес → self-hosted Business €120/мес
- **Queue mode** (Business+) — Redis + Postgres для high-volume processing

**Минусы:**
- Multi-tenant не native — нужна кастомная настройка (external secrets, параметризация)
- Меньше готовых интеграций (1100 nodes vs 8000 у Zapier)
- Для некоторых Google операций придётся использовать HTTP Request вместо готовых nodes
- Self-hosted требует DevOps навыков

**Когда выбирать:**
- Маленькая команда, но есть технический founder
- Нужен контроль над затратами при масштабе
- Сложные AI-флоу (много шагов)
- Важен минимальный vendor lock-in

**Путь:**
- Старт: n8n Cloud Starter (€20/мес) для скорости
- 50+ клиентов: self-hosted Community (free + $50/мес VPS)
- 100+ клиентов: self-hosted Business (€120/мес) с queue mode

---

#### Make — ЗАПАСНОЙ ВАРИАНТ 1

**Плюсы:**
- **Лучший визуальный интерфейс** для сложных флоу (routers, loops, aggregators)
- **Богатейшая библиотека** готовых интеграций (1500+), включая Google
- **Быстрее всего MVP** — почти всё делается кликами, минимум кода
- **Хорошая Google интеграция** — refresh Sheets charts, templates, native OAuth

**Минусы:**
- **Operation-based pricing** — каждый шаг = 1 operation. 10 шагов × 20k запусков = 200k операций → дорого ($500+/мес)
- **Полный vendor lock-in** — нет self-host, сценарии привязаны к Make
- **Dynamic connections** только на Enterprise — сложно масштабировать multi-tenant
- **Ограниченный код** — есть Code module, но без NPM библиотек

**Когда выбирать:**
- **Скорость важнее цены** — нужен MVP за 2-4 недели
- Команда без dev-навыков (pure no-code)
- Готовы принять SaaS и более высокие затраты при росте
- Нужны максимально готовые интеграции

**Пример стоимости:**
- 10 клиентов: ~$9-16/мес (10k операций)
- 100 клиентов: ~$200-500+/мес (зависит от сложности флоу)

---

#### Zapier — ЗАПАСНОЙ ВАРИАНТ 2

**Плюсы:**
- **Самая зрелая платформа** — 8000+ apps, лучшая документация
- **Лучшая надёжность** — enterprise-grade uptime, auto-replay на failures
- **Проще всего** — интуитивный интерфейс для non-tech пользователей

**Минусы:**
- **Самый дорогой** — task-based pricing. 750 tasks/$20, 2000 tasks/$69
- **Ограниченная логика** — есть Paths, но нет циклов. Сложные флоу = несколько Zap'ов
- **Быстро упираешься в лимиты** при AI-флоу (много tasks на одну встречу)
- **Полный vendor lock-in** — zero self-hosting

**Когда выбирать:**
- **Enterprise reliability критична** — нужна максимальная стабильность
- Бюджет не ограничен
- Простые workflow (5-10 шагов)
- Нужна максимально готовая экосистема

**Пример стоимости:**
- 10 клиентов: ~$20-50/мес
- 100 клиентов: ~$407-815+/мес

---

#### Pipedream — ЗАПАСНОЙ ВАРИАНТ 3

**Плюсы:**
- **Code-first** — полная свобода (Node.js/Python/Go), любые NPM библиотеки
- **Credit-based pricing** — платишь за compute time, не за шаги. Быстрые флоу очень дешёвые
- **GitHub sync** — versioning workflows как код
- **Serverless** — не нужна инфраструктура

**Минусы:**
- **Требует dev-навыков** — нет визуального builder, всё через код
- **Меньше готовых интеграций** — придётся писать HTTP requests к Google API
- **SaaS vendor lock-in** — нет self-host (хотя можно экспортировать код)

**Когда выбирать:**
- **Есть сильный JS/Python разработчик** в команде
- Нужен максимальный контроль кода
- Сложная AI-логика, которую трудно реализовать в visual builder

**Пример стоимости:**
- 10 клиентов: $0-29/мес (Free tier generous)
- 100 клиентов: $49-99/мес (зависит от compute time)

---

#### Activepieces — ТЁМНАЯ ЛОШАДКА

**Плюсы:**
- **Open-source (MIT)** — можно форкнуть и модифицировать
- **"Unlimited tasks"** на Cloud Plus ($25/мес) — очень выгодно
- **AI-first design** — native поддержка LangChain, OpenAI, Claude

**Минусы:**
- **Молодая платформа** (est. 2022-2023) — меньше battle-tested
- **Меньшее комьюнити** (~19k GitHub stars vs 45k у n8n)
- **Документация с пробелами**

**Когда выбирать:**
- Готовы рискнуть ради низкой цены ($25/мес за unlimited)
- AI-heavy workflows
- Нужен open-source, но n8n кажется сложным

---

### ИТОГОВАЯ РЕКОМЕНДАЦИЯ: Оркестратор

**Основной выбор: n8n**
- Старт: Cloud Starter (€20/мес)
- Миграция при росте: self-hosted Community (free + $50/мес infra)
- Scale: self-hosted Business (€120/мес)

**Когда взять Make:** если скорость важнее цены, нет dev в команде
**Когда взять Zapier:** если нужна максимальная надёжность, бюджет не ограничен
**Когда взять Pipedream:** если есть сильный dev, нужен контроль кода

---

## 2. SVAIB-CORE — Сравнение вариантов

### Сводная таблица

| Решение | Модель | Старт | Стоимость MVP | Auth/API | Multi-tenant | RLS | RAG-ready | Миграции |
|---------|--------|-------|---------------|----------|--------------|-----|-----------|----------|
| **Supabase** | PostgreSQL | 1-2 часа | $0-25/мес | Встроен (Auth + REST/GraphQL) | Shared-table + RLS | ✅ Native | ✅ pgvector | ✅ CLI + SQL |
| **Neon** | PostgreSQL (serverless) | 2-3 часа | $5-30/мес | Нужна реализация | Database-per-tenant идеален | ✅ Native PG | ✅ pgvector | ✅ Native PG |
| **AWS RDS** | PostgreSQL (managed) | 1-2 дня | $30-100/мес | Нужна реализация | Все паттерны | ✅ Native PG | ✅ pgvector | ✅ Native PG |
| **Firebase/Firestore** | NoSQL (document) | 1-2 часа | $0-50/мес | Встроен (Auth + SDK) | Security Rules | ⚠️ Rules-based | ❌ Нет | ❌ Schemaless |

### Детальное сравнение

#### Supabase — РЕКОМЕНДАЦИЯ (единогласно)

**Плюсы:**
- **Backend-as-a-Service** — Auth, Storage, REST/GraphQL API, Real-time из коробки. Экономит недели разработки
- **PostgreSQL в основе** — надёжная реляционная модель для клиенты/встречи/задачи
- **Row Level Security (RLS)** — multi-tenant безопасность на уровне БД, не только приложения
- **Instant APIs** — REST/GraphQL генерируются автоматически из схемы БД
- **pgvector support** — векторные embeddings для RAG (semantic search по контексту компаний)
- **Generous free tier** — 500MB DB, 1GB storage, 50k MAU
- **Простые миграции** — versioned SQL files + CLI

**Минусы:**
- **Vendor lock-in на BaaS фичи** (auth, storage) — миграция потребует переписывания
- **Pro plan обязателен для production** ($25/мес) — free tier не для prod
- **При >100 клиентах** может потребоваться Enterprise ($100-300/мес) или миграция

**Когда выбирать:**
- **Маленькая команда** — нужна максимальная скорость до MVP
- **Реляционная модель данных** (клиенты/встречи/задачи)
- **Multi-tenant с безопасностью** — RLS критичен для корпоративных данных
- **RAG в будущем** — pgvector встроен

**Путь масштабирования:**
- 0-20 клиентов: Free tier или Pro $25/мес
- 20-100 клиентов: Pro $25-75/мес
- 100+ клиентов: Enterprise $100-300/мес или migrate to managed Postgres

---

#### Neon — ЗАПАСНОЙ ВАРИАНТ 1

**Плюсы:**
- **Serverless** — scale-to-zero, платишь только за активное использование
- **Дешевле при низкой нагрузке** — $5-30/мес vs $25/мес у Supabase
- **Чистый PostgreSQL** — нет vendor lock-in на BaaS
- **Instant branching** — dev/staging environments за секунды
- **Database-per-tenant** идеален для масштаба (изоляция на уровне БД)

**Минусы:**
- **Нет BaaS features** — auth, API, storage надо делать самим
- **Cold start latency** — если БД не использовалась, есть задержка на wake-up (~1-2 сек)
- **Больше dev-времени** — нужно реализовать auth, REST API, secrets management

**Когда выбирать:**
- **Технически сильная команда** — готовы сами сделать auth/API
- **Нужен больший контроль** — не хотите зависимости от BaaS
- **Переменная нагрузка** — scale-to-zero экономит деньги
- **Database-per-tenant архитектура** — планируется с самого начала

**Пример стоимости:**
- MVP: $5-30/мес (pay-as-you-go)
- 100+ клиентов: $50-150/мес

---

#### AWS RDS PostgreSQL — ЗАПАСНОЙ ВАРИАНТ 2

**Плюсы:**
- **Максимальная надёжность** — enterprise-grade, Multi-AZ, automated backups
- **Полный контроль** — любая конфигурация, расширения, tuning
- **Compliance** — HIPAA, SOC2 сертификации
- **Все паттерны multi-tenant** — shared/database-per-tenant/schema-per-tenant

**Минусы:**
- **Дорого** — $30-100/мес (t3.micro), $150-500/мес (t3.medium Multi-AZ)
- **Сложная настройка** — 1-2 дня на setup, нужна инфраструктурная экспертиза
- **Нет BaaS features** — auth, API, storage делать самим
- **Always-on costs** — платишь за инстанс 24/7, даже если не используется

**Когда выбирать:**
- **Enterprise масштаб** (500+ клиентов) — нужна максимальная надёжность
- **Compliance требования** — HIPAA, SOC2
- **Database-per-tenant** для полной изоляции
- **Бюджет не ограничен** — готовы платить за reliability

**Пример стоимости:**
- MVP: $30-100/мес (t3.micro)
- 100 клиентов: $150-500/мес (Multi-AZ)

---

#### Firebase/Firestore — НЕ РЕКОМЕНДУЕТСЯ

**Плюсы:**
- **Быстрый старт** — BaaS, auth, storage, SDK из коробки
- **Real-time updates** — native поддержка live data
- **Generous free tier** — хорош для прототипов

**Минусы:**
- **NoSQL для реляционных данных** — клиенты/встречи/задачи естественно реляционные, в Firestore придётся денормализовывать или делать сложные запросы
- **Нет SQL миграций** — schemaless, сложно эволюционировать схему
- **Pricing непредсказуем** — платишь за read/write/delete операции, может резко вырасти при неоптимальном дизайне
- **Нет native RLS** — multi-tenant безопасность через Security Rules, менее надёжно
- **Нет pgvector** — для RAG придётся использовать внешние сервисы

**Когда выбирать:**
- Если уже глубоко в Firebase ecosystem
- Данные действительно документные (не реляционные)
- Real-time критичнее всего

**Вывод:** для svaib модель данных реляционная → PostgreSQL лучше

---

### ИТОГОВАЯ РЕКОМЕНДАЦИЯ: svaib-core

**Основной выбор: Supabase Pro ($25/мес)**
- PostgreSQL + BaaS features = максимальная скорость до MVP
- RLS + pgvector = безопасность + RAG-ready
- До 100+ клиентов не нужна миграция

**Когда взять Neon:** если есть dev для реализации auth/API, нужен больший контроль
**Когда взять RDS:** при enterprise масштабе (500+) и compliance требованиях
**Не брать Firebase:** реляционная модель данных плохо ложится на NoSQL

---

## 3. GOOGLE-SYNC — Сравнение паттернов

### Сводная таблица паттернов

| Паттерн | Подход | Multi-tenant | Quota control | Надёжность | UX | Сложность MVP | Scale 100+ |
|---------|--------|--------------|---------------|------------|-----|---------------|-----------|
| **Backend-First OAuth** | External service управляет OAuth → Google API | ✅ Отлично (1 клиент = 1 token set) | ✅ Централизован | ✅ Высокая | ⚠️ Требует UI | Средняя | ✅ Отлично |
| **Apps Script Add-on** | Apps Script в документах → UI + логика | ⚠️ Сложно (нужно дублировать скрипты) | ❌ Ограничен (6 min timeout, 90 min/day quota) | ⚠️ Средняя | ✅ Native | Низкая | ❌ Плохо |
| **Гибридный** | Backend для sync + Apps Script для UI | ✅ Отлично | ✅ Централизован | ✅ Высокая | ✅ Native | Высокая | ✅ Отлично |
| **iPaaS коннекторы** | n8n/Make Google nodes → OAuth через платформу | ⚠️ Зависит от платформы | ⚠️ Лимиты платформы | ⚠️ Средняя | ❌ Нет | Низкая | ⚠️ Средне |

### Детальное сравнение

#### Backend-First OAuth — РЕКОМЕНДАЦИЯ

**Архитектура:**
```
OAuth tokens в Supabase (encrypted)
  ↓
n8n/Backend извлекает токен по client_id
  ↓
Прямые Google API calls (Sheets/Docs/Slides)
  ↓
Batch operations + exponential backoff
```

**Плюсы:**
- **Multi-tenant без костылей** — 1 клиент = 1 набор OAuth tokens в БД
- **Централизованный контроль** — quota management, retry logic, error handling в одном месте
- **Надёжность** — exponential backoff, idempotency, monitoring
- **Масштабируемость** — до 100 клиентов через User OAuth, дальше Domain-Wide Delegation
- **Переносимость** — не привязаны к Apps Script или конкретному iPaaS

**Минусы:**
- **OAuth verification** нужна для production (3-5 дней, требует Privacy Policy)
- **Нет native UX** — пользователи не видят кнопок в Google Docs/Sheets
- **Больше dev-времени** — нужно реализовать OAuth flow, token refresh, error handling

**Когда выбирать:**
- **Продакшн-продукт** — нужна надёжность и масштабируемость
- **10-100+ клиентов** — multi-tenant критичен
- **Сложная логика** — нужен контроль над retry, quotas, errors

**Критические детали:**

**OAuth 2.0 Refresh Token Limit:**
- Google ограничивает **100 active refresh tokens** на один Client ID
- До 100 клиентов: User OAuth работает
- 100+ клиентов: **обязательно Domain-Wide Delegation** (Service Accounts не подвержены лимиту)

**Batch operations (примеры):**
```javascript
// Sheets — добавить задачи (batch)
POST https://sheets.googleapis.com/v4/spreadsheets/{id}:batchUpdate
{
  "requests": [
    {
      "appendCells": {
        "sheetId": 0,
        "rows": [
          {"values": [{"stringValue": "Task 1"}, {"stringValue": "pending"}]},
          {"values": [{"stringValue": "Task 2"}, {"stringValue": "done"}]}
        ]
      }
    }
  ]
}
```

**Exponential backoff (обязательно):**
```javascript
async function callGoogleAPI(url, opts, maxRetries = 5) {
  for (let i = 0; i < maxRetries; i++) {
    const res = await fetch(url, opts);
    if (res.status === 429) { // Quota exceeded
      const delay = Math.pow(2, i) * 1000 + Math.random() * 1000;
      await new Promise(r => setTimeout(r, delay));
      continue;
    }
    return res.json();
  }
}
```

**Idempotency (обязательно):**
- Добавить скрытую колонку `svaib_task_id` в Sheets
- Перед записью проверять существование задачи
- Защита от дублирования при retries

---

#### Apps Script Add-on — ЗАПАСНОЙ ВАРИАНТ 1

**Архитектура:**
```
Apps Script в Google Docs/Sheets/Slides
  ↓
Sidebar с кнопками ("Process meeting", "Link to svaib")
  ↓
Apps Script вызывает Google API + наш backend
```

**Плюсы:**
- **Fastest to market** — 2-4 недели до MVP
- **Native UX** — пользователи видят кнопки прямо в Google Docs
- **Zero infrastructure** — Google хостит скрипты
- **Simplest auth** — user authorizes once, Apps Script имеет доступ к его документам

**Минусы:**
- **6-minute execution timeout** — если processing >10 pages, нужно разбивать на chunks
- **90 min/day trigger quota** — не для high-volume background sync
- **Multi-tenant сложно** — нужно дублировать скрипты для каждого клиента или делать сложный routing
- **Vendor lock-in** — привязка к Google Apps Script
- **Сложно масштабировать** на 100+ клиентов

**Когда выбирать:**
- **Proof-of-concept** — нужен быстрый MVP для validation
- **10-20 клиентов max** — не планируется масштаб
- **UX критичнее масштабируемости**
- **Маленькая команда** — нет ресурсов на backend разработку

**Эволюция:**
Начать с Apps Script Add-on для MVP → мигрировать на Backend-First при росте до 20+ клиентов

---

#### Гибридный паттерн — ЗОЛОТАЯ СЕРЕДИНА

**Архитектура:**
```
Backend для критической синхронизации (Background OAuth)
  +
Apps Script для UI (Sidebar, кнопки)
```

**Плюсы:**
- **Лучшее из двух миров** — надёжность Backend + native UX Apps Script
- **Multi-tenant работает** — backend управляет OAuth для всех клиентов
- **Background sync надёжен** — не упирается в Apps Script лимиты
- **User-friendly** — кнопки в Google для ручных действий

**Минусы:**
- **Высокая сложность MVP** — нужно разработать и backend, и Apps Script
- **Больше moving parts** — два компонента, которые нужно синхронизировать
- **Больше времени до launch** — 6-8 недель vs 2-4 недели Apps Script-only

**Когда выбирать:**
- **После MVP** — начать с Backend-First или Apps Script, добавить второй компонент позже
- **UX важен** — пользователи хотят кнопки в Google
- **Масштаб планируется** — 50-100+ клиентов

**Рекомендация:**
Не для MVP. Начать с Backend-First → добавить Apps Script UI после validation продукта.

---

#### iPaaS коннекторы (n8n Google nodes) — НЕ ОСНОВА

**Архитектура:**
```
n8n workflow → Google Sheets node (OAuth через n8n)
```

**Плюсы:**
- **Минимум кода** — визуальная настройка в n8n
- **Быстро** — готовые nodes для Sheets/Docs/Slides
- **OAuth управляется платформой** — n8n хранит credentials

**Минусы:**
- **Multi-tenant сложно** — динамический выбор credentials в некоторых nodes ограничен
- **Гибкость ниже** — не все Google API операции покрыты готовыми nodes
- **Vendor lock-in** — workflow привязаны к n8n nodes

**Когда использовать:**
- **Дополнение к Backend-First** — простые операции через n8n nodes, сложные через HTTP Request
- **Тестирование** — на MVP можно начать с nodes, потом мигрировать на HTTP API

**Рекомендация:**
Использовать n8n Google nodes где удобно, но **не полагаться только на них**. Для critical операций использовать HTTP Request node с прямыми Google API calls.

---

### ИТОГОВАЯ РЕКОМЕНДАЦИЯ: Google-sync

**Основной паттерн: Backend-First OAuth**

**MVP реализация:**
1. OAuth tokens в Supabase (encrypted)
2. n8n извлекает token по client_id
3. Прямые Google API calls через HTTP Request node
4. Batch operations везде
5. Exponential backoff обязательно
6. Idempotency через svaib_task_id

**Эволюция:**
- **Фаза 1 (MVP):** Backend-First только
- **Фаза 2 (20-50 клиентов):** добавить минимальный Apps Script для UI кнопок
- **Фаза 3 (100+ клиентов):** Domain-Wide Delegation (обход 100 tokens limit)

**Когда взять Apps Script-First:** для быстрого proof-of-concept (2-4 недели), но планировать миграцию
**Когда взять Гибридный:** после validation продукта, когда UX стал критичен
**Не полагаться только на iPaaS коннекторы:** использовать как helper, не основу

---

## 4. КРИТИЧЕСКИЕ ФАКТЫ

### Google API Quotas (конкретные цифры)

**Limits:**
- Sheets API: **300 req/min per project**, 60 req/min per user
- Docs API: **300 req/min per project**, 60 req/min per user
- Slides API: **300 req/min per project**, 100 req/min per user
- Drive API: 20,000 req/100s per user

**Реальный сценарий — 50 клиентов:**
- 50 clients × 10 users × 5 meetings/day = 2,500 meetings/day
- Per meeting: 1 read (Docs) + 1 write (Sheets) + 1 update (Slides) = 3 API calls
- **Total: 7,500 calls/day** = 312 calls/hour = **5 calls/min**

**С batching (10 operations per batch):**
- 7,500 / 10 = **750 calls/day** = 31 calls/hour = **0.5 calls/min**

**Вывод:** ✅ well within limits (300 req/min). Даже без batching есть **60x запас**, с batching — **600x запас**.

**При 100 клиентах:**
- 100 × 10 × 5 = 5,000 meetings/day = 15,000 calls/day = 625 calls/hour = **10 calls/min**
- ✅ Всё ещё в лимитах, но **нужен rate limiting** для peak hours

---

### OAuth 2.0 Refresh Token Limit — КРИТИЧНО

**Проблема:**
Google ограничивает **100 active refresh tokens** на один OAuth 2.0 Client ID.

**Что это значит:**
- 1 клиент svaib = 1 refresh token
- При создании 101-го токена, самый старый автоматически аннулируется
- **Без предупреждения**

**Решение:**
- **До 100 клиентов:** User OAuth работает
- **100+ клиентов:** переход на **Domain-Wide Delegation** через Service Accounts
  - Service Accounts не подвержены 100 tokens limit
  - Требует однократного approval от Google Workspace Admin клиента
  - Более сложная настройка, но единственный способ масштабироваться

**Action:**
Изучить Domain-Wide Delegation flow **уже на MVP**, чтобы не получить blocker при росте.

---

### OAuth Verification Requirements

**Без верификации:**
- Max **100 test users**
- Экран предупреждения при авторизации ("This app hasn't been verified")

**Для production:**
- Нужна OAuth verification от Google
- Sensitive scopes (Drive, Sheets, Docs): **3-5 рабочих дней** review
- Требования:
  - Privacy Policy
  - Terms of Service
  - Demo video приложения
  - Объяснение использования scopes

**Timeline:**
Начать процесс за **2-4 недели до production launch**.

---

### Batch Operations — не опция, must-have

**Эффективность:**
- **10-100x** меньше API calls
- Пример: 100 задач в Sheets
  - Без batch: 100 API calls
  - С batch: 1 API call

**Примеры реализации:**

**Sheets batchUpdate:**
```javascript
POST /v4/spreadsheets/{id}:batchUpdate
{
  "requests": [
    {"appendCells": {...}},
    {"appendCells": {...}},
    // до 50-100 операций
  ]
}
```

**Slides batchUpdate:**
```javascript
POST /v1/presentations/{id}:batchUpdate
{
  "requests": [
    {"replaceAllText": {...}},
    {"refreshSheetsChart": {...}}
  ]
}
```

**Вывод:** реализовать batch operations **с первого дня**, иначе быстро упрётесь в quotas при росте.

---

## 5. ФИНАЛЬНАЯ СТОИМОСТЬ ПО ФАЗАМ

**MVP (10-20 клиентов):**
- n8n Cloud Starter: €20/мес
- Supabase Pro: $25/мес
- Google API: $0 (в лимитах)
- **Total: ~$45/мес**

**Growth (50-100 клиентов):**
- n8n self-hosted: $50/мес (VPS)
- Supabase Pro: $25-75/мес
- Google API: $0 (с batching)
- **Total: ~$75-125/мес**

**Scale (100+ клиентов):**
- n8n Business self-hosted: €120/мес
- Supabase Enterprise: $100-300/мес
- Google API: $0 (multiple projects для quota multiplication)
- Domain-Wide Delegation: one-time setup cost
- **Total: ~$220-420/мес**

---

## 6. ACTION ITEMS для старта

**Week 1:**
1. Создать Google Cloud Project, получить OAuth credentials
2. Развернуть Supabase, создать таблицы + RLS policies
3. Развернуть n8n (Cloud или self-hosted)
4. Настроить OAuth в n8n, получить первый refresh token

**Week 2:**
5. Создать базовый workflow: webhook → read Docs → call LLM → save to Supabase
6. Добавить batch update для Sheets
7. Тестировать на 1 клиенте

**Week 3-4:**
8. Добавить batch update для Slides
9. Реализовать exponential backoff
10. Добавить idempotency checks (svaib_task_id)
11. Настроить multi-tenant (параметризация по client_id)

**Before production:**
12. Подать на OAuth verification (2-4 недели заранее)
13. Настроить monitoring для quotas
14. Документировать Domain-Wide Delegation flow для будущего

---

## 7. КЛЮЧЕВЫЕ ПРИНЦИПЫ (не забывать)

1. **Batch operations везде** — 10-100x эффективность
2. **Idempotency обязательна** — svaib_task_id в Sheets
3. **Exponential backoff** — для всех Google API calls
4. **Multi-tenant через параметры** — client_id → OAuth token
5. **Domain-Wide Delegation** — планировать с MVP, обязательно при 100+
6. **OAuth verification** — начать за 2-4 недели до launch
7. **Тонкий оркестратор** — координирует, не хранит state
8. **Stateless AI** — LLM calls через API, контекст из Google + Supabase

**Контент живёт в Google, структура в svaib-core, оркестратор координирует.**<!-
