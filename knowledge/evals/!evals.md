---
title: "Evals — сводка знаний по оценке AI-систем"
source: "internal synthesis (industry research 2026-07-17 + eval literature)"
source_type: docs
status: processed
added: 2026-07-18
updated: 2026-07-18
review_by: 2026-10-18
tags: [evals, llm-as-judge, agent-evaluation, statistics, eval-tooling]
publish: false
---

# Evals — сводка знаний

## Кратко

Синтез практики оценки LLM-пайплайнов и агентов на 2026 год: типы eval, устройство датасетов, статистика на малых выборках, LLM-as-judge с его bias'ами, инструментарий рынка. Ориентировано на команды без выделенной eval-инфраструктуры, которые оценивают собственные генеративные артефакты (скиллы, агенты, pipeline).

## Три типа eval

| Тип | Вопрос | Baseline | Гейт |
|---|---|---|---|
| **regression** | Не сломала ли новая версия то, что работало | прошлая версия | не хуже baseline |
| **capability-delta** | Насколько новая версия лучше | прошлая версия | значимая дельта |
| **pairwise / multi-candidate** | Какой из кандидатов лучше | текущий инструмент/подход | победитель по категориям, не по среднему |

Capability-eval стартует с низким pass-rate («что умеет система»); дойдя до потолка, кейс переходит в regression-suite с baseline ~100% — дальше он охраняет от отката, а не измеряет рост (Anthropic, «Demystifying evals for AI agents»).

## Строгость зависит от решения

Объём данных, схема грейдинга и статистическая строгость масштабируются с ценой ошибки и величиной эффекта, который нужно обнаружить. Универсальных ярусов и порогов размера набора нет. Anthropic рекомендует начинать с 20–50 простых задач из реальных провалов; зрелым системам нужны более крупные и сложные наборы, чтобы различать меньшие изменения ([Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)).

## Порядок построения: error-analysis-first

Практик Hamel Husain рекомендует не писать evaluator под каждый воображаемый провал заранее. Рабочий порядок: собрать реальные трейсы → сделать свободные заметки об ошибках → сгруппировать их в failure taxonomy → строить evaluator под повторяющиеся и значимые провалы ([LLM Evals FAQ](https://hamel.dev/blog/posts/evals-faq/)). По его оценке, 60–80% времени разработки AI-продукта уходит на error analysis и эвалы — это норма, а не избыточные накладные расходы; pass rate 70% на честном наборе полезнее, чем 100% на беззубом.

## Датасеты и golden-set

- Кейсы происходят из error analysis реальных провалов, не из воображения; растут из пойманных прод-фейлов, не полируются upfront.
- Валидный кейс: однозначен (два эксперта сходятся в вердикте), passable (есть reference-решение, доказывающее решаемость), баланс positive/negative, неэксплуатируем (нет лазеек-читов в грейдере).
- **Silver → gold:** LLM может подготовить черновик эталона, но перевод в gold требует человеческой проверки или заранее валидированной процедуры разметки; согласие двух моделей само по себе не доказывает корректность.
- **Holdout:** зарезервированная часть, в которую не смотрят при итерации промпта — иначе оптимизация подгоняется под артефакты сета (Goodhart). На малом наборе отдельный holdout может оказаться слишком мал для надёжного вывода; один из вариантов — темпоральный holdout из свежих эксплуатационных провалов.
- Pass-rate 100% может означать как сильную систему, так и слишком лёгкий или узкий набор; нужно проверять покрытие и сложность кейсов.

## Статистика на малых выборках

При n меньше нескольких сотен нормальное приближение (CLT, t-тест, Wald-CI) даёт систематически слишком узкие доверительные интервалы — ложные «значимые» улучшения.

- **Оценка одной версии:** bootstrap-CI (percentile, ~1000 ресемплов); Wilson score / Clopper-Pearson для биномиальной pass-rate (не Wald).
- **Сравнение двух версий на одном наборе (paired):** McNemar для бинарного pass/fail (точный биномиальный вариант при малом числе расхождений); Wilcoxon signed-rank для rubric-баллов; permutation/bootstrap на разнице — универсальный запасной вариант.
- **Сравнение 3+ кандидатов:** Cochran's Q (бинарный), Friedman (rubric-баллы); значимый общий тест → парные post-hoc с поправкой на множественность (Bonferroni/Holm).
- **Правда мощности:** на 20-50 кейсах статистически надёжно ловятся только крупные сдвиги (десятки процентных пунктов); детектируемый эффект ~4-5 п.п. требует сотен кейсов. На малых выборках NHST — не жёсткий гейт, а санитарная проверка «не шум ли»; решение принимается по дельте + CI + разбивке по категориям.
- Собственная ошибка измерения LLM-судьи систематическая, не усредняется повторными прогонами — закладывается в неопределённость сравнения, а не игнорируется.
- Надёжность через `pass^N` (все N прогонов успешны) применяется только там, где у артефакта нет права на пересдачу; иначе используется majority-свёртка. `pass@k` (хотя бы один успех из k) — отдельная метрика для другого сценария, эти два понятия не взаимозаменяемы.

## LLM-as-judge

- **Pointwise vs pairwise:** pointwise (вывод против rubric) — для регрессии и мониторинга. Истинный pairwise (два вывода в одном промпте) даёт более тонкий сравнительный сигнал, но чувствителен к position bias — обязательна рандомизация/swap порядка, order-зависимый вердикт засчитывается как ничья. Pointwise + post-hoc дельта гасит position bias ценой потери части сравнительного сигнала.
- **Bias'ы и лечение:**

| Bias | Как проявляется | Лечение |
|---|---|---|
| Length | длиннее оценивается выше | rubric штрафует лишнюю длину; нормировка на токен |
| Position | вердикт зависит от порядка слотов | рандомизация/swap порядка; order-зависимое = ничья |
| Family/self-preference | судья завышает оценки текстам своей модельной семьи (~+10% win rate у GPT-4 своим ответам) | судья другого семейства, чем генератор — критично именно для pairwise-сравнений версий |
| Verbosity-confidence | уверенно поданная неверная информация оценивается выше робкой верной | rubric штрафует необоснованные утверждения, поощряет хеджирование |
| Calibration drift | согласие с людьми деградирует со временем | периодическая сверка на фиксированном gold-set, alert при падении |

- **Валидация судьи глубже kappa:** Cohen's kappa — базовый, но недостаточный порог (парадоксально занижается при дисбалансе классов). TPR/TNR на labeled held-out — раздельно измеряет пропуск регрессий (низкий TNR) и ложные тревоги. Разрыв exact-match/kappa может достигать 33-41 п.п. (arXiv 2606.19544). Судья — сам артефакт под eval: согласие с людьми (reliability) не равно валидности.
- **Same-model judge:** допустим для проверки бинарных нетоварных критериев, если судья валидирован против человеческих меток (Hamel); для pairwise-сравнения версий кросс-модельность важнее — там self-preference bias бьёт напрямую.
- **Ансамбли (LLM jury):** панели разных моделей могут снижать отдельные систематические bias'ы, но стоимость и качество зависят от задачи и состава панели; их нужно валидировать против человеческих меток.

## Online vs offline: где проходит грань

Трёхчастная таксономия (LangWatch, qaskills 2026):

| Слой | Когда гоняют | Что проверяют | Блокирует прогон? |
|---|---|---|---|
| Experiments (offline eval) | при каждом изменении | качество против golden set | да, merge/deploy |
| Online monitors | каждый прод-прогон, асинхронно | reference-free сигналы | нет |
| Guardrails | каждый прод-прогон, синхронно | неторгуемые бинарные политики (формат, PII, противоречия) | да, ответ |

Грань — по роли, не по механике: проверка в live-path, которая гейтит результат прогона, — guardrail, даже если скоринг тот же, что у офлайн-eval. Правило «don't guardrail quality metrics»: субъективное качество меряют офлайн и асинхронно; онлайн блокируют только по бинарным нарушениям политики.

**Consistency-ревьюер базы знаний** — устоявшийся пример легитимного online-guardrail (аналог lint, не eval): проверяет, что новое добавление не противоречит уже записанному, до коммита/записи (прецедент — [knowledgebase_guardian](https://github.com/datarootsio/knowledgebase_guardian)). Практика LLM-wiki — «lint pass по таймеру»: orphan detection + contradiction flagging + stale-claim checks; главный failure mode — drift (агент не обновляет кросс-ссылки, страницы тихо устаревают). Гибрид NLI+LLM даёт лучший баланс precision/recall на противоречиях, чем один LLM-судья; кросс-документные противоречия остаются трудным случаем даже для гибрида. Такой ревьюер reference-free и не заменяет офлайн-регресс на golden set — он ловит «не сломал ли этот прогон базу», а не «эта версия лучше прежней».

## Инструментарий (карта рынка, детали и критерии выбора — в eval-tooling.md)

В марте 2026 года OpenAI объявила о приобретении promptfoo и будущей интеграции его технологии в OpenAI Frontier; open-source CLI остаётся доступным ([OpenAI](https://openai.com/index/openai-to-acquire-promptfoo/)). Практический паттерн — лёгкий CI-раннер (например, promptfoo или DeepEval) плюс опциональная платформа для аннотации, истории и дашбордов. Самописный харнес также может быть оправдан, если доменная специфика важнее готового UI.

## Источники

- [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Anthropic — Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Hamel Husain — LLM Evals FAQ](https://hamel.dev/blog/posts/evals-faq/)
- [Don't Use the CLT in LLM Evals <few hundred (arXiv 2503.01747)](https://arxiv.org/pdf/2503.01747)
- [Reliability without Validity — LLM-as-Judge meta-eval (arXiv 2606.19544)](https://arxiv.org/pdf/2606.19544)
- [Self-Preference Bias in LLM-as-a-Judge (arXiv 2410.21819)](https://arxiv.org/abs/2410.21819)
- [LangWatch — Experiments, online evaluations, guardrails 2026](https://langwatch.ai/blog/llm-evaluations-explained-experiments-online-evaluations-guardrails-and-when-to-use-each-in-2026)
- [qaskills — Offline vs online LLM evaluation 2026](https://qaskills.sh/blog/offline-vs-online-llm-evaluation-2026)
- [DeepEval — LLM-as-a-judge guide](https://deepeval.com/guides/guides-llm-as-a-judge)
- [knowledgebase_guardian (dataroots)](https://github.com/datarootsio/knowledgebase_guardian)
- [LLM Wiki maintenance and knowledge drift](https://www.glukhov.org/knowledge-management/knowledge-systems-architectures/compiled-knowledge/llm-wiki-maintenance-knowledge-drift) · [Karpathy LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [Contradiction Detection in RAG Systems (arXiv 2504.00180)](https://arxiv.org/pdf/2504.00180)
- [Corpus-Level Knowledge Inconsistencies in Wikipedia (arXiv 2509.23233)](https://arxiv.org/pdf/2509.23233)
