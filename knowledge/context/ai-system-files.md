---
title: "AI System Files — конфигурационные файлы для AI-ассистентов (CLAUDE.md, AGENTS.md, soul.md и др.)"
source: "https://agents.md/"
source_type: article
status: processed
added: 2026-02-28
updated: 2026-02-28
review_by: 2026-05-28
tags: [claude-md, agents-md, dotfiles, ai-config, soul-md, memory, context-engineering]
publish: false
version: 3
---

# AI System Files

## Кратко

Конфигурационные файлы, определяющие поведение AI coding-ассистентов в проектах. Две оси: **инструкции** (CLAUDE.md, AGENTS.md, GEMINI.md — "как работать с этим проектом") и **персона/память** (soul.md, identity.md, memory.md — "кто ты и что помнишь"). AGENTS.md движется к кросс-платформенному стандарту через AAIF (Linux Foundation). Все инструменты сходятся на Markdown как формате и иерархической загрузке по директориям.

Исследование проведено мультимодельно: Gemini Deep Research + Claude Research (Compass) + GPT Deep Research (февраль 2026). Ниже — синтез подтверждённых фактов.

---

## Карта файлов: кто что читает

| Инструмент | Основной файл | Формат | Импорты | Иерархия |
|---|---|---|---|---|
| **Claude Code** | `CLAUDE.md`, `.claude/rules/*.md` | Markdown | `@path` (до 5 хопов) | cwd → корень; поддиректории — lazy load |
| **OpenAI Codex** | `AGENTS.md`, `AGENTS.override.md` | Markdown + TOML (config) | Fallback-имена в конфиге | Корень → cwd; override замещает |
| **Gemini CLI** | `GEMINI.md` | Markdown + JSON (config) | `@file.md`; имя файла настраивается | Global → workspace → JIT |
| **Cursor** | `.cursor/rules/*.mdc` (legacy: `.cursorrules`) | MD + YAML frontmatter | Множество файлов + globs | Global settings + проектные правила |
| **Windsurf** | `.windsurf/rules/*.md` | Markdown | 4 режима активации | Workspace + поддиректории + до git root |
| **GitHub Copilot** | `.github/copilot-instructions.md` | MD + YAML frontmatter | `applyTo` globs | Repo + org level |
| **Junie** | `.junie/guidelines.md` | Markdown | Нет (один файл) | Только корень |
| **Aider** | `.aider.conf.yml` + `CONVENTIONS.md` | YAML + MD | `read:` ключ в конфиге | Global + проект |
| **Cline** | `.clinerules` или `.clinerules/` | Markdown | Директория + conditional rules | Global → workspace |
| **RooCode** | `.roo/rules/` + `.roomodes` | MD + YAML/JSON | Режимы + skills | Mode-specific → agent rules → general |
| **Amp** | `AGENTS.md` | MD + YAML frontmatter | `@path` с glob-паттернами | cwd → $HOME; поддиректории — lazy |
| **Devin** | `AGENTS.md` + web Knowledge | Markdown | Авто-импорт из других форматов | Trigger-based retrieval |
| **Factory** | `AGENTS.md` + `.factory/droids/` | MD + YAML frontmatter | Множество в дереве | Ближе к файлу → выше приоритет |

### Кросс-чтение: кто читает чужие файлы

| Инструмент | AGENTS.md | CLAUDE.md | GEMINI.md |
|---|---|---|---|
| GitHub Copilot | да | да | да |
| Amp | да | да (fallback) | — |
| Devin | да | да (авто-импорт) | — |
| Gemini CLI | да (через настройку) | настраивается | да |
| Codex | да | через fallback-имена | — |
| Cursor | да | — | — |
| Claude Code | нет | да | — |

Claude Code — единственный крупный инструмент, который не читает AGENTS.md нативно. Обходной путь — симлинк `ln -s AGENTS.md CLAUDE.md`.

### Три модели загрузки контекста

1. **Иерархия по директориям** — cwd → родители → поддеревья по необходимости
2. **Разделение global / project / local** (local не в git)
3. **Модульность** через директории правил и/или @imports

---

## Паттерн «Персона» (Soul / Identity)

### OpenClaw: трёхслойная архитектура

| Файл | Назначение |
|---|---|
| **SOUL.md** | Ядро личности: ценности, границы, тон. Секции: Core Truths, Boundaries, Vibe, Continuity |
| **IDENTITY.md** | Метаданные: имя, аватар, тема |
| **USER.md** | Контекст пользователя: имя, таймзона, предпочтения |
| **MEMORY.md** | Накопленные факты и паттерны |

Разделение «кто агент» (Soul) от «что агент делает» (инструкции) — архитектурный паттерн, не косметика. Позволяет ревьюить изменения в «душе» отдельно от «памяти» и ограничивать загрузку конфиденциального.

### souls.directory

Открытый каталог SOUL.md-шаблонов (~81+ персон в 8 категориях). Автор: David Dias. Примеры: Surgical Coder, Socratic Mentor, Security Auditor. API: `curl https://souls.directory/api/souls/{slug}.md`.

### Закрытые экосистемы

Ни одна mainstream-платформа не достигает уровня разделения OpenClaw:
- **ChatGPT Custom GPTs** — всё в одном поле Instructions (~8K символов)
- **Claude Projects** — три слоя (Profile, Project Instructions, Styles), но без формального разделения identity/instructions
- **Character.AI** — одно поле definition (3 200 символов)

---

## Стандартизация

### AAIF (Agentic AI Foundation)

Учреждена 9 декабря 2025 под Linux Foundation. Основатели: Anthropic, Block, OpenAI. Platinum-участники: AWS, Bloomberg, Cloudflare, Google, Microsoft. Три якорных проекта: **MCP**, **AGENTS.md**, **goose**.

### AGENTS.md как стандарт

Наиболее широко принятый формат. Формат: plain Markdown, без обязательной схемы. Рекомендуемые секции: Project Overview, Build & Test, Code Style, Architecture, Testing, Git Workflows. Поддерживается большинством инструментов (Codex, Cursor, Gemini CLI, Amp, Factory, Devin, RooCode, Windsurf, Copilot, Junie).

### Инструменты синхронизации

Для решения проблемы фрагментации (каждый инструмент — свой файл) появились:
- **block/ai-rules** — управление конфигами для 11 агентов из одного источника
- **dotagent** — парсер/конвертер для 12+ форматов
- **ruler** — дистрибуция правил в 30+ агентов

---

## Best Practices и Anti-patterns

### Эффективность context files (исследование ETH Zurich)

Исследование "Do Context Files Help?" (ETH Zurich, arxiv 2602.11988) на задачах SWE-bench:

| Сценарий | Resolve rate | Стоимость |
|---|---|---|
| Без context file | baseline | baseline |
| Developer-written | **+4%** | +20% |
| LLM-generated (/init) | **-3%** | +20% |

LLM-generated файлы дублируют то, что агент и так найдёт через rg и package.json — чистый overhead. **Исключение:** когда в репозитории нет документации (.md, docs/, примеры удалены), auto-generated файлы дают +2.7% и обгоняют developer-written — потому что заполняют пробел, а не дублируют.

Инструкции при этом работают: агенты упоминают `uv` 1.6 раза/задачу когда он в context file vs <0.01 без. Проблема не в инструкциях, а в их количестве и качестве.

### Что работает

| Принцип | Детали |
|---|---|
| **Реактивный подход** | Добавляй правило только когда агент ошибается. Не делает ошибку — не пиши правило (ETH Zurich, @nobilix) |
| **Краткость** | ~150 строк для надёжного выполнения. Instruction budget общий: system prompt инструмента + context file + задача. Каждая строка конкурирует за внимание |
| **Условные правила** | «если делаешь X — используй Y» вместо «всегда используй Y». Снижает noise для нерелевантных задач |
| **Модульность** | Дробить на маленькие файлы с условной активацией (globs, режимы). Progressive disclosure: инструкции только для части кодовой базы, в которой агент работает |
| **Бизнес-контекст > структура** | Писать про что проект, текущую стадию, нестандартные требования — не описание файловой структуры |
| **Compiler/linter > текст** | Если правило можно выразить через ESLint rule, tsconfig strict, pre-commit hook — это надёжнее текстовой инструкции |

### Anti-patterns

| Anti-pattern | Почему плохо |
|---|---|
| **Auto-generated файлы без ревизии** | /init генерирует дубликат существующей документации: -3% resolve rate, +20% стоимость (ETH Zurich) |
| **Раздувание файла** | LLM удерживают ~150–200 инструкций; при росте деградация равномерная — модель начинает игнорировать ВСЕ правила |
| **Негативные инструкции** | «Не используй X» парадоксально увеличивает вероятность использования X. Лучше: «используй Y вместо X» |
| **Дублирование README/CONTRIBUTING** | Агенты и так читают эти файлы. Сошлись, не копируй |
| **Устаревшие команды** | Сменил npm на pnpm, но не обновил dotfile → агент ломает сборку. Периодически удаляй файл целиком и смотри что реально сломается |
| **Чувствительное в always-loaded** | MEMORY.md нельзя грузить в shared contexts (утечка данных) |
| **Чужие awesome-packs** | Нет нюансов проекта, зато есть рудименты, которые модели и так знают |

### Размеры файлов (подтверждённые лимиты)

| Инструмент | Рекомендация | Hard limit |
|---|---|---|
| CLAUDE.md | <150 строк | Нет (200K token context) |
| AGENTS.md (Codex) | — | **32 KiB** combined |
| GEMINI.md | <10K слов | Настраивается |
| Cursor Rules (.mdc) | <500 строк на файл | Нет |
| Windsurf Rules | — | **12 000 символов** на файл |

### Monorepo: паттерн организации

```
repo/
├── AGENTS.md              # Общие правила
├── packages/
│   ├── frontend/
│   │   └── AGENTS.md      # React-конвенции
│   └── backend/
│       └── AGENTS.md      # API-паттерны
├── agent_docs/            # Детальные документы (по ссылке)
└── CLAUDE.local.md        # Персональные настройки (в .gitignore)
```

---

## Архитектура памяти через файлы

### Спектр уровней памяти

| Уровень | Тип | Пример | Инфраструктура |
|---|---|---|---|
| **0 — Статические инструкции** | Написаны человеком, загружаются дословно | CLAUDE.md, AGENTS.md | Ноль |
| **1 — Авто-память** | Пишет агент, загружается при старте | Claude MEMORY.md, Windsurf Memories | Ноль (локальные файлы) |
| **2 — Файлы + семантический поиск** | Markdown + векторный индекс | OpenClaw memsearch (BM25 + vector) | Локальный embeddings |
| **3 — Внешние memory API** | Память вне контекстного окна | Mem0 | Облачный сервис |
| **4 — Темпоральные графы** | Entity-relationship с временными метками | Graphiti/Zep | Neo4j/FalkorDB + MCP |

Файлы — «нулевой уровень» памяти (аудируемость, git-diff, ручная правка). Индексация и графы — надстройки, но source of truth остаётся в редактируемых файлах.

### Сравнение: Claude Code vs OpenClaw

| Параметр | Claude Code | OpenClaw |
|---|---|---|
| **Где хранится** | `~/.claude/projects/<id>/memory/` | Workspace: `memory/` |
| **Структура** | MEMORY.md (индекс) + topic-файлы | Дневные логи `YYYY-MM-DD.md` + MEMORY.md (curated) |
| **Автозагрузка** | Первые 200 строк MEMORY.md | Сегодня + вчера |
| **Поиск** | Нет нативного | Гибридный BM25 + vector |
| **Безопасность** | CLAUDE.local.md в .gitignore | MEMORY.md не грузится в shared contexts |

### Память в других инструментах

- **Gemini CLI:** `/memory add` дописывает в глобальный `~/.gemini/GEMINI.md`
- **Windsurf:** Cascade Memories — автогенерация, привязка к workspace
- **Cline:** Memory Bank — директория `memory-bank/` с файлами projectBrief, activeContext, systemPatterns
- **Cursor:** Memories (авто из чатов) + Notepads (beta) + паттерн Memory Bank от сообщества

---

## Наблюдаемые тренды

**Гибридная конвергенция:** AGENTS.md становится универсальным базовым слоем (аналог `.editorconfig`), а tool-specific директории (`.claude/rules`, `.cursor/rules`, `.windsurf/rules`) сохраняются для продвинутых функций.

## Открытые проблемы

| Проблема | Суть |
|---|---|
| **Конфликты правил** | CLAUDE.md запрещает X, AGENTS.md рекомендует — нет протокола приоритетов. Copilot признаёт: выбор **недетерминирован** |
| **Версионирование памяти** | MEMORY.md в git = шум в коммитах; вне git = потеря командного контекста |
| **Безопасность** | Prompt injection через конфиги: 40–84% success rate (Liu et al., 2025). CVE-2025-59944 — RCE в Cursor. Memory poisoning через PR |

---

## Экосистема и каталоги

| Ресурс | Что делает |
|---|---|
| [cursor.directory](https://cursor.directory) | Каталог Cursor-правил с голосованием |
| [awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) | Курированные примеры .cursorrules |
| [souls.directory](https://souls.directory) | Каталог SOUL.md-шаблонов (~81+ персон) |
| [SkillsMP](https://skillsmp.com) | Маркетплейс agent skills (SKILL.md) |
| [10xRules.ai](https://10xrules.ai) | Генерация AI coding rules из 100+ фреймворков |
| [block/ai-rules](https://github.com/nicepkg/ai-rules) | SSOT-менеджер для 11 агентов |
| [dotagent](https://github.com/paulrobello/dotagent) | Парсер/конвертер 12+ форматов |

---

## Источники

- [AGENTS.md — спецификация](https://agents.md/) — официальная документация стандарта
- [AAIF (Linux Foundation)](https://aaif.io/) — Agentic AI Foundation
- [souls.directory (GitHub)](https://github.com/thedaviddias/souls-directory) — каталог SOUL.md-шаблонов
- [ETH Zurich "Do Context Files Help?" (2025)](https://arxiv.org/abs/2602.11988) — эффективность context files на SWE-bench
- [Рефат @nobilix — разбор исследования](https://t.me/nobilix/229) — реактивный подход, практические рекомендации
- [Liu et al. "Your AI, My Shell" (2025)](https://arxiv.org/abs/2505.06554) — безопасность AI конфигов

## Связанные файлы

- [!context.md](!context.md) — сводка по Context Engineering, RAG, Memory
- [agent-memory.md](agent-memory.md) — 5 архитектур памяти AI-агентов (спектр уровней 0-4 из этого файла дополняет карту)
- [search-mechanics.md](search-mechanics.md) — как Claude Code, Cursor, Claude Projects ищут файлы
- [markdown-for-llm.md](markdown-for-llm.md) — оптимизация Markdown для LLM и RAG
- [../tools/openclaw.md](../tools/openclaw.md) — OpenClaw: пример архитектуры с Soul/Identity/Memory
- [../coding/claude-code.md](../coding/claude-code.md) — Claude Code: фичи, CLAUDE.md, субагенты
- [../plugins/!plugins.md](../plugins/!plugins.md) — экосистема плагинов (пересечение с маркетплейсами)
