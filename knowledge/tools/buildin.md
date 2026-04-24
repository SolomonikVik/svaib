---
title: "Buildin — китайский no-code workspace, аналог Notion с REST API и hosted MCP"
source: "https://buildin.ai"
source_type: docs
status: processed
added: 2026-04-24
updated: 2026-04-24
review_by: 2026-07-24
tags: [buildin, notion-alternative, no-code, mcp, api, china]
publish: false
version: 1
---

# Buildin

## Кратко

Buildin (buildin.ai) — китайский no-code workspace, аналог Notion: страницы из блоков, базы данных как страницы со схемой, шаринг и пермишены. Доступен из РФ, поэтому используется как замена Notion в командах, отрезанных от него. Три способа интеграции с AI: REST API `api.buildin.ai/v1`, hosted MCP-сервер, ручной экспорт страницы в Markdown/PDF/CSV/Word из UI. Бесплатный тариф API/MCP не даёт — нужен платный план.

## Связанные файлы

- [!tools.md](!tools.md) — сводка по AI-инструментам и платформам
- [../agents/mcp.md](../agents/mcp.md) — MCP как протокол; здесь Buildin фигурирует как пример hosted MCP-сервера
- [claude-project.md](claude-project.md) — другая клиентская среда хранения данных (Google Drive + Claude Projects)

---

## Что это

No-code workspace в парадигме Notion: страницы (page) собираются из блоков, базы данных — это страницы с типизированными свойствами, дочерние строки — тоже страницы. Шаринг через ссылку (`buildin.ai/share/...`), workspace = "space".

**Зачем знать:** в РФ-командах, где Notion недоступен, Buildin часто оказывается главным хранилищем структурированных документов (контракты, реестры сотрудников, базы клиентов). Если строим AI-инфраструктуру для такой команды — данные у клиента уже там, и нужно их забрать или подключить.

## Тарифы и доступ к API/MCP

Pricing на 2026-04-24 (проверять перед обещаниями клиенту: <https://buildin.ai/pricing>):

| План | Цена | API & MCP |
|---|---|---|
| Free | $0 | нет |
| Plus | $10/user/мес (~$8 при годовой) | да |
| Business | $15/user/мес | да |
| Enterprise | custom | да |

**Ключевое:** API и MCP — фича от Plus и выше. Бесплатный тариф годится только для UI-экспорта (если он там не ограничен — нужно проверять в живом workspace). Page History (180 дней) — Pro+.

## Три пути интеграции

### 1. UI-экспорт (без интеграции)

Меню "..." в правом верхнем углу страницы → **Export Page** → PDF / Markdown / CSV / Word. Экспортируется один page со всеми блоками. Для всей базы данных есть отдельный экспорт CSV/Markdown в меню database.

Подвох: row базы открывается как отдельная страница, и экспорт row по идее должен работать через то же меню "..." — но это нужно проверять в конкретном workspace. Меню "..." визуально неочевидное: пользователи часто не находят пункт.

Когда подходит: разовая выгрузка, ручной snapshot, нет бюджета на Plus, нет инженерных рук.

### 2. REST API

Base URL: `https://api.buildin.ai`, auth: `Authorization: Bearer <token>`.

Структура notion-flavored: `parent.database_id` или `parent.page_id`, `properties.<name>.type`, rich-text массивы с `text`, `annotations`, `type`. **Ответ — JSON block tree, НЕ markdown.** Конвертация block tree → md делается на стороне клиента.

Основные endpoints:

| Метод | Path | Назначение |
|---|---|---|
| POST | `/v1/pages` | Создать page/row |
| GET | `/v1/pages/{page_id}` | Получить page (properties) |
| PATCH | `/v1/pages/{page_id}` | Обновить properties |
| POST | `/v1/pages/search` | Vector search по pages |
| POST | `/v1/databases` | Создать БД |
| GET | `/v1/databases/{database_id}` | Схема БД |
| POST | `/v1/databases/{database_id}/query` | Список rows (пагинация, фильтры, сортировка) |
| GET | `/v1/blocks/{block_id}/children` | Содержимое страницы блоками |
| PATCH | `/v1/blocks/{block_id}/children` | Добавить child block |
| POST | `/v1/search` | Global search |
| POST | `/oauth/token` | OAuth exchange |

Полная OpenAPI-спека: <https://github.com/next-space/buildin-api-sdk/blob/master/openapi.json>.

**Database = страницы с parent.database_id.** Row БД — обычная page, отличается только parent. Чтобы выгрузить контракт сотрудника по URL: URL → page_id → `GET /v1/pages/{id}` (properties) + `GET /v1/blocks/{id}/children` (тело) → конвертировать block tree в Markdown.

Лимиты БД: 100 properties max, 100 options в select, до 100 rows за один запрос. Formula-поля read-only.

### 3. Hosted MCP

URL формата: `https://mcp.buildin.ai/message?token=<authorization_code>`. Подключается одной строкой в `.mcp.json` любого MCP-клиента (Claude Code, Cursor, и пр.):

```json
{
  "mcpServers": {
    "buildin": { "url": "https://mcp.buildin.ai/message?token=YOUR_TOKEN" }
  }
}
```

Token = authorization code Internal Plugin'а (см. ниже).

**Список tools, которые отдаёт MCP, не документирован.** Rate limits тоже. Узнаётся только подключением живого сервера и `tools/list`.

## Создание плагина и токена

Buildin → `buildin.ai/dev/integrations` → Create APP Plugin → выбрать space + нужные permissions → получить authorization code (= токен).

Два типа интеграций:

- **Internal Plugin** — без OAuth, токен выдаётся сразу при создании, привязан к space. Permissions меняются PATCH'ем через API. Подходит для собственных скриптов и MCP клиента.
- **External Application** — полноценный OAuth 2.0, `POST /oauth/token` с `grant_type=authorization_code`, нужен `redirectUris` и проверка `client_secret`. Для публичных продуктов.

Scopes: `readContent`, `insertContent`, `updateContent`, `readUserWithEmail`, `readUserWithoutEmail`. Read-only делается одним `readContent`.

**Page-permissions выдаются поштучно на конкретные страницы.** Не подтверждено документально, наследуется ли разрешение с базы на все её rows — нужно проверять эмпирически. Если контрактов сотен — может потребоваться явная авторизация плагина на каждую row либо на всю БД.

## SDK и community

Официальный SDK: `next-space/buildin-api-sdk` — содержит `openapi.json`, инструкцию по генерации Java/TypeScript клиентов через openapi-generator. Свежий (последний коммит — конец лета 2025), но **community вокруг практически отсутствует**: ноль issues, ноль forks, единичные звёзды. Внешних сигналов о качестве API нет — на чужие грабли опереться не получится.

OAuth-демо: `next-space/buildin-external-integration` (TypeScript, минимальный пример).

## Риски и ограничения

- **Tools hosted MCP не публикуются** — что именно умеет (fetch/search/create/update), узнаётся только подключением. Может оказаться, что fetch-page-as-markdown нет, и Claude получает шумный JSON block tree.
- **Rate limits не документированы** — узнаётся эмпирически.
- **API возвращает не Markdown, а JSON block tree** — конвертация в md лежит на стороне клиента (paragraph/heading/list/todo/callout/divider/table — все типы блоков задокументированы, но писать конвертер придётся самим).
- **Permission на pages выдаётся поштучно** — наследование с БД не подтверждено документально.
- **Community мёртвое** — задать вопрос некому, опыта в сети мало.
- **Нет Free плана для API/MCP** — любая интеграция требует от клиента подписки от Plus.
- **Качество markdown-экспорта из UI** (callouts, toggle-lists, ссылки между страницами) — не проверено, нужно тестировать в живом workspace.

## Когда что выбирать

| Сценарий | Путь | Почему |
|---|---|---|
| Разовая выгрузка одной страницы / БД | UI-экспорт | Ноль инженерии, работает сразу. Проверить доступность на текущем плане |
| Регулярный snapshot базы в наш scaffold по команде | REST API + конвертер block tree → md | Полный контроль формата, кэширование, diff по `last_edited_time` |
| Интерактивное чтение Buildin'а из чата AI | Hosted MCP | Подключается одной строкой, AI сам ходит. Минус — список tools непредсказуем, в файл сохранять неудобно |
| Запись/обновление контента из AI | REST API (Internal Plugin со scope `insertContent`/`updateContent`) | MCP может не покрывать write-операции; через API контроль явный |

## Источники

- <https://buildin.ai/product> — обзор продукта
- <https://buildin.ai/pricing> — тарифы
- <https://buildin.ai/share/8087361a-defb-4871-8eb1-bae8a207881e> — Plugin Dev Complete Guide (Internal vs External, OAuth, scopes)
- <https://buildin.ai/share/e884b561-80e8-45b9-8300-2ada0c6113ec> — Database API
- <https://buildin.ai/share/a9e60536-bd5c-4fd6-8cb0-e6b5e2d985be> — MCP endpoint
- <https://buildin.ai/share/226960ff-8e59-4fa1-814f-493de410d7cc> — пример настройки MCP в Cursor
- <https://buildin.ai/share/a7a45a47-4f5b-439f-a652-901e7d25c111> — Set pages (секция Export Page)
- <https://github.com/next-space/buildin-api-sdk> — официальный SDK + OpenAPI
- <https://github.com/next-space/buildin-external-integration> — OAuth-демо
