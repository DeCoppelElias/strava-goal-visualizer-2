# Dashboard UI Refresh — Design Spec

**Date:** 2026-06-07
**Scope:** Frontend only (`DashboardPage.tsx`, `PaceChart.tsx`, `index.css`)
**Backend changes:** None

---

## Overview

Five targeted improvements to the personal dashboard to reduce noise, consolidate information, and make the chart more immediately readable.

---

## 1. Sync Control — Move to Page Header

**Current:** A full-width card ("Sync Activities") is the first row on the dashboard.

**Change:** Remove the sync card entirely. The `.page-header` becomes a flex row:
- Left: page title + subtitle (unchanged)
- Right: a compact ghost `Sync` button (existing `.btn.btn--ghost` style)

Sync feedback moves inline, beneath the button, as small monospace text:
- Success: `{n} runs synced · Last synced {time}` in `--text-3`
- Cooldown: warning-coloured text `Try again in {n} min`
- Error: danger-coloured text `Sync failed — please try again`

The button shows a spinner + "Syncing…" while in-flight, same as today.

---

## 2. Stats — Consolidated Card

**Current:** Three separate `stat-tile` cards in a grid row (Total km, % Complete, Pace badge).

**Change:** Replace with a single card containing a 4-row 2-column table. No cell borders — rows separated by padding only.

| Label | Value | Notes |
|---|---|---|
| Total distance | `342.1 km` | `distance_to_date_km.toFixed(1) + " km"` |
| Progress | `68.4%` | `progress_pct.toFixed(1) + "%"` |
| Needed weekly pace | `14.2 km/week` | See computation below |
| vs. Ideal | `+12.3 km` or `−8.4 km` | Green if positive, red if negative |

**Styling:** Labels use Manrope, `--text-2`. Values use JetBrains Mono, `--text-1`. The `vs. Ideal` value uses `--success` when positive, `--danger` when negative.

**Needed weekly pace computation (frontend):**
```ts
const today = new Date()
const year = today.getFullYear()
const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0
const daysInYear = isLeap ? 366 : 365
const dayOfYear = Math.floor((today.getTime() - new Date(year, 0, 1).getTime()) / 86400000) + 1
const remainingDays = daysInYear - dayOfYear
const remainingWeeks = remainingDays / 7
const remainingKm = data.goal_km - data.distance_to_date_km
const neededWeeklyPace = remainingKm <= 0 ? null : remainingKm / remainingWeeks
```
- If `neededWeeklyPace === null` (goal reached): display `"Goal achieved"` in `--success` colour
- Otherwise: display `neededWeeklyPace.toFixed(1) + " km/week"`

**vs. Ideal computation (frontend):**
```ts
const idealToDate = (dayOfYear / daysInYear) * data.goal_km
const vsIdeal = data.distance_to_date_km - idealToDate
// display: (vsIdeal >= 0 ? "+" : "") + vsIdeal.toFixed(1) + " km"
```

The old `on_pace` badge is removed — `vs. Ideal` carries the same information with more precision.

---

## 3. PaceChart — Dual Highlight Dots at Today

**Current:** `dot={false}` on both the `Area` (actual) and `Line` (pace) — no visible points.

**Change:** At today's day-of-year position, render two visible dots:

1. **Actual dot** — on the actual line, filled circle, colour `--accent`, radius 4px
2. **Ideal dot** — on the pace line, filled circle, colour `--text-3`, radius 3px

Plus a small km label above the actual dot (e.g. `342.1 km`), JetBrains Mono 11px, `--text-1`.

**Implementation approach:**
- Compute `todayDayOfYear` inside `buildChartData` (or inline in the component) using `new Date()`
- Use a custom `dot` render function on the `Area` for actual: render a visible `<circle>` only when `entry.day === todayDayOfYear`; invisible for all other points
- Use a custom `dot` render function on the `Line` for pace: same condition, but with `--text-3` fill and smaller radius
- The km label is rendered as a Recharts `<Label>` on the actual dot, positioned `"top"`

**Edge case:** If today has no actual data point (the user hasn't run yet today and today is not in `daily_series`), the actual dot is omitted. The ideal dot still renders at today's pace value, computed as `(todayDayOfYear / daysInYear) * goalKm`.

To guarantee today's position always has a chart point, `buildChartData` should ensure a point exists for `todayDayOfYear` with `pace` set and `actual` either from the series or `undefined`.

---

## 4. PaceChart — Area Fill Removed

**Current:** The `Area` for actual data has `fill={accentDim}` — a translucent blue fill under the line.

**Change:** Set `fill="transparent"` on the `Area`. The actual line remains blue (`--accent`), stroke width unchanged. The dashed ideal pace `Line` remains in `--text-3`. No area fill anywhere on the chart.

---

## 5. PaceChart — Reusability

`PaceChart` stays a pure visual component. All new logic (dots, label) is derived solely from its existing props (`dailySeries`, `goalKm`). No dashboard-specific state is passed in.

Add a `showHighlight?: boolean` prop defaulting to `true`. When `false`, the dual dots and km label are suppressed. This allows the club view to opt out cleanly.

---

## CSS Changes

- `.stats-row` and `.stat-tile` are removed (no longer used)
- `.pace-badge`, `.pace-badge--on`, `.pace-badge--behind` are removed
- New classes added for the stats table layout: `.stats-table`, `.stats-table__row`, `.stats-table__label`, `.stats-table__value`
- `.page-header` gets `display: flex; align-items: flex-start; justify-content: space-between`
- New `.sync-inline` wrapper for the right-side sync control group

---

## Out of Scope

- Backend changes — none required
- Red/green fill between the two chart lines — dropped
- Line colour change based on pace status — dropped
- Club view chart — future work; reuse via `showHighlight` prop
