"""Validate and project an exact GFZ Kp/ap bulk snapshot (retrospective only)."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import duckdb

START = datetime(1932, 1, 1, tzinfo=timezone.utc)
STEP = timedelta(hours=3)
SOURCE = "https://kp.gfz.de/fileadmin/files_for_gfz_cms/Kp_ap_since_1932.txt"
MAX_RAW = 30_000_000


def iso(t):
    return t.isoformat().replace("+00:00", "Z")


def parse(lines):
    expected = START
    count = 0
    for number, line in enumerate(lines, 1):
        if line.startswith("#"):
            if count:
                raise ValueError(f"unexpected header at line {number}")
            continue
        try:
            y, m, d, hour, mid, days, midpoint, kp, ap, flag = line.split()
            h = Decimal(hour)
            if h not in range(0, 24, 3):
                raise ValueError("invalid interval start")
            t = datetime(int(y), int(m), int(d), int(h), tzinfo=timezone.utc)
            offset = Decimal((t - START) // STEP) / 8
            if (
                t != expected
                or Decimal(mid) != h + Decimal("1.5")
                or Decimal(days) != offset
                or Decimal(midpoint) != offset + Decimal("0.0625")
            ):
                raise ValueError("grid discontinuity or inconsistent time fields")
            if flag not in ("0", "1"):
                raise ValueError("invalid definitive flag")
            k, a = Decimal(kp), int(ap)
            if k == -1 and a == -1:
                value, amplitude = None, None
            elif not k.is_finite() or not 0 <= k <= 9 or not 0 <= a <= 400:
                raise ValueError("invalid or inconsistent missing index")
            else:
                value, amplitude = float(k), a
        except (ValueError, InvalidOperation, OverflowError) as exc:
            raise ValueError(f"invalid GFZ record at line {number}: {exc}") from exc
        count += 1
        yield (
            iso(t),
            iso(t + STEP),
            value,
            amplitude,
            "definitive" if flag == "1" else "preliminary",
            number,
        )
        expected += STEP
    if not count:
        raise ValueError("empty GFZ archive")


def project(archive: Path, manifest: Path, output: Path):
    meta = json.loads(manifest.read_text())
    if (
        meta["schema_version"] != 1
        or meta["source_url"] != SOURCE
        or meta["license"] != "CC BY 4.0"
    ):
        raise ValueError("unexpected source or license")
    if archive.stat().st_size > MAX_RAW:
        raise ValueError("compressed snapshot too large")
    compressed = archive.read_bytes()
    if hashlib.sha256(compressed).hexdigest() != meta["gzip_sha256"]:
        raise ValueError("compressed snapshot digest mismatch")
    with gzip.open(archive, "rb") as f:
        raw = f.read(MAX_RAW + 1)
    if (
        len(raw) > MAX_RAW
        or len(raw) != meta["raw_bytes"]
        or hashlib.sha256(raw).hexdigest() != meta["raw_sha256"]
    ):
        raise ValueError("raw snapshot digest/size mismatch")
    if output.exists():
        raise FileExistsError(output)
    with tempfile.TemporaryDirectory(dir=output.parent) as td:
        path = Path(td) / "rows.csv"
        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ("interval_start", "interval_end", "kp", "ap", "status", "source_line")
            )
            writer.writerows(parse(raw.decode("ascii").splitlines()))
        stage = Path(td) / "projection.parquet"
        with duckdb.connect() as con:
            con.execute("set timezone='UTC'")
            con.execute(
                """
                create table gfz as select *, ?::varchar as raw_sha256
                from read_csv(?, header=true, columns={
                'interval_start':'TIMESTAMPTZ','interval_end':'TIMESTAMPTZ',
                'kp':'DOUBLE','ap':'INTEGER','status':'VARCHAR','source_line':'BIGINT'})
            """,
                [meta["raw_sha256"], str(path)],
            )
            stats = con.execute("""
                select count(*), count(*) filter (where status='definitive'),
                count(*) filter (where kp is null), min(interval_start)::varchar,
                max(interval_end)::varchar,
                max(interval_end) filter (where status='definitive')::varchar
                from gfz
            """).fetchone()
            if stats[:3] != (
                meta["rows"],
                meta["definitive_rows"],
                meta["missing_rows"],
            ):
                raise ValueError("manifest counts differ")
            boundaries = tuple(
                iso(datetime.fromisoformat(t)) if t is not None else None
                for t in stats[3:]
            )
            if boundaries != tuple(
                meta[k]
                for k in (
                    "interval_start",
                    "interval_end_exclusive",
                    "definitive_end_exclusive",
                )
            ):
                raise ValueError("manifest interval boundary mismatch")
            con.execute(
                "copy (select * from gfz order by interval_start) to ? (format parquet, compression zstd)",
                [str(stage)],
            )
        # Atomic no-clobber publication on the same filesystem.
        output.hardlink_to(stage)
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(project(args.archive, args.manifest, args.output)))


if __name__ == "__main__":
    main()
