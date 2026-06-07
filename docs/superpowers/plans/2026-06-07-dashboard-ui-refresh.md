# Dashboard UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move sync inline to the page header, consolidate stats into a single card with weekly-pace and vs-ideal metrics, and add dual highlight dots on the chart at today's position.

**Architecture:** Frontend-only — three files touched in order: `index.css` first (CSS foundation), then `DashboardPage.tsx` (restructured header + new stats card), then `PaceChart.tsx` (highlight dots, fill removed, `showHighlight` prop). No backend changes required; all new metrics are derived from data the API already returns.

**Tech Stack:** React 18, TypeScript, Recharts, Vite, CSS custom properties

---

## Files

| Action | File |
|---|---|
| Modify | `frontend/src/index.css` |
| Modify | `frontend/src/pages/DashboardPage.tsx` |
| Modify | `frontend/src/components/PaceChart.tsx` |

---

### Task 1: CSS — add stats-table + sync-inline, remove old classes

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Remove the stats-row / stat-tile / pace-badge block**

Delete the entire `/* ── Stats Row ── */` section (currently lines 302–357). It contains:
`.stats-row`, `.stat-tile`, `.stat-tile__value`, `.stat-tile__label`, `.pace-badge`, `.pace-badge--on`, `.pace-badge--behind`

- [ ] **Step 2: Remove the sync-result / sync-count / sync-timestamp block**

Delete the three rules `.sync-result`, `.sync-count`, `.sync-timestamp` (currently lines 398–415).

- [ ] **Step 3: Update `.page-header` to a flex row**

Replace:
```css
.page-header {
  margin-bottom: 32px;
}
```
with:
```css
.page-header {
  margin-bottom: 32px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
```

- [ ] **Step 4: Add `.sync-inline` and sync feedback classes**

Directly after the updated `.page-header` block, add:
```css
.sync-inline {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
  padding-top: 2px;
}

.sync-feedback {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text-3);
  letter-spacing: 0.02em;
}

.sync-feedback--warning {
  color: var(--warning);
}

.sync-feedback--danger {
  color: var(--danger);
}
```

- [ ] **Step 5: Add stats-table classes**

After the `/* ── Dashboard Page ── */` section, add:
```css
/* ── Stats Table ────────────────────────────────────────── */

.stats-table {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.stats-table__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  transition: border-color 180ms ease;
}

.stats-table__row:last-child {
  border-bottom: none;
}

.stats-table__label {
  font-size: 13px;
  color: var(--text-2);
}

.stats-table__value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-1);
}

.stats-table__value--success {
  color: var(--success);
}

.stats-table__value--danger {
  color: var(--danger);
}
```

- [ ] **Step 6: Verify build passes**

Run from `frontend/`:
```
npm run build
```
Expected: exits 0, no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/index.css
git commit -m "style(dashboard): add stats-table and sync-inline css, remove stat-tile"
```

---

### Task 2: DashboardPage — move sync to page header

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Restructure the page header**

Replace the current `.page-header` div (lines 103–106):
```tsx
<div className="page-header">
  <h1 className="page-title">Dashboard</h1>
  <p className="page-subtitle">{new Date().getFullYear()} · Running Goal</p>
</div>
```
with:
```tsx
<div className="page-header">
  <div>
    <h1 className="page-title">Dashboard</h1>
    <p className="page-subtitle">{new Date().getFullYear()} · Running Goal</p>
  </div>
  <div className="sync-inline">
    <button
      className="btn btn--ghost"
      onClick={() => void handleSync()}
      disabled={syncing}
    >
      {syncing ? (
        <>
          <span className="btn__spinner" aria-hidden="true" />
          Syncing…
        </>
      ) : (
        'Sync'
      )}
    </button>
    {syncCount !== null && lastSyncAt !== null && (
      <span className="sync-feedback">
        {syncCount} {syncCount === 1 ? 'run' : 'runs'} synced · Last synced {formatSyncTime(lastSyncAt)}
      </span>
    )}
    {syncError?.type === 'cooldown' && (
      <span className="sync-feedback sync-feedback--warning" role="alert">
        Try again in {Math.ceil(syncError.retryAfterSeconds / 60)} min
      </span>
    )}
    {syncError?.type === 'api' && (
      <span className="sync-feedback sync-feedback--danger" role="alert">
        Sync failed — please try again
      </span>
    )}
  </div>
</div>
```

- [ ] **Step 2: Delete the sync card block**

Remove the entire `{/* Sync card */}` comment and the `<div className="card">` block that follows it (currently lines 108–151). This is the block that renders the "Sync Activities" card with the full-width button, sync result, and error messages.

- [ ] **Step 3: Verify build passes**

Run from `frontend/`:
```
npm run build
```
Expected: exits 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat(dashboard): move sync button to page header"
```

---

### Task 3: DashboardPage — consolidated stats card

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Add `computeDashStats` helper**

After the `formatSyncTime` function (around line 16), add this module-level helper. It takes the loaded dashboard data and returns two derived values:

```tsx
function computeDashStats(data: PersonalDashboard) {
  const today = new Date()
  const year = today.getFullYear()
  const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0
  const daysInYear = isLeap ? 366 : 365
  const dayOfYear =
    Math.floor((today.getTime() - new Date(year, 0, 1).getTime()) / 86400000) + 1
  const remainingKm = data.goal_km - data.distance_to_date_km
  const remainingWeeks = (daysInYear - dayOfYear) / 7
  const neededWeeklyPace = remainingKm <= 0 ? null : remainingKm / remainingWeeks
  const idealToDate = (dayOfYear / daysInYear) * data.goal_km
  const vsIdeal = data.distance_to_date_km - idealToDate
  return { neededWeeklyPace, vsIdeal }
}
```

`neededWeeklyPace` is `null` when the goal is already reached. `vsIdeal` is positive when ahead, negative when behind.

- [ ] **Step 2: Derive `dashStats` in the component body**

Inside `DashboardPage`, directly before the `return` statement, add:

```tsx
const dashStats = dashState.status === 'loaded' ? computeDashStats(dashState.data) : null
```

- [ ] **Step 3: Replace the stats-row JSX with the stats card**

Inside the `{dashState.status === 'loaded' && (...)}` fragment, replace the entire `{/* Stats row */}` block (the `<div className="stats-row">...</div>`) with:

```tsx
{/* Stats card */}
{dashStats && (
  <div className="card">
    <div className="card__header">
      <span className="card__label">Stats</span>
    </div>
    <div className="card__body">
      <div className="stats-table">
        <div className="stats-table__row">
          <span className="stats-table__label">Total distance</span>
          <span className="stats-table__value">
            {dashState.data.distance_to_date_km.toFixed(1)} km
          </span>
        </div>
        <div className="stats-table__row">
          <span className="stats-table__label">Progress</span>
          <span className="stats-table__value">
            {dashState.data.progress_pct.toFixed(1)}%
          </span>
        </div>
        <div className="stats-table__row">
          <span className="stats-table__label">Needed weekly pace</span>
          <span
            className={`stats-table__value${
              dashStats.neededWeeklyPace === null ? ' stats-table__value--success' : ''
            }`}
          >
            {dashStats.neededWeeklyPace === null
              ? 'Goal achieved'
              : `${dashStats.neededWeeklyPace.toFixed(1)} km/week`}
          </span>
        </div>
        <div className="stats-table__row">
          <span className="stats-table__label">vs. Ideal</span>
          <span
            className={`stats-table__value ${
              dashStats.vsIdeal >= 0
                ? 'stats-table__value--success'
                : 'stats-table__value--danger'
            }`}
          >
            {dashStats.vsIdeal >= 0 ? '+' : ''}
            {dashStats.vsIdeal.toFixed(1)} km
          </span>
        </div>
      </div>
    </div>
  </div>
)}
```

- [ ] **Step 4: Verify build passes**

Run from `frontend/`:
```
npm run build
```
Expected: exits 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat(dashboard): consolidate stats into single card with weekly pace and vs-ideal"
```

---

### Task 4: PaceChart — remove area fill and add `showHighlight` prop

**Files:**
- Modify: `frontend/src/components/PaceChart.tsx`

- [ ] **Step 1: Update the `Props` interface**

Replace:
```tsx
interface Props {
  dailySeries: DailyDistancePoint[]
  goalKm: number
}
```
with:
```tsx
interface Props {
  dailySeries: DailyDistancePoint[]
  goalKm: number
  showHighlight?: boolean
}
```

- [ ] **Step 2: Accept `showHighlight` in the component signature**

Replace:
```tsx
export default function PaceChart({ dailySeries, goalKm }: Props) {
```
with:
```tsx
export default function PaceChart({ dailySeries, goalKm, showHighlight = true }: Props) {
```

- [ ] **Step 3: Remove `accentDim` from CSS var reads and add `text1`**

Replace the CSS var block:
```tsx
const accent    = style.getPropertyValue('--accent').trim()     || '#4b8cf7'
const accentDim = style.getPropertyValue('--accent-dim').trim() || 'rgba(75,140,247,0.10)'
const border    = style.getPropertyValue('--border').trim()     || '#272c3d'
const text3     = style.getPropertyValue('--text-3').trim()     || '#3d4358'
const surface2  = style.getPropertyValue('--surface-2').trim()  || '#1c2030'
```
with:
```tsx
const accent   = style.getPropertyValue('--accent').trim()    || '#4b8cf7'
const border   = style.getPropertyValue('--border').trim()    || '#272c3d'
const text1    = style.getPropertyValue('--text-1').trim()    || '#e8eaf0'
const text3    = style.getPropertyValue('--text-3').trim()    || '#3d4358'
const surface2 = style.getPropertyValue('--surface-2').trim() || '#1c2030'
```

- [ ] **Step 4: Set fill to transparent on the Area**

Replace:
```tsx
<Area
  dataKey="actual"
  stroke={accent}
  fill={accentDim}
  strokeWidth={2}
  dot={false}
  connectNulls
/>
```
with:
```tsx
<Area
  dataKey="actual"
  stroke={accent}
  fill="transparent"
  strokeWidth={2}
  dot={false}
  connectNulls
/>
```

- [ ] **Step 5: Bump the top chart margin to give room for the future km label**

Change `margin={{ top: 8, right: 8, bottom: 0, left: 0 }}` to `margin={{ top: 20, right: 8, bottom: 0, left: 0 }}`.

- [ ] **Step 6: Verify build passes**

Run from `frontend/`:
```
npm run build
```
Expected: exits 0.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/PaceChart.tsx
git commit -m "feat(chart): remove area fill, add showHighlight prop"
```

---

### Task 5: PaceChart — dual highlight dots at today's position

**Files:**
- Modify: `frontend/src/components/PaceChart.tsx`

- [ ] **Step 1: Update `buildChartData` return type and expose `todayDayOfYear`**

Replace the current `buildChartData` function entirely with:

```tsx
function buildChartData(
  dailySeries: DailyDistancePoint[],
  goalKm: number,
): { data: ChartPoint[]; daysInYear: number; todayDayOfYear: number } {
  const year = new Date().getFullYear()
  const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0
  const daysInYear = isLeap ? 366 : 365

  const today = new Date()
  const todayDayOfYear =
    Math.floor((today.getTime() - new Date(year, 0, 1).getTime()) / 86400000) + 1

  const paceAt = (day: number) => Math.round((day / daysInYear) * goalKm * 10) / 10

  const byDay = new Map<number, ChartPoint>()

  for (const day of [...MONTH_START_DAYS, daysInYear]) {
    byDay.set(day, { day, pace: paceAt(day) })
  }

  // Guarantee today always has a chart point so the highlight dot can render
  if (!byDay.has(todayDayOfYear)) {
    byDay.set(todayDayOfYear, { day: todayDayOfYear, pace: paceAt(todayDayOfYear) })
  }

  for (const p of dailySeries) {
    const day = toDayOfYear(p.date, year)
    const existing = byDay.get(day)
    byDay.set(day, {
      day,
      actual: p.cumulative_km,
      pace: existing?.pace ?? paceAt(day),
    })
  }

  return {
    data: [...byDay.values()].sort((a, b) => a.day - b.day),
    daysInYear,
    todayDayOfYear,
  }
}
```

- [ ] **Step 2: Destructure `todayDayOfYear` from `buildChartData`**

Replace:
```tsx
const { data, daysInYear } = buildChartData(dailySeries, goalKm)
```
with:
```tsx
const { data, daysInYear, todayDayOfYear } = buildChartData(dailySeries, goalKm)
```

- [ ] **Step 3: Add custom dot render functions**

After the CSS var reads and before the `return`, add both render functions. These are defined inside the component so they close over `showHighlight`, `todayDayOfYear`, `accent`, `text1`, and `text3`:

```tsx
const renderActualDot = (props: { cx: number; cy: number; payload: ChartPoint }) => {
  const { cx, cy, payload } = props
  if (!showHighlight || payload.day !== todayDayOfYear || payload.actual === undefined) {
    return <circle r={0} cx={cx} cy={cy} fill="transparent" />
  }
  return (
    <g>
      <circle cx={cx} cy={cy} r={4} fill={accent} />
      <text
        x={cx}
        y={cy - 10}
        textAnchor="middle"
        fontSize={11}
        fontFamily="JetBrains Mono, monospace"
        fill={text1}
      >
        {payload.actual.toFixed(1)} km
      </text>
    </g>
  )
}

const renderPaceDot = (props: { cx: number; cy: number; payload: ChartPoint }) => {
  const { cx, cy, payload } = props
  if (!showHighlight || payload.day !== todayDayOfYear) {
    return <circle r={0} cx={cx} cy={cy} fill="transparent" />
  }
  return <circle cx={cx} cy={cy} r={3} fill={text3} />
}
```

- [ ] **Step 4: Wire the dot renders into the chart elements**

On the `Line` for pace, replace `dot={false}` with `dot={renderPaceDot as (props: unknown) => React.ReactElement}`.

On the `Area` for actual, replace `dot={false}` with `dot={renderActualDot as (props: unknown) => React.ReactElement}`.

Add `import type { ReactElement } from 'react'` at the top of the file if the cast triggers a TypeScript error; otherwise `React.ReactElement` can be replaced with just `JSX.Element` which requires no import.

The final `Line` and `Area` elements:
```tsx
<Line
  dataKey="pace"
  stroke={text3}
  strokeDasharray="4 4"
  strokeWidth={1.5}
  dot={renderPaceDot as (props: unknown) => JSX.Element}
  connectNulls
/>
<Area
  dataKey="actual"
  stroke={accent}
  fill="transparent"
  strokeWidth={2}
  dot={renderActualDot as (props: unknown) => JSX.Element}
  connectNulls
/>
```

- [ ] **Step 5: Verify build passes**

Run from `frontend/`:
```
npm run build
```
Expected: exits 0, no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/PaceChart.tsx
git commit -m "feat(chart): add dual highlight dots at today's position with km label"
```

---

### Task 6: Visual verification

**Files:** none

- [ ] **Step 1: Start the dev server**

Ensure Postgres + backend are running, then from `frontend/`:
```
npm run dev
```

- [ ] **Step 2: Log in and navigate to Dashboard**

Check each of the five visual changes:

1. **Header:** "Dashboard" title on the left, compact "Sync" ghost button top-right. Clicking it syncs and shows inline feedback beneath the button.
2. **Stats card:** Single card with four rows — Total distance, Progress, Needed weekly pace, vs. Ideal. "vs. Ideal" is green when ahead, red when behind. If goal is reached, "Needed weekly pace" shows "Goal achieved".
3. **Chart:** No blue fill under the actual line — just the line itself.
4. **Chart:** Blue dot on the actual line at today's position, with a km label above it. Grey dot on the dashed pace line at the same x position.
5. **Goal edit card:** Unchanged.

- [ ] **Step 3: Verify edge case — no runs today**

If today has no run, the actual dot should be absent; the grey ideal dot should still appear on the dashed line.
