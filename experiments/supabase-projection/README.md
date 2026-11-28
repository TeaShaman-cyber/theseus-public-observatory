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
