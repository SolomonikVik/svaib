---
title: "svaib — дизайн-гайд для схем и диаграмм"
updated: 2026-03-19
version: 1
scope: "publications, posts"
priority: high
---

# Brand — Схемы и диаграммы

## Кратко

Как делаем схемы-картинки для постов и документов: стек, принципы, ошибки, протокол. Выводы из создания диаграммы «Архитектура аналитика встреч» (март 2026). Палитра и философия — в [brand.md](brand.md).

## Связанные файлы

- [brand.md](brand.md) — палитра, логотип, философия
- [brand-design-pdf.md](brand-design-pdf.md) — дизайн-гайд для PDF-документов
- Эталон HTML: [_examples/diagram-meeting-analytics.html](_examples/diagram-meeting-analytics.html)

---

## Стек

**HTML + CSS → Puppeteer → PDF + PNG.**

Почему не weasyprint (как для документов): Puppeteer рендерит через Chromium — Google Fonts грузятся надёжнее, SVG-стрелки отрисовываются корректно.

```
HTML (схема) → Puppeteer (headless Chrome) → PDF + PNG
```

**Установка:** `cd /tmp && npm install puppeteer`

**Скрипт конвертации** (`/tmp/convert-pdf.js`):
```js
const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 788 });
  await page.goto('file:///path/to/diagram.html', { waitUntil: 'networkidle0', timeout: 30000 });
  await page.evaluateHandle('document.fonts.ready');
  await new Promise(r => setTimeout(r, 2000)); // ждём шрифты
  await page.pdf({ path: 'output.pdf', width: '1400px', height: '788px', printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 } });
  await page.screenshot({ path: 'output.png', clip: { x: 0, y: 0, width: 1400, height: 788 } });
  await browser.close();
})();
```

---

## Формат и размеры

| Параметр | Значение | Почему |
|----------|---------|--------|
| Ориентация | **Landscape** (горизонтальная) | Для постов — горизонтальные картинки лучше |
| Размер | 1400 × 788 px | Близко к 16:9, хорошо для соцсетей |
| `@page` | `size: 1400px 788px; margin: 0;` | Без полей |

---

## Палитра для схем

Из [brand.md](brand.md), расширенное использование:

| Элемент | Цвет | HEX |
|---------|------|-----|
| Рамки блоков, стрелки, теги | Teal | `#00B4A6` |
| Заголовки блоков | Dark Teal | `#008B7F` |
| Основной текст | Dark Blue | `#2C3E50` |
| Вторичный текст | Gray | `#6B7280` |
| Фон блоков | Light Teal | `#F0FDFB` |
| **Акцентный блок** (выжимка и т.п.) | Pink рамка + фон | `#FF4D8D` + `#FFF5F8` |
| Лейблы-акценты | Pink текст | `#FF4D8D` |
| Фон страницы | Белый | `#FFFFFF` |

**Правило:** розовый используется для **одного ключевого блока** (центральный, самый важный) — рамка, фон, заголовок. Остальные блоки — teal. Это создаёт визуальный фокус.

---

## Шрифты

```html
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800&family=Roboto:wght@400;500&display=swap" rel="stylesheet">
```

| Элемент | Шрифт | Размер |
|---------|-------|--------|
| Заголовки блоков | Montserrat 800 | 22–34px |
| Лейблы | Roboto 500 | 12–13px |
| Теги (pills) | Roboto 500 | 11px |
| Основной текст | Roboto 400 | 13–16px |
| Буллеты | Roboto 400 | 13px |

---

## Элементы

### Блоки (карточки)
- `border: 2.5px solid #00B4A6`
- `border-left: 7px solid #00B4A6` — утолщённая левая полоса (маркер бренда)
- `border-radius: 14px`
- `background: #F0FDFB`
- Акцентный блок: `border: 3px solid #FF4D8D`, `border-left: 8px solid #FF4D8D`, `background: #FFF5F8`

### Теги (pills)
```css
.tag { display: inline-block; font-size: 11px; border-radius: 6px; padding: 3px 8px; margin: 2px 3px; }
.tag-teal { background: #E0F7F5; color: #008B7F; border: 1px solid #00B4A6; }
.tag-pink { background: #FFE5ED; color: #FF4D8D; border: 1px solid #FF4D8D; }
.tag-gray { background: #F3F4F6; color: #6B7280; border: 1px solid #D1D5DB; }
```

### Стрелки (SVG)
- Bezier curves (`<path>` с `C` командой) — плавные, не ломаные
- `stroke="#00B4A6" stroke-width="2.5-3"`
- Наконечники: `<polygon>` треугольники с `fill="#00B4A6"`
- Стрелка к розовому блоку: `fill="#FF4D8D"`

### Логотип
```html
<!-- Правый верхний угол, мелкий -->
<div style="position:absolute; top:12px; right:36px; font-family:'Montserrat'; font-weight:700; font-size:14px;">
  <span style="color:#00B4A6;">sv</span><span style="color:#FF4D8D;">ai</span><span style="color:#00B4A6;">b</span><span style="color:#FF4D8D;">.</span>
</div>
```

### Футер
Мелкий `svaib.` (14px, gray #9CA3AF, розовая точка) — правый нижний угол. Опционален если логотип наверху.

---

## Позиционирование блоков

### КРИТИЧНО: vertical centering в Puppeteer

**CSS flexbox/grid centering НЕ РАБОТАЕТ** с `position: absolute` в Puppeteer:
- `display: flex; justify-content: center;` — **игнорируется**
- `display: grid; place-items: center;` — **игнорируется**
- `display: table; vertical-align: middle;` — **игнорируется**
- `position: absolute; top: 50%; transform: translateY(-50%)` — **игнорируется**

**Решение: ручной `padding-top`.** Вычислить высоту контента, вычесть из высоты блока, разделить на 2.

```
padding-top = (block_height - content_height) / 2
```

Пример: блок 268px, контент ~130px → `padding-top: 69px`.

**Это главная ошибка сессии** — потрачено 20 минут на попытки CSS centering. В следующий раз сразу считать padding.

### Подход к координатам

Для схем с абсолютным позиционированием:

1. **Определить «коридор»** — вертикальные границы (задаются самыми высокими/широкими элементами)
2. **Все колонки выровнять по коридору** — top и bottom совпадают
3. **Каждый блок — `position: absolute`** с явными `left`, `top`, `width`, `height`
4. **Стрелки — отдельный SVG** поверх всего (`pointer-events: none; z-index: 5`)
5. **Координаты стрелок** вычислять от краёв блоков: `right_edge = left + width`, `center_y = top + height/2`

---

## Протокол создания схемы

### 1. Согласование ASCII-схемой
Показать Виктору текстовую схему (ASCII art) со стрелками. Согласовать:
- Блоки и их содержание
- Направление потока (горизонтальное/вертикальное)
- Какие аннотации внутри блоков

### 2. Бренд-гайд
Прочитать `meta/marketing/brand.md` + этот файл. Ключевое:
- Montserrat + Roboto
- Teal + Pink (pink = один акцентный блок)
- Утолщённая левая полоса на карточках

### 3. HTML за одну итерацию
- Все блоки через `position: absolute` с inline styles
- Vertical centering через **ручной padding-top** (не CSS flex/grid!)
- SVG стрелки — bezier curves
- Проверить все тексты, теги, лейблы — **не обрезать контент**

### 4. Рендер + проверка
```bash
cd /tmp && node convert-pdf.js
```
- Открыть PNG, проверить визуально
- Проверить: текст не обрезан, блоки не перекрываются, стрелки попадают в блоки

### 5. Показать Виктору
Открыть PDF: `open path/to/file.pdf`

---

## Антипаттерны (что НЕ делать)

| Ошибка | Почему плохо | Что делать |
|--------|-------------|-----------|
| CSS flex/grid centering с position:absolute | Не работает в Puppeteer | Ручной padding-top |
| Обрезать контент ради «чистоты» | Контент = ценность схемы | Все тексты, теги, аннотации — обязательны |
| Несколько итераций CSS экспериментов | Тратит 20 минут | Сразу ручной padding, одна итерация |
| Маленький текст | Нечитаемо в посте | Заголовки 22–34px, текст 13–16px |
| Весь в teal без акцента | Нет визуального фокуса | Один ключевой блок — розовый |
| Вертикальная ориентация | Не подходит для постов | Всегда landscape для соцсетей |

---

## Реализации

| Схема | HTML-исходник | PDF | Дата |
|-------|-------------|-----|------|
| Архитектура аналитика встреч | [_examples/diagram-meeting-analytics.html](_examples/diagram-meeting-analytics.html) | [posts/2026-03-19_фиаско-аналитик-встреч_диаграмма.pdf](posts/2026-03-19_фиаско-аналитик-встреч_диаграмма.pdf) | 2026-03-19 |
