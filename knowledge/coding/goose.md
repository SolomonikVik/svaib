---
title: "Goose — загрузка плагинов, command-хуки, MCP и обновление Git-источника"
source: "https://github.com/aaif-goose/goose"
source_type: repo
status: processed
added: 2026-10-13
updated: 2026-10-13
review_by: 2027-01-13
tags: [goose, harness, plugins, hooks, python, mcp, acp, updates]
publish: false
---

# Goose

## Кратко

Goose — открытый харнесс с плагинами, скиллами, command-хуками, расширениями MCP и ACP. Загрузчик плагина и конфигурация MCP самого харнесса имеют разные ограничения. Для переноса Claude-хуков важно проверить окружение, доставку stdout в модель и фактическое применение отказа.

## Пакет и ресурсы

Поддерживаемый plugin directory должен соответствовать формату установщика Goose. Корень Claude marketplace не равен самостоятельному плагину: наличие каталога с несколькими plugin sources не гарантирует, что установщик выберет нужный. Скиллы из установленного пакета обнаруживаются отдельным механизмом. См. [плагины](https://github.com/aaif-goose/goose/blob/main/documentation/docs/guides/context-engineering/plugins.md) и [реализацию загрузчика](https://github.com/aaif-goose/goose/blob/main/crates/goose/src/plugins/mod.rs).

Директория Claude `agents/` не становится автоматически реестром дочерних агентов Goose. У Goose есть собственные механизмы делегирования; совпадение общего слова «агент» не доказывает совместимость Markdown-профиля, его инструментов и политики наследования.

В проверенном загрузчике Markdown-профилей `AgentMetadata` читает только `name`, `description` и `model`; frontmatter `tools` игнорируется. Перенос профиля поэтому не сохраняет allowlist инструментов: ограничения нужно выразить через действующий механизм Goose и проверить в дочерней сессии. Это результат чтения загрузчика, не доказательство исполнения дочернего агента; перед применением к новой версии контракт проверяют заново. [Загрузчик summon](https://github.com/aaif-goose/goose/blob/main/crates/goose/src/agents/platform_extensions/summon.rs).

В plugin MCP loader требуется stdio-декларация с командой; HTTP-декларация Claude-пакета не является эквивалентной. При этом сам runtime Goose поддерживает HTTP MCP. Ограничение одного загрузчика нельзя записывать как отсутствие HTTP MCP во всём харнессе. Для HTTP-сервера нужен поддерживаемый путь настройки native extension. См. [plugin MCP parser](https://github.com/aaif-goose/goose/blob/main/crates/goose/src/plugins/mcp_servers.rs) и [ACP](https://github.com/aaif-goose/goose/blob/main/documentation/docs/gdk/acp/index.md).

## Command-хуки

Плагин-хуки используют собственное окружение, включая `PLUGIN_ROOT`. Скрипт, ссылающийся на `CLAUDE_PLUGIN_ROOT`, требует перевода переменной либо общего запускателя. Native имена `write`, `edit`, `shell`, поля cwd и пути также нужно привести к контракту исходного обработчика. См. [хуки](https://github.com/aaif-goose/goose/blob/main/documentation/docs/guides/context-engineering/hooks.md).

Запуск команды ещё не означает исполнение её результата. В пути `UserPromptSubmit` stdout обработчика не используется как Claude `additionalContext`, поэтому печать карты скриптом не доказывает её доставку модели. Для такого контекста нужен отдельный путь внедрения в запрос. Перед применением этого вывода к новой сборке нужно проверить соответствующий event handler. См. [исполнение хуков](https://github.com/aaif-goose/goose/blob/main/crates/goose/src/hooks/mod.rs).

Для tool gate нужно перевести решение исходного скрипта в решение, которое Goose применяет до записи. Для Stop доступные сведения о последнем ответе можно преобразовать в вход Python-обработчика или Claude-проекцию истории. Это позволяет сохранить предметную логику, но не устраняет мост между контрактами. См. [переносимость хуков](../plugins/cross-harness-hooks.md).

## Git-обновления и ACP

Обновление зарегистрированного Git-плагина включается отдельно. При обнаружении скиллов общий механизм может проверить отслеживаемый источник, если прошёл интервал проверки, и заменить установленную копию; неудачная загрузка сохраняет прежнюю. Такое обновление следует выбранной ветке источника, а не обязательно последнему стабильному релизу. См. [менеджер плагинов](https://github.com/aaif-goose/goose/blob/main/crates/goose/src/plugins/mod.rs).

Путь обнаружения скиллов относится к общему runtime, поэтому не ограничен TUI. Однако его наличие в коде не гарантирует обновление при каждом ACP initialize: проверка зависит от вызова discovery и включённых компонентов. Применение нового содержимого в ACP-сессии нужно проверять отдельно. См. [skills client](https://github.com/aaif-goose/goose/blob/main/crates/goose/src/skills/client.rs).

Политика «последний стабильный релиз» требует собственного выбора версии источника, проверки пакета и момента активации. Автообновление ветки и автообновление самого Goose не заменяют эту политику.

## Лицензия и границы проверки

Goose распространяется по [Apache-2.0](https://github.com/aaif-goose/goose/blob/main/LICENSE). Собственный провайдер и его условия рассматриваются отдельно. Подключение через [BB](../tools/bb.md) не меняет plugin runtime; общий критерий полного рабочего цикла — [контракт исполнения](agent-runtime-contract.md).
