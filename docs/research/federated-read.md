# Hybrid collection and federated scientific reads

Issue #44; existing #14, #35, #13 remain the owning research lines.
Keep scheduled exporters for ephemeral observations whose history
we need to preserve. For provider-owned long-lived scientific archives,
prefer bounded remote selection, not a local mirror.

| Source ID | Route | Temporal support | Fields |
|---|---|---|---|
| nasa-omni-hourly | NASA CDAWeb HAPI 2.0 | UTC hourly interval, source midpoint | bz (GSM nT), speed (km/s), dst (nT) |
| gfz-kp-ap | Existing private remote Parquet | UTC 3h interval, definitive only | kp, ap |
| Existing probes | Existing collectors and SQL projections | Existing contracts unchanged | Existing signals |

The new entrypoint is deliberately read-only, separate from the exporters.
It emits a common window/source/route/coverage/rows envelope, with per-field
missing counts, provenance and SHA-256 of the canonical serialized selection.
NASA also provides exact response-byte digest, URL, returned parameter
metadata and retrieval time. GFZ provides the admitted source/object hashes
(not a new whole-file hash verification on every range read) and source line.
No credentials or archive copies are needed for NASA. GFZ uses the existing
exe.dev proxy and signed DuckDB httpfs. Errors fail visibly; no silent fallback.

```sh
python3 scripts/science_read.py nasa-omni-hourly \
  --start 2024-05-10T00:00:00Z --end 2024-05-11T00:00:00Z \
  --fields bz speed dst
python3 scripts/science_read.py gfz-kp-ap \
  --start 2024-05-10T00:00:00Z --end 2024-05-11T00:00:00Z
```

Bounds: whole UTC hours, half-open, at most 31 days per request.
HAPI request selects only allowlisted parameters in provider order,
20s socket timeout, 2 MiB response acceptance limit, no redirects.
Header schema and application status validated even on HTTP 200.
Provider fill sentinels become null, not zero. Missing hours remain missing.
GFZ returns only fully contained definitive 3h intervals; no interpolation.
OMNI midpoint tags converted to their hourly support, preserving the
difference from GFZ start tags. Both are retrospective observations;
historical publication availability is not established. Dst may be
provisional/quick-look; no claim of definitive OMNI values.

Canary (2026-11-28): 2024-05-10 UTC, selected for known storm conditions,
not a statistical test. NASA 24/24 rows, no fill, 1656 response bytes,
SHA256 fad3b652e437e7fb41b2af4dfb37539fd2a7937ca8e2c5c0e2cdd0b2194767c7.
GFZ 8/8 definitive intervals. SQL interval containment joined 24 hourly
rows to 8 distinct Kp exposures. Do not count those 24 rows as independent
Kp measurements or treat this selected storm as causal evidence.
Exact GFZ network byte consumption not measured. No whole NASA archive
download, no new storage object, no recurring schedule.
OPeNDAP, additional HAPI datasets and a general SQL planner remain future
adapters, not claimed operational. Pin actual selected inputs for published
experiments because provider archives can be revised.

Source metadata: https://cdaweb.gsfc.nasa.gov/hapi/info?id=OMNI2_H0_MRG1HR
and https://omniweb.gsfc.nasa.gov/html/ow_data.html .
