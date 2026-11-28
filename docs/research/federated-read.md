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

## INTERMAGNET minute vectors and capture reconciliation (#47)

The common reader now accepts `intermagnet-minute`, with explicit station
`irt`, `kak`, `lzh`, or `had` and quality `definitive` (default)
or `best-avail`. No automatic substitution across quality classes or
stations. Maximum request duration 24h, same whole-hour CLI boundaries,
minute-level UTC support in the parser. XYZ and independent scalar F
are in nT. Header validation checks HAPI 3.1/status, station and quality
description, orientation, parameter shape/components/units/fill,
coordinates and minute-start semantics. Reject duplicate, unordered,
out-of-window and malformed rows. Missing entire minutes and channel
fill values remain missing, not zeros. A schema-valid all-fill response
has partial coverage, not a healthy observation.

```sh
python3 scripts/science_read.py intermagnet-minute --station lzh \
  --quality definitive --start 2017-09-08T01:00:00Z \
  --end 2017-09-08T02:00:00Z
```

Live canary from exe.dev, 2026-11-28: 2017-09-08 01:00–02:00 UTC,
60/60 minutes for each IRT, KAK and LZH, all four channels present.
Response sizes 5626, 5583, 5585 bytes respectively. This verifies
selective historical access; it does not establish continuous coverage
or physical coherence. Source conditions:
https://intermagnet.org/data_conditions.html .
Keep raw station data within permitted research scope; no bulk publication.

For the private operational buffer, use the existing authorized Supabase
CLI, explicit project reference, UTC six-hour boundaries and at most seven
days per query:

```sh
python3 scripts/magnetic_read.py --project-ref YOUR_PROJECT_REF \
  --start 2026-11-25T00:00:00Z --end 2026-11-29T00:00:00Z
```

This reads at most 200 attempts (rejects overflow), verifies each saved
payload hash in memory, validates received snapshots using the same
parser, and reports per-window/channel coverage and transitions between
successive schema-valid snapshots. Changed, unchanged, newly available and
subsequently missing channel values are counted separately. A failed or
malformed later attempt never erases the last valid snapshot. First and
latest valid timestamps, latest attempt status and union of ever-observed
channels are reported without exposing raw measurements. Only observed
window groups are returned, not a scheduler completeness audit. No
permanent local archive, new database table, credential or collector.

Live buffer check: eight attempts, four windows, three complete windows
with 360 minutes/1440 channels each, two valid snapshots per complete
window. All repeated channels identical (4320 comparisons total). The
fresh IRT window has two HTTP400 attempts and zero valid snapshots; do not
call this a recovered gap or a station outage. Actual 72h revisit still
needs time to occur. Synthetic fixtures demonstrate changed/recovered/lost
channels and preservation across errors; no natural revision has yet
been observed. Comparisons use parsed finite double values, not exact
decimal lexical identity; raw payload hashes preserve byte-level evidence.

## Schumann resonance measured frequencies (#50)

`schumann-nck-frequency` reads three measured modal peak-frequency
matrices (vertical electric component Ez) from the version-specific
Zenodo record [13220677](https://doi.org/10.5281/zenodo.13220677),
prepared by Tamás Bozóki, 2024-08-05, CC BY 4.0. Station Nagycenk,
Hungary (47.6 N, 16.7 E). Source metadata and exact per-file hashes
are pinned; reject changed bytes, malformed grids, nonfinite values
other than the published nan missing markers. No modeled frequency
file is admitted. Each selected mode requires a complete tiny 5662-byte
source file, read into memory, not a server-side temporal query.
The common CLI selects a subset of the decoded time tags.

```sh
python3 scripts/science_read.py schumann-nck-frequency \
  --start 2023-02-10T00:00:00Z --end 2023-02-21T00:00:00Z
```

Coverage is strictly 2023-02-10 through 20 inclusive, 48 UT labels per
day. Do not infer exact averaging support or publication time from the
half-hour labels: rows carry sample_at, not fabricated interval bounds.
No interpolation. The longer NCK files are monthly diurnal averages,
not continuous hourly measurements; separate product adapter required.
Amplitude units/support need separate validation before admission.
Live verification 2026-11-28: 528 tags, 525 finite values per mode,
three missing per mode, 16986 source bytes, selection SHA256
c868264941f6cfcedfa84ffa3e2156688903003262aeb096235a968f3c7aee86.
No data persisted on exe.dev or mirrored to Supabase. For a future
published experiment, retain pinned input identities and verify
lightning and environmental covariates before statistical inference.
