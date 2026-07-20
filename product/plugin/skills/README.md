---
title: "Skills — исполняемые навыки Second Value AI Brain"
updated: 2026-07-10
version: 4
scope: "product_core"
priority: high
---

# Skills

## Кратко

Скиллы, которые реально едут клиенту в составе plugin. Организация по доменам (задачам бизнеса), не по типу артефакта.

## Связанные файлы

- [../../README.md](../../README.md) — обзор продукта (пять частей)
- [../README.md](../README.md) — plugin в целом (agents/, hooks/, границы с runtime)
- [../../methodology/](../../methodology/) — методологии, из которых рождаются скиллы
- [../../methodology/ontology/entities.md](../../methodology/ontology/entities.md) — каталог сущностей (используется в промптах)
- [../../methodology/ontology/behavioral_patterns.md](../../methodology/ontology/behavioral_patterns.md) — каталог паттернов (используется в промптах)
- [../../architecture.md](../../architecture.md) — архитектура продукта

---

## Структура

По доменам. Каждый домен = папка. Внутри — файлы с префиксами по типу артефакта.

```
plugin/skills/
├── README.md                       ← этот файл
├── channels/                       ← общие каналы доставки (shared-слой, не домен)
│   └── telegram/                   ← Telegram Bot API: send_telegram.sh (plain) + send_telegram_rich.sh (rich) + SKILL.md (канон)
├── scaffold/                       ← деплой каркаса клиенту (init-brain), в разработке
│   ├── _draft_spec.md              ← черновик спеки скилла
│   └── template/                   ← сам каркас клиента (был product/scaffold/)
├── email-assistant/                ← триаж почты
├── meeting-analysis/                ← анализ встреч (пайплайн L1/L2)
│   ├── README.md                   ← пайплайн, карта файлов, как запустить
│   ├── orchestrator-meeting.md     ← оркестратор полного цикла (entity-only)
│   ├── L1-prompt-entity-extractor.md     ← выжимка бизнес-сущностей
│   ├── L1-prompt-behavior-extractor.md   ← поведение (аналитический, не в пайплайне)
│   ├── L1-prompt-behavior-extractor-v2.md ← поведение (клиентский, experimental)
│   ├── L1-procedure-chunking.md          ← чанкинг (needs-revalidation)
│   ├── L2-prompt-protocol-full.md             ← выжимка → протокол (полный)
│   ├── L2-prompt-protocol-telegram.md             ← выжимка → Telegram-сводка
│   └── L2-procedure-scaffold-update.md   ← выжимка → обновление scaffold (дельта)
└── metrics-analysis/                ← вертикаль метрик
```

---

## Конвенции именования

| Префикс | Тип | Что это |
|---------|-----|---------|
| `prompt-` | Промпт | Отдельная инструкция для LLM, одна задача |
| `skill-` | Скилл | Исполняемый навык (доставляется через .claude/skills/) |
| `agent-` | Агент | Автономный агент с логикой и состоянием |
| `hook-` | Хук | Триггер (событие → действие) |

Если в домене есть пайплайн с несколькими слоями — допустим комбинированный префикс: `L1-prompt-`, `L2-prompt-` и т.д. Слой идёт первым, тип артефакта — вторым.

---

## Жизненный цикл

```
prompt → skill → agent
```

Не обязательно проходить все стадии. Промпт может остаться промптом, если задача не требует большего. Скилл может не стать агентом, если не нужна автономность.

---

## Граница скилл / вертикаль

Скилл — атомарный помощник для одной операции (обработка встречи, подготовка summary, разбор почты). Не имеет собственных сущностей в слоях продукта.

**Папка в `skills/` не равна вертикали.** Папки в этой мастерской могут быть организованы по управленческим циклам (вертикалям) или по операциям — но скилл сам по себе вертикали не создаёт. Если у нового помощника нет своих сущностей, маршрутов памяти и процедур в слоях — это скилл, не вертикаль.

См. [../../methodology/ontology/management_cycles.md](../../methodology/ontology/management_cycles.md) и [../../architecture.md](../../architecture.md) (раздел «Вертикали управленческих циклов»).

---

## Что уже есть / что в планах

| Скилл | Статус | Примечание |
|-------|--------|-----------|
| `channels/telegram` | есть | канал доставки в Telegram (plain + rich), общий ресурс для meeting/email/др. Канон — `channels/telegram/SKILL.md` |
| `scaffold` (`init-brain`) | в разработке | спека — `scaffold/_draft_spec.md`, разворачивает `scaffold/template/` клиенту |
| `email-assistant` | есть | триаж почты |
| `meeting-analysis` | есть | пайплайн L1/L2, см. `meeting-analysis/README.md` |
| `metrics-analysis` | есть | вертикаль метрик |
| `weekly-review` | план | еженедельный ритуал: итоги → weekly_progress, новый план |
| `/today` | план | план дня: читает CLAUDE.md + 03_plan.md |
| `/week` | план | план недели: итоги прошлой → новый план |
| `/month-review` | план | анализ месяца: weekly_progress + goal + timeline |
| `/quarter-plan` | план | планирование квартала: goal + ideas + plan |

---

## Текущий этап

Ведем разработку в этой же папке (её же деплоим клиенту), при необхоимости пользуемся функционалом ветвления git, для тестирования и экспериментов.
