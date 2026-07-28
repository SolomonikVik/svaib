# Coding — AI-кодинг и разработка

Среды разработки, AI-кодинг ассистенты, практики разработки с AI, UI-дизайн с AI.

**Границы:** Сюда — всё, где пишется или генерируется код/UI. НЕ сюда: платформы автоматизации без кода (-> tools/), агентные протоколы и SDK (-> agents/), скиллы как формат (-> skills/).

## Файлы

- [!coding.md](!coding.md) — сводка знаний

### Методология AI-разработки

- [ai-dev-practices.md](ai-dev-practices.md) — **синтез принципов** AI-first разработки (hub-файл: 3 принципа проектирования среды из OpenAI, Anthropic, Hashimoto; + практика микро-команд: ревью как узкое место, кросс-модельная асимметрия, anti-slop, METR)
  - [engineering-harness.md](engineering-harness.md) — детали принципа "Harness Engineering" (Hashimoto 6 шагов, OpenAI 7-phase SDLC, Anthropic данные)
  - [spec-driven-dev.md](spec-driven-dev.md) — детали принципа "Spec First": SDD как парадигма, инструменты (Spec Kit, Kiro, Tessl, OpenSpec, BMAD), schema-first контракты узлов, Agent Contracts, кейс малой команды, критика
- [ai-ready-architecture.md](ai-ready-architecture.md) — **структура кода** под AI-агентов: sinks vs pipes, честные интерфейсы, progressive disclosure в коде (Ian Bull)
- [likec4.md](likec4.md) — LikeC4: DSL «архитектура как код», синтаксис, фильтрация views, MCP, сравнение со Structurizr/D2/Mermaid C4/PlantUML C4

### Тестирование

- [testing.md](testing.md) — тестирование AI-generated кода: failure modes, TDD+AI, property-based testing, mutation testing, multi-layer verification, инструменты

### Среды и инструменты

- [claude-code.md](claude-code.md) — Claude Code: CLI, расширения, плагины, система расширения
- [agent-teams.md](agent-teams.md) — Agent Teams в Claude Code: multi-agent разработка
- [vscode-agents.md](vscode-agents.md) — VS Code Agent Sessions: unified workspace для агентов
- [n8n-claude-code.md](n8n-claude-code.md) — Claude Code + n8n: MCP-серверы, скиллы, паттерны разработки автоматизаций
- [ui-design.md](ui-design.md) — UI-дизайн с AI: workflow, генераторы, инструменты

## Связи

- [../tools/](../tools/) — сравниваешь пути автоматизации: код (здесь) vs no-code (tools)
- [../skills/](../skills/) — пишешь скилл для своей среды → формат и примеры SKILL.md в skills/
