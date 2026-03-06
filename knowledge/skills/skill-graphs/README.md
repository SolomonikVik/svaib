# Skill Graphs — сети файлов знаний

Архитектурный паттерн: навигация агента по знаниям отвязана от файловой структуры. Файлы связаны wikilinks, агент потребляет минимум контекста, послойно углубляясь. На примере arscontexta v0.8.0.

> Эта папка организована как пример skill graph подхода: descriptions в YAML отвечают на "зачем читать", README работает как MOC с аннотированными связями.

**Границы:** Сюда — skill graph как паттерн и архитектура. НЕ сюда: формат SKILL.md (-> [../!skills.md](../!skills.md)), конкретные скиллы проекта (-> .claude/skills/).

## Концепция

Зачем skill graph и как устроен — начни здесь:

- [skill-graphs.md](skill-graphs.md) — теория, четыре примитива, progressive disclosure. Отвечает на "зачем это вообще нужно и как работает"

## Архитектура

Как arscontexta реализует skill graph — от обзора к деталям:

- [architecture.md](architecture.md) — обзор: Three-Space, MOC hierarchy, Node, Pipeline (6Rs), Hooks, Progressive Disclosure. Читай первым, если нужно понять как устроена система
- [kernel-primitives.md](kernel-primitives.md) — 15 фундаментальных примитивов, организованных в DAG из трёх слоёв. Читай, если нужно понять из чего собирается конфигурация
- [hooks-and-sessions.md](hooks-and-sessions.md) — операционный слой: точный порядок session-orient, hooks.json, write-validate. Читай, если нужны конкретные детали реализации хуков

## Паттерны для plugin

Что переиспользовать в Second AI Brain — vocabulary, blocks, presets:

- [arscontexta-patterns.md](arscontexta-patterns.md) — vocabulary transformation (один фреймворк → язык клиента), feature blocks composition (17 модульных блоков CLAUDE.md), presets (personal, research), two-level skills

## Проектирование скиллов

Как arscontexta строит свои скиллы — паттерны и полный пример:

- [arscontexta-skill-anatomy.md](arscontexta-skill-anatomy.md) — 7 паттернов: EXECUTE NOW, фазовая архитектура, edge cases, quality gates. Читай, если проектируешь сложный скилл
- [arscontexta-architect-example.md](arscontexta-architect-example.md) — полный пример /architect (500+ строк). Все 7 паттернов в действии — reference implementation

## Примеры

Как выглядят реальные файлы arscontexta:

- [arscontexta-file-examples.md](arscontexta-file-examples.md) — node (claim-as-title), hub MOC, domain MOC, agent, starter MOC, goals. Реальные файлы из GitHub, каждый с пояснением какой элемент архитектуры иллюстрирует
