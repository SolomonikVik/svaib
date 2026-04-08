---
title: "Vocabulary transformation, feature blocks и presets — паттерны для plugin, который обслуживает разные домены одним фреймворком"
source: "https://github.com/agenticnotetaking/arscontexta"
source_type: research
status: processed
added: 2026-03-03
updated: 2026-03-06
review_by: 2026-06-06
tags: [skill-graph, arscontexta, plugin, vocabulary-transformation, feature-blocks]
publish: false
version: 2
---

# Паттерны arscontexta для plugin-архитектуры

## Кратко

Конкретные архитектурные решения из arscontexta v0.8.0, применимые к Second AI Brain plugin: vocabulary transformation (маппинг терминов на доменный язык клиента), feature blocks composition (сборка CLAUDE.md из модульных блоков), presets (параметризованные конфигурации), двухуровневые скиллы (plugin-level vs generated), hooks bundle (orient/validate/persist).

## 1. Vocabulary Transformation

Plugin не навязывает терминологию — маппит свои термины на доменный язык клиента через YAML:

```yaml
# vocabulary.yaml — пример
vocabulary:
  note: claim          # research domain
  note: reflection     # personal domain
  note: decision       # business domain
  moc: topic map       # или theme map, life area
  reduce: extract      # глагол обработки
  inbox: encounters    # или journal, задачи
```

Один framework, клиент видит свой язык. Применяется ДО генерации всех файлов. В Hub MOC arscontexta vocabulary transformation выделен как отдельная guidance area: `[[vocabulary-transformation]] — 6-level domain-native vocabulary mapping`. Шесть уровней маппинга — содержимое не вытащено, нужно дополнительное исследование.

**Для Second AI Brain:** plugin поверх нашей методологии → термины клиента. "Контекст" → "База знаний", "Скаффолд" → "Структура рабочего пространства" и т.д.

## 2. Feature Blocks Composition

CLAUDE.md клиента собирается из **17 модульных блоков** (11 обязательных, всегда включены + 6 условных, зависят от конфигурации). Секции: Philosophy, Discovery-First Design, Session Rhythm, Self Space, Memory Type Routing, Pipeline Compliance, Self-Improvement и др. Каждый блок — независимый фрагмент. Принципы:

- Vocabulary transformation ДО сборки (блоки уже на языке клиента)
- Если блок отключен — ссылки на него перемаршрутизируются
- Границы блоков невидимы в финальном тексте (когерентная проза, не конструктор)

**Для Second AI Brain:** plugin = набор блоков. Консалтинг определяет какие включить. Генерация CLAUDE.md — автоматическая.

## 3. Presets (Dimensions + Vocabulary + Categories)

Каждый пресет — конфигурация по 8 измерениям (0.0-1.0):

```yaml
# preset.yaml — пример research
dimensions:
  atomicity: 0.8       # гранулярность заметок
  processing: 0.8      # глубина pipeline
  linking: 0.7         # количество связей
  automation: 0.8      # степень автоматизации
extraction_categories: [claims, evidence, methodology-comparisons, contradictions, open-questions]
```

Два верифицированных пресета:

**personal:**
- self_space: true, personality: "warm-supportive"
- Starter MOCs: life-areas, people, goals
- Vocabulary: note → reflection, moc → life area

**research:**
- self_space: false, personality: "neutral-analytical"
- Starter MOCs: domain-overview, methods, open-questions
- Vocabulary: note → claim, moc → topic map

Примеры starter файлов для personal preset: [arscontexta-file-examples.md](arscontexta-file-examples.md).

**Для Second AI Brain:** пресеты по типу клиента (CEO, CTO, маркетинг-директор). Каждый — свой набор dimensions.

## 4. Two-Level Skills: plugin-level vs generated

arscontexta различает:
- **Plugin-level skills** (10 шт.) — управляют lifecycle: setup, health, reseed, architect. Работают ДО генерации vault
- **Generated skills** (16 шт. из skill-sources/) — рабочие инструменты: reduce, reflect, reweave. Генерируются В vault клиента

**Для Second AI Brain:** plugin содержит skill-templates, которые разворачиваются у клиента с его vocabulary и categories.

## 5. Company Graphs (эволюция)

Heinrich расширил skill graph до масштаба компании: "Company Graphs = Context Repository". Корпоративный knowledge graph как markdown: решения с альтернативами, встречи с извлечёнными claims, конкурентные анализы.

Источник: https://x.com/arscontexta/status/2026492755430474002

## 6. Hooks Bundle

Три хука покрывают базовые нужды:
- **session-orient.sh** — при старте: tree + goals + maintenance signals (10+ observations → suggest rethink)
- **write-validate.sh** — при записи: non-blocking проверка YAML schema
- **auto-commit.sh** — при записи: автокоммит (async)

## 7. Баг #14882 (верифицировано 2026-03-03)

Claude Code грузит ВЕСЬ body SKILL.md при старте, не только description. Issue OPEN с декабря 2025. Но: skill graph — это knowledge files (обычные .md), не SKILL.md. Агент читает их через Read/Grep. Баг не убивает концепцию, убивает только "100 SKILL.md файлов".

## Не исследовано

- 249 research claims в methodology/ — не прочитаны. Это ядро методологии arscontexta
- Конкретные generator templates (17 feature blocks) — содержимое не изучено
- Vocabulary transformation — 6 уровней маппинга, содержимое файла не вытащено

## Источники

- [arscontexta GitHub](https://github.com/agenticnotetaking/arscontexta) — MIT, v0.8.0, 2K+ stars
- [arscontexta.org](https://www.arscontexta.org/)
- [Heinrich: Company Graphs](https://x.com/arscontexta/status/2026492755430474002)
- [Bug #14882](https://github.com/anthropics/claude-code/issues/14882)

## Связанные файлы

- [skill-graphs.md](skill-graphs.md) — теория: что такое skill graph и зачем
- [architecture.md](architecture.md) — архитектура: Three-Space, MOC, Pipeline, Hooks
- [kernel-primitives.md](kernel-primitives.md) — 15 примитивов, presets определяют какие включены
- [arscontexta-file-examples.md](arscontexta-file-examples.md) — реальные файлы: starter MOC, goals (иллюстрация presets)
- [arscontexta-skill-anatomy.md](arscontexta-skill-anatomy.md) — 7 паттернов проектирования скиллов
- [arscontexta-architect-example.md](arscontexta-architect-example.md) — полный пример скилла /architect
- [../../cases/arscontexta.md](../../cases/arscontexta.md) — кейс arscontexta как продукт
- [../../skills/!skills.md](../../skills/!skills.md) — сводка знаний о Skills
