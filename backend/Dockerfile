FROM python:3.12-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first (cached layer unless pyproject.toml / uv.lock change)
ENV UV_SYSTEM_PYTHON=1
COPY pyproject.toml uv.lock ./
RUN uv sync --group backend --no-install-project

# Copy source and install the project itself
COPY backend/ backend/
COPY frontend/ frontend/
RUN uv sync --group backend --no-editable

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
