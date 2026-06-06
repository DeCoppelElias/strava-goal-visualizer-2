from datetime import datetime

from pydantic import BaseModel, Field


class GoalResponse(BaseModel):
    yearly_running_goal_km: float


class UpdateGoalRequest(BaseModel):
    yearly_running_goal_km: float = Field(gt=0, le=100_000)


class PersonalDashboardResponse(BaseModel):
    goal_km: float
    distance_to_date_km: float
    progress_pct: float
    on_pace: bool
    expected_pct: float
    last_sync_completed_at: datetime
