# TASK-6.6 — Club Pace Chart Design

_Date: 2026-06-13_

---

## Summary

Add a multi-line progress chart to the club view showing each member's cumulative running distance as a **percentage of their individual goal** over the current year, with a shared linear pace reference line. The chart complements the existing progress bar list by revealing how members' progress evolved over time.

---

## Key Decisions

| Question | Decision | Rationale |
|---|---|---|
| Y-axis unit | % of goal | Normalises different goals; single shared pace line works; raw km already shown in progress bars below |
| Color palette | Hue-rotated from accent | Needs per-member identity; opacity stepping breaks down beyond 3 members; style accent rule was written for UI chrome, not multi-series data viz |
| Pace reference line | Single shared diagonal (0→100% over the year) | Works for all members simultaneously on the % scale |
| Member identification | Current user: `--accent` blue, thicker line, "(you)" in legend, end-of-line label. Others: hue-rotated colors, end-of-line labels | Legend alone requires color matching; combining thicker line + inline labels makes identification immediate |

---

## Backend

### `backend/dashboard/dashboard_service.py`

**Extract `_build_daily_series` helper:**

```python
def _build_daily_series(
    rows: list[tuple[str, float]]  # (date_str YYYY-MM-DD, meters)
) -> list[DailyDistancePoint]:
```

Moves the existing cumulative-sum logic out of `get_personal_dashboard`. Takes `(date_str, meters)` tuples sorted chronologically, returns `list[DailyDistancePoint]`.

`get_personal_dashboard` calls the helper instead of doing it inline — no behaviour change.

**Rewrite `get_club_dashboard` query:**

Replace the `GROUP BY user_id` aggregate with a raw-rows query:

```sql
SELECT user_id, start_date, distance_meters
WHERE user_id IN (...) AND start_date >= year_start
ORDER BY start_date ASC
```

In Python:
- Group rows by `user_id` using `defaultdict(list)`
- For each member: call `_build_daily_series` to build their series; sum meters to get `distance_to_date_km`
- One DB round trip for all members

### `backend/dashboard/schemas.py`

Add `daily_series: list[DailyDistancePoint]` to `MemberProgressResponse`.

### `frontend/src/api/client.ts`

Add `daily_series: DailyDistancePoint[]` to `MemberProgress` interface.

---

## Frontend

### New: `frontend/src/components/ClubPaceChart.tsx`

**Props:**
```ts
interface Props {
  members: MemberProgress[]
  currentAthleteId: number
}
```

**Color palette** (fixed array of 5 calm hue-rotated colors, cycles for clubs > 5):
```ts
const MEMBER_COLORS = [
  '#4b8cf7', // blue  — reserved for current user via currentAthleteId
  '#3eb8a0', // teal
  '#7c5cbf', // purple
  '#d4884a', // amber
  '#b85c7c', // rose
]
```

The current user always gets `--accent` (read via `getComputedStyle` like `PaceChart` does). Other members are assigned palette colors by index (skipping index 0 so blue is free). Beyond 5 other members, colors repeat — acceptable for typical club sizes.

**Data transform per member:**
```ts
point.cumulative_km / member.goal_km * 100  // → percentage
```

**Pace reference line dataset:** Points at each `MONTH_START_DAYS` boundary (same array as `PaceChart`) plus day 365/366:
```ts
{ day, pace: Math.round((day / daysInYear) * 100 * 10) / 10 }
```

**Chart structure (Recharts `LineChart`):**
- `<XAxis>` — day-of-year, month label formatter (same as `PaceChart`)
- `<YAxis>` — `{v}%` formatter, domain `[0, 100]` (fixed)
- `<CartesianGrid>` — horizontal only, `--border` stroke
- One dashed `<Line dataKey="pace">` in `--text-3`, `strokeWidth: 1.5` — shared pace reference
- Per member: `<Line>` with their color; current user gets `--accent` + `strokeWidth: 3`, others get `strokeWidth: 2`; `connectNulls`
- `<Legend>` with display names; current user's entry appends `" (you)"`
- End-of-line name labels: custom `dot` renders a `<text>` element at the last data point of each member's series (display name, 11px JetBrains Mono, member color). Overlap accepted for small clubs; legend is the fallback.
- `<Tooltip>` — `surface-2` bg, `--border`, rounded-8, JetBrains Mono 12px; shows all members' percentages at hovered day

**Height:** 260px (slightly taller than `PaceChart`'s 240px to accommodate the legend).

### `frontend/src/pages/ClubsPage.tsx`

- Accept `currentAthleteId: number` prop (passed from `App.tsx` which already holds `SessionUser.strava_athlete_id`)
- Render `<ClubPaceChart members={clubDashboard.members} currentAthleteId={currentAthleteId} />` inside the Members card, above the member list, when `clubDashboard.members.length > 0`
- Replace the existing `{/* TASK-6.6: ... */}` comment with the chart

---

## Testing

### Backend integration test

In `tests/backend/dashboard/test_dashboard_service.py`:

- Seed two users both in the same club, each with known activity histories (e.g. user A: 10 km on day 5; user B: 20 km on day 10)
- Call `get_club_dashboard` and assert:
  - Each member's `daily_series` contains correct cumulative km values at the correct dates (percentage conversion is client-side)
  - `distance_to_date_km` is accurate (now derived from the same raw-rows pass, not a separate aggregate)
  - A member with no activities returns `daily_series: []`

### Frontend

- Chart renders with one line per member when data loads
- Switching clubs re-renders with new data (existing `useEffect` on `selectedClubId` handles this)
- Current user's line is visibly thicker and blue with "(you)" in legend
- Tooltip shows all members' percentages at hovered day
- Empty-state: when `members.length === 0`, chart is not rendered (existing empty-state message shows instead)

---

## Out of Scope

- Animating lines drawing in
- Zoom/pan on the chart
- Hiding/showing individual member lines
- Handling clubs with > 5 members specially (color repeat is accepted)
