import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware

from backend.auth.router import router as auth_router
from backend.clubs.router import router as clubs_router
from backend.dashboard.router import router as dashboard_router
from backend.goals.router import router as goals_router
from backend.privacy.router import router as privacy_router
from backend.shared.config import settings
from backend.shared.db import engine
from backend.shared.logging import configure_logging
from backend.shared.rate_limit import limiter
from backend.shared.request_id import RequestIdMiddleware
from backend.sync.router import router as sync_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
configure_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — run DB migrations on startup
# ---------------------------------------------------------------------------
def _run_migrations() -> None:
    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Running database migrations...")
    await asyncio.to_thread(_run_migrations)
    logger.info("Database migrations complete.")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Strava Goal Visualizer API", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    https_only=settings.session_cookie_secure,
    same_site="lax",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.include_router(auth_router)
app.include_router(sync_router)
app.include_router(goals_router)
app.include_router(dashboard_router)
app.include_router(clubs_router)
app.include_router(privacy_router)


# ---------------------------------------------------------------------------
# Health schemas
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str


class DbHealthResponse(BaseModel):
    db: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/health/db", response_model=DbHealthResponse)
@limiter.limit("10/minute")
async def health_db(request: Request) -> DbHealthResponse:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return DbHealthResponse(db="ok")
    except (SQLAlchemyError, OSError) as exc:
        logger.error("DB health check failed: %s", exc)
        return DbHealthResponse(db="error")
