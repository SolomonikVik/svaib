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
│   │   ├── index.html — Main landing page with multi-screen navigation
│   │   ├── app.js — Application logic (state management, screen navigation)
│   │   ├── data.js — Business data (industries, AI roles, task templates)
│   │   └── styles.css — Design system styles
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

**Tech Stack:** Vanilla HTML/JS/CSS (статический сайт)
**Deployment:** Vercel auto-deploy from `dev/src/` on push to main
**Live URL:** https://svaib.com

### Application Flow

1. **Landing Screen** (`index.html#landing`) — Hero with CTA
2. **Industries Screen** — User selects industry (e.g., "Гостиничный бизнес")
3. **Roles Screen** — User selects AI role (e.g., "AI-помощник руководителя")
4. **Tasks Screen** — User selects task, gets ready-to-use AI prompt

### State Management

`AppState` object in `app.js` tracks:
- `currentScreen` — Current active screen
- `selectedIndustry` — Selected industry from data.js
- `selectedRole` — Selected AI role
- `selectedTask` — Selected task template

### Data Structure

`data.js` contains:
- `APP_DATA.industries[]` — Industry catalog with roles
- Each role has `tasks[]` with ready-to-use AI prompts
- Prompt templates include context, instructions, output format

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

1. Edit files in `dev/src/`
2. Test locally (use Live Server or `python3 -m http.server 8000`)
3. Commit changes: `git add . && git commit -m "description"`
4. Push to GitHub: `git push`
5. Vercel auto-deploys to https://svaib.com

### Testing Locally

```bash
cd dev/src
python3 -m http.server 8000
# Open http://localhost:8000
```

Or use VS Code Live Server extension.

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

## Planned Migration

**Next.js migration** planned:
- Create `dev/next-app/` for new Next.js codebase
- Keep `dev/src/` running until migration complete
- Parallel deployment strategy (old + new versions)

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
