# svaib Design System — Quick Reference

## 🎨 Основные цвета (копируй hex-коды)

### Primary (Бирюзовый)
```
#00B4A6  — Основной
#008B7F  — Hover
#E0F7F5  — Light фон
#F0FDFB  — Subtle фон
```

### Accent (Розовый) — только для сайта!
```
#FF4D8D  — Основной
#E6548A  — Hover
#FFE5ED  — Light фон
```

### Градиент (только для сайта!)
```css
background: linear-gradient(135deg, #00B4A6 0%, #FF4D8D 100%);
```

---

## 📝 Типографика

### Шрифты
```html
<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@600;700;800&display=swap" rel="stylesheet">
```

```css
/* CSS */
font-family: 'Sora', sans-serif;  /* Заголовки h1-h3 */
font-family: 'Inter', sans-serif; /* Всё остальное */
```

### Размеры
```
42px — h1 (Sora Bold, letter-spacing: -0.02em)
32px — h2 (Sora Bold, letter-spacing: -0.01em)
24px — h3 (Sora Semibold, letter-spacing: -0.01em)
20px — h4 (Inter Semibold)
16px — body (Inter Regular, line-height: 1.6)
14px — UI элементы (Inter Medium/Semibold)
12px — мелкий текст (Inter Regular)
```

---

## 🔘 Кнопки (детальная спецификация)

### Primary Button (приложение)
```css
background-color: #00B4A6;
color: #FFFFFF;
padding: 12px 24px;
border-radius: 12px;
font-size: 14px;
font-weight: 600;
border: none;
box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
transition: all 0.2s ease;
```

**Hover:**
```css
background-color: #008B7F;
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02), 0 4px 16px rgba(0, 0, 0, 0.04);
```

### Gradient CTA Button (сайт)
```css
background: linear-gradient(135deg, #00B4A6 0%, #FF4D8D 100%);
color: #FFFFFF;
padding: 12px 24px;
border-radius: 12px;
font-size: 14px;
font-weight: 600;
border: none;
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02), 0 4px 16px rgba(0, 0, 0, 0.04);
```

**Hover:**
```css
box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02), 0 12px 24px rgba(0, 0, 0, 0.06);
transform: translateY(-1px);
```

### Secondary Button
```css
background-color: #E0F7F5;
color: #00B4A6;
padding: 12px 24px;
border-radius: 12px;
font-size: 14px;
font-weight: 600;
border: none;
```

### Размеры кнопок
```css
.btn-sm:  padding: 8px 16px;  font-size: 12px;
.btn:     padding: 12px 24px; font-size: 14px;  /* стандарт */
.btn-lg:  padding: 16px 32px; font-size: 16px;
```

---

## 📦 Карточки (детальная спецификация)

### Стандартная карточка
```css
background-color: #FFFFFF;
border: 1px solid #E5E7EB;
border-radius: 16px;
padding: 24px;
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02), 0 4px 16px rgba(0, 0, 0, 0.04);
transition: all 0.2s ease;
```

**Hover:**
```css
box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02), 0 12px 24px rgba(0, 0, 0, 0.06);
transform: translateY(-2px);
```

### Highlighted карточка
```css
background-color: #E0F7F5;  /* primary-light */
border: 1px solid #E5E7EB;
border-radius: 12px;
padding: 20px;
```

### Иконка в карточке
```css
width: 48px;
height: 48px;
background-color: #E0F7F5;  /* primary-light */
border-radius: 12px;
/* иконка внутри цветом #00B4A6 */
```

---

## 📝 Формы (детальная спецификация)

### Input / Textarea
```css
width: 100%;
padding: 12px 16px;
border: 2px solid #E5E7EB;
border-radius: 12px;
font-size: 14px;
font-family: 'Inter', sans-serif;
color: #1A1A1A;
background-color: #FFFFFF;
outline: none;
transition: border-color 0.2s ease;
```

**Focus:**
```css
border-color: #00B4A6;
```

**Placeholder:**
```css
color: #9CA3AF;  /* text-tertiary */
```

### Label
```css
display: block;
font-size: 14px;
font-weight: 500;
color: #1A1A1A;
margin-bottom: 8px;
```

### Textarea
Те же стили что input, плюс:
```css
resize: vertical;
min-height: 100px;
```

---

## 🏷️ Badges (детальная спецификация)

```css
display: inline-flex;
align-items: center;
padding: 4px 10px;
border-radius: 999px;  /* полностью круглый */
font-size: 12px;
font-weight: 600;
```

### Варианты
```css
.badge-primary:
  background: #E0F7F5;
  color: #00B4A6;

.badge-gradient:
  background: linear-gradient(135deg, #00B4A6 0%, #FF4D8D 100%);
  color: #FFFFFF;

.badge-accent:
  background: #FFE5ED;
  color: #FF4D8D;
```

---

## 📐 Spacing (отступы)

Всё кратно 4px:
```css
4px   — var(--space-1)   или  0.25rem
8px   — var(--space-2)   или  0.5rem
12px  — var(--space-3)   или  0.75rem
16px  — var(--space-4)   или  1rem
20px  — var(--space-5)   или  1.25rem
24px  — var(--space-6)   или  1.5rem
32px  — var(--space-8)   или  2rem
48px  — var(--space-12)  или  3rem
64px  — var(--space-16)  или  4rem
```

**Типичное использование:**
- Padding карточки: **24px**
- Gap между элементами: **12-16px**
- Margin между секциями: **48px**
- Padding кнопки: **12px 24px**

---

## 🎭 Border Radius (скругления)

```css
8px   — Маленькие элементы (badges, иконки)
12px  — Стандарт (кнопки, инпуты, highlighted cards)
16px  — Большие карточки
20px  — Контейнеры, секции
999px — Круглые элементы (pills, круглые badges)
```

**По умолчанию:** **12px** для большинства UI-элементов

---

## 💫 Shadows (тени)

```css
/* Subtle (легкая) */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);

/* Standard (стандартная для карточек) */
--shadow-md: 0 1px 3px rgba(0, 0, 0, 0.02), 
             0 4px 16px rgba(0, 0, 0, 0.04);

/* Elevated (при hover) */
--shadow-lg: 0 4px 6px rgba(0, 0, 0, 0.02), 
             0 12px 24px rgba(0, 0, 0, 0.06);

/* Extra (модалки) */
--shadow-xl: 0 8px 16px rgba(0, 0, 0, 0.04), 
             0 20px 40px rgba(0, 0, 0, 0.08);
```

---

## 🎨 Полная палитра CSS переменных

```css
:root {
  /* Primary (Бирюзовый) */
  --color-primary: #00B4A6;
  --color-primary-hover: #008B7F;
  --color-primary-light: #E0F7F5;
  --color-primary-subtle: #F0FDFB;
  
  /* Accent (Розовый) */
  --color-accent: #FF4D8D;
  --color-accent-hover: #E6548A;
  --color-accent-light: #FFE5ED;
  
  /* Gradient */
  --gradient-hero: linear-gradient(135deg, #00B4A6 0%, #FF4D8D 100%);
  
  /* Backgrounds */
  --bg-primary: #FAFBFC;
  --bg-secondary: #F3F4F6;
  --surface: #FFFFFF;
  
  /* Text */
  --text-primary: #1A1A1A;
  --text-secondary: #6B7280;
  --text-tertiary: #9CA3AF;
  --text-on-primary: #FFFFFF;
  
  /* Borders */
  --border: #E5E7EB;
  --border-light: #F3F4F6;
  
  /* States */
  --success: #10B981;
  --warning: #F59E0B;
  --error: #EF4444;
  --info: #3B82F6;
  
  /* Typography */
  --font-heading: 'Sora', sans-serif;
  --font-body: 'Inter', sans-serif;
  
  /* Spacing */
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-12: 3rem;     /* 48px */
  
  /* Border Radius */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-full: 9999px;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 1px 3px rgba(0, 0, 0, 0.02), 0 4px 16px rgba(0, 0, 0, 0.04);
  --shadow-lg: 0 4px 6px rgba(0, 0, 0, 0.02), 0 12px 24px rgba(0, 0, 0, 0.06);
  --shadow-xl: 0 8px 16px rgba(0, 0, 0, 0.04), 0 20px 40px rgba(0, 0, 0, 0.08);
}
```

---

## ⚠️ ВАЖНЫЕ ПРАВИЛА

### 1. Монохромность приложения
**В приложении:**
- ✅ Только бирюзовый (#00B4A6)
- ✅ Серые нейтралы
- ❌ НЕ используй розовый
- ❌ НЕ используй градиент

**На сайте:**
- ✅ Бирюзовый + Розовый
- ✅ Градиент для CTA

### 2. Шрифты
- **Sora** — ТОЛЬКО h1, h2, h3
- **Inter** — всё остальное

### 3. Анимации
Всегда добавляй:
```css
transition: all 0.2s ease;
```

### 4. Скругления
- **12px** — стандарт для большинства элементов
- **16px** — большие карточки
- **999px** — круглые badges

---

## 📱 Примеры HTML для копирования

### Кнопка Primary
```html
<button style="
  background-color: #00B4A6;
  color: white;
  padding: 12px 24px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
">
  Кнопка
</button>
```

### Кнопка Gradient (CTA)
```html
<button style="
  background: linear-gradient(135deg, #00B4A6 0%, #FF4D8D 100%);
  color: white;
  padding: 12px 24px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0,0,0,0.02), 0 4px 16px rgba(0,0,0,0.04);
">
  Попробовать бесплатно
</button>
```

### Input
```html
<input type="text" 
  placeholder="Введите текст"
  style="
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #E5E7EB;
    border-radius: 12px;
    font-size: 14px;
    font-family: 'Inter', sans-serif;
    outline: none;
  "
  onfocus="this.style.borderColor='#00B4A6'"
  onblur="this.style.borderColor='#E5E7EB'"
>
```

### Карточка
```html
<div style="
  background: white;
  border: 1px solid #E5E7EB;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.02), 0 4px 16px rgba(0,0,0,0.04);
">
  <h3 style="font-family: 'Sora', sans-serif; font-size: 24px; margin-bottom: 12px;">
    Заголовок карточки
  </h3>
  <p style="color: #6B7280; line-height: 1.6;">
    Текст описания карточки
  </p>
</div>
```

### Badge
```html
<span style="
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: linear-gradient(135deg, #00B4A6 0%, #FF4D8D 100%);
  color: white;
">
  NEW
</span>
```

---

## 🎨 Для Figma/Sketch

### Color Styles
```
Primary:        #00B4A6
Primary Light:  #E0F7F5
Accent:         #FF4D8D
Accent Light:   #FFE5ED
Text:           #1A1A1A
Text Secondary: #6B7280
Background:     #FAFBFC
Border:         #E5E7EB
```

### Text Styles
```
H1: Sora Bold 42px, -2% letter-spacing
H2: Sora Bold 32px, -1% letter-spacing
H3: Sora Semibold 24px, -1% letter-spacing
Body: Inter Regular 16px, 1.6 line-height
UI: Inter Semibold 14px
```

### Component Specs
```
Button:       12px radius, 12px/24px padding
Card:         16px radius, 24px padding
Input:        12px radius, 12px/16px padding, 2px border
Badge:        999px radius, 4px/10px padding
Icon box:     48px square, 12px radius
```

---

**Версия:** 1.0  
**Дата:** 15.10.2025  
**Автор:** Виктор Соломоник  
**Источник:** Ocean Wave Hybrid — финальная утверждённая версия