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

## Sierra Nevada: range-based remote archive (#50)

University of Granada [dataset](https://hdl.handle.net/10481/71563),
CC BY-NC-ND 3.0. Method: Salinas et al., 2022,
https://doi.org/10.1016/j.cageo.2022.105148, section 7; original
Packaging.py at asalinas62/Sierra_Nevada_SR commit
499b41695aed7189a08e78eb76ec7598149ff1a1 confirms the positional arrays.
Internal noncommercial research only; do not publish adapted data.
Available monthly members March 2013–February 2017, each sensor
separate (0 NS, 1 EW). No new local archive or database.

```sh
python3 scripts/science_read.py schumann-sierra-nevada --sensor 0 \
  --start 2017-02-01T00:00:00Z --end 2017-02-02T00:00:00Z
```

The source ZIP is 3579685616 bytes; Last-Modified 2021-11-16 18:51:19
GMT. Require matching length, Last-Modified, HTTP206 and exact Content-Range
on every request; no redirects or full-body fallback. Python zipfile
reads the directory and one explicitly named member, checks ZIP CRC and
bounded size; 64 MiB response budget, at most 64 requests, 48 MiB member
ceiling. No strong provider ETag was supplied, so the size/date checks
are not a cryptographic version pin; record selected member SHA256.
The selected NPZ is decoded in memory. Only four small NPY arrays are
interpreted (saturation, chi-square, fitted peak amplitudes/frequencies,
time); strict dtype/shape/byte length, no pickle or execution.
Source code identifies three interleaved amplitude/frequency pairs.
Peak amplitudes are spectral amplitude values, not raw field magnitudes.
Do not compare them directly to NCK electric-field amplitudes.
Retain exact UTC start tags, including microseconds; nominal ten-minute
support, not a uniform exact grid. Nonfinite values become null, actual
coverage unknown until gap/support audit; fit/saturation indicators are
preserved, not interpreted as a passed quality filter. Only one calendar
month per call; sub-month selection requires reading that month's member.

Canary 2026-11-28: directory 98 entries, 8047 bytes transferred.
February 2017 sensor 0 member SHA256
26e9ee44b283089dd7d688ba3e8a8f5b2fb939bfbc94537333470b80ec0f2139,
16139826 decoded bytes, 14689647 HTTP range bytes in six requests.
1662 distinct records, first 2017-02-01T02:24:21.355000Z,
last 2017-02-26T21:36:46.437000Z; all three frequency columns finite,
not proof of month completeness. Common CLI day selection yielded 101
records; selection digest
b8df5d8e4bbf5848658524f7ffe96f669c6d35ea1f965b11508dd4374f03260d.
No whole-archive download or persistent data files. EW not yet tested
live. No inference or quality-filter threshold selected.

### Lightning control access feasibility

New WGLC 2026 release [Zenodo 20277101](https://zenodo.org/records/20277101)
covers 2010–2025, overlapping both SR products. Separate NetCDF4 files,
rather than the older 1.1 GB ZIP. The daily 0.5-degree grid file is
1963832881 bytes, publisher MD5 45d5d39387fe4a1748dac51a90f9fa4e.
Live Range 0–511 returned 206 and the HDF5 signature, no ETag or
Last-Modified. Only the signature/transport is verified, not any
lightning observations. Need a bounded HDF5/NetCDF subset reader
with explicit source version, coordinate/time axes, fill and chunk
semantics. No such library in the current pinned QA environment.
Do not install an unpinned dependency or download the whole object.
README and metadata disagree on CC BY-SA 4.0 versus CC BY 4.0;
resolve before redistribution. Daily density is not hourly lightning
and cannot explain individual ten-minute SR events without a
separately justified temporal model.

## WGLC daily lightning density (#53)

The versioned 2026 WGLC release (Kaplan and Lau,
https://doi.org/10.5281/zenodo.20277101) is now selectively readable via
HDF5 on a bounded HTTP range cache. The actual daily NetCDF has 5844 days
(2010-01-01 through 2025-12-31), 360 latitude and 720 longitude centers,
0.5 degree spacing. The README's time dimension count is stale.
Density units are strokes km^-2 day^-1; source counts are corrected for
detection efficiency. Only density is admitted, not power fields.
Zero is a valid value, -9999 is missing. Coordinates, dimension order,
units, time origin/calendar, chunk shape, fill and scaling metadata
are validated before reading the selected data. No interpolation.

Use a dedicated optional environment (pinned Python 3.12 test route):

```sh
python3 -m venv /tmp/wglc-venv
/tmp/wglc-venv/bin/pip install --only-binary=:all: -r experiments/wglc/requirements.txt
/tmp/wglc-venv/bin/python scripts/science_read.py wglc-daily-density \
  --start 2023-02-10T00:00:00Z --end 2023-02-13T00:00:00Z \
  --bbox 46 48 16 18
/tmp/wglc-venv/bin/python -m unittest discover -s experiments/wglc -v
```

Bounds: at most 31 complete UTC days; bounding box at most 10 degrees
per axis, non-wrapping, half-open cell-center selection. Split antimeridian
queries explicitly. HDF5 file-object access caches 256 KiB blocks in memory
with 32 MiB / 128 requests per query and fails closed on range mismatch.
The versioned URL, file size and internal DOI are checked; no strong ETag
or Last-Modified is available. Publisher MD5 recorded, NOT verified
over the full file. Slice SHA256 records the exact normalized result.
No disk mirror, new storage service or scheduler. Optional HDF5 packages
are pinned separately; no impact on existing readers. Dedicated CI runs
a real synthetic chunked HDF5 fixture, including missing/zero and axis drift.

Live checks 2026-11-28: three UTC days, 16 cells per day, 48 values each.
Hungary bbox [46,48,16,18]: all 48 valid zeros.
Equatorial Africa bbox [-5,-3,25,27]: 20 nonzero values, all 48 valid.
Each query transferred 1160753 bytes, five ranges, out of 1963832881.
Normalized slice hashes:
e96896ecdd4a50281785f2de57578b32bdc5361e372b00ee371ec894bdae7d8f
and 647045b4d653f315dbc8cd144b2c46c43625bd5f5f1a6b5e3cc1e74ae9ba4faf.
Common CLI reproduces the Hungary digest. These are feasibility samples,
not an estimate of global lightning or SR coupling. The daily resolution
and local box are insufficient to explain sub-hourly SR dynamics; define
global source-region aggregations and daily estimands separately.

License discrepancy remains (Zenodo CC BY 4.0 vs file README CC BY-SA
4.0). No raw or transformed dataset is republished here; internal research
only until resolved. Cite both methodology papers:
https://doi.org/10.5194/essd-13-3219-2021 and
https://doi.org/10.5194/essd-14-5665-2022.

### Missingness contract

For OMNI and GFZ, per-field missing counts include both explicit fill/null
values and absent expected intervals. A missing interval contributes once
to each selected field. No synthetic measurement row or zero is inserted.
Coverage is partial when an expected interval is absent. GFZ counts only
fully contained definitive three-hour slots. CLI regression tests cover
all six source routes with synthetic boundary responses, invalid options,
window validation, canonical selection digest and failure without fallback.
