---
title: "Context Graphs — институциональная память решений организации (Foundation Capital)"
source: "https://foundationcapital.com/context-graphs-one-month-in/"
source_type: article
status: processed
added: 2026-02-16
updated: 2026-02-16
review_by: 2026-05-16
tags: [context-graphs, decision-traces, agent-trajectories, enterprise-ai, memory]
publish: false
version: 1
---

# Context Graphs

## Кратко

Context Graph — институциональная память о том, КАК организация принимает решения. Не "что произошло" (CRM/ERP), а ПОЧЕМУ: какие исключения применили, какой прецедент учли, кто одобрил и зачем. Концепция Foundation Capital (Ashu Garg, Jaya Gupta), январь 2026. Стала одной из самых обсуждаемых идей в AI — циркулировала в Slack OpenAI и Anthropic. Ключевое понятие: "decision traces" — записи рассуждений за решениями, которые накапливаются в queryable граф. Агенты создают traces автоматически, проходя по системам (траектории). Компании: Maximor (финансы), PlayerZero (production engineering), Regie (demand gen), Glean, Cognition.

---

## Суть концепции

**Проблема.** Enterprise software хорошо записывает результаты (цена, тикет, скидка), но не reasoning за ними. Какие исключения применили? Какой прецедент сработал? Кто одобрил и почему? Этот контекст живёт в Slack-тредах, разговорах, головах людей.

**Decision traces** — недостающие записи reasoning за решениями. Со временем они накапливаются в context graph: живую, queryable карту того, как организация принимает решения.

**Тезис Foundation Capital:** Context graphs определят следующее поколение enterprise software. Прошлое поколение владело данными (Salesforce — клиенты, Workday — сотрудники, SAP — операции). Следующее будет владеть reasoning layer — связью между данными и действиями.

> "The last generation of software captured *what* happened. This generation will capture *why*."

---

## Ключевые идеи

### Decision traces — компаундящий актив

Модели commoditize. Но high-fidelity запись того, как организация работает — proprietary и трудно копируемая. Кто начнёт собирать traces сейчас, получит компаундящий актив.

Decision traces можно захватить только будучи "present at decision time" — ретроспективно не восстановишь. Поэтому стартапы имеют преимущество: агенты живут в execution path и захватывают traces как побочный продукт работы. Инкумбенты не контролируют workflow.

### Как vs Почему

Главный pushback: нельзя захватить настоящее "почему" — intent ненаблюдаем. Ответ (Arvind из Glean): захватываешь "как" (какую политику применили, какие доказательства смотрели, какое исключение сделали), а "почему" **выводишь из паттернов** со временем. Это уже значительно больше, чем есть сейчас.

### Траектории агентов

Когда агент выполняет задачу (расследует инцидент, обрабатывает запрос), он проходит по системам, читает данные, вызывает API. Эта **траектория = decision trace**. Накопи достаточно траекторий — и мировая модель организации возникает сама.

> "The schema isn't the starting point. It's the output." — Animesh (PlayerZero)

Не задавай онтологию заранее — пусть агенты обнаружат её через использование.

### Stateful reasoning

Conviva: захватить traces — только начало. Нужен stateful reasoning — связывание действий с результатами. Это путь к "AlphaGo moment" для AI-агентов: обучение на чужих ошибках и удачах.

---

## Открытые вопросы

**Категория или фича?** Context graph — самостоятельная категория или фича внутри warehouse/catalog/observability? Открытый вопрос. Но слой необходим — в этом консенсус.

**Где живёт граф?** Data warehouse (read path, не write path — контекст теряется при ETL)? Orchestration layer (привязка к конкретному тулу)? Выделенная "context OS" (ещё одна система)?

**Кто владеет?** Governance и access control для decision traces в регулируемых индустриях — нетривиальная проблема.

**Как работать со временем?** Решения имеют half-life. Политики меняются, команды меняются. Агент должен знать, какие прецеденты ещё действуют, а какие уже нет. Нет очевидного правила протухания. → Прямая связь с [temporal-graphs.md](temporal-graphs.md).

---

## Экосистема

| Компания | Домен | Подход |
|----------|-------|--------|
| **PlayerZero** | Production engineering | Агенты расследуют инциденты → траектории = traces → мировая модель |
| **Maximor** | Финансы | Context graphs для финансовых решений |
| **Regie** | Demand gen | Context graphs для маркетинга и продаж |
| **Glean** | Enterprise search | "Finally has a name" — называют свой подход context graphs |
| **Cognition** | Developer tools | Привязали term к запуску с Cursor, Cloudflare, Vercel |
| **Tonkean** | Process orchestration | Строят context graphs с клиентами |
| **Tessera** | — | Портфельная компания Foundation Capital |

---

## Связь с SVAIB

Наш framework/ontology — по сути context graph для CEO. Мы структурируем decision traces руководителя: встречи → протоколы → решения → задачи. Разница с Foundation Capital: они говорят про enterprise-масштаб, мы — про персональный Second AI Brain одного руководителя. Но принцип тот же: собирать reasoning, а не только результаты.

Открытый вопрос про темпоральность ("как решения протухают") — то, что мы решаем через temporal graphs (Graphiti, Hindsight). Context graphs дают naming и framing для того, зачем это нужно.

Идея "schema is the output" (PlayerZero) — интересный контрапункт к нашему подходу с предзаданной онтологией. Мы даём scaffold, но он должен быть достаточно гибким для органического роста.

---

## Источники

- Оригинальная статья: [AI's Trillion Dollar Opportunity: Context Graphs](https://ashugarg.substack.com/p/ais-trillion-dollar-opportunity-context) (Ashu Garg, Substack)
- Follow-up: [Context Graphs, One Month In](https://foundationcapital.com/context-graphs-one-month-in/) (Foundation Capital, 30 января 2026)
- Dharmesh Shah (HubSpot): "a system of record for decisions, not just data"
- Aaron Levie (Box): "the era of context — differentiator is organizational knowledge you feed models"
- Animesh (PlayerZero): [How to Build a Context Graph](https://www.linkedin.com/pulse/how-build-context-graph-animesh-koratana-6abve/)
- Conviva: [Can Context Graphs Create a Path to an AlphaGo Moment for AI Agents?](https://www.conviva.ai/resource/can-context-graphs-create-a-path-to-an-alphago-moment-for-ai-agents/)
- Контекст из поста @llm_under_hood (Telegram): связь с OpenClaw, Engineering Harness, соревнование 11 апреля (Personal & Trustworthy Autonomous Agents)

## Связанные файлы

- [temporal-graphs.md](temporal-graphs.md) — Temporal Knowledge Graphs: решение открытого вопроса про "как решения протухают"
- [agent-memory.md](agent-memory.md) — обзорная карта архитектур памяти агентов
- [!context.md](!context.md) — сводка по Context Engineering
- [../agents/openclaw.md](../agents/openclaw.md) — пример файловой Memory (decision traces на минималках)
- [../agents/!agents.md](../agents/!agents.md) — агентные траектории как источник decision traces
