# TASK-6.4 — Club Dashboard Endpoint Design

**Date:** 2026-06-10
**Task:** Implement `GET /dashboard/club/{club_id}`

---

## Decisions Made During Brainstorming

### URL and service location

Original backlog spec: `GET /clubs/{club_id}/progress` in `ClubsService`.

**Changed to:** `GET /dashboard/club/{club_id}` in `DashboardService`.

Rationale: All "compute a progress view" logic lives in one service. `ClubMembership` lives in `shared/models`, so `DashboardService` querying it introduces no cross-domain import. The URL mirrors `GET /dashboard` (personal) → `GET /dashboard/club/{id}` (club), which is semantically consistent.

### Display name

Original backlog spec: `MemberProgressResponse` had no name field.

**Added:** `display_name: str` on `User`, stored as `"Firstname L."` (first name + last initial) when a last name is present, or `"Firstname"` alone when it is not. Full last name is not stored.

Rationale: Strava truncates last names to an initial for non-followed club members. The design doc cites GDPR data minimization. First name + initial is sufficient for club-member identification and matches Strava's own privacy convention.

`display_name` is populated from the OAuth callback's `token_data["athlete"]` dict, which contains `firstname: str` and `lastname: str` (confirmed against Strava `SummaryAthlete` model). It is updated on every login in case the user changes their name on Strava.

### `progress_pct`

Kept for frontend convenience, consistent with `PersonalDashboardResponse`.

---

## Schemas (`backend/dashboard/schemas.py`)

```python
class MemberProgressResponse(BaseModel):
    strava_athlete_id: int
    display_name: str
    distance_to_date_km: float
    goal_km: float
    progress_pct: float

class ClubDashboardResponse(BaseModel):
    club_id: int
    club_name: str
    members: list[MemberProgressResponse]
```

---

## Data Model (`backend/shared/models.py`)

Add to `User`:

```python
display_name: Mapped[str] = mapped_column(Text, default="")
```

New Alembic migration: `ALTER TABLE users ADD COLUMN display_name TEXT NOT NULL DEFAULT ''`.

---

## OAuth Update (`backend/auth/strava_oauth_service.py`)

`_upsert_user` accepts the full `athlete` dict instead of just the integer ID:

```python
async def _upsert_user(self, db: AsyncSession, athlete: dict[str, Any]) -> User:
    strava_athlete_id: int = athlete["id"]
    firstname = athlete.get("firstname", "")
    lastname = athlete.get("lastname", "")
    last_initial = f" {lastname[0]}." if lastname else ""
    display_name = f"{firstname}{last_initial}".strip()
    # fetch-or-create user, set user.display_name = display_name on both paths
```

`process_callback` passes `token_data["athlete"]` (the full dict) instead of `token_data["athlete"]["id"]`.

---

## Service (`backend/dashboard/dashboard_service.py`)

New method:

```python
async def get_club_dashboard(
    self, db: AsyncSession, requesting_user_id: int, club_id: int
) -> ClubDashboardResponse:
```

**Steps (3 queries, no N+1):**

1. **Membership check** — query `ClubMembership` where `user_id=requesting_user_id` and `club_id=club_id`. Raise `HTTPException(403)` if not found.
2. **Club fetch** — `select(Club).where(Club.id == club_id)`. Raise `HTTPException(404)` if missing.
3. **Members** — `select(User)` joined to `ClubMembership` where `club_id=club_id`.
4. **Activity aggregates** — single query: `select(Activity.user_id, func.sum(Activity.distance_meters))` where `user_id IN (member_ids)` and `start_date >= year_start`, grouped by `user_id`.
5. **Goals** — `select(Goal)` where `user_id IN (member_ids)`.
6. **Build response** — one `MemberProgressResponse` per member who has a goal. Members without a goal are excluded. Members with a goal but no activities get `distance_to_date_km=0.0`, `progress_pct=0.0`.

`progress_pct = round(distance_to_date_km / goal_km * 100, 2)`

---

## Route (`backend/dashboard/router.py`)

```python
@router.get("/dashboard/club/{club_id}", response_model=ClubDashboardResponse)
@limiter.limit("30/minute")
async def get_club_dashboard(
    request: Request,
    club_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> ClubDashboardResponse:
    return await dashboard_service.get_club_dashboard(db, current_user.id, club_id)
```

No changes to `dependencies.py` — `get_dashboard_service` already exists.

---

## Testing

### Integration — `tests/backend/dashboard/test_club_dashboard_service.py`

- Two members both in same club, both with goals and activities → both appear with correct `distance_to_date_km`, `goal_km`, `progress_pct`, `display_name`
- Requesting user not a member → `403`
- Member with no goal → excluded from `members`
- Member with goal but no activities → included with `distance_to_date_km=0.0`, `progress_pct=0.0`
- Activities from a previous year → not counted
- User B cannot see a club they are not in, even if the club exists

### Router tests — `tests/backend/dashboard/test_club_dashboard_router.py`

- Unauthenticated → `401`
- Non-member (service raises `403`) → `403`
- Happy path → `200` with correct response shape

### Auth service additions — `tests/backend/auth/test_strava_oauth_service.py`

- `firstname="Elias"`, `lastname="De Coppel"` → `display_name="Elias D."`
- Re-login with different name → `display_name` updated
- Athlete with no `lastname` → `display_name="Elias"` (no trailing dot or space)

---

## Backlog and Design Doc Updates Required

- `docs/epics/backlog.md`: update TASK-6.4 to reflect the new URL and `ClubDashboardResponse` shape
- `docs/design.md`: update the route table (`GET /clubs/{id}/progress` → `GET /dashboard/club/{club_id}`) and authorization table accordingly
