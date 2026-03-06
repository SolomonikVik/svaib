---
title: "15 универсальных примитивов arscontexta образуют DAG из трёх слоёв — каждый следующий зависит от предыдущих"
source: "https://github.com/agenticnotetaking/arscontexta"
source_type: research
status: processed
added: 2026-03-06
updated: 2026-03-06
review_by: 2026-06-06
tags: [skill-graph, arscontexta, kernel, primitives, dag]
publish: false
version: 1
---

# Kernel Primitives — 15 строительных блоков arscontexta

## Кратко

kernel.yaml определяет 15 примитивов, организованных в DAG (directed acyclic graph) из трёх слоёв. Каждый примитив зависит от предыдущих — нельзя включить MOC-иерархию без wikilinks. Это минимальное ядро: setup проверяет все 15 при валидации, но конкретная конфигурация может отключить часть convention/automation.

## Три слоя

### Foundation (базовые — не зависят ни от чего)

| Примитив | Что делает |
|----------|-----------|
| `markdown-yaml` | YAML frontmatter как queryable metadata |
| `wiki-links` | Связи между файлами по имени |
| `unique-addresses` | Уникальные имена файлов (без конфликтов при плоской структуре) |

### Convention (зависят от foundation)

| Примитив | Зависит от | Что делает |
|----------|-----------|-----------|
| `moc-hierarchy` | wiki-links, description-field | Hub → Domain → Topic → Node |
| `tree-injection` | — | `tree -L 3` при старте сессии |
| `description-field` | markdown-yaml | Однострочное описание в YAML для сканирования |
| `topics-footer` | markdown-yaml | Привязка node к MOC через YAML |
| `schema-enforcement` | markdown-yaml | Валидация YAML при записи |
| `self-space` | — | Отдельное пространство идентичности (self/) |
| `session-rhythm` | — | Ритм сессий: старт → работа → финиш |
| `discovery-first` | — | Сначала найди, потом читай |
| `operational-learning-loop` | — | Обучение через observations в ops/ |
| `task-stack` | — | Очередь задач в ops/ |
| `methodology-folder` | — | ops/methodology/ для operational learnings |

### Automation (зависят от convention)

| Примитив | Зависит от | Что делает |
|----------|-----------|-----------|
| `semantic-search` | description-field | Embeddings через qmd (MCP) |
| `session-capture` | session-rhythm | Автоматическая запись сессий |

## DAG-зависимости

Ключевое свойство: зависимости направленные. `moc-hierarchy` зависит от `wiki-links` и `description-field` — нельзя включить MOC без wikilinks. `semantic-search` зависит от `description-field` — embeddings работают поверх описаний.

При setup arscontexta derivation engine определяет какие примитивы нужны для конкретного домена. Все 15 проверяются при валидации, но часть convention-примитивов может быть отключена (например, `self-space` выключен в research preset).

## Связанные файлы

- [architecture.md](architecture.md) — как примитивы складываются в архитектуру (Three-Space, Pipeline, Hooks)
- [hooks-and-sessions.md](hooks-and-sessions.md) — реализация session-rhythm и session-capture через hooks
- [arscontexta-patterns.md](arscontexta-patterns.md) — presets определяют какие примитивы включены
