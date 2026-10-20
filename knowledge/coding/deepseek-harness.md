---
title: "DeepSeek Harness — профили, мосты хуков, MCP и ACP"
source: "https://github.com/deepseek-ai/deepseek-harness"
source_type: repo
status: processed
added: 2026-10-13
updated: 2026-10-13
review_by: 2027-01-13
tags: [deepseek-harness, dsh, harness, cordis, hooks, mcp, acp, plugins]
publish: false
---

# DeepSeek Harness — профили, мосты хуков, MCP и ACP

## Кратко

DeepSeek Harness (DSH) — модульный агентный харнесс на Cordis: профиль собирает модельного провайдера, инструменты, скиллы, хуки, MCP и интерфейс. Claude/Codex-ресурсы подключаются по компонентам через отдельные мосты; это не обещание полной совместимости исходного marketplace. Наличие ACP-сервера даёт путь к внешнему интерфейсу, но не подтверждает работоспособность конкретной связки с ним.

## Профили и ресурсы

Профили `web`, `headless`, `acp` и `sdk` задают собственные compositions: упорядоченные bundles и Cordis patches. Поздняя правка заменяет весь `config` выбранной строки, а не объединяет вложенные поля. Скиллы, хуки и MCP нужно проверить в итоговой композиции отдельно. [Контракт профилей](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/app-boot/README.md#profiles).

Filesystem-загрузчик ищет скиллы в `.dsh/skills`, `.agents/skills`, пользовательских корнях и `customSkillDirs`. Поддерживаются `<name>/SKILL.md` и верхнеуровневый `<name>.md`; произвольного рекурсивного поиска нет. Каталог ресурсов Claude-плагина нужно подключать явно. [Скиллы](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/skill/skill-filesystem/README.md).

## Command-хуки и Stop

Экспериментальные мосты Claude/Codex монтируют отдельно с `configPath`; обычное обнаружение всех слоёв настроек этих хостов не воспроизводится. Runner передаёт JSON на stdin и выполняет команду через `ctx.shell`, поэтому Python-логику можно сохранить при доступном интерпретаторе. Совпадение названий событий не означает совпадения данных и момента исполнения. [Claude bridge](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/experimental/hooks-claude-code/README.md), [Codex bridge](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/experimental/hooks-codex/README.md).

В проверенном контракте Stop может запросить продолжение через `agent.steer()`, но мосты не дают пригодный текст последнего ответа или путь транскрипта; `stop_hook_active` всегда `false`. Адаптер должен сам передать текущий ответ и ограничить продолжение одним разом. `continue: false` здесь не останавливает run; доставка SessionStart перед первым запросом также не гарантирована. Эти границы нужно перепроверять при смене версии. [Общий контракт переноса хуков](../plugins/cross-harness-hooks.md).

## MCP, модель и авторизация

Одна строка `mcp-client` подключает один сервер через stdio либо Streamable HTTP. Проверенный HTTP transport использует `url` и `requestInit.headers`; browser OAuth, `authProvider` и управление refresh в этом пути не реализованы. Заголовок с действующим токеном не заменяет полный жизненный цикл пользовательского OAuth и успешный вызов инструмента в рабочей сессии. [Transport](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/mcp/mcp-client/src/transport.ts).

`llm-pi-ai` позволяет задавать собственные endpoint, credentials и каталог моделей для Chat Completions, Responses и Anthropic Messages. Реальные контекст, выходной бюджет и tool calls проверяют на выбранном API; поддержка протокола не доказывает качество LLM. OAuth модельного провайдера и OAuth MCP — разные подключения. [Провайдеры](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/llm/llm-pi-ai/README.md), [общие требования к модели](third-party-models.md).

## Обновления, ACP и лицензии

Plugin manager принимает registry/Git/path-источники; замена существующей зависимости требует restart, изменения development links — rebuild/restart. Установка и перечитывание профиля не подтверждают автоматическое получение следующего релиза внешнего пакета. Исполняемый host plugin работает внутри процесса вне workspace sandbox. [Plugin manager](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/plugin-manager/README.md), [политики обновления](../plugins/plugin-update-hook-paths.md).

У DSH есть stdio ACP-сервер, запускаемый профилем `acp`; он рассчитан на автоматизацию и исключает часть интерактивных UI-возможностей. Подключение через [BB](../tools/bb.md) проверяют отдельно: сессию, модель, подтверждения, файловые операции и ресурсы профиля. [ACP DSH](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/acp/acp/README.md).

Сам DSH распространяется по MIT, но необязательный backend `dsh-subagent-claude-code` использует официальный Claude Agent SDK и его runtime с отдельными условиями. Наличие этого backend не доказывает, что основной DSH запускается через Claude Code. Для независимой среды проверяют выбранные компоненты, а не самоназвание модели. [README и предупреждение о breaking changes](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/README.md), [зависимости](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/THIRD_PARTY_NOTICES.md), [границы Agent SDK](../agents/claude-agent-sdk.md).

Для адаптации нужно закрепить исходный срез и перепроверять контракт после обновления; [лицензии и региональные условия](harness-regional-availability.md) независимы от технической совместимости. Общий критерий приёмки — [контракт рантайма](agent-runtime-contract.md).
