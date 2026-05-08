# strava-goal-visualizer-2

## Local Development Quickstart

**Prerequisites:** Python 3.12+, [uv](https://github.com/astral-sh/uv), PostgreSQL 16.

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd strava-goal-visualizer-2

# 2. Copy and fill in environment variables
cp .env.example .env
# Edit .env with your values

# 3. Install dependencies and the project (enables 'backend.*' / 'frontend.*' imports)
uv sync --group backend --group frontend
# If uv is not available, use pip as a fallback:
# .venv\Scripts\python.exe -m pip install -e .

# 4. Start the backend (PowerShell)
.venv\Scripts\uvicorn.exe backend.main:app --reload

# 5. In a separate terminal, start the frontend (PowerShell)
.venv\Scripts\streamlit.exe run frontend/app.py
```

Backend runs at http://localhost:8000. Frontend runs at http://localhost:8501.

## Docker Compose (recommended for local development)

**Prerequisites:** Docker with Compose plugin.

```bash
# 1. Copy and fill in environment variables
cp .env.example .env
# Edit .env with your Strava credentials and secrets

# 2. Start all services (db, backend, frontend)
docker compose up --build

# 3. Verify
curl http://localhost:8000/health      # → {"status":"ok"}
curl http://localhost:8000/health/db   # → {"db":"ok"}
# Streamlit: http://localhost:8501
```

All services have health checks. The backend waits for PostgreSQL to be healthy before starting, and the frontend waits for the backend.
