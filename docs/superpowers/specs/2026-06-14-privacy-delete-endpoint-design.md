# TASK-7.4: `POST /privacy/delete` Endpoint Design

**Date:** 2026-06-14
**Status:** Approved

---

## Goal

Allow an authenticated user to permanently delete their own account and all associated data (GDPR right to erasure / DSAR self-service).

---

## Dependencies

- **TASK-7.2** — `PrivacyService.delete_user_data` already implemented
- **TASK-2.6** — `get_current_user` dependency already implemented
- `DeletionReason.USER_INITIATED` enum value exists in `backend/shared/models.py`

---

## Schema

**File:** `backend/privacy/schemas.py`

Add one model:

```python
class DeleteResponse(BaseModel):
    deleted: bool
```

---

## Endpoint

**File:** `backend/privacy/router.py`

```python
@router.post("/privacy/delete", response_model=DeleteResponse)
@limiter.limit("5/hour")
async def delete_user_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    privacy_service: PrivacyService = Depends(get_privacy_service),
) -> DeleteResponse:
    await privacy_service.delete_user_data(
        db, user_id=current_user.id, reason=DeletionReason.USER_INITIATED
    )
    request.session.clear()
    return DeleteResponse(deleted=True)
```

### Key behaviour

- `DeletionReason.USER_INITIATED` is passed so `deletion_events` records the reason correctly.
- `request.session.clear()` is called after the delete — the session middleware writes the cleared cookie into the response, so the client is logged out.
- DB commit happens at `get_db` context exit (after the endpoint returns via `session.begin()` auto-commit), which is the correct order.
- Rate limit: `5/hour` (same as export endpoint, per `docs/design.md` §6.0.3).
- Unauthenticated calls raise `401` via `get_current_user`.

---

## Tests

**Location:** `tests/backend/privacy/`

Integration test against a real Postgres (via `db` fixture):

1. Seed a user with activities, goal, sync state, club memberships, OAuth credentials.
2. Set `user_id` in session to simulate authentication.
3. Call `POST /privacy/delete` → assert `200 {"deleted": true}`.
4. Assert all rows gone from DB (users, activities, goals, etc.).
5. Assert `deletion_events` has one entry with reason `USER_INITIATED`.
6. Assert subsequent `GET /session/me` returns `401` (session cleared).
