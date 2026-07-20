---
title: "arscontexta — Claude Code плагин для генерации персональных knowledge systems"
source: "https://github.com/agenticnotetaking/arscontexta"
source_type: repo
status: processed
added: 2026-02-21
updated: 2026-02-21
review_by: 2026-05-21
tags: [second-brain, skill-graph, claude-code-plugin, knowledge-base, markdown, competitor]
publish: false
version: 1
---

# arscontexta — персональный Second Brain как Claude Code плагин

## Кратко

arscontexta — Claude Code плагин от Heinrich (@arscontexta), который через разговор генерирует персональную систему знаний (knowledge base / skill graph). Пользователь описывает как думает и работает — плагин выводит полную когнитивную архитектуру. На выходе: markdown-файлы, которыми пользователь владеет. Первая публичная реализация паттерна [Skill Graphs](../context/skill-graphs/skill-graphs.md) в виде готового продукта. Резонанс: 6.7K лайков, 2.3M просмотров (февраль 2026). Лицензия: MIT.

Движется в том же направлении, что и SVAIB: персональная AI-инфраструктура на базе markdown, данные у пользователя.

## Что делает

Через conversational derivation engine (не шаблон, а рассуждение от первых принципов) создаёт:

- **Markdown-based vault** с wiki-linked заметками, формирующими traversable knowledge graph
- **Processing pipelines** для извлечения инсайтов, поиска связей, поддержания качества
- **Automation hooks** для enforce структуры при записи и capture session state
- **Navigation maps** на уровне hub, domain и topic
- **Domain-native templates** с schema validation
- **Документацию**, объясняющую систему в словах пользователя

## Архитектура: Three-Space Model

Каждая сгенерированная система делится на три пространства:

| Пространство | Что внутри | Темп роста |
|---|---|---|
| **self/** | Идентичность агента, методология, цели | Медленный |
| **notes/** | Граф знаний, основной контент | Стабильный еженедельный |
| **ops/** | Операционное состояние, очереди, сессии | Флуктуирующий |

Разделение инвариантно — сохраняется даже когда имена папок адаптируются под конкретный домен.

## Pipeline обработки: 6 Rs

Расширение Cornell Note-Taking:

| Фаза | Что делает |
|------|-----------|
| **Record** | Зафиксировать |
| **Reduce** | Извлечь инсайты |
| **Reflect** | Найти связи |
| **Reweave** | Обновить старые заметки в свете нового |
| **Verify** | Проверки качества |
| **Rethink** | Оспорить допущения |

Каждая фаза запускает свежего субагента для оптимального контекстного окна.

## Что внутри репо

| Компонент | Описание |
|-----------|---------|
| **10 skills** | setup, help, tutorial, ask, health, recommend, architect, reseed, upgrade, add-domain |
| **17 feature blocks** | Composable генераторы |
| **249 research claims** | Методологическая база: Zettelkasten, Cornell, когнитивная наука, graph theory, agent architecture |
| **kernel.yaml** | 15 системных примитивов |
| **Subagent orchestration** | Агент для обработки знаний |
| **Platform adapters** | Адаптеры для Claude Code и shared |
| **Presets** | Pre-validated конфигурации (research preset и др.) |

Технические требования: Claude Code v1.0.33+, `tree`, `ripgrep`. Опционально: `qmd` для semantic search.

## Интересные идеи

- **6 Rs pipeline** — формализованный цикл обработки заметок: Record → Reduce → Reflect → Reweave → Verify → Rethink
- **Three-space model** — чёткое разделение identity/content/operations
- **Derivation engine** — генерация системы из разговора, а не из шаблона
- **kernel.yaml** — 15 примитивов как минимальное ядро

## Источники

- [GitHub: agenticnotetaking/arscontexta](https://github.com/agenticnotetaking/arscontexta)
- [Твит с анонсом (6.7K likes)](https://x.com/arscontexta/status/2023957499183829467)
- [Статья: Skill Graphs](https://x.com/arscontexta/status/2023957499183829467) — концепция, на которой построен arscontexta

## Связанные файлы

- [../context/skill-graphs/skill-graphs.md](../context/skill-graphs/skill-graphs.md) — Skill Graphs: концепция, которую arscontexta реализует
- [../plugins/!plugins.md](../plugins/!plugins.md) — Плагины Claude Code: формат, экосистема
- [../context/!context.md](../context/!context.md) — Context engineering, RAG, Memory (пересечение по архитектуре памяти)
- [../context/agent-memory.md](../context/agent-memory.md) — Архитектуры памяти AI-агентов (three-space model как вариант)
