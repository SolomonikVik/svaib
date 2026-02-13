# Inbox

Сюда кидай ссылки, темы, инструменты на разбор. Когда будет время — разберём через `/svaib-knowledge`.

Формат: что угодно — ссылка, название, пара слов о чём это.

---

- [ ] https://code.claude.com/docs/en/memory - посмотреть пт
	еще материалы
		Практический совет: Если обсудили что-то важное (архитектура, решение, ограничение API) — сразу говори "запиши это в [файл]". Тогда после compact не потеряется.
		Sources:
		- Context Memory Loss After Auto Compact - https://github.com/anthropics/claude-code/issues/3841
		- CLAUDE.md Persistence Through Compression - https://github.com/anthropics/claude-code/issues/11629
		- Session Memory — Decode Claude - https://decodeclaude.com/session-memory/
		- Master Claude Memory in 7 Steps - https://alirezarezvani.medium.com/master-claude-memory-in-7-steps-cut-context-loss-by-80-with-project-scoped-recall-b1ff67f0bc2e

- [x] sv-lab: разобраться с плагинами https://code.claude.com/docs/ru/plugins → knowledge/plugins/!plugins.md
- [ ] sv-lab: опыт Claudesidian: Claude+Obsidian https://github.com/heyitsnoah/claudesidian 
- [ ] sv-lab: опыт - встроить агента от versel https://t.me/the_ai_architect/214 
- [ ] sv-lab: опыт - встроить skill frontend https://t.me/the_ai_architect/218 

- [ ] sv-lab: Изучить вот это @aiwizards  - пост от 6 января и от 18 января- это ря

https://github.com/vamplabAI/sgr-agent-core

sv-app: вообще используем skill https://t.me/kdoronin_blog/1114  2026

- [ ] sv-learn: sgr https://abdullin.com/schema-guided-reasoning/demo
- [ ] https://t.me/countwithsasha/374 взять инструмент плюс из поста ниже 
- [ ] https://t.me/nobilix/182
- [ ] https://t.me/llm_under_hood/727 
- [ ] https://t.me/aostrikov_ai_agents/11 
- [ ] https://t.me/neuraldeep/1783 начни отсюда про агентов
- [ ] https://habr.com/ru/companies/sberbank/articles/934938/ agents

## улучшение агента
2. Почему сожрал контекст

Ты прав, это ошибка. Вот что произошло:

Я делал всё сам в основном контексте вместо делегирования субагентам:

Прочитал 3 больших файла напрямую (claude-code.md 264 строки, cowork.md 161, !skills.md 249) — всё село в мой контекст
6 WebFetch возвращали целые страницы документации (plugins reference — сотни строк) — всё в мой контекст
4 WebSearch — результаты тоже сюда
Что нужно было сделать: Запустить 2-3 Task агента параллельно:

general-purpose агент: "исследуй свежее состояние плагинов Claude Code/Cowork, верни сводку"
Explore агент: "найди и суммаризируй всё что у нас есть про плагины в knowledge/"
Каждый агент работает в своём контексте, а мне возвращает только сжатый результат. Вместо ~3000 строк сырых данных получил бы ~100 строк выжимки. Контекст основного окна остался бы чистым.

Урок: WebFetch + Read больших файлов = контекст-киллер. Для исследовательских задач — всегда делегировать через Task.
Хорошо бы прямо проанализировать, как это происходит, взять какой-то отдельный чат и проработать, чтобы он посмотрел, как это работает, посмотрел лучшие практики, и мы на основании исследования зафиксировали правильную методологию, скил его. 
Виктор хочет проверить — могу ли я делегировать исследование агентам и получить результат без траты контекста. Отличная идея — и практическая проверка, и ответ на вопрос про портабельность hooks/commands/agents.

Запущу два агента параллельно:

Один проверит — hooks формат используется где-то кроме Claude?
Другой проверит — commands/agents markdown формат используется где-то кроме Claude?
Именно. Запускаю двух агентов параллельно — они исследуют в своём контексте, мне вернут только выжимку.

Task:Check hooks portability
IN

Research question: Are Claude Code hooks (hooks.json format with events like PreToolUse, PostToolUse, UserPromptSubmit, Stop, SessionStart etc.) used ONLY in Claude Code/Cowork/Factory Droid ecosystem? Or have other AI coding tools (Cursor, Copilot, Cline, OpenAI Codex, Windsurf, etc.) adopted a similar or compatible hooks system?

Search the web for:
1. "hooks" or "lifecycle hooks" in other AI coding agents (Cursor, Copilot, Cline, Codex CLI, Windsurf)
2. Any standard or specification for AI agent hooks/event handlers beyond Claude Code
3. Whether Factory Droid's hooks compatibility is full or partial

Return a concise summary (max 15 lines): what's Claude-only, what's portable, what's unclear. Include sources.
И заметь — агенты вернули мне ~40 строк каждый, использовав в сумме ~54K токенов в своих контекстах. Мой контекст получил только выжимку.