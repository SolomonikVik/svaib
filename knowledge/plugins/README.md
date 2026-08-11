# Plugins — система расширения AI-агентов

Плагины Claude Code / Cowork: формат, спецификация, маркетплейсы, экосистема, best practices разработки. Плагин = пакет из Skills + Commands + Agents + Hooks + MCP + LSP для распространения.

**Границы:** Здесь — плагины КАК ФОРМАТ и экосистема вокруг них. Содержимое компонентов (как писать Skills, паттерны агентов, техники промптинга) — в соответствующих папках: skills/, agents/, prompting/. Конкретные продукты (Claude Code, Cowork) — в coding/ и tools/.

## Файлы

- [!plugins.md](!plugins.md) — сводка знаний
- [agent-plugins-standard.md](agent-plugins-standard.md) — Agent Plugins 1.0: вендор-нейтральный стандарт упаковки (skills + MCP), расхождения с форматом Anthropic, CLI-трансляция

## Связи

- [../skills/](../skills/), [../agents/](../agents/), [../prompting/](../prompting/) — собираешь плагин → как устроены его компоненты
- [../coding/](../coding/), [../tools/](../tools/) — понять, как среда-хост (Claude Code, Cowork) исполняет плагин
