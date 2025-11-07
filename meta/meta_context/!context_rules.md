---
title: "Правила работы с контекстом проекта SVAIB"
updated: 2025-11-07
version: 5
scope: "always"
priority: critical
---

# Правила работы с контекстом SVAIB

## Файлы проекта

### Стратегия и управление
- **!context_rules.md** - правила работы с контекстом, навигация по проекту
- **!!custom_instructions.md** - кастомные инструкции для AI-ассистентов в проекте
- **viktor_profile.md** - профиль Виктора Соломоника (компетенции, ценности, мотивация)
- **nikita_profile.md** - профиль Никиты (со-основатель, продажи/маркетинг/коммерция)
- **project_overview.md** - целостное описание проекта SVAIB
- **execution_plan.md** - OKR и план исполнения проекта
- **weekly_progress.md** - трекер "камней недели" и прогресса
- **technical_infrastructure.md** - серверы, API, домены, инфраструктура
- **investment_strategy.md** - стратегия привлечения инвестиций
- **storage_system.md** - система хранения проекта (Git + Google Drive)

### Продукт и клиенты
- **product_overview.md** - описание продукта svaib (управленческий AI для встреч)
- **presentation_methodology.md** - методология "Презентажка" (управленческий фреймворк)
- **implementation_AI_strategies.md** - стратегии внедрения AI в бизнесе
- **design-cheatsheet.md** - дизайн-система svaib

### Внутренняя мастерская
- **agents_catalog.md** - каталог AI-агентов команды SVAIB

### Исследования
- **smb_meetings_research.md** - исследование планерок в малом бизнесе
- **smb_roles_tasks_research.md** - исследование задач для AI-ролей в малом бизнесе

### Публичная активность
- **osvaivaemsia_meetings.md** - интерактивные встречи с Никитой
- **svaib_presentation_guide.md** - гайд по стилю презентаций svaib

---

## Матрица релевантности

| Тип запроса | Приоритетные файлы | Дополнительные |
|-------------|-------------------|----------------|
| О создателе/Викторе | viktor_profile.md | project_overview.md |
| О партнере/Никите/команде | nikita_profile.md | project_overview.md |
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
| Продукт svaib (описание) | product_overview.md | presentation_methodology.md |
| Методология "Презентажка" | presentation_methodology.md | product_overview.md |
| Исследование планерок в МСБ | smb_meetings_research.md | product_overview.md |
| Стратегии внедрения AI | implementation_AI_strategies.md | - |
| Задачи для ролей в SMB | smb_roles_tasks_research.md | product_overview.md |
| Дизайн-система | design-cheatsheet.md | - |
| Встречи с Никитой | osvaivaemsia_meetings.md | - |
| Стиль презентаций / Визуал слайдов | svaib_presentation_guide.md | - |
| Организация файлов / Где что хранится | storage_system.md | technical_infrastructure.md |

---

## Принцип работы с контекстом

- **Файлы = постоянные сущности** с уникальными именами
- **Папки = временная организация** которая может меняться
- **Ссылки между файлами** - только по именам, не по путям
- При перемещении файлов между папками - контекст не меняется

---

## Naming Conventions

### Типы файлов
- **Обычные файлы:** короткие названия (`project_overview.md`, `execution_plan.md`)
- **Исследования:** с суффиксом `_research.md` → размещаются в `meta/research/`
  - Примеры: `smb_meetings_research.md`, `competitors_research.md`
- **Архивные версии:** с префиксом версии → размещаются в `meta/z_archive/`
  - Формат: `{original_name}_v{N}_{reason}.md`
  - Пример: `mvp_overview_v1_platform.md`

---

## Правила обновления контекста

### Single Source of Truth
- Каждый факт хранится в ОДНОМ файле
- Другие файлы ссылаются на имя файла, но не копируют содержимое
- При изменении → обновляем только один источник

### Правила обновления

**Когда обновлять файл:**
1. **Прямое изменение** - появилась новая информация по теме файла
2. **Устранение коллизии** - связанный файл изменился, текущий стал противоречить ему

**Как обновлять:**
- Инкремент `version` в YAML (было N → стало N+1)
- Обновление `updated` на текущую дату
- После обновления → проверка связанных файлов на новые коллизии
- Ссылки между файлами только по именам, без путей

---
