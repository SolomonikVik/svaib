---
title: "Context Graphs — институциональная память решений организации (Foundation Capital)"
source: "https://ashugarg.substack.com/p/ais-trillion-dollar-opportunity-context"
source_type: article
status: processed
added: 2026-02-16
updated: 2026-02-21
review_by: 2026-05-21
tags: [context-graphs, decision-traces, agent-trajectories, enterprise-ai, memory]
publish: false
version: 2
---

# Context Graphs

## Кратко

Context Graph — институциональная память о том, КАК организация принимает решения. Не "что произошло" (CRM/ERP), а ПОЧЕМУ: какие исключения применили, какой прецедент учли, кто одобрил и зачем. Концепция Foundation Capital (Ashu Garg, Jaya Gupta): оригинальная статья декабрь 2025, вирусный follow-up январь 2026. Циркулировала в Slack OpenAI и Anthropic. Ключевое понятие: "decision traces" — записи рассуждений за решениями, которые накапливаются в queryable граф. Агенты создают traces автоматически, проходя по системам (траектории). Тезис: прошлое поколение софта владело данными (Salesforce, Workday, SAP) — следующее будет владеть reasoning layer. Стартапы имеют преимущество перед инкумбентами: сидят в execution path и захватывают traces at decision time. Компании: PlayerZero, Maximor, Regie, Glean, Cognition, Arize (observability).

---

## Суть концепции

**Проблема.** Enterprise software хорошо записывает результаты (цена, тикет, скидка), но не reasoning за ними. Какие исключения применили? Какой прецедент сработал? Кто одобрил и почему? Этот контекст живёт в Slack-тредах, разговорах, головах людей.

**Decision traces** — недостающие записи reasoning за решениями. Со временем они накапливаются в context graph: живую, queryable карту того, как организация принимает решения.

**Тезис Foundation Capital:** Context graphs определят следующее поколение enterprise software. Прошлое поколение владело данными (Salesforce — клиенты, Workday — сотрудники, SAP — операции). Следующее будет владеть reasoning layer — связью между данными и действиями.

> "The last generation of software captured *what* happened. This generation will capture *why*."

Важное различие: **rules** говорят агенту что должно происходить в общем случае ("используй официальный ARR для отчётности"). **Decision traces** фиксируют что произошло в конкретном случае ("использовали определение X, по политике v3.2, с VP exception, на основе прецедента Z, и вот что изменили"). Агентам нужны не только правила, но и доступ к следам прошлых решений.

### Слепые зоны сегодняшнего софта

Сегодняшний enterprise software записывает результаты, но не reasoning. Вот четыре категории контекста, который теряется — именно этот gap заполняют decision traces:

1. **Exception logic в головах людей.** "Мы всегда даём healthcare-компаниям +10%, потому что у них зверские procurement-циклы." Этого нет в CRM — tribal knowledge, передаваемое при онбординге.

2. **Прецеденты прошлых решений.** "Мы структурировали похожую сделку с Company X в прошлом квартале — нужно быть консистентными." Ни одна система не связывает эти две сделки и не хранит причину выбора структуры.

3. **Cross-system синтез.** Саппорт-лид проверяет ARR в Salesforce, видит две открытые эскалации в Zendesk, читает Slack-тред про churn risk — и решает эскалировать. Синтез в голове. В тикете только "escalated to Tier 3".

4. **Цепочки одобрений вне систем.** VP одобряет скидку в Zoom-звонке или Slack DM. В opportunity — только финальная цена. Кто одобрил отклонение и почему — не записано.

### Практический пример: как decision trace закрывает gap

Агент предлагает скидку 20%. Политика ограничивает renewals 10%, если нет service-impact exception. Агент:
- Достаёт 3 SEV-1 инцидента из PagerDuty
- Находит открытую эскалацию "cancel unless fixed" в Zendesk
- Находит прошлогодний renewal-тред, где VP одобрил аналогичное исключение
- Маршрутизирует exception в Finance → Finance одобряет

В CRM появляется один факт: "скидка 20%". Но если агент записал trace — появляется полная картина: какие данные собраны, какая политика применена, какой прецедент использован, кто одобрил. Этот trace становится прецедентом для будущих решений.

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

## Почему инкумбенты не смогут

**Операционные инкумбенты (Salesforce, ServiceNow, Workday)** наследуют архитектурные ограничения. Salesforce хранит current state — знает как opportunity выглядит сейчас, но не как выглядела в момент решения. Невозможно replay состояния мира на момент decision time → нельзя аудировать, учиться, использовать как прецедент. Плюс слепые зоны: эскалация зависит от данных в CRM + Zendesk + PagerDuty + Slack — ни один инкумбент не видит cross-system картину.

**Warehouse-игроки (Snowflake, Databricks)** — в read path, не в write path. Получают данные через ETL после принятия решений. К моменту попадания в warehouse decision context потерян. Databricks ближе (Neon, Lakebase, AgentBricks), но быть рядом с местом сборки агентов ≠ быть в execution path.

**Стартапы с системами агентов** — в orchestration path. Когда агент обрабатывает запрос, он собирает контекст из нескольких систем, оценивает правила, маршрутизирует исключения. Orchestration layer видит полную картину и может записать trace at commit time, а не post factum.

---

## Три стратегии стартапов

**1. Заменить system of record целиком.** CRM или ERP, перестроенный вокруг agentic execution с event-sourced state и native policy capture. Сложно — инкумбенты укоренились. Пример: **Regie** — AI-native sales engagement platform вместо Outreach/Salesloft; агент как first-class actor (prospecting, outreach, follow-ups, routing, escalation).

**2. Заменить модули, не систему.** Целить в конкретные sub-workflows, где концентрируются exceptions и approvals. Стать system of record для этих решений, синхронизировать финальное состояние обратно в инкумбент. Пример: **Maximor** — автоматизация cash, close management, core accounting без замены GL. ERP остаётся ledger, Maximor становится source of truth для reconciliation logic.

**3. Создать новый system of record.** Начать как orchestration layer, но персистить то, что никогда не хранилось: decision traces. Со временем replayable lineage становится authoritative artifact. Пример: **PlayerZero** — автоматизация L2/L3 support, но реальный актив = context graph: модель того, как code + config + infra + customer behavior взаимодействуют в реальности.

---

## Сигналы: где строить context graph

**High headcount.** 50 человек делают workflow вручную (маршрутизация тикетов, триаж запросов, reconciliation между системами) — сигнал. Люди нужны потому, что decision logic слишком сложна для традиционной автоматизации.

**Exception-heavy decisions.** Рутинные детерминированные workflows не нуждаются в decision lineage. Интересны поверхности, где логика сложна, прецедент важен, "it depends" — честный ответ. Deal desks, underwriting, compliance reviews, escalation management.

**Glue functions — организации на стыке систем.** RevOps существует потому, что кто-то должен reconcile sales + finance + marketing + customer success. DevOps — bridge между development + IT + support. SecOps — между IT + engineering + compliance. Эти роли возникают именно потому, что ни один system of record не владеет cross-functional workflow. Агент, автоматизирующий такую роль, может персистить decision traces, которые роль производила. Путь к новому system of record — не заменой инкумбента, а захватом категории истины, видимой только когда агент в workflow.

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
| **Arize** | Observability для агентов | Мониторинг, дебаг и оценка agent decision quality — инфраструктурный слой для context graphs |

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
- [../tools/openclaw.md](../tools/openclaw.md) — пример файловой Memory (decision traces на минималках)
- [../agents/!agents.md](../agents/!agents.md) — агентные траектории как источник decision traces
