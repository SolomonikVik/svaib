---
title: "svaib — дизайн-гайд для standalone HTML-артефактов"
updated: 2026-05-01
version: 1
scope: "publications, client_materials, internal_artifacts"
priority: high
---

# Brand — HTML-артефакты

## Кратко

Как делаем самостоятельные HTML-страницы для клиентских intro, методологических схем, внутренних драфтов и визуальных one-pager'ов. Это не дизайн-система сайта svaib.com и не гайд для статичных диаграмм. Это практический канон для файлов вида `something.html`, которые можно открыть локально в браузере и сразу показать Виктору, клиенту или команде.

Палитра и философия — в [brand.md](brand.md). Сайт — отдельно в [brand-design-web.md](brand-design-web.md). Статичные схемы/PNG/PDF — отдельно в [brand-design-diagrams.md](brand-design-diagrams.md).

## Связанные файлы

- [brand.md](brand.md) — палитра, логотип, философия, tone of voice
- [brand-design-web.md](brand-design-web.md) — сайт svaib.com и web-дизайн продукта
- [brand-design-diagrams.md](brand-design-diagrams.md) — схемы-картинки через HTML → Puppeteer → PNG/PDF
- [../../framework/methodology/metrics/intro-for-client-v2.html](../../framework/methodology/metrics/intro-for-client-v2.html) — пример клиентского intro
- [../../framework/_inbox/scaffold/2026-05-01_scaffold-draft-v1.html](../../framework/_inbox/scaffold/2026-05-01_scaffold-draft-v1.html) — пример структурного one-pager

---

## Что это за формат

Standalone HTML-артефакт — один файл, который:

- открывается локально без dev-сервера;
- содержит весь CSS внутри `<style>`;
- может использовать Google Fonts, но не зависит от сборки Next.js/Tailwind;
- объясняет одну идею, документ, модель или клиентский процесс;
- выглядит достаточно аккуратно, чтобы показать наружу без отдельного дизайнера.

Типовые задачи:

- клиентский intro по методологии (`metrics`, `meeting analysis`, onboarding);
- визуализация draft-модели (`scaffold`, `fern`, architecture);
- внутренний review artifact для обсуждения;
- “презентация в одну страницу”, которую проще читать в браузере, чем в markdown.

## Базовая эстетика

**Формула:** тёмное рабочее поле + светлая типографика + teal как структура + pink как редкий акцент.

HTML-артефакты должны ощущаться как “серьёзная схема, которую приятно читать”, а не как лендинг и не как слайдовая открытка.

### Цвета

| Роль | HEX | Использование |
|---|---|---|
| Background | `#071015` | Общий фон страницы |
| Soft background | `#0B161B` | Подложки, участки второго уровня |
| Panel | `#101D23` | Основные секции и карточки |
| Panel 2 | `#13262D` | Карточки внутри секций |
| Line | `#25444D` | Границы карточек |
| Teal | `#00B4A6` | Структура, линии, номера, основные акценты |
| Pink | `#FF4D8D` | Один-два смысловых акцента, `ai` в логотипе |
| Yellow | `#FFD600` | Редкий статусный сигнал / warning |
| Text | `#F0F8F7` | Основной текст на тёмном фоне |
| Muted | `#A7BABD` | Вторичный текст |
| Soft text | `#789096` | Служебный текст, подписи |

**Правило pink:** розовый не является структурным цветом. Использовать для:

- `ai` и точки в логотипе;
- одного проблемного/важного блока;
- одного номера секции или label, если нужен фокус.

Не использовать pink как массовый цвет карточек, фон страницы или постоянный цвет заголовков.

## Типографика

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&amp;family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@400;500;600&amp;display=swap" rel="stylesheet">
```

| Элемент | Шрифт | Размер |
|---|---|---|
| H1 | Sora 800 | `clamp(44px, 6vw, 82px)` |
| H2 | Sora 800 | `clamp(25px, 3vw, 38px)` |
| H3 / карточки | Sora 700 | 13–19px |
| Основной текст | Inter 400–500 | 14–19px |
| Пути / код | JetBrains Mono 500–600 | 12–15px |
| Chips / labels | Inter или JetBrains Mono 700–800 | 11–13px |

**Не использовать отрицательный letter-spacing.** В этих артефактах текст должен быть ровным и спокойным.

## Базовый каркас страницы

Рекомендуемая структура:

1. `top-line` — тонкая teal-полоска сверху.
2. `nav` — логотип `svaib.` слева, chips справа.
3. `hero` — слева тезис/H1, справа визуальная мини-карта или flow.
4. `summary-strip` — 3 коротких тезиса.
5. `section` — 3-6 крупных смысловых секций.
6. `footer` — источник/статус артефакта + логотип.

Минимальный CSS-скелет:

```css
:root {
  --bg: #071015;
  --panel: #101d23;
  --panel-2: #13262d;
  --line: #25444d;
  --teal: #00b4a6;
  --pink: #ff4d8d;
  --text: #f0f8f7;
  --muted: #a7babd;
  --radius: 8px;
  --shadow: 0 22px 80px rgba(0, 0, 0, 0.34);
}

* { box-sizing: border-box; }
html { background: var(--bg); color: var(--text); font-family: Inter, sans-serif; letter-spacing: 0; }
body { margin: 0; min-height: 100vh; background: var(--bg); color: var(--text); }
.top-line { height: 3px; background: var(--teal); box-shadow: 0 0 28px rgba(0, 180, 166, 0.55); }
.page { width: min(1240px, calc(100vw - 36px)); margin: 0 auto; padding: 26px 0 60px; }
.section { margin-top: 22px; padding: 28px; border: 1px solid var(--line); border-radius: var(--radius); background: rgba(16, 29, 35, 0.92); box-shadow: var(--shadow); }
```

## Компоненты

### Логотип

```html
<div class="logo">
  <span class="teal">sv</span><span class="pink">ai</span><span class="teal">b</span><span class="pink">.</span>
</div>
```

```css
.logo {
  font-family: Sora, Inter, sans-serif;
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
}
.teal { color: var(--teal); }
.pink { color: var(--pink); }
```

### Chips

Для статуса страницы, аудитории, типа артефакта:

```css
.chip {
  border: 1px solid rgba(0, 180, 166, 0.28);
  border-radius: 999px;
  color: var(--muted);
  background: rgba(11, 22, 27, 0.76);
  padding: 7px 11px;
  font-size: 12px;
  font-weight: 600;
}
.chip.pink {
  border-color: rgba(255, 77, 141, 0.36);
  color: #ffc1d6;
}
```

### Hero

Hero должен сразу показывать объект страницы, а не быть декоративным. Справа лучше размещать мини-карту: структура папок, pipeline, стадии, root-map.

```css
.hero {
  display: grid;
  grid-template-columns: 0.8fr 1.2fr;
  gap: 28px;
  align-items: stretch;
  margin-bottom: 26px;
}
.hero-panel {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(0, 180, 166, 0.28);
  border-radius: var(--radius);
  background: rgba(16, 29, 35, 0.9);
  box-shadow: var(--shadow);
  padding: 26px;
}
```

### Section header

```css
.section-head {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
  align-items: start;
  margin-bottom: 18px;
}
.num {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: var(--bg);
  border: 2px solid var(--teal);
  color: var(--teal);
  font-family: Sora, Inter, sans-serif;
  font-size: 15px;
  font-weight: 800;
}
.num.pink {
  border-color: var(--pink);
  color: var(--pink);
}
```

### Cards / panels

Карточки — для повторяемых элементов: проблемы, опоры, файлы, шаги. Не вкладывать карточки в карточки без необходимости.

```css
.card {
  border: 1px solid rgba(0, 180, 166, 0.2);
  border-radius: var(--radius);
  background: var(--panel-2);
  padding: 15px;
}
.card.pink {
  border-color: rgba(255, 77, 141, 0.3);
  border-left: 5px solid var(--pink);
  background: #151821;
}
```

### Folder / code blocks

Для структур папок использовать JetBrains Mono и увеличенный размер, если структура — главный объект страницы.

```css
.folder-tree {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: #081318;
  padding: 18px;
}
.tree-code {
  display: block;
  margin: 0;
  color: #d7eeee;
  font-family: JetBrains Mono, "SFMono-Regular", Consolas, monospace;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}
```

Если папки — главное содержание первого экрана, делать имена не меньше `15px`, а колонку пути шире:

```css
.root-item {
  display: grid;
  grid-template-columns: 150px 1fr;
  gap: 14px;
  padding: 12px 0;
}
.path {
  color: #d7eeee;
  font-family: JetBrains Mono, monospace;
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
}
```

## Layout-паттерны

### 1. Client intro

Подходит для объяснения методологии клиенту.

Порядок:

1. Hero: что строим и для кого.
2. Summary strip: 3 главных тезиса.
3. Проблема: почему старый подход ломается.
4. Решение: 3-4 опоры.
5. Как это выглядит в пространстве клиента.
6. Реальный пример / pipeline.
7. Что нужно от клиента.
8. Следующий шаг.

Пример: [intro-for-client-v2.html](../../framework/methodology/metrics/intro-for-client-v2.html).

### 2. Structural map

Подходит для scaffold, architecture, framework-моделей.

Порядок:

1. Hero: слева тезис, справа крупная структура.
2. Summary strip: 3 смысловых вывода.
3. Детализация ключевой единицы.
4. Миссии файлов / блоков.
5. Универсальный принцип.
6. Открытый вопрос или next step.

Пример: [2026-05-01_scaffold-draft-v1.html](../../framework/_inbox/scaffold/2026-05-01_scaffold-draft-v1.html).

### 3. Growth / staged model

Подходит для fern, maturity model, rollout.

Порядок:

1. Hero: идея роста.
2. Горизонтальная или адаптивная сетка стадий.
3. Карта применения у клиента.
4. Пример одной ветки.
5. Правила, которые удерживают модель.

Пример: [2026-04-30_fern-scaffold-growth.html](../../framework/_inbox/scaffold/2026-04-30_fern-scaffold-growth.html).

## Responsive

Минимальные правила:

```css
@media (max-width: 1080px) {
  .hero,
  .two-col {
    grid-template-columns: 1fr;
  }
  .cards-4,
  .cards-5,
  .pipeline {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .page {
    width: min(100vw - 24px, 1240px);
    padding-top: 18px;
  }
  .nav,
  .footer {
    display: block;
  }
  .cards-2,
  .cards-3,
  .cards-4,
  .cards-5,
  .pipeline {
    grid-template-columns: 1fr;
  }
  .section {
    padding: 22px 18px;
  }
}
```

## Протокол создания HTML-артефакта

1. **Прочитать источник.** Если есть `.md` рядом — он источник смысла. HTML не должен добавлять новую методологию без явного решения.
2. **Выбрать layout-паттерн.** Client intro / structural map / staged model.
3. **Собрать один standalone HTML.** CSS внутри `<style>`, без dev-сервера.
4. **Сделать первый экран содержательным.** Главный объект должен быть виден сразу: папки, pipeline, стадии, карта.
5. **Проверить размеры ключевого объекта.** Если структура папок — главное, она должна быть крупной, не служебной.
6. **Прогнать `xmllint`.**
7. **Открыть через `open path/to/file.html` и посмотреть глазами.**

Команды проверки:

```bash
xmllint --html --noout path/to/file.html
tidy -utf8 -q -e path/to/file.html
```

`tidy` может ругаться на HTML5-атрибуты (`charset`, `crossorigin`, `style type`). Это warnings, не блокер. Блокер — незакрытые теги, неэкранированные `&` в ссылках Google Fonts, сломанная структура.

## Антипаттерны

| Ошибка | Почему плохо | Что делать |
|---|---|---|
| Главный объект мелкий | Пользователь не видит главное, страница выглядит как декор | Укрупнить структуру / pipeline / карту в hero |
| Текст как длинный markdown | HTML не использует визуальную иерархию | Разбить на cards, strips, flow, sections |
| Pink везде | Теряется брендовая дисциплина и фокус | Pink только для одного-двух акцентов |
| Hero без предмета | Получается лендинг вместо рабочего артефакта | Справа показывать карту, структуру, stages, pipeline |
| Слишком много декоративных эффектов | Снижается доверие к методологии | Тёмное поле, строгие карточки, минимум украшений |
| Карточки внутри карточек | Визуальный шум и тяжесть | Секции как контейнеры, карточки только для повторяемых элементов |
| Маленький mono-текст | Пути файлов становятся нечитаемыми | Для важных путей 15px+, line-height 1.45+ |
| Новый смысл в HTML | Появляется вторая правда рядом с markdown | Новые решения сначала фиксировать в source `.md` |

## Что не покрывает этот гайд

- Сайт svaib.com и production UI → [brand-design-web.md](brand-design-web.md) + `dev/`
- Статичные диаграммы для постов/PDF → [brand-design-diagrams.md](brand-design-diagrams.md)
- PDF-документы → [brand-design-pdf.md](brand-design-pdf.md)
- Слайды → [brand-design-presentation.md](brand-design-presentation.md)

## Реализации

| Артефакт | Путь | Тип |
|---|---|---|
| Metrics intro v2 | [../../framework/methodology/metrics/intro-for-client-v2.html](../../framework/methodology/metrics/intro-for-client-v2.html) | Client intro |
| Scaffold draft v1 | [../../framework/_inbox/scaffold/2026-05-01_scaffold-draft-v1.html](../../framework/_inbox/scaffold/2026-05-01_scaffold-draft-v1.html) | Structural map |
| Fern scaffold growth | [../../framework/_inbox/scaffold/2026-04-30_fern-scaffold-growth.html](../../framework/_inbox/scaffold/2026-04-30_fern-scaffold-growth.html) | Staged model |
