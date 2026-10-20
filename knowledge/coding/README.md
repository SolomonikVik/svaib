# Coding — AI-кодинг и разработка

Среды разработки, AI-кодинг ассистенты, практики разработки с AI, UI-дизайн с AI.

**Границы:** Сюда — всё, где пишется или генерируется код/UI. НЕ сюда: платформы автоматизации без кода (-> tools/), агентные протоколы и SDK (-> agents/), скиллы как формат (-> skills/).

## Файлы

- [!coding.md](!coding.md) — сводка знаний

### Методология AI-разработки

- [ai-dev-practices.md](ai-dev-practices.md) — **синтез принципов** AI-first разработки (hub-файл: 3 принципа проектирования среды из OpenAI, Anthropic, Hashimoto; + практика микро-команд: ревью как узкое место, кросс-модельная асимметрия, anti-slop, METR)
  - [engineering-harness.md](engineering-harness.md) — детали принципа "Harness Engineering" (Hashimoto 6 шагов, OpenAI 7-phase SDLC, Anthropic данные)
  - [spec-driven-dev.md](spec-driven-dev.md) — детали принципа "Spec First": SDD как парадигма, инструменты (Spec Kit, Kiro, Tessl, OpenSpec, BMAD), schema-first контракты узлов, Agent Contracts, кейсы малой команды и интегратора на ~150 человек, критика
    - [openspec.md](openspec.md) — OpenSpec: спеки-состояние и изменения-дельты, формат требований и сценариев, принципы (enablers not gates, progressive rigor, не бэкфиллить), настройка схем, когда выбирать
- [ai-ready-architecture.md](ai-ready-architecture.md) — **структура кода** под AI-агентов: sinks vs pipes, честные интерфейсы, progressive disclosure в коде (Ian Bull)
- [likec4.md](likec4.md) — LikeC4: DSL «архитектура как код», синтаксис, фильтрация views, MCP, сравнение со Structurizr/D2/Mermaid C4/PlantUML C4

### Тестирование

- [testing.md](testing.md) — тестирование AI-generated кода: failure modes, TDD+AI, property-based testing, mutation testing, multi-layer verification, инструменты

### Среды и инструменты

- [codex.md](codex.md) — Codex CLI: провайдер Responses, плагины, доверие хукам, разрешения и длинные сессии.
- [orca.md](orca.md) — Orca IDE: координация CLI-агентов, среды на задачу и восстановление долгих сессий.
- [omp.md](omp.md) — OMP: Claude marketplace, JS/TS-хуки и сохранение Python за мостом.
- [qwen-code.md](qwen-code.md) — Qwen Code: импорт Claude-пакета, command-хуки, память и ACP.
- [kimi-code.md](kimi-code.md) — Kimi Code: собственный манифест, command-хуки, агенты и обновления.
- [hermes.md](hermes.md) — Hermes: модельный контекст, shell-хуки, согласие и portable plugin subset.
- [goose.md](goose.md) — Goose: плагины, контекст хуков, HTTP MCP и обновление Git-источника.
- [aider.md](aider.md) — Aider: границы плагинов и сторонних ACP-мостов.
- [deepseek-harness.md](deepseek-harness.md) — DSH: композиции профилей, экспериментальные мосты Python-хуков, MCP/OAuth и ACP.
- [agent-runtime-contract.md](agent-runtime-contract.md) — проверка провайдера, контекста, инструментов, компакции и разрешений.
- [harness-regional-availability.md](harness-regional-availability.md) — лицензия CLI/SDK, региональные условия и независимый API.
- [OpenCode](opencode/README.md) — особенности среды, совместимость с Claude/Codex, плагины и хуки V2.
- [Pi](pi/README.md) — переиспользование Claude/Codex-поставки, Python-хуки через расширения, проверки готовых мостов и обновления.
- [claude-code.md](claude-code.md) — Claude Code: CLI, расширения, плагины, система расширения
- [third-party-models.md](third-party-models.md) — сторонние модели в харнессах Claude Code и Codex: протоколы (Messages vs Responses), шлюзы (LiteLLM, OpenRouter, claude-code-router), Agent SDK / Codex SDK / OpenAI Agents SDK, опыт svaib с Agent SDK на модели OpenAI
- [agent-teams.md](agent-teams.md) — Agent Teams в Claude Code: multi-agent разработка
- [vscode-agents.md](vscode-agents.md) — VS Code Agent Sessions: unified workspace для агентов
- [n8n-claude-code.md](n8n-claude-code.md) — Claude Code + n8n: MCP-серверы, скиллы, паттерны разработки автоматизаций
- [ui-design.md](ui-design.md) — UI-дизайн с AI: workflow, генераторы, инструменты

## Связи

- [../tools/](../tools/) — сравниваешь пути автоматизации: код (здесь) vs no-code (tools)
- [../skills/](../skills/) — пишешь скилл для своей среды → формат и примеры SKILL.md в skills/
