# Design: Reorder Personal Dashboard + Inline Badges

**Date:** 2026-06-17
**Status:** Approved
**Type:** Frontend-only change (no backend, API, or data changes)

## Problem

The personal dashboard currently presents the achievement badges as their own
standalone card, and the cards are ordered Stats → Badges → Chart → Goal edit.
The user wants the badges promoted into the page header (between the title and
the sync control) and the content reordered so the chart leads.

## Goals

1. Move the achievement badges out of their standalone card and into the page
   header, positioned **between** the title block and the sync control.
2. Reorder the loaded-state cards so the pace chart comes first and the stats
   sit below it.

## Non-Goals

- No changes to badge thresholds, tiers, colors, or earned/unearned logic.
- No backend, API, schema, or data-shape changes.
- No changes to `BadgeIcon` SVG geometry (only the rendered size changes).

## Design

### 1. Badges move into the page header

`BadgeRow` is refactored from a full card into a compact inline group:

- Remove the `.card` / `.card__header` / `.card__body` wrapper.
- Remove the per-badge name and threshold text labels.
- Render only the four `BadgeIcon` shields in a horizontal group.
- Each `BadgeIcon` renders at **40×48px** — 50% of the original 80×96 default
  (40/80 = 48/96 = 50%; visual area ≈ 25% of the original).
- Earned tiers keep their tier color; unearned tiers stay `#3d4358` (`UNEARNED`).
- Accessibility: each badge carries a `title` and `aria-label` of the form
  `"<name> — <label> (earned)"` or `"<name> — <label> (locked)"`, e.g.
  `"Century — 100 km (earned)"`. This preserves the meaning that the visible
  name/threshold labels used to provide.

In `DashboardPage.tsx`, `<BadgeRow>` becomes the **third child** of
`.page-header`, placed between the title `<div>` and the `.sync-inline` `<div>`:

```
[ Dashboard            ]   [ 🛡 🛡 🛡 🛡 ]   [ Sync ]
[ 2026 · Running Goal  ]
```

Because `.page-header` uses `display: flex; justify-content: space-between`,
adding a third child distributes the three blocks across the header
automatically. The badge group is vertically aligned to sit alongside the title
(align to center / top of the header as appropriate).

The badges are only meaningful once dashboard data is loaded (they depend on
`distance_to_date_km`). The badge group renders in the header **only in the
`loaded` state**, so it does not appear during loading / not-synced / error
states.

### 2. Card reordering (loaded state)

Old order:

1. Stats card
2. Badges card
3. Pace chart card
4. Yearly Goal edit card

New order:

1. **Pace chart card** (unchanged internals — the progress-bar `member-row`
   stays inside this card as it is today)
2. **Stats card**
3. **Yearly Goal edit card**

The Badges card is removed entirely (its content now lives in the header).

### 3. CSS

In `index.css`:

- Add a `.header-badges` flex container for the inline badge group
  (`display: flex; gap: …; align-items: center`).
- The old `.badge-row`, `.badge-item__name`, `.badge-item__name--unearned`, and
  `.badge-item__threshold` rules become unused; remove them (keep only what the
  compact inline group needs).
- Header layout (`.page-header`, `.sync-inline`, `.page-title`,
  `.page-subtitle`) is unchanged except for accommodating the new middle child.

## Files Changed

- `frontend/src/pages/DashboardPage.tsx` — move `<BadgeRow>` into the header
  (loaded state only); reorder the three remaining cards to Chart → Stats →
  Goal edit.
- `frontend/src/components/BadgeRow.tsx` — drop the card wrapper and text
  labels; render compact 40×48 icons with `title`/`aria-label`.
- `frontend/src/index.css` — add `.header-badges`; remove the now-unused
  `.badge-row` / `.badge-item__name*` / `.badge-item__threshold` rules.

## Testing / Verification

- `npm run build` (frontend) succeeds with no type errors.
- Manual check in the running app:
  - Loaded dashboard shows four small badges in the header between the title and
    the Sync button.
  - Earned badges show their tier color; unearned are muted; hovering a badge
    shows its name + km via the title attribute.
  - Cards appear in order: Pace chart, Stats, Yearly Goal edit.
  - Loading / not-synced / error states show no badges in the header.

## Edge Cases

- **Zero distance:** all four badges render as unearned (muted color).
- **All earned (≥1000 km):** all four show tier colors.
- **Narrow viewport:** three header children may crowd; acceptable for this
  change. If wrapping is needed it can be handled as a follow-up, but the header
  is not expected to wrap at supported widths.
