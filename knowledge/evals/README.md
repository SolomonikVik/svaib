# Evals — оценка AI-систем

Как индустрия проектирует и запускает eval для LLM-пайплайнов и агентов: единицы оценки, датасеты, метрики, LLM-as-judge, инструментарий. "ЧТО известно об evals" — не наши внутренние решения.

**Границы:** сюда — переносимые внешние знания, паттерны, инструменты, papers. НЕ сюда: наши нормативные решения и обязательные контракты SVAIB (→ `lab/eval-methodology/`), конкретные датасеты/harness/прогоны конкретного eval (→ `dev/evals/`), общие агентные паттерны вне оценки (→ `agents/`), инструментарий разработки не про eval (→ `coding/`/`tools/`).

## Файлы

- [!evals.md](!evals.md) — сводка знаний
- [evaluation-design.md](evaluation-design.md) — цели, единицы оценки, датасеты, метрики, статистика, воспроизводимость
- [agent-evaluation.md](agent-evaluation.md) — траектории, tool use, состояние среды, multi-step и end-to-end evals
- [llm-as-judge.md](llm-as-judge.md) — рубрики, калибровка, bias, надёжность и границы применимости
- [eval-tooling.md](eval-tooling.md) — карта фреймворков и критерии выбора. Только карта рынка и объективные критерии — не путать с нашей процедурой принятия решения build/buy/adopt (lab/eval-methodology/playbooks/external-tool-selection.md)

## Связи

- [../agents/](../agents/) — общие агентные паттерны; `agent-evaluation.md` оценивает именно их поведение
- [../coding/](../coding/) — среды разработки, CI
- ../../lab/eval-methodology/ — наш нормативный meta-spec, использующий эти знания как фундамент
- ../../dev/evals/ — конкретные eval-инстансы
