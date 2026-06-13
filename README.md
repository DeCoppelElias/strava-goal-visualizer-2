# strava-goal-visualizer-2

## Prerequisites

- [uv](https://github.com/astral-sh/uv) — manages Python 3.12 automatically
- [Node.js](https://nodejs.org/) 18+ — for the React frontend
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

## Local Development Quickstart

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

## Docker Compose (recommended)

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
