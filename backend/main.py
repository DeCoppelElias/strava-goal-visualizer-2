import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.db import engine, get_db
from backend.dependencies import get_strava_oauth_service
from backend.helpers.config import settings
from backend.services.strava_oauth_service import StravaOAuthService

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
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
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
@limiter.limit("10/minute")  # type: ignore[misc]
async def health_db(request: Request) -> dict[str, str]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"db": "ok"}
    except (SQLAlchemyError, OSError) as exc:
        logger.error("DB health check failed: %s", exc)
        return {"db": "error"}


# ---------------------------------------------------------------------------
# Oauth
# ---------------------------------------------------------------------------
@app.post("/oauth/authorize")
@limiter.limit("10/minute")  # type: ignore[misc]
async def oauth_authorize(
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    strava_oauth_service: StravaOAuthService = Depends(get_strava_oauth_service),  # noqa: B008
) -> dict[str, str]:
    authorization_url = await strava_oauth_service.create_authorization_url(db)

    return {"authorization_url": authorization_url}
