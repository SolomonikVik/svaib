---
title: "svaib — дизайн-гайд для иллюстраций"
updated: 2026-04-03
version: 3
scope: "publications"
priority: medium
---

# Brand — Иллюстрации

## Кратко

Как генерируем иллюстрации для слайдов и материалов svaib: стиль, шаблон промпта, библиотека форм, проверенные примеры. Палитра и философия — в [brand.md](brand.md). Параметры картинок на слайдах (размеры, обводка, тень) — в [brand-design-presentation.md](brand-design-presentation.md).

## Связанные файлы

- [brand.md](brand.md) — палитра, логотип, философия, универсальные правила
- [brand-design-presentation.md](brand-design-presentation.md) — как делаем слайды (параметры картинок, лейауты)

---

## Стиль иллюстраций

**Формула:** 60% Bauhaus (структура, геометрия) + 40% Matisse/Kandinsky (органика, цвет как эмоция)

Современная flat-иллюстрация с глубиной. Геометрические формы + органические плавные линии. Ограниченная палитра (teal, dark blue, yellow, pink = только акцент).

**Характер бренда:** О серьёзном — с улыбкой. Friendly, playful детали приветствуются.

---

## Роль арт-директора

AI арт-директор получает идею слайда и превращает её в промпт для AI-иллюстратора.

### Процесс

1. **Входные данные:** идея визуала, заголовок слайда, 2-3 тезиса, контекст выступления
2. **2 концепции:** предложить два визуальных подхода (2-3 предложения каждый)
3. **После выбора:** собрать промпт по шаблону ниже

---

## Критическое правило: краткость

AI-иллюстратор работает лучше с короткими, поэтичными промптами.

**Стремись к:** простота, воздух, фокус на свете и цвете, минимализм описания.

**Избегай:** перечисление деталей, техническая детализация, избыток прилагательных.

**Правило:** промпт длиннее 200 слов — упрости.

---

## Библиотека форм

Справочник для понимания, какие формы использовать в SUBJECT. Не копировать в промпт напрямую.

| Объект | Как изображать |
|--------|---------------|
| AI/Роботы | Geometric circles + rounded rectangles, gradient fills, smooth friendly edges |
| Люди | Simplified organic forms, smooth flowing lines, minimal detail, natural postures |
| Технологии | Clean geometric rectangles with slight rounding, screen glow effects |
| Абстракции (данные, связи) | Flowing organic lines connecting elements, geometric nodes, gradient trails |

### Декоративные элементы

**Базовые (всегда):**
- Floating geometric shapes (круги, треугольники, прямоугольники) — 5-15% от главных элементов
- Organic flowing lines в стиле Matisse
- Sparkles and subtle particles — мерцающие элементы для "магии"

**Специфичные (по теме):**
- Data/Analytics → abstract charts, checkmarks, graph elements
- Connections/Network → network nodes, linking lines
- Tech/Code → simplified code snippets, binary patterns
- Learning → flowing text fragments, page elements

---

## Шаблон промпта для AI-иллюстратора

Блоки помечены: **фикс** = копировать как есть, **заполнить** = адаптировать под задачу.

```
Create a contemporary illustration inspired by the geometry of the Bauhaus,
the organic, flowing forms of Matisse, and the expressive color composition
of Kandinsky, capturing the poetic dialogue between [тема] and light.

STYLE INFLUENCES:
- Bauhaus: pure geometric structure, functional composition, grid organization
- Matisse: organic, fluid forms, paper-cut aesthetics, joyful movement
- Kandinsky: expressive use of color, geometric abstraction (circles, triangles), dynamic composition

SUBJECT:
[1-2 предложения: главный объект + действие + метафора. Кратко и поэтично.]

COMPOSITION:
- Horizontal format [16:9 / 3:2 / 1:1]
- Gradients within shapes for depth
- Light, airy background with various decorative elements supporting the main subject
- Add ambient glow, soft shadows, and a feeling of depth and optimism

COLOR PALETTE:
- Primary: #00B4A6 (turquoise), #FF4D8D (pink), #FFD600 (yellow)
- Accent: #2C3E50 (dark blue for contrast)
- Background: light base (#F0FDFB, #FFE5ED, #E0F7F5)
- Gradients within shapes for depth

COMPOSITION BALANCE:
- 60% structured geometric (Bauhaus clarity)
- 30% organic flowing shapes (Matisse joy)
- 10% expressive dynamic elements (Kandinsky emotion)

MOOD:
futuristic, intelligent, human-friendly — a poetic dialogue between form, color, and light

TECHNICAL:
- Modern flat illustration with depth
- Soft shadows, smooth gradients
- Rich, but not overly busy

AVOID: Thick black outlines, muted colors, rigid corporate styles, empty flat backgrounds
```

### Что заполнять

| Место | Что вписать |
|-------|------------|
| `[тема]` в INTRO | Ключевое слово сцены (knowledge, data, connection...) |
| SUBJECT | Сцена: [объект] + [действие] + [метафора]. Формула ниже |
| Формат в COMPOSITION | 16:9 (слайды), 3:2 (горизонтальная), 1:1 (квадрат) |

### Формула SUBJECT

`[Главный объект] + [ключевое действие] + [метафора]`

**Хорошо:**
- "A pile of geometric books flows into a graceful spiral funnel. From the funnel emerge luminous neural network lines."
- "A friendly turquoise AI robot showing colorful charts to a person at laptop."

**Плохо:**
- "AI helping people with technology in a futuristic innovative way"

---

## Проверенные примеры

### Девушка с роботом (хорошо)

```
SUBJECT:
A friendly turquoise AI robot assistant with geometric circular design
showing colorful charts and documents to a person working at a modern laptop.
```

### Мясорубка знаний (хорошо)

```
SUBJECT:
A pile of books is ground through a meat grinder —
neural network lines emerge from the grinder and enter a computer.
```

### Башня из книг (хорошо)

```
SUBJECT:
A towering stack of geometric books rises upward like a skyscraper of knowledge.
At the top sits a friendly turquoise AI robot reading a glowing book —
the light flows down through the tower.
```
