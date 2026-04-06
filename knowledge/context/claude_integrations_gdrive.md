---
title: "Google Drive + Claude Projects: матрица совместимости, зазоры чтения/записи, мосты"
source_type: docs
status: raw
added: 2026-03-20
updated: 2026-03-20
review_by: 2026-06-20
tags: [claude-projects, google-drive, cowork, integrations, svaib-clients]
publish: false
version: 1
---

# Google Drive + Claude Projects: результаты тестирования

## Кратко

Тестирование интеграции Google Drive с Claude Projects и Cowork для клиентов SVAIB. Ключевой зазор: что Cowork умеет писать — Claude в Projects не видит автоматически, и наоборот. Матрица совместимости форматов, варианты мостов (автоконвертация, Drive → GitHub → RAG), целевая архитектура для клиента-CEO без технических навыков.

## Связанные файлы

- [../tools/claude-project.md](../tools/claude-project.md) — Claude Project как delivery-среда (Drive Fetch, PK sync, уровни доступа)
- [../tools/cowork.md](../tools/cowork.md) — Cowork: возможности и ограничения
- [search-mechanics.md](search-mechanics.md) — механики поиска в Claude Projects
- [../../clients/playbook/delivery/operations/setup_claude/claude_setup_guide.md](../../clients/playbook/delivery/operations/setup_claude/claude_setup_guide.md) — гайд по настройке Claude для клиента

---

## 1. Что протестировано

### Каналы чтения из Claude Projects

**Drive Fetch (MCP-коннектор в чате)**
- `google_drive_search` — поиск файлов по Drive API (по имени, содержимому, дате, папке)
- `google_drive_fetch` — чтение содержимого Google Doc по ID
- Работает в реальном времени, без задержки
- Видит **только нативные Google Docs**
- Ограничение по папке возможно: `'FOLDER_ID' in parents` (один уровень вложенности)
- Не видит: .docx, .md, .xlsx, .pdf, Google Sheets, Google Slides
- Не видит: изображения, комментарии, suggestions внутри Google Docs

**Project Knowledge (RAG)**
- Google Docs подключаются через sync — автоматическая синхронизация (с задержкой 2+ часа, известный баг с кешированием)
- Остальные форматы (.md, .pdf, .txt) — только ручная загрузка, статичная копия
- Claude видит контент через RAG-чанки (~800 токенов)

### Каналы записи

**Cowork (Claude Desktop)**
- Читает и пишет локальные файлы в указанной папке
- Создаёт .docx, .md, .xlsx, .pptx, .pdf
- **Не может** читать/писать нативные Google Docs (внутри .gdoc — только JSON-ссылка с doc_id)
- **Не поддерживает** Google-интеграции, Projects, Memory между сессиями (официально, на март 2026)
- Через Drive for Desktop: видит файлы на Google Drive как локальные, но Google Docs остаются ссылками

**Claude Code (VS Code)**
- Та же модель — работает с файловой системой
- Может писать .md/.docx в синхронизируемую папку
- Не работает с Google Docs API напрямую (без отдельного скрипта)

**Drive коннектор в чате (Projects)**
- Только чтение. Записи нет.

---

## 2. Матрица совместимости

| Формат | Drive Search/Fetch | PK sync | PK upload | Cowork запись | Cowork чтение |
|---|---|---|---|---|---|
| Google Doc (нативный) | ✅ | ✅ (с задержкой) | — | ❌ | ❌ (только ссылка) |
| .docx | ❌ | ❌ | ✅ (вручную) | ✅ | ✅ |
| .md | ❌ | ❌ | ✅ (вручную) | ✅ | ✅ |
| .pdf | ❌ | ❌ | ✅ (вручную) | ✅ | ✅ |
| Google Sheets | ❌ | ❌ | — | ❌ | ❌ |

**Ключевой зазор:** что Cowork умеет писать — Claude в Projects не видит автоматически. Что Claude видит автоматически (Google Docs) — Cowork не умеет писать.

---

## 3. Возможные мосты

### Автоконвертация в Drive
Настройка Drive for Desktop: "Convert uploads to Google Docs editor format". Если работает — .docx, созданный Cowork, автоматически становится Google Doc → виден через Drive Fetch. **Не протестировано.**

### Google Drive → GitHub → Project Knowledge (RAG)
Цепочка: клиент пишет в Google Docs → скрипт конвертирует в markdown → пушит в GitHub-репо → Claude видит через RAG.
Варианты реализации:
- **Google Apps Script + GitHub API** — триггер по таймеру/изменению, бесплатно, живёт в экосистеме клиента
- **GitHub Actions + Google Drive API** — GitHub тянет файлы по расписанию
- **Zapier/Make** — no-code, но платно и лишняя зависимость

**Статус:** архитектурно проработано, прототип не собран.

---

## 4. Архитектура для клиента: целевая схема

```
Клиент пишет в Google Docs (нулевой барьер)
        ↓
  [автосинхронизация — скрипт, раз в день]
        ↓
GitHub-репо клиента (markdown)
        ↓
  [RAG — уже работает]
        ↓
Claude Project клиента — видит всё
```

**Что клиент делает:** пишет в Google Docs, общается с Claude в своём Project.
**Что svaib делает:** настраивает GitHub-репо, скрипт синхронизации, Claude Project с инструкциями.
**Что клиент НЕ делает:** GitHub, markdown, настройка проектов, техническая работа.

### Разделение данных по каналам

| Тип данных | Где живёт | Как Claude видит |
|---|---|---|
| Стабильные (vision, goals, team, profile) | Google Docs → PK sync | Автоматически (с задержкой) |
| Оперативные (протоколы, задачи, заметки) | Google Docs → GitHub → RAG | По расписанию синхронизации |
| По запросу (конкретный документ) | Google Docs | Drive Fetch в реальном времени |

---

## 5. Открытые вопросы

1. **Автоконвертация .docx → Google Doc** — работает ли через Drive for Desktop? Замыкает ли цепочку Cowork → Drive Fetch?
2. **Частота синхронизации Drive → GitHub** — раз в день достаточно или нужен near-realtime?
3. **Конвертация Google Docs → markdown** — качество, потеря форматирования, таблицы, вложенные элементы?
4. **Задержка PK sync** — баг или фича? Стабилизируется ли со временем?
5. **Cowork + Google интеграции** — появятся ли в ближайших релизах? (на март 2026 — официально нет)
6. **Подгрузка .md в Project Knowledge** — время появления после загрузки? (не протестировано до конца)

---

## 6. Следующие шаги

- [ ] Протестировать автоконвертацию .docx → Google Doc в настройках Drive for Desktop
- [ ] Проверить задержку появления загруженного .md в Project Knowledge
- [ ] Собрать прототип моста Google Drive → GitHub (Google Apps Script)
- [ ] Протестировать полную цепочку на одном клиентском файле