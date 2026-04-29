---
title: "metrics-analysis — мастерская скиллов по метрикам"
updated: 2026-04-29
version: 1
scope: product_core
priority: high
type: reference
---

# metrics-analysis

## Кратко

Мастерская промптов и процедур для работы AI-агента с метриками клиента. Запрос CEO → определение домена → готовый маршрут (если есть) → исполнение через Python (xlsx-skill) → ответ + опциональный trace.

Опирается на `framework/scaffold/metrics/` (семантика у клиента) и `framework/methodology/metrics.md` (архитектура, 6 слоёв).

## Файлы

| Файл | Тип | Что делает |
|------|-----|-----------|
| `orchestrator-metrics.md` | procedure | Полный цикл: вопрос CEO → ответ. Координатор основного чата. |
| `prompt-route-resolver.md` | prompt | (планируется) Классификатор: вопрос → готовый маршрут или думающая ветка |
| `prompt-thinking-branch.md` | prompt | (планируется) Думающая ветка: 4 фазы (план → валидация → исполнение → сборка) |

На первой стадии (1–2 клиента) — только оркестратор. Остальные артефакты выделяются по мере накопления опыта (триггеры — в methodology/metrics.md).

## Как использовать

1. CEO задаёт вопрос про метрики
2. Координатор основного чата читает `orchestrator-metrics.md` и следует процедуре
3. Процедура читает `01_metrics.md` клиента → находит домен → читает domain-файл → находит маршрут или строит думающую ветку
4. Расчёты выполняются через xlsx-skill (Cowork) поверх `source/*.xlsx`
5. Ответ возвращается CEO с опциональным trace (маршрут / файл / код)

## Связанные файлы

- `../../scaffold/metrics/` — клиентское пространство метрик (семантика + источники)
- `../../methodology/metrics.md` — архитектура, 6 слоёв, ритуалы, semantic layer
- `../../_inbox/metrics-scaffold/b1.md` — где жить числам (xlsx + Python)
- `../../_inbox/metrics-scaffold/o1.md` — структура и имена domain-файлов
- `../meeting-analysis/orchestrator-meeting.md` — образец оркестратора
