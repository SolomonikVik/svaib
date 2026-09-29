---
title: "Сторонние модели в харнессах Claude Code и Codex — протоколы, шлюзы, SDK, ловушки"
source: "https://github.com/openai/codex"
source_type: repo
status: processed
added: 2026-09-24
updated: 2026-09-24
review_by: 2026-12-24
tags: [codex, claude-code, agent-sdk, codex-sdk, openai-agents-sdk, litellm, openrouter, claude-code-router, llm-gateway, model-providers, responses-api]
publish: false
---

# Сторонние модели в харнессах Claude Code и Codex

## Кратко

Оба харнесса берут модель из любого эндпоинта, но говорят каждый на своём протоколе: Codex — только OpenAI Responses API (`/v1/responses`), Claude Code — Anthropic Messages (плюс форматы Bedrock и Vertex). Чужая модель подключается через шлюз-переводчик (LiteLLM, OpenRouter, claude-code-router). У Codex это штатный путь через `model_providers`; у Claude Code — путь сообщества: Anthropic прямо не поддерживает маршрутизацию в не-Claude модели. SDK обоих (Claude Agent SDK, Codex SDK) запускают бинарь своего CLI и наследуют его ограничения.

> **Снимок:** код `openai/codex` на 2026-09-24, офдоки Claude Code, LiteLLM и OpenRouter на ту же дату, опыт серверного харнесса svaib (август–сентябрь 2026).

## Сравнение

| | Claude Code / Agent SDK | Codex / Codex SDK |
|---|---|---|
| Протокол к модели | Anthropic Messages (`/v1/messages`); Bedrock InvokeModel; Vertex rawPredict | только OpenAI Responses (`/v1/responses`); Chat Completions удалён |
| Как подставить модель | переменные окружения `ANTHROPIC_BASE_URL` и др. | `[model_providers.*]` в `~/.codex/config.toml` |
| Встроенные провайдеры | Anthropic API, Bedrock, Vertex, Foundry — все только с Claude | OpenAI, Amazon Bedrock, Ollama, LM Studio |
| Позиция вендора о чужих моделях | «doesn't support routing Claude Code to non-Claude models through any gateway» | свои провайдеры добавлять предлагается самому пользователю |
| SDK | Claude Agent SDK (Python, TS) — «a library that runs the Claude Code binary» | Codex SDK (TS, Python) — обёртка над CLI `codex` |

## Codex

Провайдер описывается в конфиге и выбирается по имени:

```toml
model_provider = "gw"
model = "<имя модели в шлюзе>"

[model_providers.gw]
name = "My gateway"
base_url = "http://localhost:4000/v1"
env_key = "GW_API_KEY"
wire_api = "responses"
```

У провайдера ещё есть заголовки (`http_headers`, `env_http_headers`), ключ через команду (`auth`), ретраи и таймауты стрима. `wire_api = "chat"` Codex отвергает с ошибкой — поэтому модель без Responses API подключается только через переводчик:

- **Локальные модели** — встроенные `ollama` и `lmstudio` (флаг `--oss`) или vLLM с Responses API.
- **LiteLLM** — официальный туториал для Codex: прокси отдаёт `/v1/responses` для любых своих провайдеров, а модели Anthropic и Gemini переводит в Chat Completions на своей стороне. Для не-OpenAI моделей Codex пишет `Model metadata for … not found. Defaulting to fallback metadata` — запросы проходят. Для долгих задач туториал советует поднять `stream_idle_timeout_ms` и ретраи.
- **OpenRouter** — свой `/api/v1/responses`, но **stateless**: `store: true` и `previous_response_id` получают 400, история шлётся целиком. Есть гайд по Codex; ключ через `auth`-команду, иначе Codex не подтягивает каталог моделей.
- **Anthropic напрямую — нет.** OpenAI-совместимый эндпоинт Anthropic отдаёт только Chat Completions и сама Anthropic называет его не production-ready.

Codex заточен под модели GPT (промпты, `apply_patch`, каталог моделей); с чужой моделью харнесс работает, но качество работы с инструментами не гарантировано.

**Codex SDK.** TypeScript-версия запускает CLI и обменивается JSONL через stdin/stdout; настройки уходят флагами `--config` (опции `config`, `configOverrides`, `baseUrl`). Python (`openai-codex`) говорит с `codex app-server`; `thread_start` принимает `model`, `model_provider` и `config`. Сторонняя модель в SDK — тот же `model_providers` с Responses API.

## Claude Code и Agent SDK

Эндпоинт и модель задаются окружением: `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL`; облачные провайдеры — `CLAUDE_CODE_USE_BEDROCK` / `CLAUDE_CODE_USE_VERTEX`. Шлюз обязан отдавать один из поддерживаемых форматов; Anthropic не сертифицирует сторонние шлюзы и чужие модели за ними не поддерживает.

Чужую модель подключают сообществом:

- **LiteLLM** — принимает Anthropic Messages на `/v1/messages` и переводит в любого провайдера; туториал «Claude Code with non-Anthropic models».
- **claude-code-router** — локальный шлюз моделей для кодинг-агентов; теперь обслуживает не только Claude Code, но и Codex, OpenCode и др. (протоколы OpenAI Chat/Responses, Anthropic Messages, Gemini).

**Agent SDK** запускает тот же бинарь Claude Code, поэтому переменные и ограничения — те же. Модель задаётся опцией `model` или окружением; claude.ai-логин в продуктах на SDK сторонним разработчикам без согласования с Anthropic не разрешён — только API-ключ.

## OpenAI Agents SDK — не аналог Codex SDK

Codex SDK управляет готовым агентом Codex. OpenAI Agents SDK (`openai-agents-python`, `openai-agents-js`) — фреймворк, в котором собираешь своего агента (агенты, tools, handoffs, guardrails) поверх API моделей. Он изначально провайдер-агностичен: чужие модели через Chat Completions с своим `base_url` (`set_default_openai_api("chat_completions")`), адаптеры `LitellmModel` и `AnyLLMModel` (помечены best-effort, beta), в JS — адаптер Vercel AI SDK.

## Опыт svaib: Agent SDK с моделью OpenAI

Серверный харнесс svaib гоняет Claude Agent SDK на модели OpenAI: `ANTHROPIC_BASE_URL` → LiteLLM-sidecar в поде → OpenRouter. Ключ провайдера видит только sidecar. Путь рабочий, но с ловушками:

- **Почему LiteLLM, а не OpenRouter напрямую.** Anthropic-совместимый эндпоинт OpenRouter возит только модели Anthropic.
- **`drop_params: true` в LiteLLM.** CLI шлёт специфику Anthropic (`thinking`, `cache_control`), которой у другой модели нет; без этого флага запрос падает целиком.
- **Окружение CLI.** `ANTHROPIC_API_KEY` пустой — иначе CLI предпочтёт его токену шлюза и уйдёт мимо. Малую модель (`ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`) направить на модель шлюза — иначе CLI зовёт haiku, которой в маршрутах нет. SDK кладёт `options.env` поверх окружения процесса, а не вместо, — лишнее приходится затирать пустыми значениями, иначе секреты процесса уезжают в CLI.
- **Серверные инструменты Anthropic дают ложный успех.** `WebSearch` отбрасывается `drop_params`, шлюз отвечает 200, результатом инструмента становится фраза модели «не могу искать», и агент выдумывает ответ. Поиск пришлось дать своим инструментом; web-плагин OpenRouter через тот же путь работает и приносит источники.
- **`additionalContext` хука модель не исполняет.** Подсказка доходит до транскрипта, но модель OpenAI её игнорирует (Claude видит и отказывается как от не-пользовательской). Рабочий путь — следующий запрос в ту же сессию.
- **Субагенты.** Модель сама подставляет в вызов `model: haiku` и `isolation: worktree`; хук снимает эти поля.
- **`tool_use` транслируется корректно**, но версию LiteLLM нужно пинить.
- **Цена в отчёте SDK недостоверна.** SDK считает по тарифам Anthropic — завышение было на порядок; `usage.cost` провайдера при трансляции теряется. Точный счёт — из токенов, включая cache read/write.
- **Качество.** На рутинной сборке (повестка встречи) модель OpenAI не уступила Sonnet и была заметно быстрее и дешевле; Opus глубже связывает факты.
- **Поведение привязано к версиям SDK и CLI** — после обновления замеры повторяют.

Трек и замеры: dev/saas/agent-harness/, конфиг шлюза — _plan/gateway/litellm-config.yaml, сравнение качества — _plan/quality.md.

## Источники

- [openai/codex](https://github.com/openai/codex) — `codex-rs/model-provider-info/src/lib.rs`, `sdk/typescript/README.md`, `sdk/python/`
- [Codex — advanced config](https://developers.openai.com/codex/config-advanced)
- [LiteLLM — OpenAI Codex tutorial](https://docs.litellm.ai/docs/tutorials/openai_codex), [LiteLLM — Responses API](https://docs.litellm.ai/docs/response_api), [LiteLLM — Claude Code with non-Anthropic models](https://docs.litellm.ai/docs/tutorials/claude_non_anthropic_models)
- [OpenRouter — Responses API](https://openrouter.ai/docs/api_reference/responses/overview), [OpenRouter — Codex CLI](https://openrouter.ai/docs/cookbook/coding-agents/codex-cli)
- [Anthropic — OpenAI SDK compatibility](https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk)
- [Claude Code — LLM gateways](https://code.claude.com/docs/en/llm-gateway), [gateway protocol](https://code.claude.com/docs/en/llm-gateway-protocol), [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- [musistudio/claude-code-router](https://github.com/musistudio/claude-code-router)
- [OpenAI Agents SDK — models](https://github.com/openai/openai-agents-python/blob/main/docs/models/index.md)

## Связанные файлы

- [claude-code.md](claude-code.md) — Claude Code как харнесс и система расширения
- [../plugins/codex-plugins.md](../plugins/codex-plugins.md) — Codex как хост плагинов
- [!coding.md](!coding.md) — сводка категории
