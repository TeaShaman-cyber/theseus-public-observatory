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

Use a **new, nonexistent output directory** for each build. An existing directory
(even empty), file or symlink is rejected; the builder never clears previous
outputs. If writing fails after directory creation, treat that directory as an
incomplete attempt, not a pack; use a new path for retry.

The builder pins the Git HEAD and tree once. The requested month's working-tree
paths and bytes must match the regular files in that commit; missing, extra,
modified or symlinked inputs are rejected. All assets and input hashes use the
same captured Git blob bytes, so later working-tree changes cannot cause a
mismatch between raw evidence and its projections. Unrelated changes outside
the input set do not invalidate that data provenance.

The manifest records exact Git identity, input paths and hashes, schema coverage,
time coverage, row counts, and whether the requested calendar period is complete.
An incomplete canary must not be relabeled as a complete monthly archive.

Legacy observations stay legacy: if a v0 NOAA row recorded only response row count,
the analytical projection preserves that metadata and does not invent a historical
Kp measurement.

GitHub Actions artifacts are transient transport only. Durable published packs are
intended to be immutable GitHub Release assets.

## Integrity verification

The verifier checks the exact expected checksum entries and rejects duplicate
entries, missing or nonregular assets, manifest asset hash/size mismatches,
duplicate input paths, invalid calendar paths and unexpected/duplicate
tar members. It recomputes coverage metadata from the raw JSONL and rebuilds
both typed projections in an in-memory DuckDB connection with UTC timezone.
Schema and row multisets (including duplicate counts and null values) must
match the stored Parquet in both directions. Row counts alone are insufficient.
A v1 period can legitimately contain no Kp measurements; absence is preserved.
The legacy v0 Kp prohibition remains.

VERIFIED means internal consistency under the current v1 projection algorithm,
not proof of external authenticity. A separately trusted digest or comparison
to the canonical Git revision is still necessary to detect coordinated changes
to raw data, manifest and projections. The verifier and builder share the
projection rules; this is not an independent proof of those rules. Calendar
completeness means presence of all dates, not uninterrupted sensor coverage.
Verification rebuilds rows in memory; it is not a resource-hardened parser for
arbitrarily large untrusted packs. No published archives were rewritten.
