# Design: README Overhaul (TASK-10.2)

**Date:** 2026-06-19
**Scope:** TASK-10.2 — README overhaul with hero image, showcase GIF, badges, table of contents, features, screenshots, and documentation index.

---

## Goal

Replace the current README (which jumps straight to prerequisites with no description of the app) with one that gives any visitor an immediate understanding of what the app is, what it looks like, and where to find everything. The app may go offline after publication, so screenshots baked into the README preserve what it looked like.

---

## Assets

All images move from `assets/` to `docs/images/` and are referenced with relative paths from the README root.

| File | Used as |
|---|---|
| `assets/Personal Dashboard Screen.png` | Hero image |
| `assets/Showcase.gif` | "See it in action" section |
| `assets/Club Dashboard.png` | Screenshot after Features list |
| `assets/Badges.png` | Screenshot after Club Dashboard |
| `assets/Main Screen.png` | Not used (login screen — not compelling to visitors) |
| `assets/Privacy Page.png` | Not used (not a selling point) |

---

## README Structure

### 1. Header block
- `# Strava Goal Visualizer`
- Badges row (shields.io static badges — no CI integration needed):
  - License: MIT — links to `LICENSE`
  - Python: 3.12
  - Node: 22
- Tagline: *"A personal running goal tracker that visualises your yearly Strava progress."*
- Hero image: `docs/images/personal-dashboard.png`

### 2. Table of contents
Linked anchors to every major section:
- Overview · See it in action · Features · Tech Stack · Prerequisites · Local Development · Docker Compose · Generating Secret Keys · Running Tests · Documentation · License

### 3. Overview
3–4 sentences: what the app does, that it connects to Strava via OAuth, that it tracks yearly running goals and club progress, and that it is a self-hosted personal project.

### 4. See it in action
`docs/images/showcase.gif` with a short caption.

### 5. Features
Bullet list:
- Personal yearly running goal dashboard with cumulative pace chart
- Achievement badges at 10 / 100 / 365 / 1,000 km milestones
- Club member progress view with per-member pace lines
- Strava OAuth login — no password required
- Self-hosted on Fly.io (single-app deployment)

Followed by `docs/images/club-dashboard.png` then `docs/images/badges.png`.

### 6. Tech stack
FastAPI · React + Vite (TypeScript) · PostgreSQL · Fly.io

### 7. Prerequisites
- Node.js requirement corrected from 18+ to **22**
- Existing Windows PowerShell install instructions kept verbatim
- "No make? Run commands manually" block kept

### 8. Local Development
Existing quickstart section — unchanged in substance, minor cleanup only (no content additions).

### 9. Docker Compose
Existing section — kept verbatim.

### 10. Generating Secret Keys
Existing section — kept verbatim.

### 11. Running Tests
Existing section — kept verbatim.

### 12. Documentation
Index linking to all project docs:

| Doc | Description |
|---|---|
| `docs/ops/deployment.md` | Production deployment guide (Fly.io) |
| `docs/ops/db-statistics.md` | DB usage statistics queries |
| `docs/design.md` | Architecture and design decisions |
| `docs/design/style.md` | Frontend design system |
| `docs/workflow.md` | Development workflow |
| `docs/learnings.md` | Project learnings and gotchas |
| `docs/epics/backlog.md` | Full task backlog |

### 13. License
One line: `MIT © 2026 Elias De Coppel — see [LICENSE](LICENSE).`

---

## Implementation Steps

1. Create `docs/images/` directory
2. Copy the four used assets from `assets/` to `docs/images/` with clean filenames:
   - `personal-dashboard.png`
   - `showcase.gif`
   - `club-dashboard.png`
   - `badges.png`
3. Rewrite `README.md` with the structure above
4. Mark TASK-10.2 ✅ in `docs/epics/backlog.md`
5. Commit: `docs(readme): overhaul with screenshots, badges, and docs index (TASK-10.2)`
