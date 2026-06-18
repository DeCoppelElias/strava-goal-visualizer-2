import pytest
from backend.shared.models import DeletionEvent, DeletionReason
from sqlalchemy import select


@pytest.mark.asyncio
async def test_deletion_event_insert_and_read(db):
    event = DeletionEvent(
        user_id=12345678,
        reason=DeletionReason.USER_INITIATED,
    )
    db.add(event)
    await db.flush()

    result = await db.execute(select(DeletionEvent).where(DeletionEvent.id == event.id))
    row = result.scalar_one()

    assert row.user_id == 12345678
    assert row.reason == "user_initiated"
    assert row.deleted_at is not None


@pytest.mark.asyncio
async def test_deletion_event_strava_deauth_reason(db):
    event = DeletionEvent(
        user_id=99999999,
        reason=DeletionReason.STRAVA_DEAUTH,
    )
    db.add(event)
    await db.flush()

    result = await db.execute(select(DeletionEvent).where(DeletionEvent.id == event.id))
    row = result.scalar_one()

    assert row.reason == "strava_deauth"


def test_deletion_reason_enum_string_equality():
    assert DeletionReason.USER_INITIATED == "user_initiated"
    assert DeletionReason.STRAVA_DEAUTH == "strava_deauth"
