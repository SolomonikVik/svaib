---
title: "Командные контентные платформы с AI: как устроены пространства, права и доступ агента"
source_type: docs
status: processed
added: 2026-07-27
updated: 2026-07-27
review_by: 2026-10-27
tags: [content-platforms, permissions, governance, box, nextcloud, notion, google-workspace, microsoft-365, glean, rovo, ai-agents, privacy]
publish: false
---

# Командные контентные платформы с AI

## Кратко

Карта платформ, в которых команда и AI-агенты работают в одном пространстве данных: Microsoft 365, Google Workspace, Box, Notion, Nextcloud — и AI-слои поверх чужих систем (Atlassian Rovo, Glean). Сравнение по трём осям: как устроены общие и личные пространства, откуда агент берёт права, где проходит граница приватности от самой организации. Главный вывод рынка: зрелость платформы определяется не качеством чата, а синхронизацией прав, аудитом, отзывом доступа и контролем действий агента.

## Связанные файлы

- [../context/permission-aware-retrieval.md](../context/permission-aware-retrieval.md) — механика: как права доезжают до выдачи агента (synced vs direct, latency ACL→индекс)
- [../agents/agent-authorization.md](../agents/agent-authorization.md) — агент как субъект прав: acting-as, Zanzibar-стек, MCP-авторизация, agent gateway
- [../context/md-data-systems.md](../context/md-data-systems.md) — как из этого собирается архитектура markdown-native системы знаний
- [../context/claude_integrations_gdrive.md](../context/claude_integrations_gdrive.md) — Google Drive в связке с Claude: форматы, мосты, orphaned-файлы
- [obsidian.md](obsidian.md) · [openknowledge.md](openknowledge.md) — file-native альтернативы с командной коллаборацией

---

## Две модели рынка

**Интегрированный рабочий контур** — документы, пространства, поиск и AI внутри одной платформы: Microsoft 365, Google Workspace, Box, Notion, Nextcloud. Права берутся из самой платформы.

**AI-слой поверх нескольких источников** — индексирует или запрашивает данные чужих систем и подчиняется их правам: Atlassian Rovo, Glean. Своего system of record нет.

В обеих моделях зрелые решения не дают агенту «собственную память», оторванную от ACL источников: агент видит то, что уже вправе видеть пользователь.

## Карта платформ

| Платформа | Пространства | Откуда права у AI | Ограничение, которое важно знать |
|---|---|---|---|
| **Microsoft 365** | Общее — SharePoint, личное — OneDrive; Copilot поверх Graph | Данные, к которым у пользователя уже есть доступ; агенты включаются админом на уровне организации | Restricted SharePoint Search — **не security boundary**, а «занавеска»: прячет сайты из поиска и Copilot, но не меняет прав; Microsoft с самого начала описывала её как временную меру на время наведения порядка (объявлен вывод из эксплуатации). Реальная защита — Purview + Restricted Access Control |
| **Google Workspace** | Командное — Shared Drives, личное — My Drive | Gemini имеет те же права на Workspace-данные, что и пользователь | В shared drives доступ «расширяющийся»; limited-access-папки — единственное исключение, но **Manager shared drive всегда имеет доступ к limited-папке, снять нельзя**. Super admin экспортирует данные организации, Vault делает retain/search/export |
| **Box** | Контентная платформа + desktop-клиент (Box Drive), Notes, Hubs | AI включается по пользователям и группам; наружу — через Box MCP Server, без копирования файлов | Классификация может исключать контент из чтения/поиска AI-агентами (в т.ч. сторонними — Claude, ChatGPT, Gemini); MCP-guardrails ограничивают действия внешних агентов (создание только в разрешённых папках, запрет внешнего шаринга). Но Content Manager даёт админам просмотр контента managed users |
| **Notion** | Teamspaces, shared pages, private section; в базах — create-only без просмотра чужих записей | Notion AI и Enterprise Search поверх прав страниц | На Enterprise workspace owner через **Content Search находит любую приватную страницу и выдаёт себе доступ**. «Приватно от коллег» ≠ «приватно от организации» |
| **Nextcloud** | Self-hosted: team folders, ACL, desktop sync, встроенный Assistant | Context Agent / Assistant — локальные или OpenAI-compatible бэкенды, инструменты доступны и через MCP | **Context Chat не соблюдает File Access Control**: пользователь, которому доступ к документу запрещён правилом, может получить содержимое через чат по проиндексированным данным (документировано в админ-мануале). Индексация — фоновыми джобами, первичная долгая |
| **Atlassian Rovo** | Не storage, а AI-слой поверх Jira/Confluence и внешних систем (Teamwork Graph) | Три типа коннекторов, см. ниже; для Google Drive каждый сотрудник привязывает свой аккаунт | Granular permission control на create/write/delete у agent tools не доведён до полноценной модели |
| **Glean** | Не storage, а permission-aware поиск и агенты поверх множества систем | Документы индексируются вместе с метаданными, идентичностями и **ACL**; агенты наследуют ту же permission-модель, что и поиск, с проверкой в рантайме | Не решает вопрос system of record и наследует политику внешних платформ (см. кейс Slack ниже) |

**Три типа коннекторов Rovo** — практичная классификация, применимая шире одного вендора:
- **synced** — админ настраивает синхронизацию, контент хранится и индексируется у Atlassian сервисным аккаунтом; лучшее качество поиска и работа агентов;
- **direct** — контент забирается вживую через search API провайдера, у себя не хранится и не индексируется;
- **smart links** — без коннектора и админа, выдача по метаданным ссылки и правам конкретного пользователя; минимальная глубина контекста.

## Приватность от организации — общий провал

Требование «личное пространство сотрудника, невидимое для CEO и оргадмина» в централизованном enterprise SaaS системно не выполняется:

- Notion — owner на Enterprise находит и открывает приватные страницы через Content Search;
- Google — super admin экспортирует данные организации, Vault удерживает и выгружает Drive-данные;
- Microsoft — у админов и менеджеров есть штатные процедуры доступа к OneDrive ушедшего сотрудника;
- Box — Content Manager позволяет админам просматривать контент managed users.

Причина не в недоработке вендоров, а в противоположном требовании — **offboarding и сохранность корпоративных данных**. Shared Drives существуют, чтобы контент оставался у организации после ухода сотрудника; legal hold и eDiscovery-экспорт нужны по регуляторике. Один и тот же механизм даёт компании контроль и отменяет приватность сотрудника.

**Практический вывод:** приватность от коллег даёт любая платформа; приватность от организации внутри одного tenant не даёт ни одна. Если требование настоящее — нужна отдельная security domain, отдельный tenant или собственный слой шифрования, где админ администрирует платформу, но не читает содержимое.

## Разделение чтения и действий

Для агента «прочитать» документ уже достаточно, чтобы вынести смысл, даже если он ничего не скачивал. Поэтому классического «запретить download» мало, и рынок разводит права:

- Slack позволяет отдельно ограничивать, какие каналы, canvases и lists AI вообще может читать;
- Box вводит ограничение именно на **read/search** для AI-агентов и интеграций по классификации контента, отдельно от download;
- guardrails на действия задаются отдельно от прав на чтение (что агент может создать, куда переместить, что нельзя расшарить наружу).

## Риск платформы-владельца данных

Показательный кейс: в 2025 году Salesforce изменил условия Slack API так, что сторонние AI-платформы (включая Glean) больше не могут долговременно хранить и индексировать Slack-данные — доступ разрешён «query-by-query». Клиенты Glean получили письмо, что Slack-данные больше не попадут в их индекс и knowledge graph. При этом собственный Slack AI продолжает читать ту же историю.

Вывод для любой системы, живущей на чужих API: возможность построить контекст компании зависит от политики владельца данных и может измениться росчерком пера. Это аргумент за то, чтобы system of record был в собственном контуре, а внешние источники подключались как дополнение.

## Выход наружу без копирования

Тренд, снижающий model/vendor lock-in: платформа отдаёт свой контент разным AI-клиентам через MCP, не выпуская файлы наружу.

- **Box MCP Server** — тот же контент доступен ChatGPT, Claude, Cursor и другим MCP-клиентам с сохранением прав и audit logging; действия внешних агентов ограничиваются админскими guardrails.
- **Nextcloud** — инструменты Assistant/Context Agent доступны через MCP, бэкенд self-hosted или OpenAI-compatible.

Оговорка: сменяемость модели ≠ сменяемость governance. Права и аудит остаются привязаны к контентному или поисковому ядру.

## Источники

- [Box: контроли для AI-агентов (июль 2026)](https://www.businesswire.com/news/home/20260721998096/en/Box-Unveils-New-Controls-to-Secure-AI-Agents-Operating-Across-Enterprise-Content) · [разбор SiliconANGLE](https://siliconangle.com/2026/07/21/box-adds-security-controls-govern-ai-agents-working-enterprise-content/)
- [Nextcloud: Context Chat (админ-мануал, ограничение File Access Control)](https://docs.nextcloud.com/server/latest/admin_manual/ai/app_context_chat.html)
- [Notion: данные, доступные владельцу workspace](https://www.notion.com/help/data-accessible-by-your-workspace-owner) · [Content search](https://www.notion.com/help/admin-content-search)
- [Google Drive: папки с limited и expansive access](https://developers.google.com/workspace/drive/api/guides/limited-expansive-access)
- [Microsoft: Restricted SharePoint Search](https://learn.microsoft.com/en-us/sharepoint/restricted-sharepoint-search)
- [Atlassian: типы коннекторов Teamwork Graph](https://support.atlassian.com/organization-administration/docs/rovo-connector-types/) · [как синхронизируются права коннекторов](https://support.atlassian.com/organization-administration/docs/how-connector-permissions-are-kept-in-sync/)
- [Glean: permissions-aware подход](https://www.glean.com/perspectives/security-permissions-aware-ai)
- [Salesforce ограничил Slack API для сторонних LLM (Computerworld)](https://www.computerworld.com/article/4005509/salesforce-changes-slack-api-terms-to-block-bulk-data-access-for-llms.html)
