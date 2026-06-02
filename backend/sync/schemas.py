from datetime import datetime

from pydantic import BaseModel


class SyncResponse(BaseModel):
    synced_activities: int
    last_sync_completed_at: datetime
