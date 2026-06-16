# User Nav Dropdown Design

_Date: 2026-06-16_

## Overview

Two sequential tasks that promote the account/privacy page to a first-class nav destination and replace the standalone "Log out" button with a user icon dropdown.

**Task A** (backend + type): Expose `display_name` in `/session/me`.
**Task B** (frontend): User icon dropdown with display name, Account link, and Log out.

---

## Task A — Expose display_name in session

### Context

`display_name` is already stored on the `User` model and populated at OAuth login via `_build_display_name(athlete)` (first name + last initial). It is not currently included in the `/session/me` response.

### Changes

**`backend/auth/schemas.py`**
Add `display_name: str` to `SessionMeResponse`:

```python
class SessionMeResponse(BaseModel):
    strava_athlete_id: int
    display_name: str
    created_at: datetime
```

**`backend/auth/router.py`**
Pass the field in the response constructor:

```python
return SessionMeResponse(
    strava_athlete_id=current_user.strava_athlete_id,
    display_name=current_user.display_name,
    created_at=current_user.created_at,
)
```

**`frontend/src/api/client.ts`**
Add the field to `SessionUser`:

```ts
export interface SessionUser {
  strava_athlete_id: number
  display_name: string
  created_at: string
}
```

No migration needed — the column exists and is already populated.

### Testing

Update the existing `/session/me` integration test to assert `display_name` is present and matches the value stored on the user row.

---

## Task B — User icon dropdown

### Overview

Replace the standalone "Log out" button in `app-nav__actions` with a circular user icon button. Clicking it toggles a small dropdown panel containing the user's display name, an "Account" button (navigates to the privacy/data page), and "Log out". The `GdprFooter` is simplified to only the two public legal links.

### Page type extension

Add `'account'` to the `Page` union in `HomePage.tsx`. Render `<PrivacyPage onDeleteComplete={onLogout} />` when `page === 'account'`. No other changes to page routing logic.

### Nav structure

`app-nav__actions` (right side of nav):

```
[ Theme toggle ]  [ User icon ▼ ]
```

The user icon button (`btn--icon`) holds a person SVG. The entire icon + dropdown lives in a single wrapper `div` with `position: relative` so the panel can be absolutely positioned below it.

### Dropdown panel

Absolutely positioned below the icon button, right-aligned (`right: 0`) so it never overflows the viewport edge on narrow screens. Minimum width: `160px`.

Contents (top to bottom):
1. Display name — small muted label, not interactive
2. "Account" button — navigates to `page === 'account'`; closes dropdown
3. "Log out" button — calls `handleLogout()`; closes dropdown

### Click-outside dismissal

A `useEffect` adds a `mousedown` listener on `document` when the dropdown is open and removes it on cleanup. If the event target is outside the wrapper ref, set `isOpen` to `false`. This pattern works on mobile (touch events synthesize mousedown).

### GdprFooter simplification

Remove the `onPrivacyClick` prop and the "Data Deletion Info" link. Remove the `Props` interface entirely. Footer renders only:

```
Privacy Policy · Terms of Service
```

This is the only change to `GdprFooter.tsx`.

### Files changed

| File | Change |
|---|---|
| `frontend/src/pages/HomePage.tsx` | Add `'account'` page, user icon + dropdown, remove logout button, remove `onPrivacyClick` from footer |
| `frontend/src/components/GdprFooter.tsx` | Remove Props interface, remove Data Deletion Info link |

No new component files — the dropdown is small enough to live inline in `HomePage.tsx`.

### Mobile

The `right: 0` dropdown alignment and tap-to-open interaction work correctly on mobile. Replacing "Log out" text with an icon reduces nav crowding on narrow screens.

### Testing

- Clicking the user icon opens the dropdown showing the display name.
- Clicking "Account" navigates to the privacy/data page with the nav bar visible; dropdown closes.
- Clicking "Log out" triggers the logout flow; dropdown closes.
- Clicking anywhere outside the dropdown closes it.
- GdprFooter shows only "Privacy Policy · Terms of Service" on all pages.
- Legal pages still render correctly with working "← Back to app" navigation.
