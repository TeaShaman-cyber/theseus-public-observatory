# Edge SQL research canary (#31)

This is a test-only harness, not a deployed query service. No production
bindings, public endpoint, Cloudflare secrets or live hosted Worker are used.
The runner executes local Miniflare/workerd on GitHub-hosted compute. Native
DuckDB 1.4.3 prepares two Parquet files from the pinned public snapshot
`2b53406f741ae8e2d2b078d9233e1d2317a47185`. The WASM module executes only
the three fixed SQL queries in queries.json. Each response is compared to
the native reference. Runtime wall time includes dispatch and initialization
and is not Cloudflare-billed CPU time or a hosted latency measurement.

Run with Python 3.13, DuckDB 1.4.3 and Node 22:
```sh
python experiments/edge-sql/prepare.py tmp/edge-sql
npm ci --prefix experiments/edge-sql --ignore-scripts --no-audit --no-fund
node experiments/edge-sql/canary.mjs tmp/edge-sql
```

## Research results

See [issue #31](https://github.com/TeaShaman-cyber/theseus-public-observatory/issues/31)
for independent D1 cloud receipts and hosted emulation runs. The initial
D1 test (16 sources, 728 points) passed health aggregation, JOIN and LAG
parity in three repetitions. Both temporary resource identity and absence
after cleanup are recorded there. No D1 database remains from the test.

Workers' current 64 MiB uncompressed limit allows the measured 52,335,337
byte first bundle. The Free plan's 10 ms CPU, 128 MB memory, and 1 s startup
constraints still require actual hosted verification. R2 bucket listing
was refused (HTTP 403/10042); no subscription activation was attempted.
Basin is not accepted as a zero-cost option.

## Storage candidate

Store each normalized Radar response window intact, not independently
normalized points in one flattened global time series. At 15-minute polling,
728 points per response would amount to 69,888 point inserts/day before
indexes. A candidate D1 JSON receipt model stores one row per window
(768 window rows/day before indexes), with SQL json_each views. SQLite
3.45.1 locally expanded eight real receipts (49,253 bytes) into all 728 points;
this is not a live D1 query or billing result. A second cloud experiment
was blocked by the host; account readback confirmed no new database.
Preserve all metadata, source update time, run identity and hashes; use
a deterministic observation key and idempotent ingest. Measure D1 row
reads/writes and storage under a representative retention window before
choosing a production layout. Keep GitHub evidence recovery intact and
do not touch Repo Search's Turso or MotherDuck quotas.
