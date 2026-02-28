---
title: "AI-кодинг — среды разработки, AI-ассистенты и практики"
status: processed
added: 2026-01-30
updated: 2026-02-28
review_by: 2026-05-28
tags: [coding, ai-coding, ide, claude-code, index, methodology, testing]
publish: false
version: 17
---

# Coding — AI-кодинг и разработка

## Кратко

Всё, что связано с написанием кода и разработкой с помощью AI. Среды разработки (Claude Code, Cursor, VS Code), AI-кодинг ассистенты (Codex, Antigravity, GitHub Copilot), практики (vibe coding, agentic coding, TDD с AI, code review с AI), UI-дизайн (Lovable, v0, Bolt, Figma Make, Mobbin). Ключевой тренд: переход от single-agent к multi-agent разработке — Agent Teams в Claude Code (официально с февраля 2026) позволяют запускать команды агентов, работающих параллельно. Если вопрос про код, программирование, разработку, генерацию UI — ищи здесь. Не путать с tools/ (платформы автоматизации, не связанные с кодом).

## AI-кодинг инструменты

| Инструмент | Тип | Open source | Ключевое |
|-----------|-----|-------------|----------|
| **Claude Code** | CLI + VS Code ext | Нет | Наш основной. Skills, Hooks, MCP, Agent Teams |
| **Codex** (OpenAI) | Desktop app (Mac) + CLI | CLI — open source | Параллельные агенты в threads, автоматизации, встроенные скиллы |
| **Cursor** | IDE | Нет | Форк VS Code с AI, Cursor Rules |
| **Windsurf** | IDE | Нет | Ex-Codeium, Cascade (agentic assistant), Plan Mode |
| **Antigravity** | IDE | Нет | Google, agent-first |
| **Cline** | Extension | Apache 2.0 | Open source AI-агент, bring-your-own-inference, MCP |
| **GitHub Copilot** | Extension | Нет | Самый массовый, интеграция в VS Code/JetBrains |

Рынок AI-кодинг инструментов меняется быстро — данные актуальны на февраль 2026.

## Два уровня AI-кодинга

**Single-agent** — один AI-ассистент работает с разработчиком. Claude Code, Cursor, Copilot. Расширяется через Skills, Commands, Agents, Hooks.

**Multi-agent** — координатор (leader) управляет командой агентов (teammates) с ролями. Agent Teams в Claude Code (официально с февраля 2026) — агенты общаются через inbox, работают с общим task list, зависимости через blockedBy, delegation mode (Shift+Tab). Позволяет параллелить: исследование, ревью, кодинг независимых модулей. Экспериментальный, но официально документирован. Детали: [agent-teams.md](agent-teams.md).

Даже без Swarm Mode базовая параллельная работа возможна через Task tool (встроенный) — субагенты с изолированным контекстом, но без межагентной коммуникации.

**Cross-model review** — одна модель пишет код/план, другая ревьюит. Паттерн "senior review" из software engineering, переложенный на AI. Работает даже когда writer не в форме — reviewer ловит ошибки. Реализация через Claude Code Skill: Claude пишет → отправляет в OpenAI Codex → получает замечания → дорабатывает (до 3 итераций). Скилл: [codex-review](https://github.com/artwist-polyakov/polyakov-claude-skills/tree/main/plugins/codex-review/skills/codex-review). Ревьюер не привязан к Codex — завтра может быть другая модель.

## Автономные агенты и инфраструктура

**[AutoForge](https://github.com/AutoForgeAI/autoforge)** (автор Leon Van Zyl, ранее Autocoder) — долгоживущий автономный кодинг-агент на Claude Agent SDK. Двухагентная архитектура: Initializer разбивает проект на фичи, Coding Agent реализует их последовательно. SQLite для трекинга между сессиями, React-мониторинг. Multi-model (Claude, Ollama, GLM, Kimi). Наш опыт: 80% проекта через AutoForge, 20% добиваешь в Claude Code CLI. Идеален для PoC и несложных задач.

**[Sandboxed.sh](https://github.com/Th0rgal/sandboxed.sh)** — self-hosted оркестратор AI-кодинг-агентов в изолированных контейнерах (systemd-nspawn/Docker). Поддерживает Claude Code, OpenCode, Amp. Web dashboard + iOS app. Git-backed библиотека скиллов и MCP. Rust + TypeScript. MIT. Позволяет развернуть автономную фабрику агентного кодирования в облаке. Активная разработка.

## Claude Code + n8n — разработка автоматизаций через AI

Экосистема для создания n8n workflow через Claude Code. Три паттерна: (A) AI строит workflow через MCP + скиллы, (B) n8n выставляет workflow как MCP-тулы для AI (Instance-Level MCP, v1.76+), (C) n8n вызывает Claude Code через SSH/SDK. Доминант в community — czlonkowski (n8n-mcp + n8n-skills): knowledge server с документацией 1236 нод + 7 скиллов (expressions, patterns, validation, node config, JS, Python, MCP tools). Методология Spec Driven Development: спецификация → план → реализация с ручным review на каждом этапе. Честная оценка: ускоряет, но ошибки неизбежны — нужны знания n8n. Детали: [n8n-claude-code.md](n8n-claude-code.md).

## UI-дизайн

Всё про создание интерфейсов с AI: workflow, инструменты, кейсы, фишки. Проверенный подход: референсы (Mobbin) → описание текущего состояния → параллельный запуск генераторов (Lovable, v0, Bolt) → выбор лучшего → интеграция через Claude Code. Скриншоты работают лучше текстовых описаний. Новый тренд: **design-in-IDE** — Pencil.dev встраивает Figma-подобный canvas прямо в IDE, дизайн в .pen файлах (JSON) живёт в git, код генерируется через MCP по точным координатам (не по скриншотам). Детали: [ui-design.md](ui-design.md).

## Engineering Harness — проектирование среды для агентов

Сдвиг роли инженера: от "писать код" к "проектировать среду, в которой агенты пишут код надёжно". Термин Mitchell Hashimoto (создатель Terraform, Ghostty). Две формы: (1) implicit prompting — AGENTS.md с правилами, предотвращающими ошибки; (2) programmed tools — скрипты верификации. OpenAI подтвердила: команда за 5 месяцев через Codex — ~1M строк, 1500 PR, 0 строк вручную, 1/10 времени. Парадигма: "Humans steer. Agents execute." Детали: [engineering-harness.md](engineering-harness.md).

## AI Development Practices — методология AI-first разработки

Синтез принципов из индустриальных источников (OpenAI, Anthropic, Hashimoto). Три принципа проектирования среды:

1. **Spec First** — ЧТО агент должен сделать (спецификация до кода, план в файл, верификация по пунктам). Детали: [spec-driven-dev.md](spec-driven-dev.md)
2. **Context Architecture** — ГДЕ агент работает (прогрев сверху-вниз, AGENTS.md, Memory Bank, документация как ToC)
3. **Harness Engineering** — КАК среда контролирует качество (реактивный: ошибка → правило; проактивный/garbage collection: фоновые агенты чистят код). Детали: [engineering-harness.md](engineering-harness.md)

Плюс практические заметки: corrections > waiting (OpenAI), парадокс надзора (Anthropic), делегирование D/R/O (OpenAI), end-of-day agents (Hashimoto).

Индустриальные данные: OpenAI (1M строк, 0 вручную), Anthropic (+67% PRs, автономность ×2), Spotify (no code since Dec 2025). Полный синтез с источниками: [ai-dev-practices.md](ai-dev-practices.md).

## Тестирование AI-generated кода

Тестирование кода от AI-агентов требует особых подходов: AI-код имеет предсказуемые failure modes (control-flow omissions, context blindness, plausible-but-wrong). Для соло-разработчика тест-система — единственный "напарник по code review".

Ключевые подходы: TDD + AI (тест = точный промпт, снижает hallucination), Property-Based Testing (свойства вместо примеров — ловит edge cases), Mutation Testing (coverage ≠ качество, mutation score показывает реальную эффективность тестов), Multi-layer verification (deterministic → security → agentic).

Философия @ai_driven: тест-система — primary quality guarantor. Каждый баг на проде = баг тест-системы. Каждый баг-фикс = два фикса (код + тест-система).

Детали: [testing.md](testing.md).

## Связанные материалы

- [skills/superpowers.md](../skills/superpowers.md) — крупнейшая авторская библиотека скиллов для AI-кодинга (TDD, debugging, code review, субагенты). Скиллы subagent-driven-development и dispatching-parallel-agents — формализация паттернов multi-agent работы
