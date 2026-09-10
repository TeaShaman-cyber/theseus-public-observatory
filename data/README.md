# Data

`data/` contains public-source observations and rebuildable analytical projections.

## Authority

Canonical observation history:

```text
data/YYYY-MM-DD/public-status.jsonl
```

Each line is one collection run. Existing rows are append-only historical evidence.

Projections:

```text
data/latest/public-status.json
data/index/observatory.duckdb
```

`latest` must equal the final row of the most recent dated JSONL file. DuckDB is disposable and rebuildable.

## Schema Versions

### v0

Historical compact rows. They remain valid and are not rewritten.

### v1

New rows include:

```text
schema_version
collected_at
run
sources[]
```

Each v1 source includes:

```text
schema_version
id / label / url
adapter
ok
http_status / latency_ms / content_type
payload_sha256
transport.status
parser.status
semantic.status
summary / error
```

For v1, `ok` means semantic measurement availability.

Transport, parser/schema health, and semantic availability are separate so HTTP success cannot hide a dead sensor.

## Astronomy

USNO rows preserve public context for the configured observer:

- `usno_sun_moon`
- `usno_moon_phases`
- `usno_solar_eclipses`

The current observer is Kaliningrad (`54.7104, 20.4522`, UTC+2). `observer_local_date` is kept separately from the UTC collection timestamp.

Only public data belongs here.
