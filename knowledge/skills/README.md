# Skills — Исполняемые инструкции для AI

Формат SKILL.md, принципы проектирования, экосистема, библиотеки скиллов.

**Границы:** Сюда — скиллы как формат и методология. НЕ сюда: конкретные скиллы проекта svaib (-> .claude/skills/), техники промптинга без структуры SKILL.md (-> prompting/).

## Файлы

- [!skills.md](!skills.md) — сводка знаний (формат, принципы, экосистема)
- [superpowers.md](superpowers.md) — Superpowers: крупнейшая авторская библиотека скиллов
- [skill-tooling.md](skill-tooling.md) — Инструменты lifecycle: линтинг (agnix), валидация (ccgg), маршрутизация (showcase, pipeline), автогенерация (Claudeception), quality gates
- [skill-activation.md](skill-activation.md) — Механика активации: надёжность, hooks, стратегии
- [last30days-skill.md](last30days-skill.md) — last30days: кейс Python-heavy архитектуры (code-enforced phases, fallback chains, strict output template)

## Связи

- [../agents/](../agents/) — скиллы как один из инструментов агентных систем
- [../plugins/](../plugins/) — скилл как компонент плагина (упаковки)
- [../prompting/](../prompting/) — содержимое скилла = промпт-инжиниринг в структуре SKILL.md
