# Achievement Badges — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 4 milestone achievement badges (10 / 100 / 365 / 1,000 km) to the personal dashboard, derived from `distance_to_date_km` with no backend changes.

**Architecture:** Pure frontend feature. `BadgeIcon.tsx` renders one inline-SVG badge (shield + running shoe); `BadgeRow.tsx` holds the thresholds, computes earned state, and renders 4 badges in a card. `DashboardPage.tsx` drops the card between the Stats and Pace chart cards. No backend changes — `distance_to_date_km` is already in the `GET /dashboard/personal` response.

**Tech Stack:** React 18, TypeScript, inline JSX SVG, existing CSS card patterns (`card`, `card__header`, `card__label`, `card__body`).

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `frontend/src/components/BadgeIcon.tsx` | SVG badge: shield outline + running shoe with per-tier detail |
| Create | `frontend/src/components/BadgeRow.tsx` | Earned-state logic + renders 4 badges in a `card` |
| Modify | `frontend/src/pages/DashboardPage.tsx` | Import + render `<BadgeRow>` between Stats and Pace chart cards |
| Modify | `frontend/src/index.css` | Add `.badge-row`, `.badge-item`, `.badge-item__name`, `.badge-item__threshold` |

> **No test steps:** The project has no frontend test framework (no Vitest/Jest). All verification is visual via the Vite dev server. Backend has no changes so no integration tests are required.

---

## Task 1: BadgeIcon component

**Files:**
- Create: `frontend/src/components/BadgeIcon.tsx`

### SVG design notes

ViewBox: `0 0 80 96`. All paths are stroke-only (`fill="none"`). Shield and shoe use `strokeWidth="2"`; detail lines (laces, tread, panel) use `strokeWidth="1.5"`.

**Shield path** — heraldic shield: rounded top corners, straight sides, pointed bottom:
```
M 10,2 L 70,2 Q 78,2 78,10 L 78,56 Q 66,80 40,94 Q 14,80 2,56 L 2,10 Q 2,2 10,2 Z
```

**Shoe path** — right-facing running shoe silhouette, sole at y=68, toe cap curves right, heel back vertical at x=15:
```
M 15,68 L 15,50 Q 15,42 22,38 L 34,34 L 58,30 Q 66,28 68,36 Q 70,44 66,54 Q 60,68 50,68 Z
```

**Per-tier detail:**
- Silver+: 3 lace strokes across the upper
- Gold+: 2 heel tread lines + 2 toe tread lines
- Platinum: adds a midsole/upper panel line

- [ ] **Step 1: Create `frontend/src/components/BadgeIcon.tsx`**

```tsx
interface BadgeIconProps {
  tier: 'bronze' | 'silver' | 'gold' | 'platinum'
  color: string
  width?: number
  height?: number
}

const SHIELD = 'M 10,2 L 70,2 Q 78,2 78,10 L 78,56 Q 66,80 40,94 Q 14,80 2,56 L 2,10 Q 2,2 10,2 Z'
const SHOE   = 'M 15,68 L 15,50 Q 15,42 22,38 L 34,34 L 58,30 Q 66,28 68,36 Q 70,44 66,54 Q 60,68 50,68 Z'

export default function BadgeIcon({ tier, color, width = 80, height = 96 }: BadgeIconProps) {
  const hasLaces = tier === 'silver' || tier === 'gold' || tier === 'platinum'
  const hasTread = tier === 'gold' || tier === 'platinum'
  const hasPanel = tier === 'platinum'

  return (
    <svg viewBox="0 0 80 96" width={width} height={height} xmlns="http://www.w3.org/2000/svg">
      {/* Shield */}
      <path d={SHIELD} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      {/* Running shoe — Bronze: bare outline only */}
      <path d={SHOE} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {/* Laces — Silver+ */}
      {hasLaces && (
        <>
          <line x1="26" y1="41" x2="52" y2="36" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="26" y1="47" x2="50" y2="43" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="26" y1="53" x2="46" y2="49" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
        </>
      )}
      {/* Sole tread — Gold+ */}
      {hasTread && (
        <>
          {/* Heel tread */}
          <line x1="17" y1="63" x2="24" y2="63" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="17" y1="66" x2="24" y2="66" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          {/* Toe tread */}
          <line x1="52" y1="62" x2="58" y2="62" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
          <line x1="50" y1="65" x2="56" y2="65" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
        </>
      )}
      {/* Midsole/upper panel line — Platinum */}
      {hasPanel && (
        <line x1="16" y1="58" x2="62" y2="48" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      )}
    </svg>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/BadgeIcon.tsx
git commit -m "feat(badges): add BadgeIcon SVG component"
```

---

## Task 2: BadgeRow component + CSS

**Files:**
- Create: `frontend/src/components/BadgeRow.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Create `frontend/src/components/BadgeRow.tsx`**

```tsx
import BadgeIcon from './BadgeIcon'

type Tier = 'bronze' | 'silver' | 'gold' | 'platinum'

interface BadgeSpec {
  tier: Tier
  name: string
  threshold: number
  color: string
  label: string
}

const BADGES: BadgeSpec[] = [
  { tier: 'bronze',   name: 'First Steps', threshold: 10,   color: '#9c6b3c', label: '10 km'    },
  { tier: 'silver',   name: 'Century',     threshold: 100,  color: '#8b91a8', label: '100 km'   },
  { tier: 'gold',     name: 'One a Day',   threshold: 365,  color: '#b8922a', label: '365 km'   },
  { tier: 'platinum', name: 'Thousand',    threshold: 1000, color: '#9ab0c8', label: '1,000 km' },
]

const UNEARNED = '#3d4358'

interface Props {
  distanceKm: number
}

export default function BadgeRow({ distanceKm }: Props) {
  return (
    <div className="card">
      <div className="card__header">
        <span className="card__label">Badges</span>
      </div>
      <div className="card__body">
        <div className="badge-row">
          {BADGES.map((b) => {
            const earned = distanceKm >= b.threshold
            return (
              <div key={b.tier} className="badge-item">
                <BadgeIcon tier={b.tier} color={earned ? b.color : UNEARNED} />
                <span className={`badge-item__name${earned ? '' : ' badge-item__name--unearned'}`}>
                  {b.name}
                </span>
                <span className="badge-item__threshold">{b.label}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add badge styles to `frontend/src/index.css`**

Append the following block to the end of `frontend/src/index.css`:

```css
/* ── Badges ──────────────────────────────────────────── */

.badge-row {
  display: flex;
  justify-content: space-around;
  align-items: flex-start;
  gap: 8px;
}

.badge-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex: 1;
}

.badge-item__name {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-2);
  text-align: center;
}

.badge-item__name--unearned {
  color: var(--text-3);
}

.badge-item__threshold {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text-3);
  text-align: center;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/BadgeRow.tsx frontend/src/index.css
git commit -m "feat(badges): add BadgeRow component and badge styles"
```

---

## Task 3: Dashboard integration

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

The badge row must appear **between the Stats card and the Pace chart card** (spec: "below Stats, above Pace chart").

- [ ] **Step 1: Add the import at the top of `DashboardPage.tsx`**

After the existing `import PaceChart from '../components/PaceChart'` line, add:

```tsx
import BadgeRow from '../components/BadgeRow'
```

- [ ] **Step 2: Insert `<BadgeRow>` in the JSX**

Inside `DashboardPage.tsx`, in the `{dashState.status === 'loaded' && ( <> ... </> )}` block, insert the `<BadgeRow>` card **after the Stats card closing `</div>` and before the Pace chart card opening `{/* Pace chart card */}`**:

```tsx
{/* Badges card */}
<BadgeRow distanceKm={dashState.data.distance_to_date_km} />
```

The resulting order in the `<>` fragment should be:
1. Stats card `<div className="card">` … `</div>`
2. `<BadgeRow distanceKm={dashState.data.distance_to_date_km} />`
3. Pace chart card `<div className="card">` … `</div>`
4. Goal edit card `<div className="card">` … `</div>`

- [ ] **Step 3: Start dev server and verify visually**

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173`. Log in and navigate to the Dashboard tab (requires at least one sync). Verify:

| Check | Expected |
|-------|----------|
| Badges card appears between Stats and Pace chart | ✓ |
| Unearned badges render in dark grey (`#3d4358`) | ✓ |
| Earned badge renders in tier color (Bronze `#9c6b3c`, etc.) | ✓ |
| Tier name below icon in `--text-2` (earned) or `--text-3` (unearned) | ✓ |
| Threshold label below name in JetBrains Mono | ✓ |
| Dark and light mode both look clean | ✓ |
| Badge row is not shown on the Clubs page | ✓ |

To test all 4 badge states at once without running 1,000 km, temporarily change your distance assertion (or use browser devtools to inspect the rendered SVGs for correct stroke colors).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat(badges): integrate BadgeRow into personal dashboard"
```

---

## Task 4: Backlog entry

**Files:**
- Modify: `docs/epics/backlog.md`

- [ ] **Step 1: Append the following task entry at the end of `docs/epics/backlog.md`** (after the TASK-7.8 block and before the trailing notes):

```markdown
#### TASK-8.1 ✅ _(ad-hoc)_

**Name:** Achievement Badges

**Goal:** Display four milestone achievement badges on the personal dashboard when year-to-date distance crosses 10 / 100 / 365 / 1,000 km. Badge state derives from `distance_to_date_km` — no backend changes required.

**Context:** Pure frontend feature. Shield + running shoe SVG badges with progressive detail per tier. Earned badges render in tier color; unearned in `--text-3` (`#3d4358`). Design spec: `docs/superpowers/specs/2026-06-16-achievement-badges-design.md`.

**Input:** `frontend/src/pages/DashboardPage.tsx`, `frontend/src/index.css`

**Output:**
- `frontend/src/components/BadgeIcon.tsx` — SVG badge component (shield + shoe, 4 tier variants)
- `frontend/src/components/BadgeRow.tsx` — Badge row card with earned-state logic
- `frontend/src/pages/DashboardPage.tsx` — Render `<BadgeRow>` between Stats and Pace chart cards
- `frontend/src/index.css` — Add `.badge-row`, `.badge-item`, `.badge-item__name`, `.badge-item__threshold`

**Dependencies:** TASK-5.x (personal dashboard `distance_to_date_km`)

**Complexity:** Small

**Testability:** Badges card visible on Dashboard, not on Clubs page. Earned badges show tier color; unearned show dark grey. All four tiers render at correct threshold.
```

- [ ] **Step 2: Commit**

```bash
git add docs/epics/backlog.md docs/superpowers/specs/2026-06-16-achievement-badges-design.md
git commit -m "docs(backlog): add TASK-8.1 achievement badges"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|-----------------|------------|
| 4 tiers: Bronze 10 km, Silver 100 km, Gold 365 km, Platinum 1,000 km | `BADGES` constant in `BadgeRow.tsx` (Task 2) |
| Shield shape, stroke-only | `SHIELD` path, `fill="none"` in `BadgeIcon.tsx` (Task 1) |
| Running shoe with progressive detail | `SHOE` path + `hasLaces`/`hasTread`/`hasPanel` in `BadgeIcon.tsx` (Task 1) |
| Tier colors, unearned → `#3d4358` | `color` prop + `UNEARNED` constant in `BadgeRow.tsx` (Task 2) |
| 80×96 viewBox | `viewBox="0 0 80 96"` default in `BadgeIcon.tsx` (Task 1) |
| Card with `card__header` + `card__label` + `card__body` | `BadgeRow.tsx` (Task 2) |
| Tier name: 12px Manrope 400 | `.badge-item__name` CSS (Task 2) |
| Threshold label: 11px JetBrains Mono | `.badge-item__threshold` CSS (Task 2) |
| Below Stats, above Pace chart | `DashboardPage.tsx` insertion order (Task 3) |
| Not shown in club views | `BadgeRow` is only rendered in `DashboardPage.tsx` (Task 3) |
| No backend changes | Confirmed — `distance_to_date_km` already in API response |

**Placeholder scan:** No TBDs, TODOs, or "similar to Task N" references — all steps contain complete code.

**Type consistency:** `Tier` type is defined once in `BadgeRow.tsx` and passed straight through to `BadgeIcon.tsx`'s `tier: 'bronze' | 'silver' | 'gold' | 'platinum'` prop. `UNEARNED` constant (`'#3d4358'`) matches the spec's `--text-3` dark value. `BadgeIconProps.color` is a `string` throughout.
