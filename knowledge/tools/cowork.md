---
title: "Cowork — агентная платформа Anthropic для knowledge workers (не разработчиков)"
source: "https://claude.com/blog/cowork-research-preview"
source_type: docs
status: processed
added: 2026-02-01
updated: 2026-08-07
review_by: 2026-10-21
tags: [cowork, anthropic, plugins, knowledge-work, agents, svaib-product]
publish: false
---

# Cowork — агентная платформа для knowledge workers

## Кратко

Cowork — фича Claude Desktop (macOS, Windows), запущена в январе 2026 как research preview; с июля 2026 — также web и mobile (beta). Приносит агентную архитектуру Claude Code (субагенты, параллельная работа) в GUI для не-разработчиков: sales, legal, finance, marketing. Работает в sandboxed VM. Расширяется через Plugins — тот же формат что Claude Code. Критически важно для продукта SVAIB: плагины = техническая реализация модели подписки "Skills + Agents + Онтология".

---

## Cowork vs Claude Code

| | Cowork | Claude Code |
|---|---|---|
| **Интерфейс** | Claude Desktop GUI | CLI / VS Code / JetBrains |
| **Аудитория** | Knowledge workers (sales, legal, finance) | Разработчики |
| **Среда** | Sandboxed VM | Прямой доступ к файловой системе |
| **Формат плагинов** | Идентичный | Идентичный |
| **Субагенты** | Task tool (до ~10 параллельных) | Task tool (до ~10 параллельных) |

Техническая архитектура одна: тот же Task tool, те же субагенты, тот же формат плагинов. Различие — интерфейс и целевая аудитория. Прямая цитата Anthropic: *"Built for Cowork, also compatible with Claude Code."*

---

## Ключевые возможности

**Plugins.** Система расширения через Skills + Commands + Agents + Hooks + MCP. Всё файловое (Markdown + JSON). **Hooks — исключение:** в sandboxed VM Cowork они молча не срабатывают (известный открытый баг Anthropic, не конкретного плагина) — Skills/Commands/MCP того же плагина работают штатно. Подробнее о формате, экосистеме и этом ограничении → [plugins/!plugins.md](../plugins/!plugins.md) (раздел "Claude Code ↔ Cowork").

**Skills.** Три канала установки: встроенный каталог (Customize), загрузка своего скилла (папка/ZIP), и `.claude/skills/` подключённой папки — последнее подтверждено живым прогоном meeting-analysis 30.07.2026 (сборка builder'ом, скилл подхватился и отработал полный цикл). Skills доступны на всех платных планах.

**Deliverable-first вывод (критично для HITL-скиллов).** Cowork системно склоняет модель к схеме «результат = файл, в чате — краткий статус»: это заявленный дизайн платформы (запросил документ — получил .docx, не текст в чате). Следствие: скилл, требующий показать согласующему полный текст в чате (HITL-экраны), в Cowork молча деградирует до «смотрите файл» — воспроизведено на живом прогоне meeting-analysis 30.07.2026 (выжимка не показана в чате). Инструкция показа должна явно запрещать замену показа ссылкой/превью/пересказом. Отсылка к файлу вдобавок ненадёжна: известный баг пустого превью в панели Cowork ([#33499](https://github.com/anthropics/claude-code/issues/33499)).

**Scheduled Tasks.** Recurring и on-demand задачи через `/schedule`. Docs: [Anthropic](https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-cowork).

**Multi-App.** Claude работает сквозь Excel и PowerPoint, передавая контекст между приложениями (pivot tables, conditional formatting, генерация презентаций из данных). Research preview.

**Enterprise Private Marketplaces.** Компании создают внутренние каталоги плагинов: per-user provisioning, OpenTelemetry для трекинга, корпоративный брендинг.

---

## Sandbox и сетевые ограничения

Cowork выполняет все команды в sandboxed VM. Исходящий трафик проходит через MITM-прокси (`localhost:3128`), который фильтрует домены по allowlist.

**Allow network egress** (Settings → Capabilities):
- **OFF (по умолчанию):** прокси блокирует все нестандартные домены (`403 Forbidden`, заголовок `X-Proxy-Error: blocked-by-allowlist`). Доступны только ~23 захардкоженных dev-домена
- **ON:** трафик идёт напрямую через NAT, без прокси

**Domain allowlist:** даже при ON, если выбран не "All domains" — конкретные домены могут быть заблокированы. Есть открытые баги Anthropic с allowlist.

**Важно:** изменение настройки применяется только к **новым сессиям**. Уже запущенные сессии не подхватывают изменение.

**Диагностика:** `env | grep -i proxy` — если в выводе `HTTPS_PROXY=http://localhost:3128`, прокси активен и фильтрует трафик.

При **ON + All domains** произвольный домен вне списка dev-доменов проходит: `curl` к стороннему HTTPS отдаёт `200`, переменных прокси в окружении нет. Обе половины картины сошлись — фильтрация включается вместе с настройкой, а не действует всегда (проверено 07.08.2026).

> Отчёты расследований: `clients/_inbox/cowork-telegram-debug-report.md` (31.03.2026) · `dev/gateway/env-probe.md` (07.08.2026)

## Файловая система: что переживает сессию

`~` внутри песочницы разворачивается в **`/sessions/<имя-сессии>/`, и имя своё у каждой сессии**: файл, созданный в предыдущей, в следующей недоступен. Реальная домашняя директория машины из песочницы **не видна вовсе** — примонтирована только приложенная рабочая папка.

Практическое следствие: единственное персистентное и записываемое место в Cowork — рабочая папка (обычно синхронизируемая через облачный диск). Любая схема «положить конфиг или секрет в `~/.config/...`» здесь не работает конструктивно, а не «ненадёжна». Ранее это описывал только сторонний реверс-инжиниринг; подтверждено прогоном 07.08.2026.

## Скиллы и их скрипты в песочнице (проверено живьём 02.09.2026)

Диагностика в сессии Cowork на копии базы клиента (Linux-VM, Claude Code внутри с `--plugin-dir`):

- В `/sessions/<сессия>/mnt/` лежат `.claude`, `.remote-plugins`, рабочая папка, `outputs`, `uploads`. Скрытые каталоги `ls` без `-a` не показывает — агент легко делает ложный вывод «плагин не смонтирован».
- **Установленный скилл** лежит в `/sessions/<сессия>/mnt/.remote-plugins/plugin_<id>/skills/<скилл>/`, его `scripts/` **из bash доступны и исполняются**. Копия тех же файлов из рабочей папки `.claude/skills/<скилл>/` смонтирована тоже.
- **`${CLAUDE_SKILL_DIR}` в Cowork бесполезен**: в одном прогоне остался строкой, в другом подставился в путь **хоста**, в третьем — в `/sessions/<сессия>/mnt/.claude/skills/<скилл>` (смонтированная `~/.claude` хоста, скилла там нет) (`~/.config/Claude/local-agent-mode-sessions/<session>/<id>/rpm/plugin_<id>/skills/<скилл>/`), которого из VM нет. Найти папку установленного скилла можно так: `find /sessions -path '*/skills/<скилл>/scripts/<файл>' -not -path '*/.claude/*' | head -1` — но это приём диагностики: как скиллы адресуют свои файлы, решает meta-spec §2.
- Проверка версии (`skill_version.py`, маркер `.skill-version.json` в базе) осмысленна только из копии плагина: она несёт штамп установленного архива. Копия из рабочей папки всегда равна маркеру и молчит. Гейт spine v2 на этой же механике отрабатывал в бою.
- Путь к архиву `.skill` внутри смонтированной папки, выведенный агентом отдельной строкой, Cowork показывает карточкой с кнопкой обновления. ❗️ 03.09: кнопка сообщает «установилось», но скилл после этого не работает; в v2 (июль) тот же путь обновления работал. Надёжная установка — только Customize → Skills.
- `TMPDIR` в bash-песочнице — `/sessions/<сессия>/tmp`, свой у каждой сессии: кэш, положенный «в /tmp на сутки», в следующей сессии не виден (выгрузка канона scaffold-align качает архив заново каждую сессию, 3–9 с).
- Слэш-команда установленного скилла регистрируется только после рестарта приложения (dev/plugin-builder/_issues.md №8); длина `description` меряется в символах (744 символа / 1270 байт приняты).

## Коннекторы: только OAuth

Свой MCP-сервер подключить можно — `Customize → Connectors → Add → Add custom connector`. Поля: `Name`, `Remote MCP server URL` (HTTPS-адрес, где сервер принимает MCP-запросы), в Advanced — `OAuth Client ID` и `OAuth Client Secret`, **оба опциональны**.

- **Поля для статического заголовка `Authorization: Bearer` нет.** Приём, которым живёт `claude mcp add --header` в CLI, в десктопе и Cowork недоступен: стороннему серверу нужен настоящий OAuth-контур.
- Опциональность `Client ID` / `Secret` означает, что динамическая регистрация клиента (RFC 7591) не обязательна — пару можно выдать вручную.
- Коннекторы имеют тип **Web** и живут в аккаунте claude.ai, а не на машине. Отсюда их главное свойство: Google Drive одновременно виден в `claude mcp list` в терминале и в десктопном приложении, **при этом его токена на диске нет вовсе** — в `~/.claude/.credentials.json` лежит только собственный OAuth аккаунта Claude. Для стороннего сервиса это готовая модель «авторизовал один раз в аккаунте — работает во всех средах, секрета на диске не остаётся».

---

## Официальные плагины

Anthropic выпускает open-source плагины для knowledge workers по отраслям: productivity, sales, customer support, product management, marketing, legal, finance, data, enterprise search, bio-research, design, engineering, HR, operations + partner-built плагины. Все Apache-2.0.

**Актуальный каталог:** [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)

Примечательные:
- **productivity** — задачи, календари, daily workflows. Коннекторы: Slack, Notion, Asana, Linear, Jira, Monday, ClickUp, Microsoft 365
- **sales** — prospect research, call prep, pipeline. HubSpot, Close, Clay, ZoomInfo, Fireflies
- **data** — SQL, визуализация, дашборды. Snowflake, Databricks, BigQuery, Hex
- **enterprise-search** — поиск по email, chat, docs, wikis. Slack, Notion, Guru, Jira
- **cowork-plugin-management** — создание и кастомизация плагинов изнутри Cowork

Коннекторы: Google Workspace (Calendar, Drive, Gmail), DocuSign, Microsoft 365, FactSet, WordPress и др. Список растёт — актуальный перечень в репозитории.

---

## Pricing / Access

| План | Цена | Cowork |
|------|------|--------|
| Free | $0 | Нет |
| Pro | $20/мес | Есть (research preview) |
| Max 5x | $100/мес | Есть |
| Max 20x | $200/мес | Есть |
| Team | $25/seat/мес | Есть + admin controls |
| Enterprise | Custom | SSO, audit logs, SCIM, private marketplaces |

**Ограничения (research preview):**
- Cowork НЕ попадает в Audit Logs, Compliance API, Data Exports
- Запрещено для HIPAA, FedRAMP, FSI regulated workloads
- История хранится локально, нет cross-device sync

---

## Хронология

| Дата | Событие |
|------|---------|
| 12 января 2026 | Launch (macOS, Max plan) |
| 16 января | Pro план |
| 23 января | Team и Enterprise |
| 30 января | Plugins (research preview, все платные планы) |
| 10 февраля | Windows (x64) |
| 24 февраля | Enterprise: private marketplaces, новые коннекторы, multi-app, отраслевые шаблоны плагинов |
| 25 февраля | Scheduled Tasks |
| Июль 2026 | Web и mobile (beta) — эфемерность ФС и egress-ограничения те же |

---

## Связь с продуктом SVAIB

Product vision описывает модель подписки "Плагин": Skills (методология) + Agents (автоматизация) + Онтология (структура).

| SVAIB продаёт | Cowork Plugin содержит |
|--------------|----------------------|
| Skills (методология) | `skills/` (SKILL.md) |
| Agents (автоматизация) | `agents/` + `hooks/` |
| Онтология (структура) | CLAUDE.md + commands/ |
| Коннекторы | `.mcp.json` |

Наша `.claude/` уже plugin-compatible — шаг до плагина: создать `plugin.json`, реорганизовать файлы. Anthropic покрывает generic (sales, legal) — наша ценность в кастомизации + русскоязычный рынок.

---

## Ссылки

- Cowork: https://claude.com/blog/cowork-research-preview
- Plugins: https://claude.com/blog/cowork-plugins
- Enterprise: https://claude.com/blog/cowork-plugins-across-enterprise
- Plugin docs: https://code.claude.com/docs/en/plugins
- Knowledge-work plugins: https://github.com/anthropics/knowledge-work-plugins
- Official plugin directory: https://github.com/anthropics/claude-plugins-official

---

## Связанные материалы

- [plugins/!plugins.md](../plugins/!plugins.md) — Плагины: формат, спецификация, маркетплейсы, best practices
- [coding/claude-code.md](../coding/claude-code.md) — Claude Code: рабочая среда, система расширения
- [skills/!skills.md](../skills/!skills.md) — Skills как формат: проектирование, экосистема
- [coding/agent-teams.md](../coding/agent-teams.md) — Agent Teams: координация команды AI-агентов
- [../context/claude_integrations_gdrive.md](../context/claude_integrations_gdrive.md) — тестирование интеграции Cowork + Google Drive + Claude Projects: что пишет, что видит, где зазоры
