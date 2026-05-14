import logging

from backend.config import settings
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

logger = logging.getLogger(__name__)

engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)
