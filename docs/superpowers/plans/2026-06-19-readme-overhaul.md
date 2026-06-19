# README Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite README.md with a hero image, showcase GIF, badges, table of contents, features screenshots, and a documentation index so any visitor immediately understands what the app is and looks like.

**Architecture:** Pure documentation task — copy 4 image assets from `assets/` to `docs/images/` with clean filenames, then rewrite `README.md` in full. No code changes.

**Tech Stack:** Markdown, shields.io static badges.

---

## Files Touched

| File | Action | Purpose |
|---|---|---|
| `docs/images/personal-dashboard.png` | Create (copy) | Hero image |
| `docs/images/showcase.gif` | Create (copy) | "See it in action" section |
| `docs/images/club-dashboard.png` | Create (copy) | Screenshot after Features list |
| `docs/images/badges.png` | Create (copy) | Screenshot after club dashboard |
| `README.md` | Rewrite | Full overhaul |
| `docs/epics/backlog.md` | Modify | Mark TASK-10.2 ✅ |

---

## Task 1: Copy images to `docs/images/`

**Files:**
- Create: `docs/images/personal-dashboard.png`
- Create: `docs/images/showcase.gif`
- Create: `docs/images/club-dashboard.png`
- Create: `docs/images/badges.png`

- [ ] **Step 1: Create the `docs/images/` directory and copy assets**

  ```bash
  mkdir -p docs/images
  cp "assets/Personal Dashboard Screen.png" docs/images/personal-dashboard.png
  cp "assets/Showcase.gif" docs/images/showcase.gif
  cp "assets/Club Dashboard.png" docs/images/club-dashboard.png
  cp "assets/Badges.png" docs/images/badges.png
  ```

- [ ] **Step 2: Verify all four files exist**

  ```bash
  ls docs/images/
  ```

  Expected output:
  ```
  badges.png
  club-dashboard.png
  personal-dashboard.png
  showcase.gif
  ```

- [ ] **Step 3: Commit images**

  ```bash
  git add docs/images/
  git commit -m "docs(images): add screenshots and showcase gif for README"
  ```

---

## Task 2: Rewrite README.md

**Files:**
- Rewrite: `README.md`

- [ ] **Step 1: Replace the entire contents of `README.md` with the following**

  ```markdown
  # Strava Goal Visualizer

  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
  [![Node](https://img.shields.io/badge/Node-22-green.svg)](https://nodejs.org/)

  > A personal running goal tracker that visualises your yearly Strava progress.

  ![Personal Dashboard](docs/images/personal-dashboard.png)

  ## Table of Contents

  - [Overview](#overview)
  - [See it in action](#see-it-in-action)
  - [Features](#features)
  - [Tech Stack](#tech-stack)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Docker Compose](#docker-compose)
  - [Generating Secret Keys](#generating-secret-keys)
  - [Running Tests](#running-tests)
  - [Documentation](#documentation)
  - [License](#license)

  ## Overview

  Strava Goal Visualizer connects to your Strava account and tracks your progress towards a yearly running distance goal. Set a target in kilometres, sync your activities, and watch the pace chart fill in as the year progresses — giving you an honest read on whether you're ahead or behind the expected pace at any point in the year.

  Beyond personal goals, the app shows club progress: each member's cumulative distance plotted on a shared chart, so you can see at a glance how the whole group is tracking. Achievements unlock at milestone distances (10 / 100 / 365 / 1,000 km), and the dashboard updates whenever you choose to sync.

  The app is self-hosted — you run your own instance with your own Strava API credentials. No third-party service stores your data.

  ## See it in action

  ![Showcase](docs/images/showcase.gif)

  ## Features

  - Personal yearly running goal dashboard with cumulative pace chart
  - On-pace indicator — shows whether you're ahead or behind at today's date
  - Achievement badges at 10 / 100 / 365 / 1,000 km milestones
  - Club member progress view with per-member pace lines
  - Strava OAuth login — no password required
  - Self-hosted on Fly.io with a single-command deploy

  ![Club Dashboard](docs/images/club-dashboard.png)

  ![Badges](docs/images/badges.png)

  ## Tech Stack

  | Layer | Technology |
  |---|---|
  | Backend | FastAPI (Python 3.12), SQLAlchemy async, Alembic |
  | Frontend | React 18, Vite, TypeScript, Recharts |
  | Database | PostgreSQL 16 |
  | Auth | Strava OAuth 2.0, signed session cookies |
  | Deployment | Fly.io (single-app), Docker multi-stage build |

  ## Prerequisites

  - [uv](https://github.com/astral-sh/uv) — manages Python 3.12 automatically
  - [Node.js](https://nodejs.org/) **22** — for the React frontend
  - [Docker](https://www.docker.com/) — for running PostgreSQL locally
  - `make` — used for dev commands (built-in on macOS/Linux; install on Windows)

  ### Windows: install prerequisites

  Open **PowerShell** (not Git Bash) and run:

  ```powershell
  # uv (Python manager)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

  # make — pick one:
  winget install GnuWin32.Make          # requires winget (pre-installed on Windows 11)
  # or: scoop install make              # requires https://scoop.sh
  # or: choco install make              # requires https://chocolatey.org
  ```

  Restart your terminal after installing.

  #### No make? Run commands manually

  ```powershell
  uv sync --group backend --group dev
  cd frontend; npm install; cd ..
  uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
  ```

  ## Local Development

  ```bash
  # 1. Clone and enter the repo
  git clone <repo-url>
  cd strava-goal-visualizer-2

  # 2. Copy and fill in environment variables
  cp .env.example .env
  # Edit .env with your Strava credentials and generated secrets

  # 3. Install all dependencies (backend Python + frontend Node)
  make install-dev

  # 4. Start PostgreSQL
  docker compose up db -d

  # 5. Run database migrations
  uv run alembic upgrade head

  # 6. Start the backend (in one terminal)
  uv run uvicorn backend.main:app --reload --port 8000

  # 7. Start the frontend (in a separate terminal)
  cd frontend
  npm run dev
  ```

  - Backend API: http://localhost:8000
  - Frontend: http://localhost:5173
  - Swagger docs: http://localhost:8000/docs

  ## Docker Compose

  **Prerequisites:** Docker with Compose plugin.

  ```bash
  # 1. Copy and fill in environment variables
  cp .env.example .env

  # 2. Build and start all services (db, backend, frontend)
  docker compose up --build

  # 3. Verify
  curl http://localhost:8000/health     # → {"status":"ok"}
  curl http://localhost:8000/health/db  # → {"db":"ok"}
  # Frontend: http://localhost:5173
  ```

  ## Generating Secret Keys

  Run these once and paste the output into `.env`:

  ```bash
  # SESSION_SECRET_KEY
  python -c "import secrets; print(secrets.token_hex(32))"

  # TOKEN_ENCRYPTION_KEY
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

  ## Running Tests

  Docker must be running (tests spin up a throwaway Postgres via testcontainers).

  ```bash
  make test
  ```

  ## Documentation

  | Document | Description |
  |---|---|
  | [docs/ops/deployment.md](docs/ops/deployment.md) | Production deployment guide (Fly.io) |
  | [docs/ops/db-statistics.md](docs/ops/db-statistics.md) | DB usage statistics queries |
  | [docs/design.md](docs/design.md) | Architecture and design decisions |
  | [docs/design/style.md](docs/design/style.md) | Frontend design system |
  | [docs/workflow.md](docs/workflow.md) | Development workflow |
  | [docs/learnings.md](docs/learnings.md) | Project learnings and gotchas |
  | [docs/epics/backlog.md](docs/epics/backlog.md) | Full task backlog |

  ## License

  MIT © 2026 Elias De Coppel — see [LICENSE](LICENSE).
  ```

- [ ] **Step 2: Verify image paths resolve**

  All four image references in the README must match the filenames copied in Task 1:

  ```
  docs/images/personal-dashboard.png  ← hero image
  docs/images/showcase.gif            ← See it in action
  docs/images/club-dashboard.png      ← after Features list
  docs/images/badges.png              ← after club dashboard
  ```

  Check each path exists:

  ```bash
  ls docs/images/personal-dashboard.png docs/images/showcase.gif docs/images/club-dashboard.png docs/images/badges.png
  ```

  Expected: all four files listed with no errors.

- [ ] **Step 3: Commit README**

  ```bash
  git add README.md
  git commit -m "docs(readme): overhaul with screenshots, badges, and docs index (TASK-10.2)"
  ```

---

## Task 3: Mark TASK-10.2 complete in backlog

**Files:**
- Modify: `docs/epics/backlog.md`

- [ ] **Step 1: Find `#### TASK-10.2` in `docs/epics/backlog.md` and change it to `#### TASK-10.2 ✅`**

- [ ] **Step 2: Commit**

  ```bash
  git add docs/epics/backlog.md
  git commit -m "docs(backlog): mark TASK-10.2 complete"
  ```

---

## Self-Review

**Spec coverage:**
- ✅ Hero image (`personal-dashboard.png`) — Task 2 README
- ✅ Badges (MIT, Python 3.12, Node 22) — Task 2 README
- ✅ Tagline — Task 2 README
- ✅ Table of contents — Task 2 README
- ✅ Overview paragraph — Task 2 README
- ✅ Showcase GIF — Task 2 README
- ✅ Features bullet list — Task 2 README
- ✅ Club Dashboard screenshot — Task 2 README
- ✅ Badges screenshot — Task 2 README
- ✅ Tech stack table — Task 2 README
- ✅ Prerequisites with Node 22 corrected — Task 2 README
- ✅ Windows install instructions kept — Task 2 README
- ✅ Local Development quickstart — Task 2 README
- ✅ Docker Compose section — Task 2 README
- ✅ Generating Secret Keys — Task 2 README
- ✅ Running Tests — Task 2 README
- ✅ Documentation index — Task 2 README
- ✅ License line — Task 2 README
- ✅ Images copied to `docs/images/` — Task 1
- ✅ TASK-10.2 marked ✅ in backlog — Task 3
- ✅ `Main Screen.png` and `Privacy Page.png` not used — confirmed excluded

**Placeholder scan:** `<repo-url>` in the Local Development clone step is a correct, intentional placeholder (the actual URL is not known at doc-write time). No other placeholders.

**Type consistency:** N/A — documentation only.
