# Observatory research index

`observatory.duckdb` is a disposable research index rebuilt from canonical JSONL snapshots.

The database is **not** authoritative and is intentionally ignored by Git. Rebuild it with:

```bash
python scripts/build-observatory-index.py --repo-root . --output data/index/observatory.duckdb
```

Tables: `observations`, `provider_status`, `space_weather`, `astronomy`.
Views: `v_source_health`, `v_provider_events`, `v_space_weather`, `v_probe_timeline`.

Health fields are schema-aware:

- v0 rows keep legacy `collector_ok`; v1 rows leave that column null so the legacy meaning is not reused.
- v1 rows preserve `transport_status`, `parser_status`, and `semantic_status`.
- `usable` is a convenience projection: legacy `collector_ok` for v0, semantic availability for v1. It does not replace the versioned health dimensions.

The canonical v1 NOAA K-index receipt contains the latest measured Kp value. The current DuckDB `space_weather` table still indexes only Kp row-count metadata, so Kp-value analysis must read the canonical JSONL receipt until a typed Kp index field is added.
