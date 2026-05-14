---
title: Metrics — карта вертикали
updated: 2026-05-14
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

## Skills

| Файл | Статус | Роль сейчас |
|---|---|---|
| [business-metrics-intake.md](../../skills/metrics-analysis/business-metrics-intake.md) | final | Промпт-помощник заполнения `business-metrics.md` с CEO |
| [README.md](../../skills/metrics-analysis/README.md) | — | Карта skill-папки |
| [orchestrator-metrics.md](../../skills/metrics-analysis/orchestrator-metrics.md) | draft | Операционный пайплайн оркестратора: чем исполняется каждый шаг потока в проде. Приведён к `architecture.md` v2 |
| [probe_xlsx.py](../../skills/metrics-analysis/probe_xlsx.py) | code | Helper разведки xlsx — выверен, архитектурно-нейтрален |

## Scaffold

| Файл | Роль сейчас |
|---|---|
| [business-metrics.md](../../scaffold/05_metrics/business-metrics.md) | Шаблон базового файла метрик, собран по `metrics-spec.md` |
| [{domain}-metrics.md](../../scaffold/05_metrics/{domain}-metrics.md) | Шаблон функционального domain-файла метрик |
| [README.md](../../scaffold/05_metrics/README.md) | Каркас-индекс папки `05_metrics/` |
| [source/README.md](../../scaffold/05_metrics/source/README.md) | Краткий README папки источников клиента |
| [extractors/README.md](../../scaffold/05_metrics/extractors/README.md) | Краткий README папки per-client extractor'ов |

## Правило обновления карты

При изменении любого файла вертикали `metrics` нужно обновить эту карту, если изменилась:
- роль файла;
- статус (`draft` / `review` / `final`);
- порядок чтения;
- связь с другими файлами;
- место файла в процессе доставки клиенту.

README не дублирует содержание файлов, а фиксирует навигацию: чему верить, что читать, что под пересмотром.
