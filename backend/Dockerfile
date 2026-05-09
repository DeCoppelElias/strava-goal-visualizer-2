FROM python:3.12-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (cached layer unless pyproject.toml changes)
COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" sqlalchemy[asyncio] asyncpg httpx cryptography python-dotenv

# Copy source and install the project (registers backend.* and frontend.* packages)
COPY backend/ backend/
COPY frontend/ frontend/
RUN pip install --no-cache-dir --no-deps -e .

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
