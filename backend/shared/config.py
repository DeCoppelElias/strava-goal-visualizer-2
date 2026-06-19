import logging
import os
import re
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required environment variables.
# Add new required variables here as they are introduced in later tasks.
# ---------------------------------------------------------------------------
_REQUIRED_ENV_VARS: list[str] = [
    "FRONTEND_ORIGIN",
    "DATABASE_URL",
    "TOKEN_ENCRYPTION_KEY",
    "STRAVA_CLIENT_ID",
    "STRAVA_CLIENT_SECRET",
    "STRAVA_REDIRECT_URI",
    "SESSION_SECRET_KEY",
    "STRAVA_WEBHOOK_VERIFY_TOKEN",
]

_missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
if _missing:
    logger.error("Missing required environment variables: %s", ", ".join(_missing))
    sys.exit(1)


@dataclass(frozen=True)
class Settings:
    frontend_origin: str
    database_url: str
    token_encryption_key: str
    strava_client_id: str
    strava_client_secret: str
    strava_redirect_uri: str
    session_secret_key: str
    strava_webhook_verify_token: str
    sync_cooldown_seconds: int = 600
    session_cookie_secure: bool = True
    strava_webhook_subscription_id: int | None = None


def _asyncpg_url(url: str) -> str:
    # Fly Postgres sets DATABASE_URL as postgres:// or postgresql://; asyncpg needs postgresql+asyncpg://
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1).replace(
        "postgres://", "postgresql+asyncpg://", 1
    )
    # asyncpg does not accept sslmode; translate sslmode=disable → ssl=disable so
    # asyncpg does not attempt a TLS handshake (Fly internal network rejects it).
    # Any other sslmode variant is stripped and asyncpg uses its default.
    url = re.sub(r"([?&])sslmode=disable", r"\1ssl=disable", url)
    url = re.sub(r"\?sslmode=[^&]*&", "?", url)
    url = re.sub(r"[?&]sslmode=[^&]*", "", url)
    return url


settings = Settings(
    frontend_origin=os.environ["FRONTEND_ORIGIN"],
    database_url=_asyncpg_url(os.environ["DATABASE_URL"]),
    token_encryption_key=os.environ["TOKEN_ENCRYPTION_KEY"],
    strava_client_id=os.environ["STRAVA_CLIENT_ID"],
    strava_client_secret=os.environ["STRAVA_CLIENT_SECRET"],
    strava_redirect_uri=os.environ["STRAVA_REDIRECT_URI"],
    session_secret_key=os.environ["SESSION_SECRET_KEY"],
    strava_webhook_verify_token=os.environ["STRAVA_WEBHOOK_VERIFY_TOKEN"],
    sync_cooldown_seconds=int(os.environ.get("SYNC_COOLDOWN_SECONDS", "600")),
    session_cookie_secure=os.environ.get("SESSION_COOKIE_SECURE", "true").lower()
    not in ("false", "0"),
    strava_webhook_subscription_id=int(os.environ["STRAVA_WEBHOOK_SUBSCRIPTION_ID"])
    if os.environ.get("STRAVA_WEBHOOK_SUBSCRIPTION_ID")
    else None,
)
