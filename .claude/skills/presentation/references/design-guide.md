# svaib Presentation Design Guide

Brand rules for slide presentations. Source of truth: `meta/marketing/brand-design-presentation.md` [REF: brand-design-presentation.md]

**Tech stack:** PptxGenJS via `document-skills:pptx`. All HEX values below are WITHOUT `#` prefix (PptxGenJS requirement).

---

## Color Palette

### Primary

| Role | HEX | PptxGenJS | Usage |
|------|-----|-----------|-------|
| Teal | `#008B7F` | `008B7F` | H1 headings, teal top stripe, structural accents |
| Dark Blue | `#2C3E50` | `2C3E50` | H2, body text, subtitle |
| Pink | `#FF4D8D` | `FF4D8D` | Accents ONLY: the word "AI", key numbers. **Never** as background, fill, or structural color |
| Gray | `#6B7280` | `6B7280` | Footnotes, captions, small text, footer |

### Secondary (illustrations, icons, decorative shapes)

| HEX | PptxGenJS | Name |
|-----|-----------|------|
| `#00B4A6` | `00B4A6` | Bright teal |
| `#FFD600` | `FFD600` | Yellow |

### Backgrounds

| HEX | PptxGenJS | Usage |
|-----|-----------|-------|
| `#FFFFFF` | `FFFFFF` | Default slide background |
| `#F0FDFB` | `F0FDFB` | Section divider slides (light teal) |
| `#E0F7F5` | `E0F7F5` | Occasional card/shape fill (subtle) |

**Rule:** No heavy colored fills, no gradients. White background default. Max 2 color accents per slide. Pink = accent only, never background.

---

## Typography

### PptxGenJS fonts (must be installed on system or available in PowerPoint)

| Element | Font | Size (pt) | Style |
|---------|------|-----------|-------|
| Slide title (title slide) | Montserrat | 44-50 | Bold |
| Slide title (content) | Montserrat | 36-40 | Bold |
| Subtitle | Roboto | 20-24 | Regular |
| H2 / section header | Montserrat | 24-28 | Bold |
| Body text | Roboto | 14-16 | Regular |
| Captions, footnotes | Roboto | 10-12 | Regular, gray |

**Fallback pairing** (if Montserrat/Roboto not available): Arial Black + Calibri.

### For HTML (secondary format)

Google Fonts: `Montserrat:wght@700&family=Roboto:wght@400;500`

---

## Layout Patterns

**Vary layouts across slides.** Don't repeat the same pattern. Choose from:

| Pattern | When to use |
|---------|-------------|
| Two-column (text left, visual right) | Default for content + illustration |
| Icon + text rows (icon in teal circle, bold header, description) | Feature lists, benefits |
| 2x2 or 2x3 grid | Comparing options, team, categories |
| Half-bleed image (full left/right) with text overlay | Hero/impact slides |
| Large stat callout (44-50pt number + small label) | Data points, metrics |
| Timeline / process flow (numbered steps, arrows) | Sequences, roadmaps |
| Quote slide (large italic text, author below) | Testimonials, key quotes |

### Composition Rules

| Rule | Value |
|------|-------|
| Proportions | 50/50 or 60/40 (text ↔ visual) |
| Minimum margins | 0.5" from all edges |
| Gap between content blocks | 0.3-0.5" |
| Heading → content gap | 0.3-0.5" |
| Center each element in its zone | Not across the full slide |

### Vertical Placement

**Align Top** (default): heading and content start at top of their zones. Use when: much text, clear structure.

**Align Middle** (for impact): content centered vertically. Use when: 1-2 points, need breathing room.

---

## Image & Shape Rules

### Images

| Parameter | Value |
|-----------|-------|
| Preferred aspect | 3:2 (landscape) or 1:1 (square) |
| Border | 1px teal (`008B7F`) — optional, for photos |
| Shadow | `{ type: "outer", color: "008B7F", blur: 5, offset: 4, angle: 135, opacity: 0.25 }` |
| Corner rounding | `rectRadius: 0.15` (for shapes/cards) |

### Icon Style

- Use react-icons (fa, md, hi) rendered as PNG via sharp
- Icon color: teal (`008B7F`) or bright teal (`00B4A6`)
- Icon background: teal circle with white icon, or no background with teal icon
- Size: 0.4-0.6" in slide

### Shapes & Cards

- Card: `ROUNDED_RECTANGLE`, fill `FFFFFF`, border `E5E7EB` (1px), shadow, `rectRadius: 0.1`
- Divider line: teal (`008B7F`), 1.5px width
- Teal accent bar: thin rectangle (0.05" × 0.3") left of section headers

---

## Brand Markers

- **Teal top stripe**: thin rectangle at top of every slide (x: 0, y: 0, w: 10, h: 0.04), fill `008B7F`
- **Footer**: "svaib." in Montserrat 8pt, gray (`6B7280`), bottom-right corner
- **Pink dot** in "svaib." text — the only structural use of pink
- **No accent underlines** under titles — that's a hallmark of AI-generated slides

---

## Philosophy

**Formula:** 60% structural geometry (Bauhaus) + 40% organic playfulness (Matisse + Kandinsky)

**Mood:** Functional but with soul. Serious about technology, but with a smile. Not corporate rigidity, not childish playfulness — intelligent lightness.

**Design principle:** Every slide needs a visual element — icon, shape, image, or chart. Plain bullets on white background = not acceptable.
