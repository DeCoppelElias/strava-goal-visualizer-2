from pydantic import BaseModel, Field


class GoalResponse(BaseModel):
    yearly_running_goal_km: float


class UpdateGoalRequest(BaseModel):
    yearly_running_goal_km: float = Field(gt=0, le=100_000)
