from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExportUser(BaseModel):
    strava_athlete_id: int
    display_name: str
    created_at: datetime


class ExportGoal(BaseModel):
    yearly_running_goal_km: float


class ExportSyncState(BaseModel):
    last_sync_completed_at: datetime


class ExportActivity(BaseModel):
    strava_activity_id: int
    name: str
    sport_type: str
    distance_meters: float
    moving_time_seconds: int
    start_date: datetime


class ExportClubMembership(BaseModel):
    club_id: int
    synced_at: datetime


class UserExportResponse(BaseModel):
    exported_at: datetime
    user: ExportUser
    goal: ExportGoal | None
    sync_state: ExportSyncState | None
    activities: list[ExportActivity]
    club_memberships: list[ExportClubMembership]


class DeleteResponse(BaseModel):
    deleted: bool


class WebhookChallengeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    hub_challenge: str = Field(alias="hub.challenge")


class StravaWebhookPayload(BaseModel):
    object_type: str
    aspect_type: str
    owner_id: int
    updates: dict[str, str] = {}


class DeauthResponse(BaseModel):
    status: str = "ok"
