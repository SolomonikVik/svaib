---
title: "7 паттернов проектирования скиллов: EXECUTE NOW, фазовая архитектура, edge cases, quality gates — извлечены из кода arscontexta"
source: "https://github.com/agenticnotetaking/arscontexta"
source_type: research
status: processed
added: 2026-03-03
updated: 2026-03-03
review_by: 2026-06-03
tags: [skill-graph, arscontexta, skill-design, patterns]
publish: false
version: 1
---

# Анатомия скилла arscontexta

> Как устроен отдельный скилл внутри arscontexta v0.8.0. Паттерны проектирования, применимые к любому скиллу. Верифицировано по коду на GitHub и конкретному скиллу `/architect`, 2026-03-03.

## Контекст

arscontexta — plugin для Claude Code (MIT, 2K+ stars). 26 скиллов: 10 plugin-level (setup, architect, health, ask, help, recommend, reseed, upgrade, add-domain, tutorial) + 16 generated (reduce, reflect, reweave, verify и др.). Скиллы работают поверх knowledge base из 249 файлов-claims.

**Ключевое отличие от наших скиллов:** arscontexta SKILL.md не содержит знания — содержит инструкции КАК доставать знания из внешних файлов. references/ нет вообще — вся knowledge base живёт снаружи. Скилл = навигатор по knowledge base.

Ниже — 7 паттернов, извлечённых из arscontexta и применимых к проектированию скиллов. Ссылка из [todo-skill.md](../../../.claude/lab/todo-skill.md), Шаг 3.

---

## 1. EXECUTE NOW + парсинг $ARGUMENTS

Скилл начинается с императивного блока — "начинай прямо сейчас":

```markdown
## EXECUTE NOW

**Target: $ARGUMENTS**

Parse immediately:
- If target names a specific area (e.g., "schema"): focus on it
- If target is empty: run full analysis
- If target is --dry-run: analyze but don't implement

**Execute these phases sequentially:**
1. [Phase 1]
2. [Phase 2]
...

**START NOW.**
```

**Зачем:** Императивный стиль ("делай сейчас") надёжнее описательного ("вот что можно делать"). Claude склонен "размышлять" вместо действия — EXECUTE NOW снижает эту вероятность.

**$ARGUMENTS:** встроенная переменная Claude Code. `$ARGUMENTS` — всё что после `/skillname`, `$ARGUMENTS[0]`, `$ARGUMENTS[1]` — позиционные (0-based индексация). `$1`, `$2` — алиасы. Если `$ARGUMENTS` нет в контенте SKILL.md — аргументы добавляются в конец как `ARGUMENTS: <value>`.

**Применимость:** Любой скилл. Даже простой reader-telegram выиграет от "Parse $ARGUMENTS → extract URL → fetch immediately" вместо "Usage: provide a URL".

---

## 2. Фазовая архитектура с конкретными командами

Скилл разбит на последовательные фазы. Каждая фаза содержит конкретные команды — bash one-liners для простых операций, вызовы scripts/ для сложных:

```markdown
## PHASE 3: Health Analysis

Check for a recent health report:

```bash
find ops/health/ -name "*.md" -mtime -7 | sort -r | head -1
```

If no recent report — run live check:

```bash
# Count orphans
for f in notes/*.md; do
  NAME=$(basename "$f" .md)
  LINKS=$(grep -rl "\[\[$NAME\]\]" notes/ | wc -l)
  [[ "$LINKS" -eq 0 ]] && echo "ORPHAN: $NAME"
done
```
```

**Зачем:** Конкретные команды убирают неопределённость. Claude не гадает "как проверить здоровье" — у него готовые команды. Это ландшафтное управление (принцип #6): дорого ошибиться, легко сделать правильно.

**Bash vs scripts/:** Не заменяет, а дополняет. Сложная логика (HTTP-запросы, HTML-парсинг, PDF-манипуляции) → scripts/. Простые файловые операции (find, grep, wc) → bash прямо в SKILL.md. У arscontexta — только bash (их операции файловые). У нас — оба подхода.

**Применимость:** Любой скилл. sign-pdf: "Phase 1: detect document type", "Phase 2: select preset", "Phase 3: `uv run scripts/sign_pdf.py "$1" --preset invoice`", "Phase 4: validate output".

---

## 3. Edge Cases как обязательная секция

Явные инструкции что делать когда условия неидеальные:

```markdown
## Edge Cases

### No config file
Warn: "No config found. Using defaults." Proceed with defaults.

### Small vault (<10 notes)
Note: "Graph metrics less meaningful at small scale.
Focus on capture, not structural optimization."

### MCP tools unavailable
Fall back to CLI. If CLI unavailable — grep-only fallback.
Note in report: "Research from bundled references only."
```

**Зачем:** Отличие от "Limitations" (что НЕ работает). Edge Cases — это graceful degradation: что ДЕЛАТЬ когда X. "Не работает с защищёнными PDF" vs "Если PDF защищён → спроси пароль у пользователя, если не дал → предупреди и остановись".

**Применимость:** Любой скилл. Чем больше edge cases продуманы — тем реже скилл падает без объяснения.

---

## 4. Quality Gates для output

Обязательные критерии перед отдачей результата:

```markdown
### Quality Gates for Recommendations

Every recommendation MUST have:
1. Specific file references (not "update the context file"
   but "CLAUDE.md, section X, line ~150")
2. Evidence backing — at least 2 data points
3. Research citation — at least 1 specific claim
4. Risk awareness — what could go wrong
5. Reversibility assessment — can this be undone?
6. Time estimate — concrete, not vague
7. Implementation steps — ordered, each references exact files

Reject recommendations that fail any gate.
```

**Зачем:** Формализует "готово ли". Без gate-ов Claude отдаёт первый результат. С gate-ами — проверяет себя.

**Применимость:** Для сложных скиллов (knowledge-research, architect). Для простых (reader-telegram) — упрощённый вариант: "Output must include: post text, author, date. If any missing — warn."

---

## 5. Runtime Configuration (Step 0)

Перед работой скилл читает конфиг-файлы:

```markdown
## Runtime Configuration (Step 0 — before any processing)

Read these files to configure domain-specific behavior:

1. `ops/derivation-manifest.md` — vocabulary mapping
2. `ops/config.yaml` — processing depth, automation settings
3. `ops/derivation.md` — original design intent baseline

If these files don't exist, use universal defaults and warn.
```

**Зачем:** Скилл адаптируется к контексту перед работой. Не hardcoded пути, а "прочитай конфиг → узнай как здесь устроено".

> **Уточнение (верифицировано 2026-03-03):** В реальном коде architect ссылки найдены на ops/config.yaml и ops/derivation.md. Файл ops/derivation-manifest.md в скиллах не обнаружен — vocabulary mapping может быть частью derivation.md.

**Применимость:** Для plugin клиентам — обязательно (разные клиенты, разные настройки). Для внутренних скиллов — полезно если скилл работает с разными папками/форматами.

---

## 6. Articulation Test для ссылок

Каждая ссылка на другой файл/скилл проходит проверку:

```
"A connects to B because [specific reason]"
```

Голое "see also" или "related" — нежелательно. Ссылка несёт семантику: КОГДА и ЗАЧЕМ переходить.

**Пример из arscontexta:** `"Because [[forced engagement produces weak connections]], the system relies on [[natural relevance discovery]]"` — контекст перехода в самом предложении.

**Пример для наших скиллов:** "reader-jina — fallback когда основной reader не справляется с JS-heavy сайтами" лучше чем "reader-jina — альтернативный reader".

**Применимость:** Любой скилл в секции Related Skills. Наши скиллы уже частично это делают.

---

## 7. Vocabulary Templating

Параметризация скилла для разных доменов:

```markdown
{vocabulary.notes} → folder name (papers, reflections, decisions)
{vocabulary.note} → singular (paper, reflection, decision)
{vocabulary.topic_map} → MOC reference (topic map, life area)
{vocabulary.cmd_reflect} → command name (/reflect, /ponder)
```

Один скилл, один SKILL.md — но работает в разных доменах. Setup генерирует vocabulary из разговора с пользователем.

**Применимость:** Для plugin клиентам Second AI Brain. Не для внутренних скиллов (у нас один домен).

---

## Два типа скиллов (верифицировано по коду)

Не все паттерны применяются в каждом скилле. arscontexta чётко разделяет:

| Тип | Примеры | Что есть | Чего нет |
|-----|---------|----------|----------|
| **Genesis** | setup | Quality Gates (7x), Vocabulary Templating | EXECUTE NOW, Runtime Config, Edge Cases — он СОЗДАЁТ конфиг |
| **Operational** | architect, health, recommend | Runtime Config → EXECUTE NOW → фазы → Edge Cases | Они ЧИТАЮТ конфиг, созданный setup |

Genesis-скилл конфигурирует систему. Operational-скиллы работают внутри сконфигурированной системы.

---

## Пример: скилл /architect (полный)

Самый сложный скилл arscontexta. 7 фаз: locate → read derivation → health analysis → friction scan → research consultation → generate recommendations → present to user.

Ключевые паттерны в действии:
- EXECUTE NOW с парсингом $ARGUMENTS (focus area или full system)
- Runtime Configuration (Step 0: читает 3 конфиг-файла)
- 7 фаз с конкретными bash-командами в каждой
- Quality gates: 7 обязательных критериев для каждой рекомендации
- Edge cases: no derivation, no observations, small vault, no MCP
- Invariant (= Iron Law): "Architect NEVER auto-implements"
- Evidence chains: health data + friction patterns + research claims
- MCP integration: semantic search по 249 claims с трёхуровневым fallback
- 25% meta-work budget: если рекомендация >15 минут — "defer to next session"

Полный текст скилла — 500+ строк. Виктор имеет копию (передан в сессии 2026-03-03).

---

## Источники

- [arscontexta GitHub](https://github.com/agenticnotetaking/arscontexta) — MIT, v0.8.0
- Скилл /architect — верифицирован по тексту, переданному Виктором 2026-03-03
- Субагент Explore — исследование структуры skills/ и skill-sources/, 2026-03-03

## Связанные файлы

- [arscontexta-architect-example.md](arscontexta-architect-example.md) — полный пример скилла /architect (все 7 паттернов в действии)
- [skill-graphs.md](skill-graphs.md) — теория: что такое skill graph
- [architecture.md](architecture.md) — архитектура элементов: Three-Space, MOC, Node, Pipeline, Hooks
- [arscontexta-patterns.md](arscontexta-patterns.md) — паттерны для plugin (vocabulary, presets, feature blocks)
- [../!skills.md](../!skills.md) — сводка знаний о Skills
- [../../../.claude/lab/todo-skill.md](../../../.claude/lab/todo-skill.md) — процесс создания скилла (ссылается на этот файл)
