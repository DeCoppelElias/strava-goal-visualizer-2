# Club Pace Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a multi-line percentage-of-goal progress chart to the club view, showing each member's cumulative running distance over the current year on a shared axis with a linear pace reference line.

**Architecture:** Extract a `_build_daily_series` private helper from `get_personal_dashboard` and reuse it in `get_club_dashboard`, which is rewritten to fetch raw per-member activity rows in one bulk query (`WHERE user_id IN (...)`) instead of a `GROUP BY` aggregate. The frontend renders a new `ClubPaceChart` component that converts km series to percentages client-side and draws one Recharts `<Line>` per member, with hue-rotated colors and end-of-line name labels. The current user's line is always `--accent` blue and thicker.

**Tech Stack:** FastAPI + SQLAlchemy async (backend), React + Recharts (frontend), pytest + testcontainers (integration tests)

---

### Task 1: Extract `_build_daily_series` private helper

**Files:**
- Modify: `backend/dashboard/dashboard_service.py`
- Modify: `tests/backend/dashboard/test_dashboard_service.py`

- [ ] **Step 1: Write failing unit tests for `_build_daily_series`**

Add these tests to the bottom of `tests/backend/dashboard/test_dashboard_service.py`:

```python
# ── _build_daily_series unit tests ──────────────────────────────────────────

def test_build_daily_series_single_activity() -> None:
    from decimal import Decimal
    year = _real_datetime.now(UTC).year
    rows = [(datetime(year, 1, 5, tzinfo=UTC), Decimal("10000"))]
    result = DashboardService._build_daily_series(rows)
    assert len(result) == 1
    assert result[0].date == f"{year}-01-05"
    assert result[0].cumulative_km == 10.0


def test_build_daily_series_accumulates_across_days() -> None:
    from decimal import Decimal
    year = _real_datetime.now(UTC).year
    rows = [
        (_real_datetime(year, 1, 5, tzinfo=UTC), Decimal("10000")),
        (_real_datetime(year, 1, 10, tzinfo=UTC), Decimal("5000")),
    ]
    result = DashboardService._build_daily_series(rows)
    assert len(result) == 2
    assert result[0].cumulative_km == 10.0
    assert result[1].cumulative_km == 15.0


def test_build_daily_series_merges_same_day_activities() -> None:
    from decimal import Decimal
    year = _real_datetime.now(UTC).year
    rows = [
        (_real_datetime(year, 3, 1, 8, 0, 0, tzinfo=UTC), Decimal("5000")),
        (_real_datetime(year, 3, 1, 17, 0, 0, tzinfo=UTC), Decimal("3000")),
    ]
    result = DashboardService._build_daily_series(rows)
    assert len(result) == 1
    assert result[0].date == f"{year}-03-01"
    assert result[0].cumulative_km == 8.0


def test_build_daily_series_empty_input() -> None:
    result = DashboardService._build_daily_series([])
    assert result == []
```

- [ ] **Step 2: Run to confirm they fail**

```
uv run pytest tests/backend/dashboard/test_dashboard_service.py -k "build_daily_series" -v
```

Expected: `AttributeError: type object 'DashboardService' has no attribute '_build_daily_series'`

- [ ] **Step 3: Add the `Decimal` import and extract the helper in `dashboard_service.py`**

Add `from decimal import Decimal` to the imports at the top of `backend/dashboard/dashboard_service.py`.

Then add this static method inside `DashboardService` (before `get_personal_dashboard`):

```python
@staticmethod
def _build_daily_series(
    rows: list[tuple[datetime, Decimal]],
) -> list[DailyDistancePoint]:
    daily_totals: dict[str, float] = defaultdict(float)
    for start_date, distance_meters in rows:
        date_str = start_date.date().isoformat()
        daily_totals[date_str] += float(distance_meters)

    series: list[DailyDistancePoint] = []
    cumulative = 0.0
    for date_str, day_meters in daily_totals.items():
        cumulative += day_meters / 1000
        series.append(DailyDistancePoint(date=date_str, cumulative_km=round(cumulative, 3)))
    return series
```

- [ ] **Step 4: Replace the inline logic in `get_personal_dashboard` with a call to the helper**

In `get_personal_dashboard`, replace the entire block from the `# Group by calendar date` comment through the closing `daily_series.append(...)` call with:

```python
daily_series = self._build_daily_series(
    [(row.start_date, row.distance_meters) for row in rows]
)
```

The `sum_meters` line that follows still uses `rows` directly and is unchanged.

- [ ] **Step 5: Run all tests to confirm nothing broke**

```
uv run pytest tests/backend/dashboard/ -v
```

Expected: all tests pass, including the 4 new `_build_daily_series` tests.

- [ ] **Step 6: Commit**

```
git add backend/dashboard/dashboard_service.py tests/backend/dashboard/test_dashboard_service.py
git commit -m "refactor(dashboard): extract _build_daily_series helper from get_personal_dashboard"
```

---

### Task 2: Add `daily_series` to schema and rewrite `get_club_dashboard`

**Files:**
- Modify: `backend/dashboard/schemas.py`
- Modify: `backend/dashboard/dashboard_service.py`
- Modify: `tests/backend/dashboard/test_club_dashboard_service.py`

- [ ] **Step 1: Write failing integration tests for `daily_series`**

Add these two tests to the bottom of `tests/backend/dashboard/test_club_dashboard_service.py`:

```python
async def test_get_club_dashboard_includes_daily_series(db: AsyncSession) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=10, name="Series Club")
    user_a = await _seed_user(db, strava_athlete_id=1000, display_name="Eve E.")
    user_b = await _seed_user(db, strava_athlete_id=1001, display_name="Frank F.")
    await _seed_membership(db, user_a.id, club.id)
    await _seed_membership(db, user_b.id, club.id)
    await _seed_goal(db, user_a.id, yearly_km=100.0)
    await _seed_goal(db, user_b.id, yearly_km=200.0)
    year = datetime.now(UTC).year
    await _seed_activity(db, user_a.id, 10_000, datetime(year, 1, 5, tzinfo=UTC))
    await _seed_activity(db, user_a.id, 5_000, datetime(year, 1, 10, tzinfo=UTC))
    await _seed_activity(db, user_b.id, 20_000, datetime(year, 1, 10, tzinfo=UTC))

    result = await svc.get_club_dashboard(db, requesting_user_id=user_a.id, club_id=club.id)

    by_athlete = {m.strava_athlete_id: m for m in result.members}
    series_a = by_athlete[1000].daily_series
    assert len(series_a) == 2
    assert series_a[0].date == f"{year}-01-05"
    assert series_a[0].cumulative_km == 10.0
    assert series_a[1].date == f"{year}-01-10"
    assert series_a[1].cumulative_km == 15.0

    series_b = by_athlete[1001].daily_series
    assert len(series_b) == 1
    assert series_b[0].cumulative_km == 20.0


async def test_get_club_dashboard_empty_series_for_member_without_activities(
    db: AsyncSession,
) -> None:
    svc = DashboardService()
    club = await _seed_club(db, club_id=11, name="Ghost Club")
    user = await _seed_user(db, strava_athlete_id=1100, display_name="Ghost G.")
    await _seed_membership(db, user.id, club.id)
    await _seed_goal(db, user.id, yearly_km=100.0)

    result = await svc.get_club_dashboard(db, requesting_user_id=user.id, club_id=club.id)

    assert result.members[0].daily_series == []
```

- [ ] **Step 2: Run to confirm they fail**

```
uv run pytest tests/backend/dashboard/test_club_dashboard_service.py -k "daily_series" -v
```

Expected: `ValidationError` or `AttributeError` because `daily_series` field doesn't exist yet.

- [ ] **Step 3: Add `daily_series` to `MemberProgressResponse` in `schemas.py`**

Replace the `MemberProgressResponse` class in `backend/dashboard/schemas.py` with:

```python
class MemberProgressResponse(BaseModel):
    strava_athlete_id: int
    display_name: str
    distance_to_date_km: float
    goal_km: float
    progress_pct: float
    daily_series: list[DailyDistancePoint]
```

- [ ] **Step 4: Rewrite `get_club_dashboard` in `dashboard_service.py`**

Replace the entire `get_club_dashboard` method with:

```python
async def get_club_dashboard(
    self, db: AsyncSession, requesting_user_id: int, club_id: int
) -> ClubDashboardResponse:
    membership_result = await db.execute(
        select(ClubMembership).where(
            ClubMembership.user_id == requesting_user_id,
            ClubMembership.club_id == club_id,
        )
    )
    if membership_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="not_a_member")

    club_result = await db.execute(select(Club).where(Club.id == club_id))
    club = club_result.scalar_one_or_none()
    if club is None:
        raise HTTPException(status_code=404, detail="club_not_found")

    members_result = await db.execute(
        select(User)
        .join(ClubMembership, ClubMembership.user_id == User.id)
        .where(ClubMembership.club_id == club_id)
    )
    members = list(members_result.scalars().all())
    member_ids = [m.id for m in members]

    if not member_ids:
        return ClubDashboardResponse(club_id=club.id, club_name=club.name, members=[])

    now = datetime.now(UTC)
    year_start = datetime(now.year, 1, 1, tzinfo=UTC)

    activity_result = await db.execute(
        select(Activity.user_id, Activity.start_date, Activity.distance_meters)
        .where(
            Activity.user_id.in_(member_ids),
            Activity.start_date >= year_start,
        )
        .order_by(Activity.start_date.asc())
    )
    all_rows = activity_result.all()

    rows_by_user: dict[int, list[tuple[datetime, Decimal]]] = defaultdict(list)
    total_meters_by_user: dict[int, float] = defaultdict(float)
    for row in all_rows:
        rows_by_user[row.user_id].append((row.start_date, row.distance_meters))
        total_meters_by_user[row.user_id] += float(row.distance_meters)

    goals_result = await db.execute(select(Goal).where(Goal.user_id.in_(member_ids)))
    goal_by_user: dict[int, Goal] = {g.user_id: g for g in goals_result.scalars().all()}

    progress_list: list[MemberProgressResponse] = []
    for member in members:
        goal = goal_by_user.get(member.id)
        if goal is None:
            continue
        goal_km = float(goal.yearly_running_goal_km)
        distance_km = total_meters_by_user.get(member.id, 0.0) / 1000
        progress_pct = round(distance_km / goal_km * 100, 2)
        daily_series = self._build_daily_series(rows_by_user.get(member.id, []))
        progress_list.append(
            MemberProgressResponse(
                strava_athlete_id=member.strava_athlete_id,
                display_name=member.display_name,
                distance_to_date_km=distance_km,
                goal_km=goal_km,
                progress_pct=progress_pct,
                daily_series=daily_series,
            )
        )

    return ClubDashboardResponse(
        club_id=club.id,
        club_name=club.name,
        members=progress_list,
    )
```

Also remove the unused `func` import from sqlalchemy if it's no longer used elsewhere in the file — check first with a search.

- [ ] **Step 5: Run all dashboard tests**

```
uv run pytest tests/backend/dashboard/ -v
```

Expected: all tests pass, including the 2 new `daily_series` integration tests.

- [ ] **Step 6: Commit**

```
git add backend/dashboard/schemas.py backend/dashboard/dashboard_service.py tests/backend/dashboard/test_club_dashboard_service.py
git commit -m "feat(dashboard): add daily_series to club dashboard and rewrite with bulk activity query"
```

---

### Task 3: Update `client.ts` and create `ClubPaceChart.tsx`

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/components/ClubPaceChart.tsx`

- [ ] **Step 1: Add `daily_series` to `MemberProgress` in `client.ts`**

Replace the `MemberProgress` interface in `frontend/src/api/client.ts` with:

```ts
export interface MemberProgress {
  strava_athlete_id: number
  display_name: string
  distance_to_date_km: number
  goal_km: number
  progress_pct: number
  daily_series: DailyDistancePoint[]
}
```

(`DailyDistancePoint` is already exported from the same file.)

- [ ] **Step 2: Create `frontend/src/components/ClubPaceChart.tsx`**

```tsx
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { MemberProgress } from '../api/client'

interface Props {
  members: MemberProgress[]
  currentAthleteId: number
}

const MONTH_START_DAYS = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// Non-blue colors for other members (blue is reserved for current user via --accent)
const OTHER_COLORS = ['#3eb8a0', '#7c5cbf', '#d4884a', '#b85c7c', '#e05252']

function toDayOfYear(dateStr: string, year: number): number {
  const jan1 = new Date(year, 0, 1).getTime()
  const d = new Date(dateStr + 'T00:00:00').getTime()
  return Math.floor((d - jan1) / 86400000) + 1
}

function monthTickFormatter(day: number): string {
  const idx = MONTH_START_DAYS.indexOf(day)
  return idx >= 0 ? MONTH_LABELS[idx] : ''
}

interface PacePoint { day: number; pace: number }
interface MemberPoint { day: number; pct: number }

export default function ClubPaceChart({ members, currentAthleteId }: Props) {
  const year = new Date().getFullYear()
  const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0
  const daysInYear = isLeap ? 366 : 365

  const style = getComputedStyle(document.documentElement)
  const accent   = style.getPropertyValue('--accent').trim()    || '#4b8cf7'
  const border   = style.getPropertyValue('--border').trim()    || '#272c3d'
  const text3    = style.getPropertyValue('--text-3').trim()    || '#3d4358'
  const text1    = style.getPropertyValue('--text-1').trim()    || '#e8eaf0'
  const surface2 = style.getPropertyValue('--surface-2').trim() || '#1c2030'

  const paceData: PacePoint[] = [
    ...MONTH_START_DAYS.map(day => ({
      day,
      pace: Math.round((day / daysInYear) * 100 * 10) / 10,
    })),
    { day: daysInYear, pace: 100 },
  ]

  // Pre-compute per-member chart data and color assignments
  const memberDataMap = new Map<number, MemberPoint[]>()
  const colorMap = new Map<number, string>()
  let otherIdx = 0
  for (const member of members) {
    memberDataMap.set(
      member.strava_athlete_id,
      member.daily_series.map(p => ({
        day: toDayOfYear(p.date, year),
        pct: Math.round((p.cumulative_km / member.goal_km) * 100 * 10) / 10,
      })),
    )
    if (member.strava_athlete_id === currentAthleteId) {
      colorMap.set(member.strava_athlete_id, accent)
    } else {
      colorMap.set(member.strava_athlete_id, OTHER_COLORS[otherIdx % OTHER_COLORS.length])
      otherIdx++
    }
  }

  // Custom dot: renders a name label only at the last data point of each member's series
  function renderEndLabel(athleteId: number, displayName: string, color: string) {
    const data = memberDataMap.get(athleteId) ?? []
    const lastDay = data.length > 0 ? data[data.length - 1].day : null
    return (props: { cx: number; cy: number; payload: MemberPoint }) => {
      const { cx, cy, payload } = props
      if (lastDay === null || payload.day !== lastDay) {
        return <circle r={0} cx={cx} cy={cy} fill="transparent" />
      }
      return (
        <text
          x={cx + 6}
          y={cy + 4}
          fontSize={11}
          fontFamily="JetBrains Mono, monospace"
          fill={color}
        >
          {displayName}
        </text>
      )
    }
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart margin={{ top: 20, right: 90, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={border} vertical={false} />
        <XAxis
          dataKey="day"
          type="number"
          domain={[1, daysInYear]}
          ticks={MONTH_START_DAYS}
          tickFormatter={monthTickFormatter}
          tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', fill: text3 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => `${v}%`}
          domain={[0, 100]}
          tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', fill: text3 }}
          axisLine={false}
          tickLine={false}
          width={44}
        />
        <Tooltip
          contentStyle={{
            background: surface2,
            border: `1px solid ${border}`,
            borderRadius: 8,
            fontSize: 12,
            fontFamily: 'JetBrains Mono, monospace',
          }}
          labelFormatter={(label) => {
            const day = typeof label === 'number' ? label : 0
            const idx = MONTH_START_DAYS.findIndex(
              (d, i) => d <= day && (MONTH_START_DAYS[i + 1] ?? 366) > day,
            )
            return MONTH_LABELS[idx] ?? `Day ${day}`
          }}
          formatter={(value, name) => {
            const pct = typeof value === 'number' ? value : 0
            return [`${pct.toFixed(1)}%`, String(name)]
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, fontFamily: 'JetBrains Mono, monospace', color: text1 }}
        />
        <Line
          data={paceData}
          dataKey="pace"
          name="Goal pace"
          stroke={text3}
          strokeDasharray="4 4"
          strokeWidth={1.5}
          dot={false}
          connectNulls
          legendType="plainline"
        />
        {members.map((member) => {
          const color = colorMap.get(member.strava_athlete_id) ?? accent
          const isCurrent = member.strava_athlete_id === currentAthleteId
          const label = isCurrent
            ? `${member.display_name} (you)`
            : member.display_name
          const memberData = memberDataMap.get(member.strava_athlete_id) ?? []
          return (
            <Line
              key={member.strava_athlete_id}
              data={memberData}
              dataKey="pct"
              name={label}
              stroke={color}
              strokeWidth={isCurrent ? 3 : 2}
              dot={
                renderEndLabel(member.strava_athlete_id, member.display_name, color) as (
                  props: unknown,
                ) => JSX.Element
              }
              connectNulls
              legendType="plainline"
            />
          )
        })}
      </LineChart>
    </ResponsiveContainer>
  )
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```
cd frontend && npm run build
```

Expected: clean build with no type errors. Fix any TypeScript errors before continuing.

- [ ] **Step 4: Commit**

```
git add frontend/src/api/client.ts frontend/src/components/ClubPaceChart.tsx
git commit -m "feat(clubs): add ClubPaceChart component with per-member percentage lines"
```

---

### Task 4: Wire up `ClubsPage.tsx` and `HomePage.tsx`

**Files:**
- Modify: `frontend/src/pages/ClubsPage.tsx`
- Modify: `frontend/src/pages/HomePage.tsx`

- [ ] **Step 1: Update `ClubsPage.tsx` to accept `currentAthleteId` and render the chart**

Replace the top of `ClubsPage.tsx` (imports and component signature) with:

```tsx
import { useEffect, useState } from 'react'
import {
  getClubs,
  getClubDashboard,
  type Club,
  type ClubDashboard,
} from '../api/client'
import ClubPaceChart from '../components/ClubPaceChart'

interface Props {
  currentAthleteId: number
}

type ClubsStatus = 'loading' | 'error' | 'loaded'
type DashStatus = 'idle' | 'loading' | 'error' | 'loaded'

export default function ClubsPage({ currentAthleteId }: Props) {
```

Then replace the `{/* TASK-6.6: multi-line progress chart will be added here */}` comment with the chart render, placing it **above** the member list. The members card body section should look like:

```tsx
<div className="card__body">
  {dashStatus === 'loading' && (
    <p className="dash-loading">Loading…</p>
  )}
  {dashStatus === 'error' && (
    <>
      <p className="status-msg status-msg--danger" role="alert">
        Failed to load club data — please try again.
      </p>
      <button
        className="btn btn--ghost"
        onClick={() => void fetchDashboard(selectedClubId)}
        style={{ marginTop: 12 }}
      >
        Retry
      </button>
    </>
  )}
  {dashStatus === 'loaded' &&
    clubDashboard !== null &&
    clubDashboard.members.length === 0 && (
      <p className="dash-empty">
        No other members of this club have connected the app yet.
      </p>
    )}
  {dashStatus === 'loaded' &&
    clubDashboard !== null &&
    clubDashboard.members.length > 0 && (
      <>
        <ClubPaceChart
          members={clubDashboard.members}
          currentAthleteId={currentAthleteId}
        />
        <div className="member-list" style={{ marginTop: 24 }}>
          {clubDashboard.members.map((member) => (
            <div key={member.strava_athlete_id} className="member-row">
              <span className="member-row__name">
                {member.display_name}
              </span>
              <div className="member-row__bar-track">
                <div
                  className="member-row__bar-fill"
                  style={{
                    width: `${Math.min(member.progress_pct, 100)}%`,
                  }}
                />
              </div>
              <span className="member-row__stats">
                {member.progress_pct.toFixed(1)}%
                {' · '}
                {member.distance_to_date_km.toFixed(1)}
                {' / '}
                {member.goal_km.toFixed(0)} km
              </span>
            </div>
          ))}
        </div>
      </>
    )}
</div>
```

- [ ] **Step 2: Update `HomePage.tsx` to pass `currentAthleteId` to `ClubsPage`**

In `frontend/src/pages/HomePage.tsx`, find the line:

```tsx
{page === 'clubs' && <ClubsPage />}
```

Replace with:

```tsx
{page === 'clubs' && <ClubsPage currentAthleteId={user.strava_athlete_id} />}
```

- [ ] **Step 3: Verify TypeScript compiles**

```
cd frontend && npm run build
```

Expected: clean build.

- [ ] **Step 4: Run the full backend test suite**

```
uv run pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```
git add frontend/src/pages/ClubsPage.tsx frontend/src/pages/HomePage.tsx
git commit -m "feat(clubs): render ClubPaceChart in club view above member list"
```
