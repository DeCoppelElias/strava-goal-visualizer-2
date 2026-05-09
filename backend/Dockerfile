FROM python:3.12-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy source and install all runtime dependencies declared in pyproject.toml.
# [project.dependencies] is read by pip; [dependency-groups] is uv-only and ignored here.
COPY pyproject.toml ./
COPY backend/ backend/
COPY frontend/ frontend/
RUN pip install --no-cache-dir .

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
