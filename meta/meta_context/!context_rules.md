---
title: "Правила работы с контекстом проекта SVAIB"
updated: 2025-10-21
scope: "always"
priority: critical
---

# Правила работы с контекстом SVAIB

## Файлы проекта

### Стратегия и управление
- **!context_rules.md** - правила работы с контекстом, навигация по проекту
- **viktor_profile.md** - профиль Виктора Соломоника (компетенции, ценности, мотивация)
- **project_overview.md** - целостное описание проекта SVAIB
- **execution_plan.md** - OKR и план исполнения проекта
- **weekly_progress.md** - трекер "камней недели" и прогресса
- **technical_infrastructure.md** - серверы, API, домены, инфраструктура
- **investment_strategy.md** - стратегия привлечения инвестиций
- **storage_system.md** - система хранения проекта (Git + Google Drive)

### Продукт и клиенты
- **mvp_overview.md** - описание MVP продукта svaib
- **implementation_AI_strategies.md** - стратегии внедрения AI в бизнесе
- **smb_roles_tasks_research.md** - исследование задач для AI-ролей в малом бизнесе
- **design-cheatsheet.md** - дизайн-система svaib

### Внутренняя мастерская
- **agents_catalog.md** - каталог AI-агентов команды SVAIB

### Публичная активность
- **osvaivaemsia_meetings.md** - интерактивные встречи с Никитой

---

## Матрица релевантности

| Тип запроса | Приоритетные файлы | Дополнительные |
|-------------|-------------------|----------------|
| О создателе/Викторе | viktor_profile.md | project_overview.md |
| О проекте SVAIB | project_overview.md | viktor_profile.md |
| Планирование/OKR | execution_plan.md | weekly_progress.md |
| Еженедельный прогресс | weekly_progress.md | execution_plan.md |
| Техническая инфраструктура | technical_infrastructure.md | - |
| Архитектура (Dify+n8n) | technical_infrastructure.md | - |
| Серверы и домены | technical_infrastructure.md | - |
| API и интеграции | technical_infrastructure.md | - |
| Безопасность | technical_infrastructure.md | - |
| Стоимость инфраструктуры | technical_infrastructure.md | project_overview.md |
| Инвестиции и финансирование | investment_strategy.md | project_overview.md |
| Оценка проекта | investment_strategy.md | execution_plan.md |
| AI-агенты команды | agents_catalog.md | - |
| Продукт svaib (MVP) | mvp_overview.md | project_overview.md |
| Стратегии внедрения AI | implementation_AI_strategies.md | - |
| Задачи для ролей в SMB | smb_roles_tasks_research.md | mvp_overview.md |
| Дизайн-система | design-cheatsheet.md | - |
| Встречи с Никитой | osvaivaemsia_meetings.md | - |
| Организация файлов / Где что хранится | storage_system.md | technical_infrastructure.md |

---

## Принцип работы с контекстом

- **Файлы = постоянные сущности** с уникальными именами
- **Папки = временная организация** которая может меняться
- **Ссылки между файлами** - только по именам, не по путям
- При перемещении файлов между папками - контекст не меняется

---

## Правила обновления контекста

### Single Source of Truth
- Каждый факт хранится в ОДНОМ файле
- Другие файлы ссылаются на имя файла, но не копируют содержимое
- При изменении → обновляем только один источник

### Когда обновлять
- **project_overview.md** - изменение стратегии/видения
- **execution_plan.md** - корректировка OKR/планов
- **weekly_progress.md** - еженедельно (итоги недели)
- **technical_infrastructure.md** - изменение архитектуры/инфраструктуры
- **investment_strategy.md** - обновление инвестиционной стратегии
- **mvp_overview.md** - изменения в продукте
- Остальные файлы - при появлении новой значимой информации

### Принципы обновления
- Дата в YAML frontmatter (`updated:`) = дата последнего изменения
- Краткость: только важный контекст, без воды
- Консистентность между связанными файлами
- Ссылки на другие файлы - только по именам, без путей

---

**Последнее обновление:** 21 октября 2025
