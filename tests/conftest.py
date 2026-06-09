import os
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

# Set required env vars BEFORE importing any backend module: backend.shared.config
# calls sys.exit(1) at import time if any are missing, and there is no .env in CI.
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("STRAVA_CLIENT_ID", "test-client-id")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("STRAVA_REDIRECT_URI", "http://localhost:8000/oauth/callback")
os.environ.setdefault("SESSION_SECRET_KEY", "test-session-secret")

from backend.shared.models import Base  # noqa: E402  (must follow env setup above)


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Start one throwaway Postgres for the whole test session (synchronous: stays
    off the event loop, so it never collides with per-test loops)."""
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        yield pg


@pytest_asyncio.fixture
async def db(postgres_container: PostgresContainer) -> AsyncGenerator[AsyncSession, None]:
    """Per-test AsyncSession against a fresh schema. A new engine is built on the
    test's own event loop (Option A: no shared engine, no global loop-scope config)."""
    engine = create_async_engine(postgres_container.get_connection_url())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
