# Observatory research index

`observatory.duckdb` is a disposable research index rebuilt from canonical JSONL snapshots.

The database is **not** authoritative and is intentionally ignored by Git. Rebuild it with:

```bash
python scripts/build-observatory-index.py --repo-root . --output data/index/observatory.duckdb
```

Initial tables: `observations`, `provider_status`, `space_weather`.
Initial views: `v_source_health`, `v_provider_events`, `v_space_weather`, `v_probe_timeline`.

The current collector records NOAA scale values R/S/G. The planetary K-index snapshot currently records only row-count metadata, not individual Kp values; analyses must not treat Kp as available until collection is explicitly extended.
