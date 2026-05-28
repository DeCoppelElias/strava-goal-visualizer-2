from datetime import datetime

from pydantic import BaseModel


class AuthorizeResponse(BaseModel):
    authorization_url: str


class SessionMeResponse(BaseModel):
    strava_athlete_id: int
    created_at: datetime


class LogoutResponse(BaseModel):
    ok: bool


class RevokeResponse(BaseModel):
    ok: bool
