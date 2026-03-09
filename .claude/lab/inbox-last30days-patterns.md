---
title: "Паттерны last30days-skill → лечение проблем из rescue-log"
created: 2026-03-07
source: "mvanhorn/last30days-skill (GitHub, 3.8K stars, MIT)"
type: inbox
status: draft
related:
  - .claude/rescue-log.yml
  - .claude/lab/roadmap.md
  - .claude/lab/todo-skill.md
  - .claude/commands/svaib-lab.md
---

# Паттерны last30days-skill → лечение проблем из rescue-log

## Контекст

Исследован mvanhorn/last30days-skill — Claude Code skill для research по 8 платформам за 30 дней. 3.8K звёзд, MIT. Архитектура: Python-скрипт (параллельный сбор + scoring + dedupe) + SKILL.md (400 строк инструкций для Claude). Ключевое: критичные шаги вынесены в код (не в промпт), строгий шаблон вывода, graceful degradation.

Ниже — конкретные паттерны из last30days, которые лечат диагностированные проблемы из rescue-log.yml.

---

## Проблема 1: Process Step Skip (rescue-log, 2026-02-27)

**Симптом:** Координатор пропустил шаг "Исследовать" — сразу прыгнул к построению, не заглянул в knowledge/.

**Текущий guardrail:** Текстовый GATE в svaib-lab.md (строка 117) — 3 чекбокса перед шагом 3. Координатор может (и пропускает) его игнорировать.

### Паттерн из last30days: Phase Enforcement через код

У last30days фазы обеспечены архитектурой Python-скрипта:
- Phase 1 (discovery) → entity extraction → Phase 2 (drill-down) → scoring → rendering
- Каждая фаза возвращает data structure, следующая фаза принимает её как input
- Пропустить фазу невозможно — следующая упадёт без входных данных

### Предложение: Research Gate Script

**Идея:** Вынести шаг "Исследовать" из текста промпта в **скрипт**, который координатор ОБЯЗАН запустить перед проектированием.

**Реализация:**

```
.claude/scripts/research-gate.sh
```

Скрипт:
1. Принимает аргумент: тип помощника (skill | agent | hook | command) и тему
2. Проверяет knowledge/{тип}/ — ищет релевантные файлы по ключевым словам
3. Сканирует .claude/ на конфликты (существующие файлы с похожим именем/триггером)
4. Генерирует артефакт: `.claude/lab/research-{тема}.md` с результатами
5. Exit code 0 + файл = gate пройден

**В svaib-lab.md:** "Перед шагом 3 запусти: `bash .claude/scripts/research-gate.sh skill "тема"`. Без файла research-{тема}.md шаг 3 заблокирован."

**Почему это лучше текстового GATE:**
- Скрипт создаёт артефакт (файл) — его наличие/отсутствие проверяемо
- Результаты исследования сохраняются для будущих сессий
- Координатор не тратит контекст на чтение knowledge/ — скрипт делает предварительную фильтрацию

**Альтернатива (проще):** Вместо shell-скрипта — **skill с `context: fork`**, который запускается как субагент, читает knowledge/, сканирует .claude/, и возвращает структурированный отчёт. Координатор вызывает: `/research-gate skill "тема"`.

**Оценка сложности:** Средняя. Нужен 1 скрипт или 1 skill. Основная работа — определить что именно скрипт проверяет в knowledge/.

---

## Проблема 2: Scope Creep / Disproportionate Update (rescue-log, 2026-02-28)

**Симптом:** knowledge-research скилл предписывает полный цикл на любое обновление. Координатор тронул 4 места ради 1 строчки.

**Текущий guardrail:** Принцип пропорциональности добавлен в SKILL.md (3 теста). Работает как текстовая инструкция.

### Паттерн из last30days: Strict Output Template

У last30days формат вывода жёстко шаблонизирован:
```
"What I learned" section → Stats block (tree + emoji per source) → Invitation
```
Claude не может добавить "а ещё я тут поправил форматирование" — шаблон не предусматривает такую секцию. Scope ограничен форматом.

### Паттерн из last30days: Separation of Concerns

Python-скрипт = data collection (своя работа). SKILL.md = synthesis rules (своя работа). Скрипт не форматирует финальный текст. Claude не лезет в scoring. Каждый модуль знает свои границы.

### Предложение: Scope Zones в скиллах

**Идея:** Каждый скилл декларирует **зоны ответственности** — что он ДЕЛАЕТ и что он НЕ ТРОГАЕТ.

**Реализация в knowledge-research SKILL.md:**

```markdown
## Scope Zones

### WRITE zone (трогаю):
- Целевой файл в knowledge/ (один)

### READ-ONLY zone (читаю, не трогаю):
- README папки
- Связанные файлы (для проверки, не для правки)
- YAML-заголовки соседних файлов

### NO-TOUCH zone (не трогаю никогда):
- Другие файлы knowledge/ (кроме целевого)
- meta/, dev/, framework/
- CLAUDE.md
```

**Дополнение — Output Template:**

```markdown
## Формат вывода

Скилл возвращает ТОЛЬКО:
1. Что добавлено/изменено (цитата, 1-5 строк)
2. В каком файле
3. Нужно ли обновить README папки (да/нет + что именно)

НЕ возвращает: рефакторинг соседних файлов, обновление связей, "а ещё заметил что..."
```

**Почему это лучше принципа пропорциональности:**
- Принцип пропорциональности = абстрактное правило (надо интерпретировать)
- Scope Zones = конкретный whitelist/blacklist файлов (не надо думать)
- Output Template = нет места для лишних действий в формате ответа

**Оценка сложности:** Низкая. Добавить секции в существующие скиллы.

---

## Проблема 3 (превентивная): Post-Compaction Amnesia

**Не в rescue-log, но в таксономии rescue и в roadmap (v0.05, проблема verified foundation).**

**Симптом:** После compact/summarize координатор забывает контекст ранних сообщений.

### Паттерн из last30days: Артефакт как память

У last30days каждый запуск сохраняет briefing в `~/Documents/Last30Days/{topic}.md`. Даже если контекст потерян — артефакт на диске остаётся. Claude может перечитать его.

### Предложение: Session Artifact

**Идея:** Координатор в начале сложной задачи создаёт **session artifact** — файл с ключевыми решениями сессии.

**Реализация:**

```
.claude/lab/sessions/YYYY-MM-DD-{тема}.md
```

Содержимое:
- Цель сессии (1 строка)
- Ключевые решения (по мере принятия — дописываются)
- Текущий шаг процесса

**В svaib-lab.md:** "Если задача >3 шагов — создай session artifact. После compaction — перечитай его."

**Паттерн из last30days:** `--save-dir=~/Documents/Last30Days` — автосохранение результата каждого запуска. У нас аналог — автосохранение хода сессии.

**Оценка сложности:** Низкая. Конвенция + 2 строки в svaib-lab.md.

---

## Проблема 4 (превентивная): Graceful Degradation

**Не в rescue-log, но частая ситуация: API недоступен, файл не найден, субагент не вернул результат → координатор застревает.**

### Паттерн из last30days: Fallback Chains

Каждый источник у last30days имеет fallback:
- Reddit: ScrapeCreators → OpenAI API → skip
- X: Bird CLI → xAI API → skip
- Web: Parallel → Brave → OpenRouter → Claude WebSearch

Пропуск одного источника не блокирует весь process.

### Предложение: Fallback Paths в todo-файлах

**Реализация в todo-skill.md, шаг 2:**

```markdown
## Шаг 2. Поиск аналогов

**Primary:** Поиск в каталогах (таблица ниже)
**Fallback 1:** Если каталоги недоступны → веб-поиск "claude code skill {тема}"
**Fallback 2:** Если веб-поиск пуст → проверить только knowledge/ и .claude/
**Skip condition:** Виктор говорит "аналогов нет, делай" → пропустить, зафиксировать в session artifact
```

**Оценка сложности:** Низкая. Добавить fallback-строки в существующие todo-файлы.

---

## Сводка: приоритеты

| # | Что | Лечит | Сложность | Приоритет |
|---|-----|-------|-----------|-----------|
| 1 | Scope Zones + Output Template в скиллах | Scope Creep (#2) | Низкая | Высокий — можно сделать за 1 сессию |
| 2 | Fallback Paths в todo-файлах | Застревание | Низкая | Высокий — добавить строки |
| 3 | Session Artifact конвенция | Amnesia (#3) | Низкая | Средний — конвенция, не код |
| 4 | Research Gate (skill или скрипт) | Process Step Skip (#1) | Средняя | Средний — нужна разработка |

### Рекомендуемый порядок

**Сессия A (быстрые wins):**
1. Добавить Scope Zones в knowledge-research SKILL.md (и другие скиллы по аналогии)
2. Добавить Fallback Paths в todo-skill.md (и todo-agent.md когда появится)
3. Добавить конвенцию Session Artifact в svaib-lab.md

**Сессия B (разработка):**
4. Спроектировать и построить Research Gate skill (`context: fork`, субагент сканирует knowledge/ + .claude/)
5. Интегрировать в svaib-lab.md как обязательный шаг перед проектированием

---

## Бонус: что ещё взять из last30days (не привязано к rescue-log)

| Паттерн | Что у них | Что у нас | Потенциал |
|---------|-----------|-----------|-----------|
| Two-phase search | Phase 1 broad → entity extract → Phase 2 targeted | Одноразовый поиск | Для knowledge-research: Phase 1 поиск → извлечь ключевые термины → Phase 2 углублённый |
| Engagement scoring с log1p | Метрики не задавлены вирусным контентом | Нет скоринга | Для будущего knowledge curation |
| `.claude-plugin/` формат | plugin.json + marketplace.json | framework/plugin/ (в разработке) | Референс для упаковки нашего плагина |
| Quality benchmarking | 60+ файлов blinded comparisons | Нет бенчмарков | Для оценки качества наших скиллов (rescue-log = начало, но нужна метрика) |
| Budget management | Трекинг API costs per run, daily caps | Нет | Для watchlist/автоматических задач |
