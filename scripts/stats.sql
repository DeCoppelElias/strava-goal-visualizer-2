-- Curated usage summary. Run locally or against prod (see docs/ops/db-statistics.md).
-- All values cast to text so they share one result set. Order is preserved.
SELECT 'Total users'              AS metric, count(*)::text AS value FROM users
UNION ALL
SELECT 'Signups (last 7 days)',   count(*)::text
  FROM users WHERE created_at > now() - interval '7 days'
UNION ALL
SELECT 'Users who have synced',   count(DISTINCT user_id)::text FROM activities
UNION ALL
SELECT 'Users with a goal set',   count(*)::text FROM goals
UNION ALL
SELECT 'Total activities',        count(*)::text FROM activities
UNION ALL
SELECT 'Total distance (km)',     coalesce(round(sum(distance_meters) / 1000, 1), 0)::text
  FROM activities
UNION ALL
SELECT 'Clubs tracked',           count(*)::text FROM clubs;
