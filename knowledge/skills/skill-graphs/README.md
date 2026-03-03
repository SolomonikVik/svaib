# Skill Graphs — сети файлов знаний

Архитектурный паттерн: навигация агента по знаниям отвязана от файловой структуры. Файлы связаны wikilinks, агент потребляет минимум контекста, послойно углубляясь. На примере arscontexta v0.8.0.

**Границы:** Сюда — skill graph как паттерн и архитектура. НЕ сюда: формат SKILL.md (-> [../!skills.md](../!skills.md)), конкретные скиллы проекта (-> .claude/skills/).

## Файлы

- [skill-graphs.md](skill-graphs.md) — теория: что такое skill graph, зачем, четыре примитива, progressive disclosure
- [architecture.md](architecture.md) — архитектура: Three-Space, Hub MOC, Node, Pipeline (6 Rs), Hooks
- [arscontexta-patterns.md](arscontexta-patterns.md) — паттерны для plugin: vocabulary transformation, feature blocks, presets, two-level skills
- [arscontexta-skill-anatomy.md](arscontexta-skill-anatomy.md) — 7 паттернов проектирования скиллов: EXECUTE NOW, фазовая архитектура, edge cases, quality gates
- [arscontexta-architect-example.md](arscontexta-architect-example.md) — полный пример скилла /architect (500+ строк, все 7 паттернов в действии)
