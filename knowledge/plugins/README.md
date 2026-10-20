# Plugins — система расширения AI-агентов

Плагины агентных харнесов: форматы, спецификации, маркетплейсы, экосистема, best practices разработки. Формат и состав распространяемого пакета зависят от хоста.

**Границы:** Здесь — плагины КАК ФОРМАТ и экосистема вокруг них. Содержимое компонентов (как писать Skills, паттерны агентов, техники промптинга) — в соответствующих папках: skills/, agents/, prompting/. Конкретные продукты (Claude Code, Cowork) — в coding/ и tools/.

## Файлы

- [!plugins.md](!plugins.md) — сводка знаний
- [cross-harness-hooks.md](cross-harness-hooks.md) — перенос Python-обработчиков: события, доверие, последний ответ и продолжение Stop.
- [codex-plugins.md](codex-plugins.md) — плагины Codex: какой манифест читается, что грузится, маркетплейсы и автообновление, доверие к хукам, один пакет для Codex и Claude Code
- [OpenCode](../coding/opencode/!opencode.md) — отдельный формат плагина V2, перенос Agent Skills и MCP, адаптация контрактов хуков.
- [Pi](../coding/pi/!pi.md) — общий адаптер Claude-поставки, исполнение Python-хуков, границы готовых расширений и обновление marketplace.
- [plugin-distribution-monetization.md](plugin-distribution-monetization.md) — публикация в каталогах Claude и OpenAI, ограничения хуков и оплаты, отличие каталога от корпоративного SaaS-маркетплейса
- [plugin-update-hook-paths.md](plugin-update-hook-paths.md) — каталоги версий и пути хуков при обновлении: риск Codex, удержание Claude Code, границы переносимости
- [agent-plugins-standard.md](agent-plugins-standard.md) — Agent Plugins 1.0: вендор-нейтральный стандарт упаковки (skills + MCP), расхождения с форматом Anthropic, CLI-трансляция

## Связи

- [../skills/](../skills/), [../agents/](../agents/), [../prompting/](../prompting/) — собираешь плагин → как устроены его компоненты
- [../coding/](../coding/), [../tools/](../tools/) — понять, как среда-хост (Claude Code, Cowork) исполняет плагин
