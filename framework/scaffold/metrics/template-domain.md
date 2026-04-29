# Semantic model: <domain>

Шаблон domain-файла. Копировать как `<domain>.md` (`finance.md`, `sales.md`, `operations.md`, `people.md`). Заполнять под бизнес CEO.

Семантическое описание домена для AI-агента: какие источники, какие метрики, какие маршруты под типовые вопросы. Числа не хранятся здесь — только семантика. Расчёты идут через Python (xlsx-skill) поверх файлов в `source/`.

## datasets

Источники данных домена. Один dataset = один лист в xlsx (или один CSV).

```
- name: <dataset_id>           # стабильный ID, snake_case
  source: source/<file>.xlsx#<sheet>
  primary_key: <column>
  description: <что это>
  synonyms: [<как CEO называет в речи>]
  fields:
    - name: <field_id>
      expression: <column_name>          # имя колонки в xlsx
      description: <что это, единица измерения>
      synonyms: [<как CEO называет>]
      is_time: <true|false>              # для полей-дат
```

## relationships

Связи между датасетами (если есть). Опциональная секция.

```
- name: <relationship_id>
  from: <dataset_id>
  to: <dataset_id>
  from_columns: [<column>]
  to_columns: [<column>]
```

## metrics

Бизнес-определения метрик. Каждая метрика = один паспорт.

```
- name: metric_<id>            # стабильный ID, не привязан к колонкам
  version: 1                   # инкремент при изменении формулы
  owner: <кто отвечает за определение>
  expression: <SQL или Python через датасеты и поля>
  formula_human: <объяснение для CEO без кода>
  description: <бизнес-смысл, известные нюансы>
  synonyms: [<как CEO называет в речи>]
```

## routes

Готовые решения типовых вопросов CEO. Триггер → query → freshness → формат ответа.

```
- name: route_<id>
  trigger: [<фраза CEO 1>, <фраза 2>]
  query: |
    <SQL или Python, использует metric_<id> и dataset_<id>>
  freshness: <snapshot|live|hybrid>
  response_format: <число | таблица | narrative + цифра>
```

## Правила заполнения

**Стабильные ID.** Маршруты ссылаются на `metric_<id>`, не на физические колонки. Если колонка переименуется — поменяется только `expression` метрики, маршруты не сломаются.

**Версия метрики.** При изменении формулы — `version` инкрементируется. По trace всегда видно, на какой версии паспорта собран ответ.

**Синонимы — из речи клиента.** Не выдумывать. Аудит синонимов по транскриптам — обязателен.

**Iron Law.** Маршрут добавляется, когда вопрос задавался ≥2 раз и есть проверенный ответ. Один разовый удачный ответ маршрутом не становится.
