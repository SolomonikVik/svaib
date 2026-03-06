---
title: "Реальные файлы arscontexta из GitHub — как выглядят node, MOC, agent и goals на практике"
source: "https://github.com/agenticnotetaking/arscontexta"
source_type: research
status: processed
added: 2026-03-06
updated: 2026-03-06
review_by: 2026-06-06
tags: [skill-graph, arscontexta, examples, moc, node]
publish: false
version: 1
---

# Реальные файлы arscontexta — примеры из GitHub

## Кратко

Реальные файлы из arscontexta v0.8.0, вытащенные из GitHub (2026-03-05). Каждый пример иллюстрирует конкретный элемент архитектуры: node с claim-as-title, hub MOC, domain MOC, agent, starter MOC, goals. Не шаблоны — рабочие файлы.

## Node — claim как заголовок

Иллюстрирует: [architecture.md](architecture.md) → Node. Заголовок = утверждение, которое работает в предложениях. Wikilinks в прозе несут аргументацию.

```markdown
---
description: when note titles are complete claims rather than topics, traversing wiki links reads like prose
kind: research
topics: ["[[note-design]]", "[[graph-structure]]"]
source: [[2026-01-25-build-claude-a-tool-for-thought]]
---

# title as claim enables traversal as reasoning

don't name notes like topics ("thoughts on memory"). name them like claims
("structure enables navigation without reading everything").

when you link to a claim-titled note, the link becomes part of your argument:

> "because [[structure enables navigation without reading everything]],
> we invest in wiki links even though they have maintenance overhead"

the title IS the reasoning. traversal IS thinking. since [[note titles
should function as APIs enabling sentence transclusion]], the title
functions as a typed signature.

this works because [[inline links carry richer relationship data than
metadata fields]]. the prose surrounding a link encodes WHY the linked
note matters here — "because [[X]]" is a causal claim, "since [[Y]]"
is a foundation claim, "but [[Z]]" is a tension.
```

## Hub MOC — точка входа в граф

Иллюстрирует: [architecture.md](architecture.md) → Hub MOC. Не перечисляет все файлы — показывает ландшафт, направляет внимание.

```markdown
---
description: Entry point to the Ars Contexta research substrate
type: moc
---

# index

## Research Areas
- [[graph-structure]] — how wiki-linked vaults work as graph databases
- [[agent-cognition]] — cognitive science foundations for agent-operated knowledge systems
- [[discovery-retrieval]] — progressive disclosure, description quality, findability
- [[processing-workflows]] — extraction, connection, reweaving, verification pipelines
- [[note-design]] — atomicity, prose-as-title, composability
- [[maintenance-patterns]] — condition-based maintenance, health checks
- [[design-dimensions]] — the 8 configuration axes and their interaction constraints

## Guidance Areas
- [[derivation-engine]] — how the init wizard derives configurations
- [[schema-enforcement]] — templates, validation, field evolution
- [[vocabulary-transformation]] — 6-level domain-native vocabulary mapping
- [[failure-modes]] — the 10 failure modes and domain vulnerability matrix
- [[memory-architecture]] — three-space separation
- [[multi-domain-composition]] — adding and connecting multiple knowledge domains

## Domain Examples
- [[domain-compositions]] — worked examples across 12 domains
```

## Domain MOC — навигатор внутри темы

Иллюстрирует: [architecture.md](architecture.md) → MOC. Заметки внутри — тоже claims, не topics.

```markdown
---
description: How wiki-linked vaults work as graph databases — nodes, edges, traversal
type: moc
---

# graph-structure

## Core Ideas
- [[IBIS framework maps claim-based architecture to structured argumentation]]
- [[MOC construction forces synthesis that automated generation cannot replicate]]
- [[MOCs are attention management devices not just organizational tools]]
[... 38 заметок с wikilinks и описаниями ...]

## Tensions
(Capture conflicts as they emerge)

## Open Questions
- What graph metrics predict vault health most reliably?

Topics:
- [[index]]
```

## Agent — проактивный помощник

Иллюстрирует: [arscontexta-skill-anatomy.md](arscontexta-skill-anatomy.md). Модель sonnet, guidance examples вместо жёстких правил.

```markdown
---
name: knowledge-guide
description: Proactive methodology guidance agent. Monitors note creation
  and provides real-time quality advice.
model: sonnet
---

You are a knowledge systems guide, backed by the Ars Contexta methodology.

## Your Role
- Note quality — Is this title a proper prose proposition?
- Connection opportunities — Does this new note connect to existing ones?
- MOC updates — Should this note be added to a MOC?
- Schema compliance — Are the YAML fields correct?

## Guidance Examples

Good note title:
> "Mom prefers phone calls on Sunday mornings" — works in sentences

Title needs work:
> "Phone call preferences" — topic label, not a proposition

Description suggestion:
> Your description restates the title. Try adding the mechanism or implication.

Connection suggestion:
> This note about Sunday calls might connect to
> [[direct voice contact builds trust]]
```

## Starter MOC — шаблон для нового домена (personal preset)

Иллюстрирует: [arscontexta-patterns.md](arscontexta-patterns.md) → Presets. Не пустой каркас — содержит направляющие вопросы.

```markdown
---
description: Entry point for personal reflections
type: moc
topics: []
---
# my reflections

## Explorations Needed
- What are the 3-5 life areas that matter most to you right now?
- What patterns do you notice but rarely examine?
```

## Goals — рефлексия, не таск-трекер

Иллюстрирует: [hooks-and-sessions.md](hooks-and-sessions.md) → session-orient инжектирует goals первым. Goals = зеркало намерений, не список задач.

```markdown
---
description: Tracks current goals, what you are working toward, and why it matters
type: moc
topics: ["[[index]]"]
---
# current goals

What you are reaching for right now. Goals change, and that is fine.
This is not a commitment device but a reflection surface.

## Core Ideas
Add your goals here as reflections, not tasks.

## Tensions
Sometimes goals pull against each other. That tension is worth noticing,
not resolving immediately.
```

## Связанные файлы

- [architecture.md](architecture.md) — архитектура, которую примеры иллюстрируют
- [hooks-and-sessions.md](hooks-and-sessions.md) — как session-orient использует goals и identity
- [arscontexta-patterns.md](arscontexta-patterns.md) — presets, из которых генерируются starter MOC
- [arscontexta-skill-anatomy.md](arscontexta-skill-anatomy.md) — паттерны проектирования скиллов (agent-пример)
