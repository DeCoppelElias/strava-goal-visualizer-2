# Privacy Page Design — TASK-7.6

_Date: 2026-06-14_

## Summary

Add a self-service privacy page (`PrivacyPage.tsx`) accessible via the "Data Deletion Info" link in the existing `GdprFooter`. The page exposes two actions: download a copy of the user's data and delete the account. Both backend endpoints (`POST /privacy/export`, `POST /privacy/delete`) are already implemented.

---

## Navigation Wiring

`GdprFooter.tsx` gains an optional `onPrivacyClick?: () => void` prop. The "Data Deletion Info" `<a>` is replaced with a `<button>` styled identically, calling that prop when provided.

`HomePage.tsx` changes:
- `Page` type gains `'privacy'`: `type Page = 'dashboard' | 'clubs' | 'privacy'`
- `<GdprFooter>` receives `onPrivacyClick={() => setPage('privacy')}`
- Renders `<PrivacyPage onDeleteComplete={onLogout} />` when `page === 'privacy'`

Navigation back to Dashboard or Clubs happens via the existing top nav tabs, which remain active while on the privacy page. No explicit "back" button or additional prop is needed.

The `GdprFooter` remains visible on every page, including the privacy page itself.

---

## API Additions (`client.ts`)

### `postPrivacyExport(): Promise<void>`

- Calls `POST /privacy/export` via `apiFetch`
- Reads response as `Blob`
- Creates an object URL, programmatically clicks a hidden `<a download="strava-export.json">` anchor
- Revokes the object URL after click
- Throws on any non-OK response (caller handles `429` with a specific message)

### `postPrivacyDelete(): Promise<{ deleted: boolean }>`

- Calls `POST /privacy/delete` via `apiFetch`
- Returns parsed JSON body
- Throws on non-OK

---

## `PrivacyPage.tsx`

**Props:**
```ts
interface Props {
  onDeleteComplete: () => void
}
```

**Layout:** Two stacked cards inside a `privacy-page` container, following the same `surface`/`border` card pattern as `DashboardPage` and `ClubsPage`.

### Export Card — "Your Data"

- Section header: "YOUR DATA"
- Caption: "Download a copy of all your stored data as JSON."
- Button: "Download My Data" (`btn btn--primary`)
- States:
  - **idle** — button enabled
  - **loading** — spinner on button, button disabled
  - **success** — brief caption "Download started" below button
  - **error (generic)** — "Export failed. Please try again."
  - **error (429)** — "You can download at most 5 times per hour."

### Delete Card — "Delete Account"

- Section header: "DELETE ACCOUNT"
- Caption: "Permanently remove your account and all associated data from this app."
- Button: "Delete My Account" (`btn btn--danger`)

**Confirmation expand (inline, shown after clicking Delete My Account):**
- Warning text (danger-tinted): "This cannot be undone. All your activities, goals, and club memberships will be permanently deleted."
- "Confirm Delete" button (`btn btn--danger`, solid)
- "Cancel" button (`btn btn--ghost`) — collapses back to initial state

**After confirm:**
- Spinner on "Confirm Delete" button, all buttons disabled
- On success: calls `onDeleteComplete()` (which triggers `onLogout()` in `App`, redirecting to login page)
- On error: show "Deletion failed. Please try again." and re-enable buttons

---

## CSS

No new global patterns needed. Reuse:
- `.card` / surface + border for card containers
- `.page-header` / `.page-title` for the page heading
- `.btn--danger`: `background: var(--danger-dim); color: var(--danger); border: 1px solid var(--danger-dim)` — already in style guide
- Inline confirmation block uses a `var(--danger-dim)` background panel with `var(--danger)` text for the warning

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Export 429 | "You can download at most 5 times per hour." |
| Export other error | "Export failed. Please try again." |
| Delete error | "Deletion failed. Please try again." Re-enable buttons. |
| Delete success | Calls `onDeleteComplete()` → login page |

---

## Out of Scope

- Modal dialogs (inline confirmation only)
- Rate-limit countdown timer on export
- Any backend changes (all endpoints already exist)
