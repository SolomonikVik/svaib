---
title: "Model elicitation — эмпирическая методология Бориса Черни: ablation харнеса, unhobbling, verification"
source: "https://www.youtube.com/watch?v=qyPCVqFUyDo"
source_type: video
status: processed
added: 2026-08-14
updated: 2026-08-14
review_by: 2026-11-14
tags: [prompting, elicitation, ablation, system-prompt, unhobbling, product-overhang, verification, claude-code, harness]
publish: false
---

# Model elicitation — эмпирическая методология Бориса Черни

## Кратко

Подход Boris Cherny (создатель Claude Code, Anthropic) к работе с промптами, скиллами и харнесом: модель — эмпирический объект («almost a living creature»), под каждое поколение харнес сносится и пересобирается методом ablation, а ключевой навык — не prompt engineering, а **model elicitation** (раскрыть скрытые способности модели) и **verification** (дать модели способ проверять свою работу). Источник — интервью YC Startup School «We Cut 80% of Claude Code's Prompt» (июль 2026, сразу после релиза Opus 5) + сопутствующие материалы.

## Ядро: модель — эмпирический объект

Классическая инженерия проектирует систему заранее: big upfront design, стабильные интерфейсы, реархитектура как проект на годы. Модель так не работает: «every model generation, it behaves differently, it has a slightly different personality» — с каждым поколением нужно «знакомиться заново» и подстраивать харнес. Метод — научный цикл: попробовал → посмотрел, где спотыкается → поправил → снова.

> «Forget all of the things that you learned about past models… it's become an empirical science.»

Следствие: всё, что написано под прошлую модель, — кандидат на удаление. Поведение, вылеченное инструкцией для одного поколения, у следующего либо исправно само, либо ломается иначе.

## Ablation харнеса

**Что это.** Исследовательский приём, применённый к продукту: «ablation essentially is an eval where you delete things to figure out the impact». Не постепенная подрезка промпта, а полный снос и построчное восстановление:

> «You delete the entire system prompt and then you bring it back line by line to figure out what is the impact of each individual line.»

Так из системного промпта Claude Code удалили 80%+ текста без измеримой потери на coding-евалах (сам факт и шесть выводов — [../context/context-engineering-claude5.md](../context/context-engineering-claude5.md)). Причина: большинство строк корректировали ошибки, которые новая модель уже не делает — «most of that prompt was corrections for mistakes Opus 5 no longer makes». То же делают с тулами и кодом харнеса: «unship» постоянно; в коде Claude Code остались почти только safety, permissions, static analysis и UI.

**Инструменты измерения** (Claude Code):
- флаг `--system-prompt` — запуск с полностью своим системным промптом;
- недокументированный simple mode (env var вида `CLAUDE_CODE_SIMPLE=1`) — сносит вообще все промпты, включая промпты тулов. Находка Anthropic: без них модель «чуть умнее», но продукту часть промптов нужна — для управляемого поведения под пользователя.

**Регулярность сноса:**
- строишь харнес/агентный продукт — снос на **каждый релиз модели**;
- пользуешься готовым (Claude Code) — «**every 6 months** delete your CLAUDE.md, delete your skills, delete your hooks. See what the model does and it might surprise you».

**Рецепт пересборки** (три шага, явно против «угадывания»):
1. Удалить.
2. Реально пользоваться продуктом и смотреть, где модель систематически спотыкается. «You don't want to guess what's the instruction that the model needs because you might not predict it correctly.»
3. Возвращать инструкцию только при **повторном** сбое, не при первом: «the model is going to read this instruction every single time you use it — make sure that the model needs this instruction».

**Evals — тоже смертны.** Они переживают харнес, «but not by that much»: типичный eval живёт 1–3 поколения модели, затем насыщается (saturates) и пересобирается заново. Строятся из того же эмпирического цикла — из наблюдаемых, а не предполагаемых сбоев.

## Unhobbling и product overhang

- **Hobbling** — продукт мешает модели: «the model is doing something and you're just getting in the way».
- **Product overhang** — у *сегодняшней* модели уже есть способности, которые ни один продукт не раскрыл.

История рождения Claude Code — образцовый кейс: Sonnet 3.5 умел писать целые функции и файлы, а продукты того времени давали лишь автокомплит и read-only чат. Решение — убрать scaffolding и дать модели простейший харнес (терминал целиком): «all of you could create the next Claude Code if you figure out how to un-hobble the models».

Пример скрытой способности: Opus 5 + OpenCV рисует портреты и пейзажи, хотя рисовать модель не учили — «it's just the elicitation gap: if you ask it to do it the right way, it can just do it». Гипотеза Черни: таких нераскрытых способностей у текущих моделей — десятки и сотни; overhang сейчас велик, и стартапы его почти не ловят.

## Elicitation вместо prompt engineering

Волны профессии — prompt engineer → context engineer — приходят и уходят. Актуальный навык из двух частей:

1. **Задача чуть сложнее, чем кажется по силам** — вместо пошаговой микроспецификации («сначала раз, потом два, три»), которая для современных моделей контрпродуктивна: «describe the task, describe the guardrails, describe the exit criteria — and let the model cook». Типичная ошибка опытных инженеров — over-specify, заставлять модель делать ровно как сделал бы сам; «it's a journey to unlearn», относиться к модели как к коллеге.
2. **Verification** — дать модели способ проверять свою работу так, как проверял бы сам: «the verification I think is probably the single most important thing that people do not get right». Тесты, браузер, скриншоты, diff — не доверять, а инструментировать.

Кейсы масштаба (иллюстрации обоих пунктов):
- **Bun: Zig → Rust за 11 дней.** Рантайм Bun (100k+ строк Zig, ручное управление памятью) сначала лишь фаззили на утечки — потолок прежних моделей. Инженер команды Bun на каждом новом поколении заново бросал задачу «перепиши целиком»; начиная с определённого поколения модель справилась: один промпт, dynamic workflow, 11 дней со steering, тест-сьюты Bun и Node.js как верификация. Оценка вручную — «definitely over a year». Результат в проде — на нём работает сам Claude Code.
- **Electron → Swift через Claude в Slack.** Промпт уровня «каждый в зале мог бы написать»: «run the Electron app in the Mac VM, screenshot it, compare pixel by pixel to the Swift version, don't stop until you're done». На момент интервью шёл 2+ недели, тысячи агентов; Claude без запроса завёл Slack-канал и постил туда скриншоты прогресса. Разница между обычным и топ-пользователем — не секретная техника («don't listen to the LinkedIn influencers»), а эмпирика: сложная задача + инструменты верификации + чинить наблюдаемые сбои промптом, скиллом или MCP.

## Масштабирование: три механизма

Лучшие пользователи получают леверидж, запуская тысячи агентов на задачу (в зале YC таких не нашлось). Механизмы в Claude Code:

- **Dynamic workflows** — триггер фразой «use a workflow»; песочница на Bun-рантайме, многостадийная оркестрация (волна работы → волна верификации/суммаризации → новый fan-out), «алгебра для агентов». Концептуально — новый способ наращивать test-time compute. Механика и шесть паттернов — [../coding/claude-code.md](../coding/claude-code.md).
- **Loop** — повторяющаяся задача по расписанию, локально (cron для Claude).
- **Routine** — то же в облаке, ноутбук можно закрыть.

Внутренний кейс Anthropic: ~20–30 ежедневных routines сами обслуживают кодовые базы (CLI, iOS, Android, desktop) — чистка dead code, авто-ship полностью раскатанных экспериментов, дописывание и удаление тестов, «abstraction police» (унификация дублирующихся абстракций). Каждая routine — промпт в одно предложение; метод исполнения модель выбирает сама.

## Границы и критика

- **«Coding is solved» — с оговоркой самого Черни:** решено «for the kind of coding that I do», не для глубоких системных и распределённых кодовых баз и не для pixel-level UI-верификации.
- **Удалять — только scaffolding, не non-derivable constraints.** Контр-тезис бизнес-разборов: инструкции, которые модель не может вывести из контекста (brand voice, ценовые границы, полномочия подписи, compliance, definitions of done), сносить нельзя — их нарушение «не звучит громко»: «there is no compiler for tone». Тест перед удалением инструкции: (1) выводима ли из контекста? (2) поймается ли ошибка автоматически? (3) объясняли бы это новому сотруднику? (4) какова цена ошибки?
- **Скепсис HN:** «переизобретать воркфлоу каждые полгода» — налог на пользователя; больше агентов = больше токенов у вендора; auto-memory без контроля тревожит.
- **Стоимость:** многонедельные автономные прогоны на флагманских моделях — десятки-сотни тысяч долларов; у команды Anthropic токен-бюджет, недоступный обычному пользователю.

Термин «elicitation» здесь — про раскрытие способностей модели; не путать с Elicitation в MCP-протоколе (запрос ввода у пользователя, → [../agents/mcp.md](../agents/mcp.md)).

## Связанные файлы

- [../context/context-engineering-claude5.md](../context/context-engineering-claude5.md) — что именно вырезали и шесть сдвигов сборки контекста (статья Anthropic — парный первоисточник)
- [claude-5-prompting.md](claude-5-prompting.md) — формулировки и типовые сбои промптинга того же поколения
- [../skills/!skills.md](../skills/!skills.md) — проектирование скиллов; правило сноса распространяется и на них
- [../coding/claude-code.md](../coding/claude-code.md) — механика dynamic workflows, verification loops, `/doctor`
- [../coding/ai-dev-practices.md](../coding/ai-dev-practices.md) — практики Черни в общем синтезе AI-first разработки (план до кода, ревью)

## Источники

- [Boris Cherny: We Cut 80% of Claude Code's Prompt](https://www.youtube.com/watch?v=qyPCVqFUyDo) — интервью YC Startup School, июль 2026 (Diana Hu). Основной источник; цитаты сверены по ASR-транскрипту и конспектам очевидцев
- [The new rules of context engineering](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models) — Thariq Shihipar, Anthropic: письменная версия методологии
- [Тред-конспект выступления (@MyWestLord)](https://x.com/MyWestLord/status/2082855525956415987), [цитата про «6 месяцев» (@alex_prompter)](https://x.com/alex_prompter/status/2083640104158126186) — дословные цитаты с видеофрагментами
- [YC Root Access — Building Claude Code](https://www.ycrootaccess.com/p/boris-cherny-building-claude-code) — конспект с цитатами про guardrails/exit criteria
- [Context Engineering: What the 80% Cut Means for Business](https://bosio.digital/articles/context-engineering-rules) — контр-тезис про non-derivable constraints
- [Hacker News: обсуждение интервью](https://news.ycombinator.com/item?id=49077040) — критика и скепсис сообщества
