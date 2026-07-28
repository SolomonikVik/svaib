---
title: "Obsidian как платформа md-базы знаний: командная коллаборация (Relay) и agent-writable через MCP"
source_type: docs
status: raw
added: 2026-07-25
updated: 2026-07-25
review_by: 2026-10-25
tags: [obsidian, relay, crdt, yjs, knowledge-base, markdown, mcp, collaboration, sync, svaib-clients]
publish: false
version: 1
---

# Obsidian как платформа md-базы знаний

## Кратко

Obsidian — редактор персональной базы знаний на обычных markdown-файлах (папка .md на диске, данные у пользователя, local-first). Для SVAIB интересен как альтернативный клиентский слой хранения/рантайма к связке Google Drive + Claude Project: закрывает то, что у Drive болит — командную коллаборацию с приватными/общими зонами и одновременную запись — через CRDT-плагин **Relay**, а agent-writable-доступ даёт через **Obsidian MCP**. Кросс-девайсность: десктоп + мобильные приложения.

## Почему это в поле зрения продукта

Продукт SVAIB — файловая md-база, которую ассистент читает и пишет. Obsidian — зрелая экосистема ровно вокруг этого. Отличие от Google Drive: нативная работа с .md (не через конвертацию Google Docs), wiki-ссылки между заметками, богатая история версий и — главное — готовые командные решения, которых у Drive нет из коробки.

## Слой хранения

- Хранит знания как plain .md на диске (local-first), данные принадлежат пользователю, переносимы.
- YAML-frontmatter, wiki-ссылки `[[note]]`, вложения — родная модель. Совместимо с форматом наших knowledge-файлов.

## Командная коллаборация и синхронизация

Три пути по возрастанию «командности»:

- **Obsidian Sync** — официальная E2E-синхронизация между устройствами одного пользователя. Для команды слаб.
- **Relay** — сторонний плагин многопользовательской работы: real-time совместное редактирование на **Yjs/CRDT** → одновременные правки одного файла **сливаются без конфликтов** (в отличие от Google Drive, где два писателя дают «конфликтную копию»). Шаринг **отдельных папок** («личные заметки остаются приватными»), на старших тарифах — роли и ограничение приватных папок. Прямо отвечает на связку требований «общая база + приватные зоны + несколько ассистентов-писателей». Платный, есть бесплатный тариф на малые команды.
- **git** — версионирование/откат, но для нетехнической команды порог высокий (почему git не подходит клиенту-руководителю → [../context/claude_integrations_gdrive.md](../context/claude_integrations_gdrive.md)).

CRDT-движок Relay — **Yjs** — open-source; тот же класс технологии лежит в OSS-альтернативах (Nextcloud Text, HedgeDoc), если нужен self-host без проприетарного плагина.

## Agent-writable: доступ ассистента

- **Obsidian MCP** — множество community-серверов, дающих AI read/write в vault: чтение файлов, поиск, правка frontmatter, дозапись. Закрывает «ассистент пишет в файл-миссию» на файловом уровне (аналог filesystem MCP, но с пониманием vault — теги, ссылки). Карта MCP-серверов → [../agents/mcp.md](../agents/mcp.md).
- Альтернатива без MCP — «оболочка + наполнение»: Claude Code прямо в директории vault + agentic grep (паттерн claudesidian → [ai-workspaces.md](ai-workspaces.md)).

## Ограничения / когда НЕ Obsidian

- Мобильная правка «сырого» md менее удобна не-технику, чем Google Docs.
- Relay/Sync — доп. подписки; self-host коллаборации на Yjs требует инженера.
- Если данные клиента уже в Google Workspace/Drive — миграция в Obsidian-vault может не окупиться; тогда путь — Drive + MCP (→ [../context/claude_integrations_gdrive.md](../context/claude_integrations_gdrive.md)).

## Связанные файлы

- [ai-workspaces.md](ai-workspaces.md) — claudesidian: Obsidian-vault + Claude Code (оболочка + наполнение)
- [../context/claude_integrations_gdrive.md](../context/claude_integrations_gdrive.md) — альтернативный слой хранения (Google Drive) и его зазоры чтения/записи
- [../agents/mcp.md](../agents/mcp.md) — MCP-серверы (Obsidian MCP, filesystem, Google Drive MCP)
- [../context/markdown-for-llm.md](../context/markdown-for-llm.md) — как оформлять .md-файлы vault для LLM/RAG
- [../cases/arscontexta.md](../cases/arscontexta.md) — генератор персональных md-knowledge-систем (родственный подход)
- [openknowledge.md](openknowledge.md) — OpenKnowledge (Inkeep): AI-native md IDE с нативным MCP и локальным Yjs-CRDT
- [team-content-platforms.md](team-content-platforms.md) — командные платформы с AI и их модель прав: с чем сравнивать file-native слой, когда у клиента появляется команда и приватные зоны
- [../context/md-data-systems.md](../context/md-data-systems.md) — как разложить такую систему на плоскости содержимого, контекста, прав и действий
