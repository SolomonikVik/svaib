---
title: "Engineering Harness — проектирование среды для AI-агентов вместо написания кода"
source: "https://mitchellh.com/writing/my-ai-adoption-journey"
source_type: article
status: processed
added: 2026-02-16
updated: 2026-02-16
review_by: 2026-05-16
tags: [ai-coding, agents, harness, engineering-practices, codex, mitchell-hashimoto]
publish: false
version: 1
---

# Engineering Harness

## Кратко

Сдвиг роли инженера: от "писать код" к "проектировать среду, в которой агенты пишут код надёжно". Термин ввёл Mitchell Hashimoto (создатель Terraform, Vagrant, Ghostty). Два направления: (1) implicit prompting — AGENTS.md с правилами, предотвращающими повторение ошибок; (2) programmed tools — скрипты для скриншотов, фильтрованных тестов, верификации. OpenAI подтвердила концепцию: команда за 5 месяцев через Codex написала ~1M строк кода (1500 PR, 0 строк вручную), оценка — 1/10 времени ручной разработки.

---

## Mitchell Hashimoto — 6 шагов AI-адопции

Источник: [My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey) (5 февраля 2026)

Автор: Mitchell Hashimoto — создатель Terraform, Vagrant, Consul (HashiCorp), сейчас делает терминал Ghostty. Не инвестирует и не консультирует AI-компании — нет конфликта интересов.

### Шаг 1: Бросить чат-бот

Чат-бот (ChatGPT, Gemini web) — плохой инструмент для кода. Полезен для разовых вопросов, но для серьёзной работы нужен **агент** — LLM с доступом к файлам, shell и HTTP. Минимум: read files + execute programs + HTTP requests.

### Шаг 2: Воспроизводить свою работу агентом

Делаешь работу вручную, потом заставляешь агента воспроизвести тот же результат. Мучительно, но формирует экспертизу:
- Разбивать сессии на чёткие задачи (не "нарисуй сову")
- Для расплывчатых запросов — отдельно планирование, отдельно исполнение
- Дать агенту способ верифицировать свою работу = он сам чинит ошибки

Важный побочный результат: понимаешь, когда НЕ стоит использовать агента — это экономит больше всего времени.

### Шаг 3: End-of-Day Agents

Последние 30 минут дня — запускай агентов на задачи:
- Deep research (обзор библиотек, анализ landscape)
- Параллельные агенты на разные идеи (не для шиппинга — для прояснения unknowns)
- Issue/PR triage (агент не отвечает — только готовит отчёт на утро)

Даёт "тёплый старт" на следующее утро вместо холодного входа в задачу.

### Шаг 4: Делегируй стопроцентные задачи

Задачи, в которых уверен что агент справится → пусть работает фоном. Ты работаешь над другим. **Выключи уведомления от агента** — context switching дороже ожидания. Сам решай, когда проверить.

Hashimoto отмечает: это контрбаланс к проблеме skill formation (Anthropic research) — навыки не формируются для делегированных задач, но продолжают формироваться для тех, что делаешь сам.

### Шаг 5: Engineer the Harness (ключевая идея)

**Когда агент делает ошибку — инженерь решение, чтобы он НИКОГДА не повторил эту ошибку.**

Два направления:

**Implicit prompting (AGENTS.md):** Для простых ошибок — обновляй AGENTS.md (или эквивалент). Каждая строка = предотвращённая ошибка. Пример: [Ghostty AGENTS.md](https://github.com/ghostty-org/ghostty/blob/ca07f8c3f775fe437d46722db80a755c2b6e6399/src/inspector/AGENTS.md).

**Programmed tools:** Скрипты для скриншотов, фильтрованных тестов, проверки результатов. Парится с AGENTS.md — агент должен знать о существовании инструмента.

### Шаг 6: Всегда держи агента запущенным

Цель: если агент не работает — спроси себя "есть ли задача для него?". Пока ~10-20% рабочего дня. Предпочитает медленные вдумчивые модели (Amp deep mode / GPT-5.2-Codex, 30+ мин на задачу), зато результат лучше. Один агент, не параллельно — баланс между deep work и babysitting.

---

## OpenAI — Harness Engineering

Источник: [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/) (13 февраля 2026)

OpenAI применила концепцию на практике в внутреннем проекте:

- Пустой репо → ~1M строк кода за 5 месяцев
- 1500 PR, 0 строк написаны вручную
- Маленькая команда: в среднем 3.5 PR на инженера в день
- Оценка: 1/10 времени по сравнению с ручной разработкой

**Ключевые уроки:**
- "Давай агенту карту, а не 1000-страничный мануал" — контекст = scarce resource, гигантский instruction file вытесняет задачу и код
- Роль инженера: разбивать цели на building blocks и промптить агента собирать их
- Парадигма: "Humans steer. Agents execute."

Также: [Unlocking the Codex harness: how we built the App Server](https://openai.com/index/unlocking-the-codex-harness/) — технические детали Codex harness (agent loop + JSON-RPC API).

---

## Связь с практиками SVAIB

Наш CLAUDE.md, AGENTS.md, скиллы (SKILL.md) — это и есть harness engineering в действии. Каждое правило в CLAUDE.md = предотвращённая ошибка. Скилл knowledge-research — формализованный workflow для агента вместо надежды что "он сам разберётся".

Принцип Hashimoto "give the agent a way to verify its work" перекликается с нашим подходом: скилл определяет и процесс, и критерии качества.

## Связанные файлы

- [!coding.md](!coding.md) — сводка по AI-кодингу
- [claude-code.md](claude-code.md) — Claude Code как основная среда разработки
- [agent-teams.md](agent-teams.md) — multi-agent разработка (шаг 6 Hashimoto масштабируется через Agent Teams)
- [../agents/!agents.md](../agents/!agents.md) — агентные паттерны
- [../skills/!skills.md](../skills/!skills.md) — Skills как компонент harness
