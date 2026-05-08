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

# 3. Install dependencies
uv sync --group backend --group frontend

# 4. Start the backend
uv run uvicorn backend.main:app --reload

# 5. In a separate terminal, start the frontend
uv run streamlit run frontend/app.py
```

Backend runs at http://localhost:8000. Frontend runs at http://localhost:8501.
