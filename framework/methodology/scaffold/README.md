# Scaffold methodology

Методология слоя `scaffold`: архитектура клиентского каркаса данных, спецификации файлов и папок, канон README, ключевые шаблоны, развёртывание у клиента и открытые вопросы.

**Статус:** рабочий каркас. Заполняется из существующих черновиков `framework/scaffold/` и `framework/_inbox/scaffold/`.

**Граница:** эта папка — framework-only. Клиенту отгружается чистый каркас из `framework/scaffold/`; методологические файлы отсюда клиенту не копируются. Автоматизация развёртывания живёт отдельно в `framework/skills/scaffold/`.

## Порядок чтения

1. [01_architecture.md](01_architecture.md) — как устроен scaffold и почему
2. [02_file-spec.md](02_file-spec.md) — как устроен файл Second AI Brain
3. [02_folder-spec.md](02_folder-spec.md) — как устроена папка scaffold
4. [02_readme-spec.md](02_readme-spec.md) — как устроен README как карта папки
5. [02_file-templates.md](02_file-templates.md) — канон ключевых файлов scaffold
6. [deployment.md](deployment.md) — как разворачиваем у клиента
7. [open-questions.md](open-questions.md) — что ещё не решено

## Файлы

| Файл | Миссия |
|---|---|
| [01_architecture.md](01_architecture.md) | Архитектура scaffold: требования, базовые принципы, модель верхнего уровня. |
| [02_file-spec.md](02_file-spec.md) | Спецификация файла Second AI Brain: имя, YAML, заголовки, связи, ограничения. |
| [02_folder-spec.md](02_folder-spec.md) | Спецификация папки scaffold: имя, миссия, триггер появления, состав. |
| [02_readme-spec.md](02_readme-spec.md) | Канон README как карты папки: структура, порядок чтения, навигация. |
| [02_file-templates.md](02_file-templates.md) | Канон ключевых файлов scaffold: overview, active, backlog, progress, decisions и др. |
| [deployment.md](deployment.md) | Правила первичного развёртывания scaffold у клиента: что создаётся при старте, что появляется по триггеру живой работы. |
| [open-questions.md](open-questions.md) | Нерешённые вопросы, закрываемые по мере полевой проверки. |
