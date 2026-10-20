---
title: "Подключение Codex и OMP к стороннему провайдеру — пример NeuralDeep"
created: 2026-10-14
updated: 2026-10-14
status: draft
type: reference
audience: client
publish: false
---

# Подключение Codex и OMP к стороннему провайдеру — пример NeuralDeep

Две инструкции для OpenAI-совместимого провайдера на примере NeuralDeep. Codex требует поддержку **Responses API**; OMP также умеет работать через **Chat Completions**. Поэтому одного заявления «совместим с OpenAI» для Codex недостаточно.

Примеры команд — для Bash на Linux/macOS. Предполагается, что `codex` и `omp` уже установлены. Если нет — начните с [инструкции установки BB Desktop, Codex CLI и OMP](bb-and-omp.md).

## 🔹 Codex: подключить провайдера и сохранить подписку

Понадобятся установленный Codex CLI, API-ключ провайдера и название доступной модели. У провайдера должна быть поддержка **Responses API**. Ниже — пример [NeuralDeep](https://neuraldeep.ru/docs), команды для Bash на Linux/macOS.

### 1. Добавьте настройки

Откройте файл `~/.codex/config.toml` — папку `.codex` в домашней папке пользователя, файл `config.toml`. Если файла нет, создайте его. Добавьте блоки ниже, сохранив прежние настройки. Если блок `neuraldeep` уже есть, обновите его без дублирования.

```toml
[model_providers.neuraldeep]
name = "NeuralDeep"
base_url = "https://api.neuraldeep.ru/v1"
wire_api = "responses"
env_key = "NEURALDEEP_API_KEY"
requires_openai_auth = false
supports_websockets = false

[profiles.neuraldeep]
model_provider = "neuraldeep"
model = "qwen3.6-35b-a3b"
```

### 2. Введите API-ключ

Введите в терминале:

```bash
read -r -s -p "API-ключ NeuralDeep: " NEURALDEEP_API_KEY
printf '\n'
export NEURALDEEP_API_KEY
```

Вставьте ключ из личного кабинета NeuralDeep и нажмите Enter. При вводе ключ не отображается. В новом терминале этот шаг нужно повторить.

### 3. Запустите Codex

Перейдите в папку своего проекта и выполните:

```bash
codex --profile neuraldeep
```

### 4. Проверьте ответ

```bash
codex --profile neuraldeep exec "Ответь только OK. Инструменты не используй."
```

В информации о запуске должны быть провайдер `neuraldeep` и модель `qwen3.6-35b-a3b`, затем — ответ `OK`.

**Как сменить модель:** замените значение `model` в блоке `[profiles.neuraldeep]` на идентификатор из каталога провайдера.

**Как вернуться к подписке:** запускайте обычный `codex` без `--profile neuraldeep`. Прежний вход через ChatGPT сохранится, если не менять глобальные `model_provider` и профиль по умолчанию.

**Для другого провайдера:** замените название секции, `name`, `base_url`, имя переменной в `env_key` и модель в профиле. Значение `wire_api = "responses"` оставьте.

Эта инструкция настраивает запуск из терминала. Запуск из BB требует отдельной настройки процесса Codex; выбор названия модели в BB сам по себе провайдера не переключает.

Справка: [параметры подключения Codex](https://developers.openai.com/codex/config-reference), [профили и сторонние провайдеры](https://developers.openai.com/codex/config-advanced).

## 🔹 OMP: подключить провайдера и выбрать модель

### 1. Передайте ключ

Если уже выполнили этот шаг для Codex в том же терминале, повторять его не нужно.

```bash
read -r -s -p "API-ключ NeuralDeep: " NEURALDEEP_API_KEY
printf '\n'
export NEURALDEEP_API_KEY
```

### 2. Добавьте провайдера

Откройте или создайте `~/.omp/agent/models.yml`. Добавьте `neuraldeep` внутри секции `providers`, сохранив остальных провайдеров:

```yaml
providers:
  neuraldeep:
    baseUrl: https://api.neuraldeep.ru/v1
    apiKey: NEURALDEEP_API_KEY
    api: openai-completions
    authHeader: true
    models:
      - id: qwen3.6-35b-a3b
        name: Qwen 3.6 · NeuralDeep
        reasoning: true
        input: [text, image]
        contextWindow: 262144
        maxTokens: 32768
        compat:
          supportsDeveloperRole: false
          supportsReasoningEffort: false
          maxTokensField: max_tokens
```

Здесь `apiKey` содержит **имя переменной окружения**. Значение ключа OMP прочитает из неё. `openai-completions` обозначает Chat Completions API; параметры `compat` адаптируют запросы к провайдеру. Формат описан в [документации OMP](https://github.com/can1357/oh-my-pi/blob/main/docs/models.md).

### 3. Проверьте каталог и запустите модель

```bash
omp models neuraldeep
omp --model neuraldeep/qwen3.6-35b-a3b
```

Короткая проверка подключения:

```bash
omp --model neuraldeep/qwen3.6-35b-a3b --no-tools -p "Ответь только OK."
```

### 4. При необходимости назначьте модель по умолчанию

В `~/.omp/agent/config.yml` добавьте или обновите нужные поля внутри `modelRoles`:

```yaml
modelRoles:
  default: neuraldeep/qwen3.6-35b-a3b
  smol: neuraldeep/qwen3.6-35b-a3b
  slow: neuraldeep/qwen3.6-35b-a3b
  plan: neuraldeep/qwen3.6-35b-a3b
```

Тогда основной диалог, быстрые задачи, сложные задачи и планирование используют NeuralDeep. Назначение моделей ролям описано в [настройках OMP](https://github.com/can1357/oh-my-pi/blob/main/docs/settings.md).

**Для другого провайдера:** замените идентификатор `neuraldeep`, адрес API, переменную ключа, модель и её ограничения. Параметры `compat` берите из требований провайдера. Если он поддерживает Responses API, OMP позволяет указать `api: openai-responses`.

## 🔹 Если запускать через BB

BB должен получить ключ в окружении **своих процессов**. Переменная, введённая в отдельном терминале, автоматически туда не попадёт.

Для OMP файл `models.yml` используется и при запуске из BB; ключ передайте через **Machine environment** BB. Для Codex дополнительно нужен запуск с выбранным профилем через отдельную обёртку — так можно направить Codex в BB к стороннему API, сохранив обычный `codex` в терминале на подписке.
