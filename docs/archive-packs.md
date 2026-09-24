# Archive packs

Archive packs are durable, rebuildable inputs for long-window Observatory research.

Authority remains the append-only canonical history:

```text
data/YYYY-MM-DD/public-status.jsonl
```

A pack contains:

```text
raw-jsonl.tar.gz
observations.parquet
signals.parquet
schema.json
manifest.json
SHA256SUMS
```

The raw archive preserves canonical JSONL bytes. Parquet is a normalized analytical
projection. DuckDB is used as a query engine or disposable cache and is never archive
authority.

Build and verify:

```bash
python scripts/build_archive_pack.py build \
  --repo-root . \
  --period 2026-09 \
  --output-dir /tmp/observatory-data-2026-09

python scripts/build_archive_pack.py verify \
  --pack-dir /tmp/observatory-data-2026-09
```

The manifest records exact Git identity, input paths and hashes, schema coverage,
time coverage, row counts, and whether the requested calendar period is complete.
An incomplete canary must not be relabeled as a complete monthly archive.

Legacy observations stay legacy: if a v0 NOAA row recorded only response row count,
the analytical projection preserves that metadata and does not invent a historical
Kp measurement.

GitHub Actions artifacts are transient transport only. Durable published packs are
intended to be immutable GitHub Release assets.
