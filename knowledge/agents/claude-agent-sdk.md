---
title: "Claude Agent SDK — обёртка над Claude Code, компоненты и лицензии"
source: "https://code.claude.com/docs/en/agent-sdk/overview"
source_type: docs
status: processed
added: 2026-10-13
updated: 2026-10-13
review_by: 2027-01-13
tags: [claude-agent-sdk, claude-code, sdk, runtime, plugins, hooks, licensing]
publish: false
---

# Claude Agent SDK — устройство и границы

## Кратко

Claude Agent SDK позволяет управлять агентом Claude Code из Python и TypeScript: использовать его инструменты, сессии, субагентов, хуки и плагины. Агентный цикл исполняет бинарь Claude Code; SDK предоставляет программный интерфейс к нему. Python-обёртка имеет MIT-лицензию, TypeScript SDK и runtime Claude Code — собственные условия Anthropic; лицензия обёртки не распространяется на весь исполняемый пакет.

## Где исполняется агент

Приложение вызывает SDK, SDK запускает Claude Code и обменивается с ним сообщениями. Чтение файлов, вызовы инструментов, управление контекстом и продолжение сессии выполняет runtime. Это описано в [официальном обзоре архитектуры](https://code.claude.com/docs/en/agent-sdk/overview).

Python-пакет по умолчанию использует встроенный CLI; если его нет, ищет установленный Claude Code. Параметр `cli_path` выбирает другой исполняемый файл Claude Code. Реализация — [SubprocessCLITransport](https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/_internal/transport/subprocess_cli.py).

В Python можно передать собственный `Transport`. Он заменяет канал исполнения, но готового независимого агентного цикла не добавляет: потребуется реализация протокола и поведения агента на другой стороне. Это граница между переиспользованием MIT-кода интерфейса и созданием другого харнесса, а не настройка модельного провайдера. Выбор транспорта — в [исходнике клиента](https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/_internal/client.py).

## Что можно подключить

- **Инструменты и MCP:** встроенные инструменты runtime, внешние MCP-серверы и функции приложения через SDK MCP-сервер.
- **Хуки и разрешения:** приложение обрабатывает события и решения о выполнении инструментов. Программные обработчики SDK и command-хуки установленных плагинов — разные способы подключения к runtime.
- **Скиллы, агенты и плагины:** SDK использует механизмы Claude Code; плагины можно передать по локальному пути. Загрузка файлов конфигурации задаётся явно — наличие плагина на диске само по себе не доказывает, что конкретный запуск его подключил.

Описание возможностей и маршруты настройки — в [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview). Архитектуры делегирования и размещения процессов — в [материале о субагентах](subagents.md).

## Модельный провайдер не заменяет runtime

SDK принимает имя модели и настройки окружения Claude Code. Официально описаны подключения через Anthropic API и облачные платформы; приложение может использовать шлюз совместимого протокола. Форматы API, перевод запросов и ограничения сторонних моделей разобраны в [сторонних моделях в харнессах](../coding/third-party-models.md).

Даже когда шлюз направляет запросы к другой LLM, агентный цикл продолжает выполнять Claude Code. Это не превращает SDK в самостоятельный OSS-харнесс и не меняет лицензию бинаря. Поддержка сторонних платформ и условия использования claude.ai-авторизации в чужих продуктах описаны в [Quickstart](https://code.claude.com/docs/en/agent-sdk/quickstart).

## Лицензии компонентов

| Компонент | Первичный источник | Граница разрешения |
|---|---|---|
| Python-обёртка | [MIT LICENSE](https://github.com/anthropics/claude-agent-sdk-python/blob/main/LICENSE) | MIT относится к покрытому ею коду; права на копирование и изменение этого компонента сохраняются |
| TypeScript SDK | [LICENSE.md](https://github.com/anthropics/claude-agent-sdk-typescript/blob/main/LICENSE.md) | Права сохранены Anthropic, использование подчиняется Commercial Terms; это не MIT-пакет |
| Claude Code runtime | [LICENSE.md](https://github.com/anthropics/claude-code/blob/main/LICENSE.md) | Собственные условия Anthropic действуют независимо от лицензии Python-обёртки |

[README Python SDK](https://github.com/anthropics/claude-agent-sdk-python/blob/main/README.md#license-and-terms) и [документация SDK](https://code.claude.com/docs/en/agent-sdk/overview#license-and-terms) отсылают использование SDK к Commercial Terms с исключением для компонентов, имеющих другую лицензию. Из этого не следует отмена MIT для Python-кода; также не следует разрешение использовать встроенный Claude Code по MIT.

Отдельное переиспользование только MIT-компонентов без proprietary runtime и сервисов — другой состав системы. Его техническую работоспособность и применимые условия нужно оценивать отдельно. Региональные условия runtime и модельных сервисов — в [региональной доступности харнессов](../coding/harness-regional-availability.md).

## Agent SDK и API Client SDK — разные продукты

Обычные [Anthropic API SDK](https://github.com/anthropics/anthropic-sdk-python) предоставляют клиент к модельному API; [MIT-лицензия API-клиента](https://github.com/anthropics/anthropic-sdk-python/blob/main/LICENSE) не означает, что вместе с ним поставляется агентный цикл Claude Code. Agent SDK управляет готовым агентом, Client SDK оставляет сборку агента приложению. При выборе библиотеки нужно проверять точное имя пакета, его лицензию и исполняемые зависимости.

## Связанные материалы

- [Claude Code](../coding/claude-code.md) — CLI и система расширения.
- [Субагенты](subagents.md) — делегирование и размещение агентных процессов.
- [Сторонние модели](../coding/third-party-models.md) — протоколы и шлюзы.
- [Региональная доступность](../coding/harness-regional-availability.md) — лицензия, условия сервисов и география использования.
