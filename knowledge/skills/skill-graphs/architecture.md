---
title: "Архитектура Skill Graph — как устроены элементы"
source: "https://github.com/agenticnotetaking/arscontexta"
source_type: research
status: processed
added: 2026-03-03
updated: 2026-03-03
review_by: 2026-06-03
tags: [skill-graph, architecture, arscontexta, progressive-disclosure]
publish: false
version: 3
---

# Архитектура Skill Graph

> Как устроены элементы skill graph на примере arscontexta v0.8.0. Теория и зачем — в [skill-graphs.md](skill-graphs.md). Паттерны для plugin — в [arscontexta-patterns.md](arscontexta-patterns.md).

## Three-Space Architecture

Весь vault делится на три пространства с разной скоростью роста:

| Space | Что внутри | Рост | Загрузка |
|-------|-----------|------|----------|
| **self/** | Идентичность агента: identity.md, methodology.md, goals.md | Медленный (десятки файлов) | Полная при старте |
| **notes/** | Knowledge graph: атомарные заметки + MOC | Стабильный (10-50 файлов/нед) | Progressive disclosure |
| **ops/** | Операционка: очередь задач, сессии, здоровье графа | Флуктуирующий | Точечная, по запросу |

**Зачем разделение:** self/ — что агент знает о себе (меняется редко). notes/ — что агент знает о предметной области (растёт). ops/ — что агент делает прямо сейчас (меняется постоянно). Смешение трёх пространств ведёт к хаосу: goals теряются в заметках, задачи путаются со знаниями.

---

## Hub MOC (index.md) — точка входа

В терминологии arscontexta `notes/index.md` — это **Hub MOC**: верхний уровень иерархии MOC, точка входа в граф. Агент читает его первым. Hub MOC не перечисляет все файлы — показывает ландшафт и направляет внимание.

```markdown
# domain-name

{1 абзац: философия, зачем эта область}

## Synthesis
Как части связаны (развёрнутые аргументы):
- [[argument-1]] — описание в одно предложение
- [[argument-2]] — описание

## Topic MOCs
Домен разбивается на подобласти:
- [[topic-moc-1]] — описание
  - [[sub-topic]] — описание
- [[topic-moc-2]] — описание

## Cross-Domain Claims
Связи с другими доменами:
- [[claim]] — как связано

## Explorations Needed
Открытые вопросы, пробелы в знаниях
```

**Иерархия MOC:** Hub MOC (index.md) → Domain MOC → Topic MOC → Node. Hub MOC показывает домены, Domain MOC показывает темы внутри домена, Topic MOC — конкретные файлы-nodes внутри темы.

---

## Node — атомарный файл знания

**Один файл = одно законченное утверждение (claim), техника или концепция.** Файл самодостаточен — понятен без чтения других файлов.

```markdown
---
description: "One sentence adding context beyond the title (~150 chars)"
type: insight | pattern | preference | fact | decision | question | tension
status: preliminary | open | active | archived
topics: ["[[parent-topic-moc]]"]
---

Prose body. Wikilinks встроены в предложения:

"Because [[forced engagement produces weak connections]], the system
relies on [[natural relevance discovery]] rather than mandatory linking."

Каждая [[ссылка]] внутри предложения — агент видит КОНТЕКСТ
перехода: когда и зачем идти в другой файл.

## Topics
- [[parent-topic-moc]]
```

**Ключевые свойства:**
- `description` в YAML — агент сканирует ripgrep-ом (`rg 'description:'`) без чтения body
- Wikilinks в прозе, НЕ списком в конце — ссылка несёт семантику предложения
- type и status — для фильтрации (`rg 'type: tension'` → все противоречия)

---

## MOC — Map of Content

**Навигатор кластера.** Организует группу nodes в навигируемую подтему.

```markdown
---
description: "How agents navigate and retrieve from knowledge graphs"
type: moc
---

# Discovery & Retrieval

Overview paragraph: что объединяет этот кластер.

## Core Ideas
- [[progressive-disclosure-layers]] — агент потребляет информацию послойно
- [[yaml-as-query-layer]] — frontmatter как queryable database
- [[semantic-search-complements-links]] — embeddings находят то, что links пропускают

## Open Questions
- Как масштабировать навигацию при 500+ файлов?
```

**Правила жизненного цикла** (эвристики, пороги зависят от домена):
- Создавать при накоплении связанных заметок в кластере (reference рекомендует ~20+; при меньшем пороге — риск MOC Sprawl)
- Разделять (split) при явных подгруппах внутри MOC
- Объединять (merge) при перекрытии малых MOC
- Каждая запись в Core Ideas = ссылка + контекстная фраза (не голый список)

**Пример:** arscontexta (249 файлов): 7 domain MOC (graph-structure, agent-cognition, discovery-retrieval, processing-workflow и др.), каждый может содержать sub-MOC.

---

## Wikilinks — семантические связи

**Ссылка `[[name]]` внутри предложения, НЕ отдельным списком.** Агент видит связь в контексте и понимает *когда* переходить.

**Два режима размещения:**

1. **Inline** (приоритет): ссылка внутри предложения
   ```
   "Because [[anxiety follows skipped routines]], structure matters more than flexibility."
   ```

2. **Footer**: группировка в конце с дескриптором отношения
   ```
   [[note-title]] — extends this by adding temporal dimension
   [[other-note]] — contradicts: claims opposite effect under stress
   ```

**Типы отношений** (конвенция оформления, не инвариант kernel): extends, foundation, contradicts, enables, example-of.

**Articulation test** (рекомендуемая практика): каждая ссылка должна пройти проверку: "[[A]] connects to [[B]] because [specific reason]". Голое "related" или "see also" — нежелательно.

**Отличие от markdown links:** `[[name]]` резолвится по имени файла (без пути). Markdown link `[text](path)` требует путь. Wikilinks проще для плотных графов — не нужно помнить структуру папок.

---

## Processing Pipeline — 6 Rs

Цикл жизни знания в skill graph (расширение Cornell Note-Taking):

| Фаза | Команда | Что делает |
|------|---------|-----------|
| **Record** | inbox capture | Сырой материал без трения: ссылка, цитата, мысль |
| **Reduce** | `/reduce` | Извлечение structured insights. Категоризация ПЕРЕД фильтрацией |
| **Reflect** | `/reflect` | Поиск связей: MOC navigation + semantic search. Articulation test на каждую связь |
| **Reweave** | `/reweave` | Backward pass: обновление СТАРЫХ заметок новым контекстом. "Если бы я писал это сегодня — что бы изменилось?" |
| **Verify** | `/verify` | Quality assurance: schema, links, descriptions |
| **Rethink** | `/rethink` | Челлендж допущений системы. Запускается при накоплении tensions |

**Ключевой принцип:** каждая фаза запускается в **отдельном субагенте** (fresh context). Это предотвращает context contamination — каждый этап работает в "smart zone", не тащит мусор предыдущего.

**Ralph (оркестратор):** чистый оркестратор, НИКОГДА не выполняет работу сам. Спавнит субагентов через Task tool. Параллельный режим: до 5 workers + cross-connect validation pass. Subagent count == tasks processed — иначе process failure.

---

## Hooks — enforcement

В `hooks/hooks.json` arscontexta v0.8.0 настроены **3 hook-команды** (хотя README упоминает 4 — session capture реализован внутри session-orient.sh). Покрывают orient → validate → persist:

| Hook | Событие | Что делает | Timeout |
|------|---------|-----------|---------|
| **session-orient** | SessionStart | Инжектит: tree vault, goals.md, identity.md, methodology.md + maintenance signals: observations ≥10 → suggest /rethink, tensions ≥5 → suggest /rethink, sessions ≥5 → suggest /remember --mine-sessions, inbox ≥3 → suggest /reduce, methodology staleness ≥30 дней → suggest update. Также создаёт session record в ops/ | 10s |
| **write-validate** | PostToolUse(write) | Проверяет YAML: есть ли description, topics, корректные `---`. Non-blocking (warn, don't block). Возвращает additionalContext | 5s |
| **auto-commit** | PostToolUse(write) | Автокоммит после записи в vault. Async | 5s |

**Принцип:** hooks — enforcement, не intelligence. Они проверяют и сигнализируют, не принимают решения.

---

## Progressive Disclosure — как агент читает граф

5 уровней, от дешёвого к дорогому:

```
1. File tree + self/ (session-orient hook: `tree -L 3 -P '*.md'` + identity.md, methodology.md, goals.md)
2. YAML descriptions (`rg '^description:' notes/` — сканирование без чтения body)
3. MOC hierarchy (Hub → Domain → Topic — навигация с аннотированными ссылками)
4. Wiki-link traversal (inline-ссылки в прозе — переход к связанным nodes по необходимости)
5. Full content (полное содержимое файла)
+ Semantic search через qmd (параллельный канал, не часть иерархии)
```

> Верифицировано по коду arscontexta на GitHub, 2026-03-03. Heading outlines (предыдущая версия) — в коде не реализован как отдельный слой. Index.md как файл не существует — роль входной точки играет tree + self/.

**Правило:** агент останавливается на том уровне, который отвечает на вопрос. Не грузит всё.

**Ограничение (баг #14882, OPEN):** для файлов SKILL.md progressive disclosure не работает — Claude Code грузит полный body при старте сессии. Но skill graph — это knowledge files (.md), не SKILL.md. Агент читает их через Read/Grep — progressive disclosure работает.

---

## Derivation, not Templating

arscontexta не предлагает шаблоны — рассуждает из исследовательских принципов о потребностях конкретного домена. Setup (6 фаз, ~20 мин): detection → understanding (2-4 разговорных хода) → derivation (маппинг на 8 dimensions с confidence scoring) → proposal → generation → validation (15 kernel primitives).

**8 dimensions конфигурационного пространства** (по reference/presets): Atomicity, Organization, Linking, Processing, Session, Maintenance, Search, Automation. Каждый — шкала 0.0-1.0.

Отдельно от dimensions настраиваются: self-space (вкл/выкл), personality, vocabulary (маппинг терминов), extraction_categories (доменные категории). Это фичи/блоки, а не оси derivation.

---

## Источники

- [arscontexta GitHub](https://github.com/agenticnotetaking/arscontexta) — MIT, v0.8.0, 2K+ stars
- [arscontexta.org](https://www.arscontexta.org/)
- [Bug #14882](https://github.com/anthropics/claude-code/issues/14882) — progressive disclosure для SKILL.md не работает

## Связанные файлы

- [skill-graphs.md](skill-graphs.md) — теория: что такое skill graph и зачем
- [arscontexta-patterns.md](arscontexta-patterns.md) — паттерны для plugin-архитектуры
- [../!skills.md](../!skills.md) — сводка знаний о Skills
- [../../context/!context.md](../../context/!context.md) — сводка context engineering (progressive disclosure, навигация — контекстные паттерны)
