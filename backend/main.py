import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment — fail fast on missing required variables.
# Add new required variables here as they are introduced in later tasks.
# ---------------------------------------------------------------------------
_REQUIRED_ENV_VARS: list[str] = [
    "FRONTEND_ORIGIN",
]

_missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
if _missing:
    logger.error("Missing required environment variables: %s", ", ".join(_missing))
    sys.exit(1)

FRONTEND_ORIGIN: str = os.environ["FRONTEND_ORIGIN"]

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Strava Goal Visualizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
