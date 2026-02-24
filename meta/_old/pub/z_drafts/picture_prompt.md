# ЧЕРНОВИК: Попытки подобрать промпт для AI-иллюстраций

**Статус:** Черновик, эксперименты с разными подходами
**Цель:** Найти оптимальный формат промпта для генерации иллюстраций в стиле svaib (Bauhaus + Matisse + Kandinsky)
**Содержание:** Различные версии промптов и примеры (девушка с роботом, мясорубка с книгами, башня из книг)

**Итоговое решение:** См. art_director_prompt.md в pub/prompts/ — там финальная версия шаблона.

---

## 🖼️ Промпт для картинок




Твоя задача создать промпт для нейросети для AI-иллюстратора

##
основная идея картинки
A pile of books is ground through a meat grinder - neural network lines emerge from the grinder and enter a computer.

##
Цель: создать иллюстрацию в стиле svaib (Bauhaus + Matisse + Kandinsky).

## Правила:
1. Используй шаблон в качестве примера ниже
- Вводное описание - не менять слова, цифры, цвета из шаблона
- SUBJECT: 
[Конкретный объект] + [характеристики] + [действие] + [контекст/окружение] + [метафора если есть]
Пример хороший:
"A friendly turquoise AI robot assistant with geometric circular design showing colorful charts and documents to a person working at a modern laptop"
Пример плохой:
"AI helping people with technology in a futuristic innovative way"




	•	Блоки 1, 6, 7, 9, 10 — 🔒 фикс (не менять слова, цифры, цвета).
	•	Блоки 2, 3, 4, 5, 8 — 🎬 режиссируем (можно менять содержимое, но сохранять стиль и структуру).
	•	Не добавлять новые блоки.
	•	Сохранять порядок — сверху вниз.
	•	Каждый блок писать с заголовком (как в шаблоне).

2. ФОРМАТ ОТВЕТА
выведи только промпт для  не вставляю никаких вводных
То есть начинаться должен 
Create a contemporary illustration...
И заканчиваться ... AVOID

⸻

## Шаблон промпта для AI-иллюстратора

Create a contemporary illustration inspired by the geometry of the Bauhaus,
the organic, flowing forms of Matisse, and the expressive color composition
of Kandinsky.

SUBJECT:
[1–2 строки сцены — кто/что делает что, где. Без лишних деталей.]

BASE STRUCTURE (Bauhaus-inspired):
- Clean grid-based composition with clear spatial organization.
- Strong geometric foundation and alignment.
- Functional layout: [опционально — кто/что где].

FORMS (Kandinsky meets Matisse):
- Geometric shapes (circles, rectangles, triangles) combined with organic paper-cut curves.
- Smooth, rhythmic lines that convey motion.
- [опционально 1 уточнение — slight angles / rounded corners].

DECORATIVE ELEMENTS:
- [выбрать 2–3: floating geometric shapes / organic connector lines / abstract data hints / subtle sparkles]

COLOR & LIGHT:
- Primary: #00B4A6, #FF4D8D, #FFD600; Accent: #2C3E50.
- Background: soft gradient #F0FDFB → #FFE5ED (touches of #E0F7F5).
- Gradients within shapes for depth. Do not alter HEX values.

COMPOSITION BALANCE:
- 60% geometric structure, 30% organic flow, 10% expressive accents.

MOOD:
[выбрать 1 — Futuristic / Functional yet joyful / Structured yet playful]

TECHNICAL:
- Modern flat illustration with depth; soft shadows; smooth gradients; 16:9.
- Rich, but not cluttered.

AVOID:
- Thick black outlines; rigid corporate style; pure minimalism; empty flat backgrounds; muted/muddy colors; clutter.


SUBJECT: [Главный объект] [действие/состояние]. 
[Дополнительные элементы]. [Визуальная метафора если есть].




```
Create a contemporary illustration inspired by the geometry of the Bauhaus, 
the organic, flowing forms of Matisse, and the expressive color composition 
of Kandinsky.

THEME: [твоя идея картинки]

STYLE INFLUENCES:
- Bauhaus: pure geometric structure, functional composition, grid organization
- Matisse: organic, fluid forms, paper-cut aesthetics, joyful movement
- Kandinsky: expressive use of color, geometric abstraction (circles, triangles), 
  dynamic composition

COLOR PALETTE:
- Primary: #00B4A6 (turquoise), #FF4D8D (pink), #FFD600 (yellow)
- Accent: #2C3E50 (dark blue for contrast)
- Background: light base (#F0FDFB, #FFE5ED, #E0F7F5)

COMPOSITION:
- Aspect ratio: 3:2 (horizontal)
- Balance: 60% geometric structure, 40% organic playfulness
- Gradients within shapes for depth
- Light, airy background with decorative elements supporting the main subject

MOOD: [настроение: energetic / calm / futuristic / playful]

TECHNICAL:
- Modern flat illustration with depth
- Soft shadows, smooth gradients
- Rich, but not cluttered

AVOID: Thick black outlines, muted colors, rigid corporate styles, 
empty flat backgrounds
```

---


Create a contemporary illustration inspired by the geometry of the Bauhaus, 
the organic, flowing forms of Matisse, and the expressive color composition of Kandinsky,
capturing the poetic transformation of knowledge into light and structure.

SUBJECT: 
A pile of geometric books flows into a graceful spiral funnel.
From the funnel emerge luminous neural network lines connecting into a minimalist computer.

COMPOSITION:
- Layout: Left — books; Center — spiral funnel; Right — computer with network lines
- Forms: Books as clean rectangles with slight angles; Funnel made of smooth circles with soft gradients; Network lines as flowing organic paths with glowing circular nodes
- Dynamics: Gentle left-to-right motion; Spiral creates depth and rhythm
- Decorative touch: subtle geometric sparkles suggesting transformation energy
- Balance: 60% geometric precision (Bauhaus) / 40% organic flow (Matisse & Kandinsky)
- Format: 16:9

COLOR & MOOD:
- Primary: #00B4A6 (turquoise), #FF4D8D (pink), #FFD600 (yellow)
- Accent: #2C3E50 (dark blue for contrast)
- Background: light, clean gradient from #E0F7F5 to #FFE5ED
- Gradients within shapes for depth
- Mood: bright, intelligent transformation — a dialogue between knowledge and light

TECHNICAL:
- Modern flat illustration with depth
- Soft shadows and smooth gradients
- Rich details but not cluttered

AVOID: Thick black outlines, muted colors, rigid corporate style, 
empty flat backgrounds, pure minimalism


ХОРОШО - ДЕВУШКА С РОБОТОМ
Create a modern illustration combining structured geometric design with organic flowing shapes.

SUBJECT: A friendly turquoise AI robot assistant showing charts and documents to a person working at a laptop

BASE STRUCTURE (Bauhaus-inspired):
- Clean grid-based composition with clear spatial organization
- Functional layout: robot on left, person at desk on right
- Strong geometric foundation with defined areas

FORMS (Kandinsky meets Matisse):
- Robot: geometric circles and rounded rectangles with gradient fills
- Floating elements: mix of geometric shapes (circles, triangles) AND organic flowing forms (paper cut-out style curves)
- Person: simplified organic forms with smooth flowing lines
- Dynamic composition: elements at slight angles, creating visual rhythm

COLOR APPROACH (Expressive yet structured):
- Primary palette: #00B4A6 (turquoise), #FF4D8D (pink), #FFD600 (yellow)
- Gradients within shapes for depth and emotion
- Background: soft atmospheric gradient from #E0F7F5 to #FFE5ED
- Color as emotion: bold contrasts, joyful combinations

DECORATIVE ELEMENTS:
- Floating geometric shapes: circles, triangles, small rectangles
- Organic flowing lines connecting elements
- Abstract data visualizations (charts, checkmarks) in papers
- Sparkles and subtle particles
- All elements serve function while being playful

COMPOSITION BALANCE:
- 60% structured geometric (Bauhaus clarity)
- 30% organic flowing shapes (Matisse joy)  
- 10% expressive dynamic elements (Kandinsky emotion)

MOOD: Functional yet joyful, structured yet playful, serious about technology with a smile

TECHNICAL:
- Modern flat illustration with depth
- Soft shadows and smooth gradients
- 16:9 aspect ratio
- Rich details but not cluttered
- Professional yet approachable

AVOID: Pure minimalism, rigid corporate style, chaotic mess, muddy colors




----

ХООРОШО МЯСОРЫБКА

Create a contemporary illustration inspired by the geometry of the Bauhaus, the organic, flowing forms of Matisse, and the expressive color composition of Kandinsky.

THEME: A pile of books is ground through a meat grinder - neural network lines emerge from the grinder and enter a computer.

STYLISH INFLUENCES:
- Bauhaus: pure geometric structure, functional composition, grid organization
- Matisse: organic, fluid forms, paper-cut aesthetics, joyful movement
- Kandinsky: expressive use of color, geometric abstraction (circles, triangles), dynamic composition

COLOR PALETTE:
- Primary: #00B4A6 (turquoise), #FF4D8D (pink), #FFD600 (yellow)
- Accent: #2C3E50 (dark blue for contrast)
- Background: light base (#F0FDFB, #FFE5ED, #E0F7F5)

COMPOSITION:
- Horizontal format 16:9
- Balance: 60% geometric Structures, 40% organic playfulness
- Gradients within shapes for depth
- Light, airy background with various decorative elements supporting the main subject
- Add ambient glow, soft shadows, and a feeling of depth and optimism.

MOOD: 
futuristic, intelligent, human-friendly — a poetic dialogue between form, color, and light.

TECHNICAL SPECIFICATIONS:
- Modern flat illustration with depth
- Soft shadows, smooth gradients
- Rich, but not overly busy

AVOID: Thick black outlines, muted colors, rigid corporate styles, empty, flat backgrounds


Create a contemporary illustration inspired by the geometry of the Bauhaus, 
the organic, flowing forms of Matisse, and the expressive color composition 
of Kandinsky, capturing the poetic dialogue between knowledge and light.

STYLE INFLUENCES:
- Bauhaus: pure geometric structure, functional composition, grid organization
- Matisse: organic, fluid forms, paper-cut aesthetics, joyful movement
- Kandinsky: expressive use of color, geometric abstraction (circles, triangles), dynamic composition

SUBJECT:
A towering stack of geometric books rises upward like a skyscraper of knowledge. 
At the top sits a friendly turquoise AI robot reading a glowing book — the light flows down through the tower.

COMPOSITION:
- Layout: Center — vertical tower of books; Top — glowing robot; Background — faint horizon and soft gradient sky
- Forms: Books as clean rectangles with subtle angles; Robot built of smooth circles and rounded rectangles; Light as a soft flowing stream linking levels
- Dynamics: Gentle upward motion; Vertical rhythm suggesting scale and depth
- Balance: 60% geometric structures, 40% organic playfulness
- Light, airy background with various decorative elements supporting the main subject
- Add ambient glow, soft shadows, and a feeling of depth and optimism
- Decorative elements: small floating geometric sparkles around the tower symbolizing ideas
- Format: 16:9

COLOR PALETTE:
- Primary: #21C4B5 (turquoise), #FF4D8D (pink), #FFD600 (yellow)
- Accent: #2C3E50 (dark blue for contrast)
- Background: light base (#F0FDFB, #FFE5ED, #E0F7F5)
- Gradients within shapes for depth
- Keep the overall palette slightly cool and fresh

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
