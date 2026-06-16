# Achievement Badges — Design Spec

_Date: 2026-06-16_

---

## Overview

Display four milestone badges on the personal dashboard when the user's year-to-date running distance crosses fixed thresholds. Badge state is derived entirely from `distance_to_date_km` — no new sync logic or persistent award table required. Badges are athlete-only (not shown in club views).

---

## Thresholds

| Tier | Threshold | Working name |
|---|---|---|
| Bronze | 10 km | First Steps |
| Silver | 100 km | Century |
| Gold | 365 km | One a Day |
| Platinum | 1,000 km | Thousand |

A badge is earned when `distance_to_date_km >= threshold`. It reverts to unearned if the total drops below (e.g. after a deleted-activity sync). No historical state is stored.

---

## Visual Design

### Shape

Each badge is a heraldic shield: pointed bottom, straight sides, slightly curved top corners. Drawn as a stroke-only outline, no fill.

### Icon

A running shoe sits inside the shield. Stroke-only, no fill. The shoe gains detail as the tier rises:

| Tier | Shoe detail |
|---|---|
| Bronze | Bare outline — sole curve, upper, toe box only |
| Silver | + laces (3–4 horizontal strokes across the upper) |
| Gold | + sole tread lines (short horizontals at heel/toe) |
| Platinum | + side panel line separating midsole from upper |

### Colors

Each badge uses **one color** for both the shield border and the shoe stroke.

| Tier | Stroke color |
|---|---|
| Bronze | `#9c6b3c` |
| Silver | `#8b91a8` |
| Gold | `#b8922a` |
| Platinum | `#9ab0c8` |

### States

| State | Treatment |
|---|---|
| Earned | Full tier color at full opacity |
| Unearned | Stroke overridden to `#3d4358` (`--text-3`) — subtle, visible but clearly locked |

### Rendering Approach

Badge SVGs are defined as **inline JSX** inside a single `BadgeIcon.tsx` component that accepts a `color` prop. This is required so that the earned/unearned stroke color can be set at render time without needing external SVG files loaded via `<img>` (which cannot be styled via CSS after load).

The shape data (shield path + shoe paths) for each tier is defined as a constant in `BadgeIcon.tsx`. The component signature:

```tsx
interface BadgeIconProps {
  tier: 'bronze' | 'silver' | 'gold' | 'platinum'
  color: string  // hex — either tier color or #3d4358 for unearned
}
```

Size: `80×96px` viewBox, scales freely via `width`/`height` props.

---

## Dashboard Integration

Badges appear on the personal dashboard only (not in club views). They render below the Stats card and above the Pace chart card.

### Layout

A horizontal row of 4 badges, evenly spaced, inside a `Badges` card following the existing card pattern (`card__header` + `card__label` + `card__body`).

Each badge renders as:
- The SVG icon (earned color or `--text-3` unearned)
- Tier name below in `12px Manrope 400` (`--text-2` earned, `--text-3` unearned)
- Threshold label below that in `11px JetBrains Mono` (`--text-3`)

### Component

`frontend/src/components/BadgeRow.tsx` — accepts `distanceKm: number`, computes earned state internally, renders the 4 badges.

### No backend changes

Badge state is derived from `distance_to_date_km` which is already returned by `GET /dashboard/personal`. No new endpoints, no new DB columns.

---

## Acceptance Criteria

- All 4 badge tiers render correctly at both 80×96 and 2× scale.
- A badge is shown in full tier color when `distance_to_date_km >= threshold`.
- A badge is shown in `--text-3` (`#3d4358`) when `distance_to_date_km < threshold`.
- The badge row appears on the personal dashboard and nowhere else (not in club views).
- No backend changes are required.
- Both dark and light themes render cleanly (SVG strokes use explicit hex values, not CSS variables, so they remain consistent).
