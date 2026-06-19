# ---- Stage 1: Build React frontend ----
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./

# Empty string → all fetch() calls use relative paths (same origin as API in prod)
ENV VITE_API_BASE_URL=""
RUN npm run build

# ---- Stage 2: Backend runtime ----
FROM python:3.12-slim
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --only-group backend --no-dev

COPY backend/ backend/
COPY alembic.ini ./
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

CMD ["python", "-m", "uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips=*"]
