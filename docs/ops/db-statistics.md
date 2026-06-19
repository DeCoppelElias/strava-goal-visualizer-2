# Database Statistics — Querying Usage

How to read usage statistics for the Strava Goal Visualizer straight from
PostgreSQL, both locally and against the deployed Fly.io database. For a quick
glance, run the curated summary file (`scripts/stats.sql`); for anything ad-hoc,
use the query catalogue below.

> **Scope note:** These statistics use data already in the database. There is no
> `last_seen_at` column, so "active users" is approximated by *who has synced
> activities*, not login recency. Sessions are signed cookies (no server-side
> session store), so there is no "currently online" count — that state does not
> exist on the server.

---

## Quick glance: run the curated summary

`scripts/stats.sql` prints a one-table summary (total users, signups in the last
7 days, users who have synced, users with a goal, total activities, total
distance, clubs):

```
        metric         | value
-----------------------+-------
 Total users           |   342
 Signups (last 7 days) |    18
 Users who have synced |   310
 Users with a goal set |   276
 Total activities      | 48201
 Total distance (km)   | 312880.5
 Clubs tracked         |    27
```

**Local:**

```bash
docker compose exec -T db psql -U postgres -d strava_dev -f - < scripts/stats.sql
```

```powershell
Get-Content scripts/stats.sql -Raw | docker compose exec -T db psql -U postgres -d strava_dev
```

**Production (Fly.io):**

```bash
fly postgres connect -a <db-app> -d <db-name> < scripts/stats.sql
```

```powershell
Get-Content scripts/stats.sql -Raw | fly postgres connect -a <db-app> -d <db-name>
```

Replace `<db-app>` with your Postgres app name (`fly apps list`) and `<db-name>`
with the application database (e.g. `strava`). No tunnel or exposed port is
needed — `fly postgres connect` proxies through the Fly CLI.

> **Which Fly Postgres?** The command above is for **Fly Postgres** (the
> unmanaged app). If you provisioned **Managed Postgres**, use `fly mpg` instead
> — run `fly mpg --help` / `fly pg --help` to confirm the connect syntax for your
> setup. Either way, piping `scripts/stats.sql` into the resulting `psql` session
> works the same.

---

## Connecting (interactive sessions)

### Local (Docker Compose)

The compose `db` service does not publish a host port, so connect through the
container:

```bash
docker compose exec db psql -U postgres -d strava_dev
```

### Production (Fly.io)

The PostgreSQL port is never exposed publicly. Use the Fly CLI:

```bash
# Quick interactive session
fly postgres connect -a <db-app> -d <db-name>

# Or open a tunnel for a GUI client (e.g. TablePlus, DBeaver)
fly proxy 5432 -a <db-app>      # forwards localhost:5432 to the prod DB
# then connect your client to:
#   postgresql://postgres:<password>@localhost:5432/<db-name>
```

> Cross-reference: `fly logs -a <app>` streams the live plain-text logs (each line
> carries an `X-Request-ID`), useful for correlating anomalies you spot in the
> stats.

### Read-only role (recommended)

A `stats_reader` role can run every query in this doc but cannot mutate data, so
a fat-fingered `UPDATE`/`DELETE` while poking around is impossible. It is **not
deployment-specific** — the same steps work locally and in production. It matters
most against production (the local Docker DB is a throwaway), so creating it
locally is optional.

**Step 1 — Create the role (one time, as an admin/superuser).**

The `CREATE ROLE` / `GRANT` statements must be run by a role that already has
those privileges — i.e. the `postgres` superuser, *not* `stats_reader` itself.
Connect as admin, then run the block once:

```bash
# Local: connect as the postgres superuser
docker compose exec db psql -U postgres -d strava_dev

# Production: connect as the postgres superuser
fly postgres connect -a <db-app> -d <db-name>
```

```sql
CREATE ROLE stats_reader WITH LOGIN PASSWORD 'choose-a-strong-password';
GRANT CONNECT ON DATABASE <db-name> TO stats_reader;
GRANT USAGE ON SCHEMA public TO stats_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO stats_reader;
-- Make future tables (e.g. after a migration) readable too:
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO stats_reader;
```

`SELECT ON ALL TABLES` grants on tables that exist *now*; the `ALTER DEFAULT
PRIVILEGES` line covers tables added later. Run it once — it persists in the
database, so you don't recreate the role on every session.

> One caveat: `ALTER DEFAULT PRIVILEGES` only applies to tables created by the
> role that ran it. If migrations create tables as `postgres` (the usual case),
> run the `ALTER DEFAULT PRIVILEGES` line while connected as `postgres` and
> you're covered. After a migration that adds tables created by a *different*
> role, re-run the `GRANT SELECT ON ALL TABLES` line to catch up.

**Step 2 — Connect as `stats_reader` to run stats.**

Use the role's own credentials instead of the app/admin role:

```bash
# Local
docker compose exec db psql -U stats_reader -d strava_dev

# Production
fly proxy 5432 -a <db-app>      # in one terminal
psql "postgresql://stats_reader:<password>@localhost:5432/<db-name>"   # in another
```

To run the curated summary through it, pipe `scripts/stats.sql` into either
connection exactly as shown in **Quick glance** above (just swap `-U postgres`
for `-U stats_reader`).

---

## Running your own queries

The catalogue below is plain SQL — run it three ways:

- **Interactive:** open a session (`docker compose exec db psql -U postgres -d
  strava_dev` locally, or `fly postgres connect -a <db-app> -d <db-name>` in
  prod), then type queries ending in `;`. `\dt` lists tables, `\d <table>`
  describes one, `\q` quits.
- **One-off:** append `-c "SELECT ...;"` to either connect command.
- **From a file:** pipe it in, as shown in **Quick glance** above.

---

## Query catalogue

### Users

```sql
-- Total registered users
SELECT count(*) FROM users;

-- Signups per week (most recent first)
SELECT date_trunc('week', created_at) AS week, count(*)
FROM users GROUP BY 1 ORDER BY 1 DESC;

-- Most recent signups
SELECT id, display_name, created_at
FROM users ORDER BY created_at DESC LIMIT 20;
```

### Engagement

```sql
-- Users who have synced at least one activity
SELECT count(DISTINCT user_id) FROM activities;

-- Users with a yearly goal set
SELECT count(*) FROM goals;

-- Activities per user (most active first)
SELECT u.id, u.display_name, count(a.id) AS activities
FROM users u LEFT JOIN activities a ON a.user_id = u.id
GROUP BY u.id, u.display_name
ORDER BY activities DESC;
```

### Clubs

```sql
-- Clubs tracked
SELECT count(*) FROM clubs;

-- Members per club (largest first)
SELECT c.id, c.name, count(m.user_id) AS members
FROM clubs c LEFT JOIN club_memberships m ON m.club_id = c.id
GROUP BY c.id, c.name
ORDER BY members DESC;
```

### Content volume

```sql
-- Total activities and combined distance (km)
SELECT count(*) AS activities,
       round(sum(distance_meters) / 1000, 1) AS total_km
FROM activities;

-- Data date range
SELECT min(start_date) AS earliest, max(start_date) AS latest
FROM activities;
```

> All stored activities are runs (`sport_type = 'Run'` is enforced at ingest),
> so no sport filter is needed.
