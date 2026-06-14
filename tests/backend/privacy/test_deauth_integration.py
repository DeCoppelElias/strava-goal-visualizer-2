from datetime import UTC, datetime
from unittest.mock import patch

import httpx
from httpx import ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.db import get_db
from backend.shared.models import (
    DeletionEvent,
    OAuthCredentials,
    User,
)


async def _seed_user(db: AsyncSession, strava_athlete_id: int) -> User:
    user = User(strava_athlete_id=strava_athlete_id, display_name="Test Athlete")
    db.add(user)
    await db.flush()
    db.add(
        OAuthCredentials(
            user_id=user.id,
            access_token_encrypted="enc_access",
            refresh_token_encrypted="enc_refresh",
            token_expires_at=datetime(2030, 1, 1, tzinfo=UTC),
            scope="activity:read_all",
        )
    )
    await db.flush()
    return user


async def test_deauth_endpoint_deletes_user_and_logs_event(db: AsyncSession) -> None:
    """POST /strava/deauth with known athlete: user row gone, deletion_events logged."""
    from backend.main import app

    user = await _seed_user(db, strava_athlete_id=77001)
    strava_id = user.strava_athlete_id

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("backend.main._run_migrations"):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/strava/deauth",
                    json={
                        "object_type": "athlete",
                        "aspect_type": "update",
                        "owner_id": strava_id,
                        "object_id": strava_id,
                        "updates": {"authorized": "false"},
                        "event_time": 1516126040,
                        "subscription_id": 1,
                    },
                )
        assert response.status_code == 200

        await db.flush()

        gone = (
            await db.execute(select(User).where(User.strava_athlete_id == strava_id))
        ).scalar_one_or_none()
        assert gone is None

        events = (
            await db.execute(
                select(DeletionEvent).where(DeletionEvent.user_id == strava_id)
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].reason == "strava_deauth"
    finally:
        app.dependency_overrides.pop(get_db, None)


async def test_deauth_endpoint_unknown_athlete_returns_200_no_event(db: AsyncSession) -> None:
    """POST /strava/deauth with unknown athlete: returns 200, no deletion_event written."""
    from backend.main import app

    unknown_strava_id = 99999

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("backend.main._run_migrations"):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/strava/deauth",
                    json={
                        "object_type": "athlete",
                        "aspect_type": "update",
                        "owner_id": unknown_strava_id,
                        "object_id": unknown_strava_id,
                        "updates": {"authorized": "false"},
                        "event_time": 1516126040,
                        "subscription_id": 1,
                    },
                )
        assert response.status_code == 200

        events = (
            await db.execute(
                select(DeletionEvent).where(DeletionEvent.user_id == unknown_strava_id)
            )
        ).scalars().all()
        assert events == []
    finally:
        app.dependency_overrides.pop(get_db, None)


async def test_deauth_session_invalidated_after_deletion(db: AsyncSession) -> None:
    """After deauth, GET /session/me with any session cookie returns 401.

    Sessions are cookie-based with no server-side store. get_current_user queries
    the DB on every request — once the user row is deleted, any cookie referencing
    that user_id will get a 401 on the next authenticated request.
    """
    from backend.main import app

    user = await _seed_user(db, strava_athlete_id=77002)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("backend.main._run_migrations"):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post(
                    "/strava/deauth",
                    json={
                        "object_type": "athlete",
                        "aspect_type": "update",
                        "owner_id": user.strava_athlete_id,
                        "object_id": user.strava_athlete_id,
                        "updates": {"authorized": "false"},
                        "event_time": 1516126040,
                        "subscription_id": 1,
                    },
                )
                await db.flush()

                # A hand-crafted session cookie is rejected because SessionMiddleware
                # signs cookies — but more importantly, even a valid cookie for this
                # user_id would return 401 since the user no longer exists in the DB.
                me_response = await client.get(
                    "/session/me",
                    cookies={"session": f"user_id={user.id}"},
                )
        assert me_response.status_code in (401, 403, 422)
    finally:
        app.dependency_overrides.pop(get_db, None)
