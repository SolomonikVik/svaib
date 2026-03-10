---
name: presentation
description: "Create branded PPTX presentations in svaib style. Trigger when user says 'сделай презентацию', 'создай слайды', 'make slides', 'make presentation', provides slide-by-slide content for visual output, or mentions 'deck', 'слайды для семинара/встречи'. Do NOT trigger for: editing existing PPTX (use document-skills:pptx), text-only outlines, presentation theory questions, PDF documents (use document-skills:pdf)."
---

# Presentation — svaib branded slides

**Every slide follows svaib brand AND has a visual element.** No plain bullets on white. Brand rules: `meta/marketing/brand-design-presentation.md`.

---

## Environment

```bash
# Required: global npm packages
npm install -g pptxgenjs react-icons react react-dom sharp

# Run scripts with NODE_PATH:
NODE_PATH=$(npm root -g) node scripts/generate.js input.json output.pptx
```

---

## Process

### 1. Parse

Extract slides from `$ARGUMENTS` or user message. Expected:

```
Slide 1: Title here
- bullet point

Slide 2: Another title
Body text or bullets
```

If unstructured — ask user to confirm slide breakdown.

### 2. Generate

**Option A: Use the generation script** (preferred for standard layouts).

Write a JSON spec file, then run `scripts/generate.js`:

```json
{
  "title": "Presentation Title",
  "slides": [
    { "layout": "title", "title": "...", "subtitle": "..." },
    { "layout": "bullets", "title": "...", "bullets": ["...", "..."] },
    { "layout": "icon-text", "title": "...", "items": [
      { "icon": "FaCheckCircle", "heading": "...", "text": "..." }
    ]},
    { "layout": "two-column", "title": "...", "leftTitle": "...", "leftBullets": [...], "rightTitle": "...", "rightBullets": [...] },
    { "layout": "stats", "title": "...", "stats": [{ "value": "85%", "label": "..." }] },
    { "layout": "quote", "quote": "...", "author": "..." },
    { "layout": "section", "title": "..." }
  ]
}
```

```bash
NODE_PATH=$(npm root -g) node scripts/generate.js spec.json presentation.pptx
```

Available layouts: `title`, `bullets`, `icon-text`, `two-column`, `stats`, `quote`, `section`.

Icons: any from react-icons (fa, md, hi, bi, fi) — e.g., `FaCheckCircle`, `FaTimesCircle`, `FaRocket`, `MdTrendingUp`.

**Option B: Custom PptxGenJS code** (for non-standard layouts).

Write inline Node.js using `document-skills:pptx` workflow. Read `meta/marketing/brand-design-presentation.md` for exact colors, fonts, sizes. Key rules:
- HEX colors WITHOUT `#` prefix (e.g., `008B7F`)
- Never reuse option objects — create fresh each time
- `bullet: true`, never unicode "•"
- `breakLine: true` between text array items
- Every slide gets: teal top stripe (x:0, y:0, w:10, h:0.04, fill `008B7F`) + svaib logo (bottom-right, see brand file)

### 3. QA (mandatory)

Convert to images and visually inspect:

```bash
soffice --headless --convert-to pdf --outdir /tmp presentation.pptx
pdftoppm -jpeg -r 150 /tmp/presentation.pdf /tmp/slide
```

Check every slide for: overlapping elements, text overflow, alignment issues, contrast problems, margins < 0.5".

**Fix-and-verify cycle required.** Do not deliver until at least one issue has been found and fixed, or a full pass confirms no issues.

### 4. Deliver

```bash
open presentation.pptx
```

If user wants changes — iterate.

---

## Example

**Input:**
```
Слайд 1: Как AI меняет бизнес
Подзаголовок: Практический взгляд

Слайд 2: Три заблуждения
- AI заменит всех
- AI работает сам
- AI — это дорого

Слайд 3: Результаты
- 85% сокращение рутины
- 3x скорость решений
```

**JSON spec:**
```json
{
  "title": "Как AI меняет бизнес",
  "slides": [
    { "layout": "title", "title": "Как AI меняет бизнес", "subtitle": "Практический взгляд" },
    { "layout": "icon-text", "title": "Три заблуждения", "items": [
      { "icon": "FaTimesCircle", "heading": "AI заменит всех", "text": "На практике усиливает команду" },
      { "icon": "FaTimesCircle", "heading": "AI работает сам", "text": "Нужна настройка и данные" },
      { "icon": "FaTimesCircle", "heading": "AI — это дорого", "text": "Окупается за 3-6 месяцев" }
    ]},
    { "layout": "stats", "title": "Результаты", "stats": [
      { "value": "85%", "label": "Сокращение рутины" },
      { "value": "3x", "label": "Скорость решений" }
    ]}
  ]
}
```

**Output:** 3-slide PPTX — title with "AI" in pink accent, icon-text with teal circles, stats cards with pink numbers.

---

## Edge Cases

| Situation | Action |
|-----------|--------|
| No clear slide divisions | Ask user to confirm breakdown |
| >5 bullets or >100 words per slide | Warn, suggest splitting |
| User asks for HTML | Generate reveal.js + svaib CSS (secondary format) |
| Layout not in script | Use Option B (custom PptxGenJS code) |
| Montserrat/Roboto not installed | Fallback: Arial Black + Calibri |

---

## Related Skills

- `document-skills:pptx` — PptxGenJS API, QA protocol, icon pipeline, XML editing. This skill adds svaib brand on top.
- `document-skills:frontend-design` — for web pages and UI, not slide decks.
