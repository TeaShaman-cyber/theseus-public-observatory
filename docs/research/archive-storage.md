# Historical archive storage

Coordination: #35, #14, #41. Avoid turning the governed execution VM
into the science data warehouse.

- Original provider bytes and source metadata are the research evidence.
  Small immutable snapshots may live in Git (GFZ: 2.48 MB once).
  For larger public archives evaluate existing immutable Release pack
  conventions and provider-hosted originals; do not put bulk satellite
  data into Git history. Pin source URI/version/digest and license.
- Existing private Supabase Storage bucket `observatory-archives`
  serves content-addressed derived Parquet. 50 MiB object size cap,
  no public reads, no upserts; object path includes SHA-256. Store
  descriptors in Git; verify full digest at admission. It is a cache
  that can be rebuilt, not canonical evidence. Start with GFZ; no
  automatic bulk mirror or additional billable infrastructure.
- PostgreSQL remains the hot operational/metadata query plane, not
  a warehouse of duplicated historical raw records. DuckDB/httpfs
  queries the remote Parquet with predicate/column projection.
- Execution: bounded temporary staging, explicit owner/retention
  trigger and cleanup after independent durable readback. Avoid
  accumulating separate local DuckDB copies. Limit data download
  to the experiment's spatial/temporal support and use remote reads
  where practical. No assumption of unlimited free storage or egress:
  check actual quotas/usage and plan before each larger intake.

Current verified object: [GFZ storage descriptor](../../experiments/historical/gfz/storage.json).
Remote access was tested only on exe.dev through its attached proxy.
A separate runtime must establish its own credential boundary. Existing
Git journal and scheduled probe authority are unchanged.
