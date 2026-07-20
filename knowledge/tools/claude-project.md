---
title: "Claude Project — delivery-среда для клиентов SVAIB"
source_type: docs
status: processed
added: 2026-03-18
updated: 2026-03-18
review_by: 2026-06-18
tags: [tools, claude, google-drive, delivery, runtime]
publish: false
version: 1
---

# Claude Project — delivery-среда для клиентов

## Кратко

Claude Project (claude.ai) — веб-интерфейс Claude с подключением данных через Project Knowledge и Google Workspace коннекторы. Для клиентов SVAIB это основной runtime: руководитель работает в привычном браузере, данные в Google Docs, AI читает через Drive Fetch. Ноль порог входа — не нужно устанавливать CLI, учить Markdown или настраивать файловую систему.

**Docs:** https://support.claude.com/ru/articles/10166901-используйте-соединители-google-workspace

---

## Три уровня доступа к данным

| Уровень | Видит при старте | Чтение целиком | RAG-поиск |
|:--------|:-----------------|:---------------|:----------|
| **System Prompt** | да, всегда в памяти | всегда целиком | — |
| **Project Files** | да, видит названия | да, `view` (до ~16K символов) | да |
| **Project Knowledge** | нет, даже названий | нет, только чанками | да |

- <200K токенов → все Project Files загружаются целиком (идеал: нет chunking, нет retrieval misses)
- \>200K → автоматический RAG (Contextual Retrieval: chunk + BM25 + semantic)

Подробнее о механиках поиска → [../context/search-mechanics.md](../context/search-mechanics.md)

---

## Google Workspace коннекторы

Подключаются в настройках проекта. Дают Claude два инструмента в чате:

**Drive Search** — поиск файлов на Google Drive.
- Фильтрует по folder ID (`'ID' in parents`), но только один уровень вглубь (не рекурсивно)
- `semantic_query` игнорирует фильтр по папке — scope ненадёжен на уровне API
- Scope ограничивается системной инструкцией (folder ID + правила "где что искать")

**Drive Fetch** — чтение полного текста Google Doc по ID.
- Даёт актуальную версию документа (не снимок)
- Форматирование частично сохраняется: H2 → ##
- Только Google Docs — Sheets, Slides, Markdown не читаются

**RAG в Project Knowledge** — альтернативный путь.
- Файлы из Google Drive попадают в RAG-индекс
- Отстаёт: файл изменён, через 2+ часа RAG всё ещё отдаёт старую версию
- Не полагаться на свежесть — для актуальных данных использовать Drive Fetch по ID

Источник: тестирование Виктора Соломоника, март 2026.

---

## Архитектурные выводы для клиентов SVAIB

- **Клиент работает в Google Docs** — ноль порог входа, привычный инструмент
- **Markdown-scaffold не обязателен** — Google Docs нативнее и проще для руководителей
- **Актуальные данные — через Drive Fetch по ID**, не через RAG
- **Ключевые файлы** — дублировать в Project Knowledge для быстрого доступа, но не полагаться на свежесть
- **Scope** — системная инструкция (folder ID + правила), не API-фильтры

→ Подробнее о влиянии на фреймворк: `meta/management/ideas.md` → секция «Инсайты», запись 2026-03-18

---

## Связанные файлы

- [ai-workspaces.md](ai-workspaces.md) — каталог AI-оболочек (Claude Project в ряду)
- [cowork.md](cowork.md) — Cowork: другая оболочка Anthropic (для knowledge workers, плагины)
- [../context/search-mechanics.md](../context/search-mechanics.md) — механики поиска в Claude Projects (full context vs RAG, уровни доступа)
- [../coding/claude-code.md](../coding/claude-code.md) — Claude Code: CLI для разработчиков (другой runtime)
- [../context/claude_integrations_gdrive.md](../context/claude_integrations_gdrive.md) — тестирование Google Drive + Claude Projects + Cowork: матрица совместимости, зазоры, мосты
