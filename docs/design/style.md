# Frontend Style Guide

**Aesthetic Direction:** Calm Dashboard
**References:** Notion, Linear, Streamlit
**Mood:** Structured · Quiet · Organised

---

## Themes

The app supports dark mode (default) and light mode, controlled by a `data-theme` attribute on `<html>`. CSS variables switch automatically.

---

## Color Tokens

```css
/* Dark (default) */
[data-theme="dark"], :root {
  --bg:            #0d0f14;   /* deep blue-black, not pure black */
  --surface:       #13161e;   /* card/panel background */
  --surface-2:     #1c2030;   /* elevated surface, hover fills */
  --border:        #272c3d;   /* subtle separator */
  --text-1:        #e8eaf0;   /* primary — slightly warm white */
  --text-2:        #8b91a8;   /* secondary — muted */
  --text-3:        #3d4358;   /* tertiary — very subtle */

  --accent:        #4b8cf7;   /* primary blue — calm, not electric */
  --accent-dim:    rgba(75, 140, 247, 0.10);
  --accent-strong: #6ba3f9;   /* lighter variant for dark bg text */

  --danger:        #e05252;
  --danger-dim:    rgba(224, 82, 82, 0.10);
  --warning:       #d4884a;
  --warning-dim:   rgba(212, 136, 74, 0.10);
  --success:       #4caf86;
  --success-dim:   rgba(76, 175, 134, 0.10);
}

/* Light */
[data-theme="light"] {
  --bg:            #f7f8fb;
  --surface:       #ffffff;
  --surface-2:     #f0f1f6;
  --border:        #e2e4ed;
  --text-1:        #0d0f14;
  --text-2:        #5c6380;
  --text-3:        #a8adc4;

  --accent:        #3b7ef6;
  --accent-dim:    rgba(59, 126, 246, 0.08);
  --accent-strong: #2563eb;

  --danger:        #dc3535;
  --danger-dim:    rgba(220, 53, 53, 0.08);
  --warning:       #c47a30;
  --warning-dim:   rgba(196, 122, 48, 0.08);
  --success:       #2e9a6e;
  --success-dim:   rgba(46, 154, 110, 0.08);
}
```

**Rule:** Blue (`--accent`) is the only color accent. Use it for:
- Graph lines and area fills
- Active nav items
- Primary action buttons
- Highlighted numeric values (e.g. km totals, goal progress)

Everything else uses grayscale tokens. No green accent buttons.

---

## Typography

```
Body / UI:   Manrope       — weights 400, 500, 600
Mono / Data: JetBrains Mono — weights 400, 500
```

Both are available via Google Fonts. Import in `index.html`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

**Type Scale:**

| Role           | Size  | Weight | Family     | Notes                          |
|----------------|-------|--------|------------|--------------------------------|
| Page title     | 24px  | 600    | Manrope    | Not a giant hero — calm        |
| Section header | 13px  | 600    | Manrope    | Uppercase, letter-spacing 0.07em |
| Body           | 14px  | 400    | Manrope    | Default reading text           |
| Body emphasis  | 14px  | 500/600| Manrope    | Labels, key info               |
| Data value     | 20px  | 500    | JetBrains  | Large numbers (km, %)          |
| Data small     | 13px  | 400    | JetBrains  | Dates, IDs, metadata           |
| Caption        | 12px  | 400    | Manrope    | Explanatory text, timestamps   |

**Anti-patterns (do not use):**
- No `clamp(52px, 9vw, 88px)` display giants
- No `text-transform: uppercase` on body copy (only on section headers/labels)
- No `letter-spacing` on body text
- No Barlow / Barlow Condensed

---

## Spacing & Layout

```
Page padding:          32px horizontal, 40px top
Max content width:     960px (centered)
Section gap:           48px between major sections
Card padding:          20px
Card gap (in grid):    16px
Inline element gap:    8–12px
```

Graphs should occupy roughly 60–70% of page width at desktop. Not full-bleed, not thumbnail. Generous but measured.

---

## Shape & Elevation

```
Border radius:
  Cards / panels:   8px
  Buttons:          6px
  Inputs / badges:  6px
  Pills / tags:     100px

Borders:
  Default surface:  1px solid var(--border)
  No box-shadow on cards — border + bg contrast does the job

Shadows (use sparingly):
  Dropdown / modal: 0 8px 24px rgba(0,0,0,0.3)   /* dark */
                    0 4px 16px rgba(0,0,0,0.10)   /* light */
```

---

## Motion

All transitions: `180ms ease`.
No bouncing, no spring physics, no slide-in theatrics.

```css
transition: background 180ms ease, color 180ms ease, opacity 180ms ease,
            border-color 180ms ease, box-shadow 180ms ease;
```

Page-level entrance: a single short fade-in (`opacity 0→1, 200ms`). That's it.
No staggered reveals, no transform slides.

---

## Component Conventions

### Buttons

```
Primary:   bg=var(--accent),  text=#fff,       border=none
Ghost:     bg=transparent,    text=var(--text-2), border=var(--border)
Danger:    bg=var(--danger-dim), text=var(--danger), border=var(--danger-dim)
```

Hover: `background` lightens/darkens slightly (not a translateY lift).
Active: slight darken. No drop-shadow glow effects.

### Cards / Panels

Bordered surface with 8px radius and `var(--surface)` fill. Section headers inside cards use the `13px 600 uppercase` style with a bottom border separator.

### Graphs (Recharts or similar)

- Line color: `var(--accent)` (`#4b8cf7` dark / `#3b7ef6` light)
- Area fill: `rgba(75, 140, 247, 0.08)` — very subtle
- Grid lines: `var(--border)`
- Axis text: `var(--text-3)`, 11px JetBrains Mono
- Tooltip: surface-2 bg, border, rounded-8

### Nav

Compact horizontal bar, 52px tall. Brand name left-aligned in Manrope 600. Links are simple text buttons — active link gets `color: var(--accent)`. Theme toggle on the far right (sun/moon icon button).

---

## Dark / Light Mode Toggle

Store preference in `localStorage` under `"theme"`. Read on mount and apply to `document.documentElement.setAttribute("data-theme", ...)`. Default to `"dark"`.

```ts
// theme.ts
export type Theme = 'dark' | 'light'

export function getTheme(): Theme {
  return (localStorage.getItem('theme') as Theme) ?? 'dark'
}

export function setTheme(t: Theme) {
  localStorage.setItem('theme', t)
  document.documentElement.setAttribute('data-theme', t)
}
```

---

## What Changes vs Current

| Current                         | New                            |
|---------------------------------|--------------------------------|
| Barlow Condensed display font   | Manrope (calm, structured)     |
| Acid green accent (#b8ff3c)     | Calm blue (#4b8cf7)            |
| Near-black (#0a0a0a) bg         | Deep blue-black (#0d0f14)      |
| Giant 88px hero titles          | 24px understated page titles   |
| Green CTA buttons               | Blue primary buttons           |
| Dark-only                       | Dark + Light mode toggle       |
| No card structure               | Bordered surface cards         |
| translateY lift on hover        | Subtle bg-change hover         |
