---
title: Metrics — карта вертикали
updated: 2026-08-28
version: 2
---

# Metrics — карта вертикали

Карта управленческого цикла `metrics`: где лежит актуальный канон, что выверено, что под пересмотром, в каком порядке читать файлы перед работой.

## Текущая рамка

Цель вертикали — AI-аналитик базовых target metrics CEO: помощник понимает вопрос CEO, читает семантику метрик, идёт в источник, считает через детерминированный инструмент и отвечает управленчески, а не просто достаёт ячейку.

## Методология

| Файл | Статус | Роль сейчас |
|---|---|---|
| [README.md](README.md) | — | Эта карта вертикали |
| [architecture.md](architecture.md) | final | Опорный документ вертикали: линия данных, линия анализа, оркестратор, надёжность |
| [metrics-spec.md](metrics-spec.md) | final | Source of truth для формата `business-metrics.md` и `{domain}-metrics.md` |
| [extractor.md](extractor.md) | draft | Построение per-client extractor'а: контракт скилла-писателя, probe-процедура, раскладка, формат JSON-выхода, schema-hash, патологии источников |
| [use-cases.md](use-cases.md) | draft | Карта вопросов руководителя по семействам с разметкой контуров доверия; вход для дизайна метрик-скилла |

## Skills

Поставляемая часть — `plugin/skills/metrics-analysis/`:

| Файл | Статус | Роль сейчас |
|---|---|---|
| [SKILL.md](../../plugin/skills/metrics-analysis/SKILL.md) | final | Инструкция скилла: разбор запроса, чтение описаний метрик, добыча книги, форма ответа |
| [scripts/read_metrics.py](../../plugin/skills/metrics-analysis/scripts/read_metrics.py) | code | Чтение значений из книги по карте адресов: строка по меткам, ось периодов, единицы, пометки |
| [scripts/calculator.py](../../plugin/skills/metrics-analysis/scripts/calculator.py) | code | Производные: выполнение плана, отклонение, изменение к периоду, рост к прошлому году |
| [scripts/snapshot.py](../../plugin/skills/metrics-analysis/scripts/snapshot.py) | code | Кэш снимка книги вне базы клиента, свежесть по дате изменения файла |
| [business-metrics-intake.md](../../plugin/skills/metrics-analysis/business-metrics-intake.md) | final | Промпт-помощник заполнения `business-metrics.md` с CEO |

Инженерный трек — `dev/skills/metrics-analysis/`, к клиенту не едет:

| Файл | Статус | Роль сейчас |
|---|---|---|
| orchestrator-metrics.md | draft | Операционный пайплайн вертикали |
| defects.md | draft | Дефект-лист семантического слоя (30.07): 9 дефектов, 4 категории; вход для правок канона |
| connector-gsheets-mcp.md | draft | Чтение Google Sheets через Drive MCP: xlsx-выгрузка, guard-и, свежесть снимка |
| l1/runtime/ | code | Наследство серверного контура: раннер, extractor, verifier, catalog, схемы контракта. Контур снят 26.08, код покрыт 173 тестами |

## Scaffold

| Файл | Роль сейчас |
|---|---|
| [business-metrics.md](../../plugin/skills/scaffold/template/01_company/03_metrics/business-metrics.md) | Уникальный company-level шаблон базового файла метрик, собран по `metrics-spec.md` |
| [domain-metrics.md](../../plugin/skills/scaffold/template/_templates/aspects/03_metrics/domain-metrics.md) | Шаблон функционального domain-файла метрик |
| [README.md](../../plugin/skills/scaffold/template/_templates/aspects/03_metrics/README.md) | Карта metrics-aspect |
| [source/README.md](../../plugin/skills/scaffold/template/_templates/aspects/03_metrics/source/README.md) | Краткий README папки источников клиента |
| [extractors/README.md](../../plugin/skills/scaffold/template/_templates/aspects/03_metrics/extractors/README.md) | Краткий README папки per-client extractor'ов |

## Правило обновления карты

При изменении любого файла вертикали `metrics` нужно обновить эту карту, если изменилась:
- роль файла;
- статус (`draft` / `review` / `final`);
- порядок чтения;
- связь с другими файлами;
- место файла в процессе доставки клиенту.

README не дублирует содержание файлов, а фиксирует навигацию: чему верить, что читать, что под пересмотром.
