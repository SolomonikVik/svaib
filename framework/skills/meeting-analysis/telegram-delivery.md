---
title: "Telegram Delivery — автоматическая отправка сводки"
status: EXPERIMENTAL
updated: 2026-03-31
version: 1
---

# Telegram Delivery

> **EXPERIMENTAL.** Пилот автоматической отправки Telegram-сводок. Не часть пайплайна — тестируется отдельно. По результатам тестов решим, куда это ложится в архитектуре (hooks, plugin, delivery-слой).

## Что это

После шага 3 оркестратора (Telegram-сводка сгенерирована) — координатор может отправить её в Telegram через бота, вместо ручного копирования.

## Принятые решения (пилот)

- **Один бот на клиента** — изоляция, безопасность, масштабируемость. Создаём через @BotFather как сервисный шаг
- **Секреты в `.env`** — в корне рабочего пространства клиента, в `.gitignore`. Токен не передаётся в prompt и не подставляется в команду вручную
- **Скрипт-обёртка** — `send_telegram.sh` читает `.env`, отправляет через curl. Координатор вызывает только скрипт
- **Точка контроля** — координатор показывает сводку, спрашивает "отправить?". Переключение на автоотправку — в оркестраторе конкретного клиента, не в `.env`

## Требования

### Контракт запуска

Скрипт ищет `.env` через `pwd`. Координатор **всегда запускает скрипт из корня рабочего пространства** — там же где лежит `.env`. Это стандартное поведение Claude Code.

### `.env` в корне рабочего пространства клиента

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

### `send_telegram.sh` в `skills/` рабочего пространства

Source of truth — исполняемый файл `send_telegram.sh`. Здесь не дублируем код, чтобы не расходились. Ключевые моменты:
- Конвертирует markdown → HTML: `**жирный**` → `<b>жирный</b>`, убирает `- [ ]` и `---`
- `parse_mode=HTML`
- Экранирует HTML-символы (`&`, `<`, `>`)
- Разбивка длинных сообщений по 4096 символов: hard limit Telegram. L2-промпт целится в 4000, скрипт — аварийный fallback

## Инструкция координатору

Source of truth по flow — шаг 3 в [orchestrator-meeting.md](orchestrator-meeting.md). Здесь краткая справка:

1. Субагент генерирует сводку
2. Координатор спрашивает: **"Показать в чате или отправить в Telegram?"**
3. **Показать в чате** (по умолчанию) — вывести в code block для копирования
4. **Отправить в Telegram** — выполнить `send_telegram.sh "ТЕКСТ СВОДКИ"` (скрипт из `skills/`). Проверить `"ok":true`. Если `.env` не найден или ошибка — fallback на code block

## Онбординг

Пошаговая инструкция для настройки бота новому клиенту: [clients/playbook/delivery/operations/setup_telegram_bot.md](../../../clients/playbook/delivery/operations/setup_telegram_bot.md)

## Troubleshooting

### curl к Telegram возвращает 403 (только Cowork)

**Симптом:** `send_telegram.sh` возвращает `403 Forbidden`, заголовок `X-Proxy-Error: blocked-by-allowlist`. В Claude Code CLI проблема не воспроизводится.

**Причина:** Cowork выполняет команды в sandbox-VM. Если "Allow network egress" выключен — sandbox прокси блокирует все внешние домены, включая `api.telegram.org`.

**Решение:**
1. Settings → Capabilities → Allow network egress → ON
2. Domain allowlist → All domains
3. Открыть **новую сессию** Cowork (старые не подхватывают изменение)

**Диагностика:** `env | grep -i proxy` — если в выводе есть `HTTPS_PROXY=http://localhost:3128`, sandbox фильтрует трафик.

> Подробный отчёт расследования: `clients/_inbox/cowork-telegram-debug-report.md`

## Связанные файлы

- orchestrator-meeting.md — оркестратор (ссылается на этот файл)
- L2-prompt-protocol-telegram.md — промпт генерации сводки (не затрагивается)
