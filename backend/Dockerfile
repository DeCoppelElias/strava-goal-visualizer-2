FROM python:3.12-slim

WORKDIR /app

# Install uv and curl (curl used for health checks)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Set up isolated virtual environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install only backend dependencies from the lockfile
COPY pyproject.toml uv.lock ./
RUN uv sync --only-group backend --no-dev

# Copy only backend source and alembic config
COPY backend/ backend/
COPY alembic.ini ./

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
