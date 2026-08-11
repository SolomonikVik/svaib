---
title: "Google Drive + Claude Projects: матрица совместимости, зазоры чтения/записи, мосты"
source_type: docs
status: raw
added: 2026-03-20
updated: 2026-07-27
review_by: 2026-10-25
tags: [claude-projects, google-drive, cowork, integrations, svaib-clients, mcp]
publish: false
---

# Google Drive + Claude Projects: результаты тестирования

## Кратко

Тестирование интеграции Google Drive с Claude Projects и Cowork для клиентов SVAIB. Ключевой зазор: что Cowork умеет писать — Claude в Projects не видит автоматически, и наоборот. Матрица совместимости форматов, варианты мостов (автоконвертация, Drive → GitHub → RAG, прямой мост через Google Drive MCP), целевая архитектура для клиента-CEO без технических навыков.

## Связанные файлы

- [../tools/claude-project.md](../tools/claude-project.md) — Claude Project как delivery-среда (Drive Fetch, PK sync, уровни доступа)
- [../tools/cowork.md](../tools/cowork.md) — Cowork: возможности и ограничения
- [../agents/mcp.md](../agents/mcp.md) — MCP-серверы: официальный Google Drive MCP и OSS-сервер с записью
- [../tools/obsidian.md](../tools/obsidian.md) — Obsidian + Relay/MCP: альтернативный слой хранения с командной коллаборацией
- [search-mechanics.md](search-mechanics.md) — механики поиска в Claude Projects
- ../../clients/playbook/handouts/claude_setup_guide.md — гайд по настройке Claude для клиента

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

### Google Drive MCP — прямой мост чтения/записи (ещё один вариант)

Отдельный от GitHub-моста путь: подключить Drive к ассистенту через MCP-сервер — тогда чтение и запись идут прямо в Drive, без промежуточного репозитория. **Дополняет, а не заменяет** GitHub-мост.

- **Официальный Google Drive MCP** (Google, remote, OAuth) — на момент записи умеет **только read + create**: поиск, чтение, создание файлов, но **без правки существующих** (нет `update`). Для «ассистент дописывает в файл-миссию» этого мало.
- **OSS-сервер с записью** (напр. `piotr-agier/google-drive-mcp`, MIT) — закрывает зазор: `updateTextFile` = правка .md/текста по `fileId` (read-modify-write, как в локальном редакторе), поддержка **Shared Drives** (`supportsAllDrives`), история версий/откат, блокировки файлов, управление правами. Разворачивается в **team-режиме за HTTPS + OAuth** и подключается к **claude.ai / Cowork как custom connector** — работает с планшета/телефона, каждый юзер под своей Google-личностью (естественное разделение приват/общее).
- **Ограничение:** запись = last-write-wins (перезапись целиком), автослияния одновременных правок нет. Несколько ассистентов на один файл → `lockFile` либо структура «один писатель на файл»; истинный CRDT-мерж — только вне Drive (Obsidian + Relay/Yjs → [../tools/obsidian.md](../tools/obsidian.md)).

**Статус:** вариант проработан по исходникам сервера; не собран под клиента. Требует self-host MCP-сервера и проверки, что тариф Claude/Cowork разрешает кастомные коннекторы. Детали MCP-серверов → [../agents/mcp.md](../agents/mcp.md).

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
7. **Google Drive MCP как мост** — собрать прототип на OSS-сервере с записью, проверить подключение к Cowork/claude.ai как custom connector и лимиты тарифа на кастомные коннекторы. Сравнить с GitHub-мостом по надёжности и порогу поддержки.

---

## 6. Следующие шаги

- [ ] Протестировать автоконвертацию .docx → Google Doc в настройках Drive for Desktop
- [ ] Проверить задержку появления загруженного .md в Project Knowledge
- [ ] Собрать прототип моста Google Drive → GitHub (Google Apps Script)
- [ ] Протестировать полную цепочку на одном клиентском файле

---

## 7. Ownership и orphaned-файлы — риск для multi-tenant Drive

Отдельный от матрицы совместимости риск, всплывший на клиентских Drive-структурах (несколько клиентов/сотрудников создают файлы в общей иерархии): когда файл создан внутри чужой/шаренной папки (создатель файла ≠ владелец папки), а эта родительская папка удаляется, перемещается или теряет права доступа — Google Drive не может физически удалить чужой файл. Вместо этого он помечает файл как orphaned ("unorganized"), и файл остаётся у **фактического создателя** в его `My Drive` root — а не у владельца дерева папок, в которой он раньше лежал. Подтверждено и для веб-интерфейса Drive, и для `rclone` (`rclone delete` файла, которым не владеешь, физически файл не удаляет — Drive откатывает его в root настоящего владельца). Это документированное поведение Google Drive API/permissions model, не баг rclone.

**Практическое значение:** это не утечка контента между аккаунтами в смысле "чужие данные стали видны не тому" — файл возвращается к тому, кто его физически создал, просто теряет папку-контекст. Риск гигиенический (файлы копятся в root создателя), не риск раскрытия чужих данных.

**Поиск и уборка:** запрос `is:unorganized owner:me` в поиске Drive находит такие файлы у текущего владельца. Восстановить в исходную папку ("Add to My Drive") или удалить может только фактический владелец файла.

---

## 8. Модель прав Drive: что можно и чего нельзя закрыть

Практические границы, которые определяют, какие приватные зоны вообще реализуемы на Google Drive.

**Личное vs командное.** Личные материалы Google рекомендует держать в My Drive, командные — в Shared Drives: последние существуют, чтобы контент оставался у организации после ухода сотрудника.

**Ограничение подпапки.** Папки с limited access — единственный способ сузить доступ к конкретной подпапке (работает и в My Drive, и в shared drives): открыть её могут только явно добавленные пользователи. Остальные участники видят, что папка существует (серая, с иконкой), и могут запросить доступ. По умолчанию доступ в shared drive «расширяющийся» — унаследованный сверху.

**Чего закрыть нельзя.** Manager shared drive всегда имеет доступ к limited-папке внутри этого диска, снять это нельзя. Для Content Manager возможность управлять limited-папками включается настройкой диска.

**Организация видит всё.** Super admin может экспортировать данные организации, Google Vault — удерживать, искать и выгружать данные Drive. То есть «приватно от коллег» на Drive достижимо, «приватно от администратора организации» — нет. Если требование строгое, личная зона должна жить вне корпоративного tenant (отдельный аккаунт или отдельное хранилище), а не отдельной папкой внутри него.

**Следствие для агента.** Gemini в Workspace работает в правах пользователя; для внешнего AI (Claude, MCP-мост) права определяются тем аккаунтом, под которым выдан OAuth-доступ. Персональные зоны, которые не должны попасть в контекст ассистента, надёжнее не подключать к нему вовсе, чем полагаться на фильтрацию на стороне промпта.

Общая механика прав в AI-выдаче → [permission-aware-retrieval.md](permission-aware-retrieval.md); сравнение платформ → [../tools/team-content-platforms.md](../tools/team-content-platforms.md).

Источники: [Google Drive — папки с limited и expansive access](https://developers.google.com/workspace/drive/api/guides/limited-expansive-access) · [обновление опыта доступа в Drive (Workspace Updates)](https://workspaceupdates.googleblog.com/2025/02/updating-access-experience-in-google-drive.html)

Источники: [Orphaned Files in Google Drive — MakeUseOf](https://www.makeuseof.com/what-are-orphaned-files-google-drive/) · [Google Drive Orphaned Files — Patronum](https://www.patronum.io/google-drive-file-management-how-to-find-and-fix-orphaned-files) · [rclone forum — places deleted files in the root directory](https://forum.rclone.org/t/rclone-google-drive-places-deleted-files-in-the-root-directory/33100)
