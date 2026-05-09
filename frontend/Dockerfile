FROM python:3.12-slim

WORKDIR /app

# Install uv and curl (curl used for health checks)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Set up isolated virtual environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install only frontend dependencies from the lockfile
COPY pyproject.toml uv.lock ./
RUN uv sync --only-group frontend --no-dev

# Copy only frontend source
COPY frontend/ frontend/

CMD ["python", "-m", "streamlit", "run", "frontend/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
