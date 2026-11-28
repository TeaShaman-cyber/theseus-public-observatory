# Supabase projection — issue #35

Git JSONL remains canonical. The service-only projection stores one immutable
receipt per journal path/line, its SHA-256 (line bytes excluding line ending),
and the first importing Git commit. Replaying identical content is safe;
conflicting readback fails rather than silently overwriting. Only service_role
can insert/read through REST; RLS is enabled. Views use security_invoker.

Deploy schema.sql once through authorized Supabase SQL migration. On the
governed exe.dev VM, run from the repository:

```sh
python3 experiments/supabase-projection/sync.py --day 2026-11-28 --ref origin/main
```

Read source health, Radar points and same-run/provider/window paired Pearson
correlations via the observatory_sources, observatory_radar_points and
observatory_radar_correlations views. REST paths use the attached Supabase
integration; no key in code. The paired views use measurement time, not poll
time. Normalized values from different windows are not stitched. Historical
missing semantic state is retained as NULL. A missing radar series is not zero.

This slice does not change the collector, schedule imports, establish a
retention policy, or expose data publicly. Full historical backfill and
independent periodic collection remain open under #35.

## Autonomous journal refresh (second slice)

Apply schedule.sql in the dedicated Supabase project through the authorized
migration route. Run test_schedule.sql as the SQL owner (rollback-only),
then call `select observatory_sync.refresh();` and independently verify
`observatory_sync.runs` plus the imported rows. Apply activate.sql only after
acceptance. Stop via `select cron.unschedule('observatory-journal-refresh');`.

One pg_cron job runs every 15 minutes. The private observatory_sync schema
contains a synchronous http extension (no public schema exposure) and a
fixed-destination refresh function. The latter fetches the public Git main
ref and then yesterday/today UTC JSONL at that exact commit. No API token,
VM process or inbound endpoint is needed. HTTP timeouts are 10 seconds per
request (connect 3 seconds); journal acceptance is capped at 8 MiB per day
after download. Both days commit together or roll back on error. Missing day,
truncation, unexpected response or changed canonical line is a recorded
failure, never a silent overwrite. A new day before the first collector
commit can therefore report an error until that file exists. A missed day
outside the two-day lookback needs explicit backfill using sync.py.

Check job execution separately from its durable refresh verdict:
```sql
select * from observatory_sync.runs order by started_at desc limit 10;
select jobid, status, start_time, end_time
from cron.job_run_details where jobid = (
  select jobid from cron.job where jobname='observatory-journal-refresh'
) order by start_time desc limit 10;
```
The cron SQL call can complete successfully while the refresh records
`error`; the latter is the authoritative per-refresh verdict. The advisory
lock prevents overlapping manual refreshes; the cron scheduler serializes
runs of this job. No retention policy is applied yet. This sync does not
increase actual collection cadence; independent probe scheduling remains
a separate next slice. No raw private chat or local telemetry is imported.
