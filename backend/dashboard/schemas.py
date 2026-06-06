from datetime import datetime

from pydantic import BaseModel


class DailyDistancePoint(BaseModel):
    date: str  # YYYY-MM-DD
    cumulative_km: float


class PersonalDashboardResponse(BaseModel):
    goal_km: float
    distance_to_date_km: float
    progress_pct: float
    on_pace: bool
    expected_pct: float
    last_sync_completed_at: datetime
    daily_series: list[DailyDistancePoint]
