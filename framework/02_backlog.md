---
title: "Framework — бэклог"
updated: 2026-04-20
version: 1
scope: product_core
type: plan
---

# Framework — бэклог

## Кратко

Полный список задач направления на будущее. Источник для плана недели (weekly-planning). Задачи уже разобраны (из inbox) и ожидают выполнения. Чистится еженедельно (понедельник).

**Работа с файлом:** plan — дописывать по мере появления задач (из `_inbox/01_inbox.md` при разборе, из встреч, из инсайтов). Выполненная задача — `[x]` + перенос в [03_progress.md](03_progress.md). Задача пишется с достаточным контекстом: понятно что делать без открытия других файлов. Что сюда: конкретные задачи развития direction'а. Что НЕ сюда: сырое на разбор (→ [_inbox/01_inbox.md](_inbox/01_inbox.md)), то что делаем сейчас (→ [02_active.md](02_active.md)).

## Связанные файлы

- [01_overview.md](01_overview.md) — обзор направления
- [02_active.md](02_active.md) — что делаем сейчас
- [03_progress.md](03_progress.md) — хроника сделанного
- [_inbox/01_inbox.md](_inbox/01_inbox.md) — входящее на разбор

---

## Scaffold

- [ ] Проверка целостности scaffold
- [ ] Слияние [scaffold/principles.md](scaffold/principles.md) → [scaffold/MODEL.md](scaffold/MODEL.md)
- [ ] Перенести principles.md из `scaffold/` в `methodology/` — это принципы проектирования, не scaffold. Обновить ссылки в `scaffold/clients/README.md`, `scaffold/README.md`, `framework/README.md`
- [ ] В scaffold нет шаблона `product_vision` — нужен ли клиентам файл продуктового видения? См. [../meta/product/product_vision.md](../meta/product/product_vision.md) как референс

## Meeting analysis (аналитик встреч)

Пайплайн beta (S18, 2026-03-31). Entity-only, все файлы синхронизированы по канонической цепочке. Baseline: L1 19/20, L2 18.5/20.

- [ ] Pre-processing транскрибации: коррекция атрибуции спикеров перед выжимкой. Саша видит основную проблему в качестве транскрибации, не в выжимке (запрос АС)
- [ ] Верифицировать автообновление `team/` из результатов встречи — на этапе анализа, не по отдельной команде (идея, согласована с АС): `org_structure.md`, `glossary.md` и т.д. — создавать записи о людях, которых раньше не было
- [ ] Behavioral extractor: определиться v1 vs v2, протестировать на 2+ транскриптах, подключить к оркестратору
- [ ] Оптимизация пайплайна: L1 по ссылкам (не inline) + L2 ревизия-first (не append-only). Детали: [_inbox/task-pipeline-optimization.md](_inbox/task-pipeline-optimization.md)
- [ ] Telegram-бот / аккаунт AI для асинхронной коммуникации с клиентом (идея АС)
- [ ] **Баг в send_telegram.sh:37** — `curl -d text="..."` ломает HTML при наличии `&` в тексте (пример: `Vivo&amp;Jolly` → Telegram получает `<b>` без пары). Лечится заменой `-d text="$1"` на `--data-urlencode "text=$1"`. Обход через curl с urlencode сработал
- [ ] Разобрать обратную связь от Опилкина по аналитику
- [ ] Сборка скиллов: обернуть рабочие промпты meeting-analysis в SKILL.md формат
- [ ] FRAME-скоринг: приоритизация сущностей по значимости (отложен)
- [ ] **Runtime-скиллы meeting-analysis не самодостаточны.** `L2-prompt-protocol-telegram.md` ссылается на `../../ontology/protocol_format.md` и `L2-prompt-protocol-full.md`; `L2-procedure-scaffold-update.md` — на `L2-procedure-client-update.md`. При копировании клиенту ссылки ломаются. Правило: runtime-скиллы должны быть самодостаточны — только ссылки на клиентские папки и другие runtime-скиллы. Обнаружено при миграции клиента 14.04, у клиента почищено вручную

## Онтология / Memory / file_spec

- [ ] **Карта храма: definition of done для Second AI Brain.** Взять vision + architecture, приземлить на реальность: что конкретно должно существовать в готовом продукте. Результат — чеклист готовности, по которому можно оценивать направление. Без этого статус — счёт кирпичей без чертежа
- [ ] Inline-даты на volatile-данных: добавить в [memory/file_spec.md](memory/file_spec.md) (секция маркеров, рядом с [SOURCE]/[REF:]) и в [methodology/meeting_analysis.md](methodology/meeting_analysis.md) (требование к надстройке дельт). Формат — в `clients/_inbox/_todo_meeting_processor.md` секция «Требования к дельтам»
- [ ] Композиции Человек и Проект — раскрыть состав частей в [ontology/entities.md](ontology/entities.md) (A.13). Человек → my_profile.md + team.md. Проект → весь фреймворк вокруг проектов/подпроектов
- [ ] [architecture.md](architecture.md) «Сборки» — определить из каких сущностей состоят генерируемые файлы (A.16). При реализации понадобится маппинг

## Архитектура и форматы данных

- [ ] **Google Docs как альтернативный формат данных.** Обобщить слой «Данные» в architecture.md (Markdown → открытые данные), зафиксировать два формата scaffold (MD + GDocs), уточнить формулировку в product_vision.md, упростить onboarding для GDocs-клиентов. Технические ограничения Drive API — в инсайте (`_inbox/insights.md`, 2026-03-18)

## Плагин / runtime / инфраструктура

- [ ] **Единый пайплайн онбординга клиента (~3ч)** — scaffold, чеклист этапов, промпты. Контекст: [../clients/02_active.md](../clients/02_active.md)
- [ ] **Scheduled Tasks + Channels** — delivery-слой для клиента через Claude Code. Channels (Telegram ↔ CLI), Scheduled Tasks (cloud, без включённого компа), Telegram-плагин (официальный). Потенциально закрывает запрос АС на клоубот и заменяет Nanobot. Документация: [Channels](https://code.claude.com/docs/en/channels), [Scheduled Tasks](https://code.claude.com/docs/en/web-scheduled-tasks), [Telegram-плагин](https://github.com/anthropics/claude-plugins-official/tree/main/external_plugins/telegram), [Cloud environments](https://code.claude.com/docs/en/claude-code-on-the-web)
- [ ] **QMD — локальный семантический поиск по markdown** (MCP для Claude Code). 19k stars, Tobi Lütke. Установить, протестировать на нашем репо (570+ файлов), оценить качество vs grep. Если работает — часть онбординга клиента. Детали: [../lab/_inbox/qmd-research.md](../lab/_inbox/qmd-research.md)
