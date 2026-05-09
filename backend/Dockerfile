FROM python:3.12-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest and install all deps declared in pyproject.toml.
# Done before copying source so this layer is cached unless pyproject.toml changes.
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy source code and reinstall the project package (--no-deps skips re-downloading deps).
# Separate step so code changes don't bust the dependency cache layer above.
COPY backend/ backend/
COPY frontend/ frontend/
RUN pip install --no-cache-dir --no-deps .

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
