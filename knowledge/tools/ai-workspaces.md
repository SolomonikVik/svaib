---
title: "AI-оболочки — среды для работы с AI (каталог)"
source_type: docs
status: raw
added: 2026-02-11
updated: 2026-02-11
review_by: 2026-05-11
tags: [tools, ai-workspace, shells, catalog]
publish: false
version: 2
---

# AI-оболочки — где работать с AI

## Кратко

Каталог десктопных и терминальных сред для работы с AI. Не только для разработчиков — маркетолог, руководитель, SEO-специалист могут использовать эти инструменты. Часть онтологии продукта SVAIB: клиент выбирает оболочку, мы наполняем её содержимым (Skills, Agents, контекст). Инструменты быстро обновляются — здесь фиксируем суть и ссылки, не детали фич.

---

## Каталог

### Claude Code

**Что:** CLI-инструмент Anthropic для работы с AI в терминале и IDE.
**Платформы:** macOS, Linux, Windows (WSL). Интеграция: VS Code, JetBrains.
**Модели:** Claude (Opus, Sonnet, Haiku).
**Ключевое:** Система плагинов (Skills + Commands + Agents + Hooks + MCP). Субагенты, Agent Teams. Наш основной рабочий инструмент.
**Ссылка:** https://code.claude.com
**Подробнее:** [../coding/claude-code.md](../coding/claude-code.md)

---

### Cowork

**Что:** GUI-оболочка Anthropic внутри Claude Desktop. Агентная платформа для knowledge workers (не разработчиков).
**Платформы:** macOS (research preview, январь 2026).
**Модели:** Claude.
**Ключевое:** Те же плагины что Claude Code, но через GUI. Sandboxed VM. Целевая аудитория: sales, legal, finance, marketing. Маркетплейс плагинов.
**Ссылка:** https://claude.com/blog/cowork-research-preview
**Подробнее:** [cowork.md](cowork.md)

---

### OpenCode

**Что:** Open-source AI-агент для терминала с десктопным приложением. Позиционируется как открытая альтернатива Claude Code.
**Платформы:** macOS, Windows, Linux. CLI + Desktop app + расширение VS Code/Cursor.
**Модели:** 75+ моделей — Claude, OpenAI, Gemini, локальные.
**Ключевое:** Два встроенных агента (build + plan). LSP-интеграция. Мультипровайдерность — работает с любой моделью. Open-source.
**Ссылка:** https://opencode.ai
**GitHub:** https://github.com/opencode-ai/opencode

---

### Codex (OpenAI)

**Что:** Десктопное приложение OpenAI для работы с AI-агентами. Параллельные агенты, автоматизации, worktrees.
**Платформы:** macOS (февраль 2026). CLI — кроссплатформенный.
**Модели:** OpenAI (GPT-5.2, o3, codex-1).
**Ключевое:** Multi-agent: несколько агентов работают параллельно на одном репо через worktrees. Automations — агенты работают по расписанию в фоне. Skills (Figma, Linear, deploy, PDF/docx). Результаты — в review queue.
**Ссылка:** https://openai.com/codex
**Docs:** https://developers.openai.com/codex/app/

---

### Kojori

**Что:** Десктопное AI-приложение — "второй мозг". Превращает файловую систему в knowledge base. Партнёры SVAIB.
**Платформы:** macOS, Windows.
**Модели:** Anthropic (Claude), Z.AI (GLM), Moonshot (Kimi), Openrouter (скоро).
**Ключевое:** Встроенный редактор документов (WYSIWYG, как Notion). Встроенный браузер. Маркетплейс (30+ шаблонов, слэш-команды, агенты, интеграции). Local-first — данные на машине пользователя. Ориентирован на не-разработчиков: e-commerce, маркетинг, продуктовый менеджмент.
**Ссылка:** https://kojori.ru
**llms.txt:** https://kojori.ru/llms.txt
**Доступ:** Early access через Telegram: https://t.me/tribute/app?startapp=sM22

---

### VS Code

**Что:** IDE от Microsoft, с v1.109 (февраль 2026) — полноценная multi-agent платформа.
**Платформы:** macOS, Windows, Linux.
**Модели:** Claude, Codex, Copilot — все через подписку GitHub Copilot.
**Ключевое:** Unified Agent Sessions (local/background/cloud агенты в одной панели). Параллельные субагенты. Встроенный браузер. MCP Apps (интерактивный UI в чате). Agent Skills (стандарт Anthropic, GA). Самая большая экосистема расширений.
**Ссылка:** https://code.visualstudio.com
**Подробнее:** [../coding/vscode-agents.md](../coding/vscode-agents.md)

---

## Как выбирать

| Профиль пользователя | Рекомендация |
|----------------------|-------------|
| Разработчик, терминал | Claude Code, OpenCode |
| Разработчик, IDE | VS Code + расширения, Codex |
| Руководитель, маркетолог, не-разработчик | Cowork, Kojori |
| Нужна мультимодельность (разные провайдеры) | OpenCode, Kojori |
| Нужны автоматизации по расписанию | Codex |

## Связь с продуктом SVAIB

Оболочка — это интерфейс клиента. SVAIB наполняет её содержимым:

```
КЛИЕНТ выбирает оболочку          SVAIB даёт содержимое
─────────────────────────          ─────────────────────
Claude Code / Cowork / Kojori     Skills + Agents + Онтология
OpenCode / Codex / VS Code        (подписка, см. product_vision.md)
```

Подробнее о модели подписки "Плагин": [cowork.md](cowork.md), секция "Связь с продуктом SVAIB".

## Связанные файлы

- [cowork.md](cowork.md) — Cowork подробно: плагины, pricing, связь с продуктом
- [../coding/claude-code.md](../coding/claude-code.md) — Claude Code подробно: система расширения, плагины, маркетплейсы
