# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**svaib** - AI-мастерская, создающая AI-решения для бизнеса. Миссия: переводчик между сложными AI-технологиями и практическими потребностями бизнеса.

**Current Stage:** MVP development, первые недели работы
**Team:** Виктор Соломоник (vision, product, strategy) + Никита (sales, marketing)

**User:** Виктор (обращайся по имени)

## Repository Structure

```
svaib/
├── meta/          — Project context, strategy, documentation
│   ├── meta_context/
│   │   ├── project_overview.md — OKR, strategy, team, MVP stage
│   │   ├── product_overview.md — Product description (AI meeting assistant)
│   │   └── technical_infrastructure.md — Tech stack (VS Code, Git, Vercel, Claude Code)
│   ├── prompts/   — Role-specific prompts (editor, strategist, HRD)
│   └── research/  — Market research and analysis
│
├── dev/           — Development codebase
│   ├── src/       — ⚠️ DEPLOYED TO VERCEL (current production)
│   │   ├── app/   — Next.js 16 App Router
│   │   │   ├── page.js — Main landing page
│   │   │   ├── layout.js — Root layout with fonts
│   │   │   └── globals.css — Global styles and design tokens
│   │   ├── components/  — React components
│   │   │   ├── Header.jsx — Logo svaib (fixed top-right)
│   │   │   ├── Hero.jsx — Hero section with gradient CTA
│   │   │   ├── Architecture.jsx — Interactive architecture diagram (desktop) + card list (mobile)
│   │   │   ├── ArchBlock.jsx — Individual architecture block component
│   │   │   ├── ConnectionLines.jsx — SVG connections between blocks
│   │   │   ├── BlockModal.jsx — Modal with detailed block information
│   │   │   ├── CTA.jsx — Call-to-action section
│   │   │   └── Footer.jsx — Footer with contacts and links
│   │   ├── data/  — Data sources
│   │   │   └── architectureData.js — Architecture blocks and connections
│   │   ├── archive/  — Old HTML/JS/CSS version (preserved)
│   │   ├── package.json — Next.js 16.0.1, React 19.2.0
│   │   └── next.config.js — Next.js configuration
│   ├── dev_context/
│   │   └── design-cheatsheet.md — Design system reference (#00B4A6 primary, #FF4D8D accent)
│   └── prompts/   — Technical prompts (CTO, Dify copilot)
│
└── pub/           — Public materials
    ├── pub_context/
    │   └── svaib_presentation_guide.md — Presentation style guide
    ├── prompts/   — Public-facing role prompts
    └── Liga_2025/ — Conference materials
```

## Current Application Architecture

**Tech Stack:** Next.js 16.0.1 with App Router, React 19.2.0, Tailwind CSS
**Deployment:** Vercel auto-deploy from `dev/src/` on push to main
**Live URL:** https://svaib.com

### Application Structure

Single-page landing with sections:
1. **Header** - Fixed logo `svaib` (top-right): "sv" and "b" in teal, "ai" in pink
2. **Hero** - Main heading, subtitle, CTA button to Telegram
3. **Architecture** - Interactive diagram showing AI-management system:
   - **Desktop:** Canvas with positioned blocks and SVG connections
   - **Mobile:** Simple card list (responsive adaptation)
4. **CTA** - Call-to-action section
5. **Footer** - Contacts, links, archive access

### Interactive Features

**Architecture Diagram (Desktop):**
- 7 interactive blocks positioned on canvas (800px height)
- SVG lines showing data flow between blocks
- Hover effects: teal shadow + lift animation
- Click opens modal with detailed information
- Hint text: "Нажмите на блок, чтобы узнать подробности"

**Mobile Adaptation:**
- Header logo: smaller (text-2xl vs text-3xl)
- Architecture: hides canvas, shows simple card list
- All sections responsive with Tailwind breakpoints

### State Management

React hooks in `Architecture.jsx`:
- `activeBlock` — Currently selected block for modal
- `containerSize` — Canvas dimensions (tracked with useRef + useEffect)
- Modal opens on block click, closes on backdrop/X click

### Data Structure

`architectureData.js` contains:
- `blocks[]` — Array of 7 architecture blocks:
  - Presentation, AI-ассистент (central)
  - Контекст, Метрики, Задачи, Протоколы (data)
  - AI-слой (processing)
- Each block: title, subtitle, icon, position, size, category, description, features, etc.
- `connections[]` — SVG line connections between blocks
- `blockSizes` — Pixel dimensions for each block type

## Design System

**Colors:**
- Primary (Teal): `#00B4A6` (buttons, interactive elements)
- Accent (Pink): `#FF4D8D` (gradients, website only)
- Text: `#1A1A1A` primary, `#6B7280` secondary

**Typography:**
- Headings: `Sora` (bold, semibold)
- Body: `Inter` (regular, medium, semibold)

**Spacing:** All spacing multiples of 4px (12px, 16px, 24px, 32px)
**Border Radius:** 12px (buttons/inputs), 16px (cards)

Full design specs: [dev/dev_context/design-cheatsheet.md](dev/dev_context/design-cheatsheet.md)

## Development Workflow

### Making Changes

1. Edit files in `dev/src/` (components, data, styles)
2. Test locally: `cd dev/src && npm run dev` (http://localhost:3000)
3. Commit changes: `git add . && git commit -m "description"`
4. Push to GitHub: `git push`
5. Vercel auto-deploys to https://svaib.com

### Testing Locally

```bash
cd dev/src
npm install      # First time only
npm run dev      # Start Next.js dev server
# Open http://localhost:3000
```

**Important:**
- Hot reload enabled, changes visible immediately
- Check both desktop and mobile views (responsive design)
- Test interactive features (block clicks, modal, hover effects)

## Slash Commands

- `/svaib-context` — Work with project context (meta/ folder): format files, update structure, check collisions
- `/svaib-dev` — Development mode (dev/ folder): CTO role for architecture discussion or Developer role for coding tasks

## Important Rules

1. **Never break production:** `dev/src/` is live on Vercel, test changes carefully
2. **Design system compliance:** Use colors/spacing from design-cheatsheet.md
3. **Context separation:**
   - meta/ — Project strategy, documentation (rarely touch during dev)
   - dev/ — Code development (primary work area)
   - pub/ — Public materials (separate workflow)
4. **Open source:** All code will be public on GitHub
5. **Weekly "Камни недели":** Focus on concrete weekly results
6. **Next.js best practices:**
   - Use 'use client' for interactive components
   - Keep components small and focused
   - Test both desktop and mobile (responsive required)
   - Old HTML/JS/CSS version preserved in `dev/src/archive/`

## Key Principles

- **Практичность:** Focus on working solutions, not tech for tech's sake
- **Честность:** Document failures alongside successes
- **Легкость:** Approach with humor, self-irony over perfectionism
- **Weekly releases:** Ship every week, gather feedback

## Getting More Context

For detailed project context:
- @meta/meta_context/project_overview.md — Project strategy, OKR, team
- @meta/meta_context/product_overview.md — Product vision ("Презентажка" methodology)
- @meta/meta_context/technical_infrastructure.md — Infrastructure (Vercel, APIs, VPS)
- @dev/dev_context/design-cheatsheet.md — Complete design system specs

---

## Maintenance: Keeping CLAUDE.md Updated

**This file is the single source of truth. After making changes, always check if CLAUDE.md needs updating.**

### When to update CLAUDE.md:

| Change | What to update in CLAUDE.md |
|--------|----------------------------|
| Created/deleted slash command in `.claude/commands/` | Update "Slash Commands" section |
| Changed folder structure (added/removed folders) | Update "Repository Structure" section |
| Changed tech stack (e.g., migrated to Next.js) | Update "Current Application Architecture" |
| Changed deployment process (e.g., new Vercel config) | Update "Development Workflow" |
| Changed design system colors/fonts | Update "Design System" section |
| Major architectural change | Update relevant sections + "Planned Migration" if needed |

### Automatic check:

**After making changes to `.claude/commands/`, `dev/`, or `meta/` structure, always ask:**
> "Does CLAUDE.md need updating? Check the maintenance table above."
