---
title: "ICM — Interpretable Context Methodology: оркестрация агентов через файловую структуру"
source: "https://arxiv.org/abs/2603.16021"
source_type: article
status: processed
added: 2026-04-08
updated: 2026-04-08
review_by: 2026-07-08
tags: [context-engineering, orchestration, file-structure, progressive-disclosure, stage-contract]
publish: false
version: 1
---

# ICM — Interpretable Context Methodology

## Кратко

ICM (Van Clief, McDermott, 2026) — методология оркестрации AI-агентов через структуру папок вместо программных фреймворков. Центральная идея: если промпты и контекст для каждого этапа лежат файлами в организованной структуре — не нужен фреймворк координации. Нужен один агент-оркестратор, который читает правильные файлы в правильный момент. Файловая система заменяет code-level оркестрацию: порядок папок = последовательность этапов, содержимое папки = контекст этапа, output одного = input следующего.

**Источники:**
- Статья: [arXiv:2603.16021v2](https://arxiv.org/abs/2603.16021) (28 стр., 54 ссылки, Eduba / University of Edinburgh)
- Репозиторий: [RinDig/Interpreted-Context-Methdology](https://github.com/RinDig/Interpreted-Context-Methdology) (MIT, 288 stars, 3 workspace-примера, 15 design patterns)
- Протестировано на Claude Opus 4.6 + Sonnet 4.6, 52 практика, несколько production-пайплайнов

## Пять принципов

### 1. One stage, one job
Каждый этап пайплайна делает одну вещь и пишет результат в свою папку. Как проходы компилятора: лексер → парсер → оптимизатор → кодогенератор.

### 2. Plain text as the interface
Этапы общаются через markdown и JSON. Любой инструмент, который читает текст, может участвовать. Любой человек с текстовым редактором может проверить артефакт.

### 3. Layered context loading
Агент загружает только контекст, нужный для текущего этапа. Prevention, а не compression: не грузить лишнее вместо того чтобы загрузить всё и сжимать. Ссылка на Lost in the Middle: меньше нерелевантного контекста = лучше работает модель.

### 4. Every output is an edit surface
Промежуточный результат каждого этапа — файл, который человек может открыть, прочитать, отредактировать перед запуском следующего этапа.

### 5. Configure the factory, not the product
Workspace настраивается один раз (предпочтения, бренд, стиль). Каждый прогон создаёт новый результат из той же конфигурации. Правка output чинит один прогон. Правка source чинит все будущие.

Авторы прямо ссылаются на принципы Unix 70-х: программы делают одну вещь, output одной = input другой, plain text как универсальный интерфейс. Работало тогда по тем же причинам: ограниченные ресурсы (PDP-11 — память, LLM — контекстное окно).

## Пять слоёв контекста

Ядро ICM. Агент навигирует пятислойную иерархию:

```
Layer 0: CLAUDE.md          (~800 tok)   — "Где я?" (identity workspace)
Layer 1: CONTEXT.md         (~300 tok)   — "Куда идти?" (маршрутизация задач)
Layer 2: Stage CONTEXT.md   (200-500 tok) — "Что делать?" (контракт этапа)
Layer 3: Reference material (500-2k tok) — "Какие правила?" (стабильные)
Layer 4: Working artifacts   (varies)    — "С чем работаю?" (per-run)
```

Слои 0-2 = **структурные** (routing). Слои 3-4 = **контентные** (factory/product).

### Reference vs Working (Layer 3 vs Layer 4)

Ключевое разделение: разные файлы требуют разного когнитивного задания для модели.

| | Layer 3: Reference | Layer 4: Working |
|-|---------------------|------------------|
| Меняется между прогонами? | Нет | Да |
| Примеры | voice.md, design-system.md, conventions.md | research-output.md, script-draft.md |
| Задание для модели | Впитать как ограничения (internalize) | Обработать как вход (transform) |
| Когда настраивается | При setup workspace (один раз) | При каждом прогоне |
| Аналогия | Рецепт | Ингредиенты |

Если смешать reference и working в недифференцированном контексте, модель сама должна разобраться что правило, а что данные. Структурное разделение даёт модели уже организованный контекст.

## Stage contract: Inputs / Process / Outputs

Каждый этап определяет контракт в своём CONTEXT.md:

```markdown
## Inputs
- Layer 4 (working): ../01_research/output/
- Layer 3 (reference): ../../_config/voice.md
- Layer 3 (reference): references/structure.md

## Process
Write a script based on the research output.
Follow the structure in structure.md.
Match the tone described in voice.md.

## Outputs
- script_draft.md -> output/
```

Inputs-таблица явно разделяет Layer 3 и Layer 4. Контракт заранее перечисляет что нужно — **декларативный критерий достаточности контекста**. Агент не решает сам, хватит ли — контракт это определяет.

## Токен-бюджеты

При послойной загрузке каждый этап получает 2,000-8,000 токенов. При монолитной загрузке — 40,000+, большая часть нерелевантна.

```
Staged:     ~5k токенов на этап (focused)
Monolithic: ~42k токенов (80%+ irrelevant)
```

Ссылка на Lost in the Middle (Liu et al.): в длинном контексте информация в середине теряет 20%+ точности. ICM избегает проблему архитектурно.

## Практический опыт

### U-shaped паттерн вмешательства (33 практика с измерениями)

- **Stage 1 (Research):** 92% правят output — direction-setting, креативное суждение
- **Stage 2 (Script):** 30% правят — зажат между двумя "якорями"
- **Stage 3 (Production):** 78% правят — alignment work, проверка согласованности

Средние этапы получают меньше правок: зажаты между output предыдущего этапа (направление) и reference material (ограничения).

### Non-technical users

3 человека без опыта программирования создали и запустили workspaces для 10-минутных анимированных видео. Plain-text интерфейс делает оркестрацию AI доступной без программирования.

### Edit-source principle

Два типа правок output:
1. **Креативные** — человек добавляет ценность, которую система не сгенерирует. Правка output = правильно.
2. **Диагностические** — если одно и то же правится 3 раза подряд, это debugging information: нужно править source (контракт, reference), а не output.

> "Если workspaces улучшают только output — они остаются инструментами. Если они улучшают source файлы, впитывая паттерны из правок — они становятся системами, которые становятся лучше с использованием."

## Semantic debugging (future work)

ICM даёт observability (открой папку, прочитай файлы), но не traceability. Три направления:

1. **Output provenance** — каждая секция output несёт ID, привязанный к source-инструкции. Как source maps в компиляторе.
2. **Cross-stage trace verification** — проверка что output этапа N согласован с output этапа N-2. Решение: audit file + секция Verify в контракте.
3. **Breakpoints в markdown** — "пауза" внутри этапа: показать промежуточный результат перед продолжением. Спекулятивная идея.

## Где работает и где нет

**Работает:** sequential workflows с human review, повторяемые пайплайны, content production, training materials, research analysis, policy workflows. Случаи где нужна observability by default.

**Не работает:** real-time multi-agent collaboration (нужен message-passing), high-concurrency, complex branching на основе AI-решений mid-pipeline, динамическая навигация по произвольным задачам.

## Связь с другими подходами

**arscontexta** — ICM и arscontexta решают похожую задачу (послойная загрузка контекста), но по-разному. ICM — линейный pipeline с numbered stages. arscontexta — граф связей (wikilinks, MOC), оптимизирован для неструктурированной навигации. ICM лучше для повторяемых workflows, arscontexta — для открытых вопросов. → [skill-graphs/](skill-graphs/)

**LLM Wiki (Karpathy)** — "configure the factory, not the product" из ICM близко к подходу Карпатого: правь schema, а не отдельные страницы. ICM добавляет разделение reference vs working, которого у Карпатого нет. → [llm-wiki.md](llm-wiki.md)

**AI System Files** — Layer 0 ICM (CLAUDE.md) и Layer 1 (CONTEXT.md) = конфигурационные файлы, описанные в карте AI system files. → [ai-system-files.md](ai-system-files.md)

## Связанные файлы

- [!context.md](!context.md) — сводка знаний по context engineering
- [skill-graphs/](skill-graphs/) — arscontexta: граф-подход к навигации (vs pipeline-подход ICM)
- [llm-wiki.md](llm-wiki.md) — LLM Wiki (Karpathy): связь через edit-source principle
- [ai-system-files.md](ai-system-files.md) — карта конфигурационных файлов (Layer 0-1 ICM)
- [markdown-for-llm.md](markdown-for-llm.md) — как оформлять файлы для LLM (plain text principle)
