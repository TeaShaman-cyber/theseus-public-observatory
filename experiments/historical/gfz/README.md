# GFZ historical Kp/ap snapshot

One bounded snapshot of the public bulk geomagnetic archive, retrieved
2026-11-28. The exact unmodified source bytes are preserved in deterministic
gzip; manifest binds compressed and uncompressed digests, counts and
interval endpoints. This is an independent historical research input, not
a new authority for the existing NOAA operational observations or a
recurring collector. Keep this one snapshot for reproducibility; do not
append a daily copy to Git.

Attribution: Geomagnetic Observatory Niemegk, GFZ Helmholtz Centre for
Geosciences. CC BY 4.0. Data DOI https://doi.org/10.5880/Kp.0001;
Matzka et al. (2021), https://doi.org/10.1029/2020SW002641.
Format: https://kp.gfz.de/app/format/Kp_ap.txt.
Source: https://kp.gfz.de/fileadmin/files_for_gfz_cms/Kp_ap_since_1932.txt.
The file contains Kp/ap only, not the separately licensed sunspot series.

## Build and query

From repository root, with the existing DuckDB QA environment:

```sh
python3 scripts/gfz_archive.py \
  --archive experiments/historical/gfz/Kp_ap_since_1932.txt.gz \
  --manifest experiments/historical/gfz/manifest.json \
  --output /tmp/gfz.parquet
```

```sql
select interval_start, interval_end, kp, ap, source_line, raw_sha256
from read_parquet('/tmp/gfz.parquet')
where status='definitive' and kp is not null
order by interval_start;
```

Half-open UTC intervals [start,end), 3h each; missing sentinel -1 becomes
NULL, not zero. Flag 1 is definitive; flag 0 is preliminary, retained
but excluded from definitive experiments. The entire archive has
277320 unique contiguous intervals from 1932-01-01 through 2026-11-27;
277104 definitive through 2026-10-31 inclusive, 216 preliminary,
zero missing pairs. GFZ API independently confirmed the same 32
definitive Kp and 32 ap values on September 21–24, 2026 (exact match).
Kp and ap are dependent by construction, not independent confirmations.
Publication availability of definitive values at historical event times
is unknown. Use them for retrospective interval analysis only, not
real-time forecasting or the operational as-of matcher.

This slice does not change the existing #11 research design, claim a
correlation, or set up a periodic archive update. Next independent study
needs another measured physical/biological series and a prespecified
join/lag/null model. The projection is disposable; use exact source
snapshot/manifest and script revision to rebuild it. Do not store
generated Parquet in Git or duplicate this archive in Supabase without
a demonstrated query/storage need.

## Shared remote analytical projection

The original compressed snapshot is pinned in Git; the analytical
Parquet is served separately in the existing Observatory Supabase
private Storage bucket, `observatory-archives`. See [storage.json](storage.json)
for the immutable-by-convention content-addressed object and digest.
No upsert was used; storage itself is not an immutable authority.

On governed exe.dev, use the attached credential-injecting proxy
without copying any keys. DuckDB 1.4.3 with its official signed httpfs
extension can read this object directly:

```python
import duckdb, json
from pathlib import Path

m = json.loads(Path("experiments/historical/gfz/storage.json").read_text())
url = ("https://supabase.int.exe.xyz/storage/v1/object/authenticated/"
       + m["bucket"] + "/" + m["object"])
with duckdb.connect() as con:
    con.execute("LOAD httpfs")
    print(con.execute(
        "SELECT status, count(*) FROM read_parquet(?) GROUP BY 1",
        [url],
    ).fetchall())
```

Verified HTTP Range returned 206 for bytes 0–3, whole-object readback
matched the SHA-256, and DuckDB remote read returned all 277320 rows
and 277104 definitive rows. HTTP range permits partial reads; exact
egress per query has not been measured. If httpfs is unavailable, use
a bounded temporary download with digest verification and delete it
after analysis. No long-lived local archive copy is required. Official
v1.4.3 httpfs was installed from the vendor compressed extension URL
after native install failed; signature verification remained enabled.
