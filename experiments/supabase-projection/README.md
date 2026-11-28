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

## Independent status probes (third slice)

A bounded pilot runs OpenAI Status and GitHub Status (control) from
Supabase PostgreSQL in Frankfurt. This is a second collection vantage,
not a replacement for the GitHub journal or a ChatGPT inference probe.

Schema files are under `supabase/migrations/`: independent_status_probes
then status_series_projection. Both depend on the existing projection
and schedule.sql; these experimental files were applied explicitly using
the authorized CLI SQL-file route, not a general migration push. Do not
blindly replay them or treat the hosted migration history as reconciled.
Run test_status_probes.sql in a rollback-only transaction. Manually call
observatory_sync.collect_status_pair() as owner for acceptance; inspect
the actual receipts. Then run activate_status_probes.sql once to schedule
a seven-day pilot at five-minute intervals. Stop early with
`select cron.unschedule('observatory-status-probes');`.
Existing receipts are retained. At expiry, the next tick unschedules
itself; no automatic deletion. Expected pilot volume: at most about
4,032 paired probe receipts (two sources, 288 cycles/day, seven days)
plus manual/canary runs. Free-plan continuous availability is not guaranteed.

Each pair has a run timestamp, per-request completion time, endpoint
identity, collector label, elapsed HTTP wall time, HTTP status, outcome,
recognized indicator or NULL, and SHA-256 of accepted-size response text
(UTF-8, not a claim about compressed wire bytes). No raw body is stored.
Fixed destinations, 8-second request timeout, 3-second connect timeout,
no redirects, 1 MiB acceptance bound after retrieval. Transport errors,
non-200 responses and invalid/unknown payloads cannot become operational.
The private collector function is owner-only, and the receipt table and
security-invoker view are service-role read-only through REST.
Pilot activation does not change any existing cron job.

Unified SQL/REST read surface:

```sql
select sample_at, timestamp_kind, collector, source_id, outcome, indicator,
       latency_ms
from public.observatory_status_series
order by sample_at desc limit 20;
```

Keep the collector and timestamp_kind dimensions in analysis; the old
Git journal records batch time, while this pilot records request end.
Never treat missing/unknown data as zero or combine differing collector
latencies as one homogeneous series. A status API response is not a
measurement of ChatGPT serving latency or provider internal load.
No historical backfill, cross-provider correlation inference, Vercel
worker deployment or canonical-source cutover is part of this slice.

Live acceptance on 2026-11-28: manual pair 14:09:50 UTC, OpenAI/GitHub
HTTP 200, 143/49 ms; one-shot scheduled pair 14:10:45 UTC, HTTP 200,
98/27 ms, job 5 succeeded and self-unscheduled. All four rows verified
via attached REST proxy. Recurring job 4 active at */5; sustained cadence
not yet measured. Existing journal refresh remains active. Security
advisor reports the pre-existing pg_net-in-public warning only at warn
level; no new public grants.

## Operational magnetometer evidence buffer (#47)

This supplements remote archive reads, not a definitive-data substitute.
INTERMAGNET terms (https://intermagnet.org/data_conditions.html) permit
noncommercial research with attribution, with institute-specific exceptions;
bulk third-party distribution requires permission. The raw responses stay
in the private `observatory_sync` schema; do not commit or expose them.

Apply `supabase/migrations/*_magnetometer_capture_buffer.sql` once using the
explicit authorized remote SQL-file route after the existing schedule.sql.
Run `test_magnetometer_buffer.sql` in a rollback-only transaction.
The owner-only collector captures IRT (Irkutsk) and KAK (Kakioka),
`best-avail/PT1M/xyzf`, for the previous aligned 6h UTC window and the
same window 72h later. This product can mix preliminary/revised quality;
no definitive label or implied observation of physical truth is assigned.
An HTTP 200 is only received_unvalidated until the payload is checked.
Failed requests and size rejection are durable attempts too.

`magnetic_payloads` deduplicates accepted-size response text by SHA256
of its UTF-8 representation, not a claimed hash of compressed wire bytes.
`magnetic_attempts` records each station/window/capture time/status/hash
or transport SQLSTATE; later responses do not overwrite earlier evidence.
Owner-only invoker functions, private schema, RLS and explicit grant
revocations; triggers reject ordinary UPDATE/DELETE/TRUNCATE. This is
append-only/tamper-evident by application design, **not** administrator-proof
WORM storage; privileged DDL can disable triggers. No raw data is published.
A future durable offline pack needs the provider's permission if shared in
bulk. Storage/retention policy must be explicit before permanent scaling.

`activate_magnetometer_buffer.sql` creates one job at minute 17 every
6h, self-unscheduling after seven days on the next scheduled tick.
Stop early: `select cron.unschedule('observatory-magnetic-buffer');`
Expected 28 cycles, four requests each (112 attempts), plus bounded
manual and acceptance runs. Each accepts at most 128KiB after receipt
(roughly 14MiB maximum uncompressed response text for scheduled attempts,
excluding DB overhead; observed successful response ~24KiB).
Fixed source/parameters, 10s socket/request timeout configured, 3s connect,
no redirect configured, advisory lock to prevent overlap. If the database
transaction itself fails, cron records failure; no claim of exactly-once
delivery across transaction failure. Late data beyond 72h are not yet
automatically recovered; later archival reconciliation remains a separate
explicit experiment. No inference or interpolation from a missing response.
Retain pilot evidence; inspect actual size, coverage and cadence before
extending. Existing jobs are unchanged.

Acceptance 2026-11-28: first manual cycle 15:33Z. IRT 2026-11-28 06–12Z
returned HTTP400; IRT 2026-11-25 06–12Z returned HTTP200/HAPI1200,
360 timestamped non-fill lines. KAK both windows HTTP200/HAPI1200, 360
timestamped non-fill lines each. This check is not a complete scientific
schema/vector validation. Four attempts and four hashed payloads.
Rollback fixtures preserve duplicate-content references, changed bodies,
transport failure and deny mutation; existing pg_net public-schema warning
unchanged. No new public grants. Hosted migration-history reconciliation
remains open (explicit CLI SQL, not migration push).

Scheduled acceptance: one-shot job 7 succeeded 15:34:02–15:34:03 UTC
and self-unscheduled. Readback: eight attempts, four distinct payload
bodies, six received_unvalidated; identical responses deduplicated
without losing attempt timestamps. Recurring job 6 is active; the
first regular 6-hour tick and actual 72-hour revisit are not yet verified.

Read-only follow-up: see [federated read documentation](../../docs/research/federated-read.md#intermagnet-minute-vectors-and-capture-reconciliation-47).
The private buffer reconciliation CLI validates payload hashes and
scientific transport/schema/coverage without changing capture evidence.
No raw station values are emitted by the reconciliation report.
