"""Bounded, read-only federation of scientific observations."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, build_opener

if __package__:
    from .wglc_read import Selection, read_wglc
    from .sierra_read import read_sierra
    from .schumann_read import read_nck
    from .magnetic_read import QUALITIES, STATIONS, read_magnetic
else:
    from wglc_read import Selection, read_wglc
    from sierra_read import read_sierra
    from schumann_read import read_nck
    from magnetic_read import QUALITIES, STATIONS, read_magnetic

HAPI = "https://cdaweb.gsfc.nasa.gov/hapi"
DATASET = "OMNI2_H0_MRG1HR"
FIELDS = {
    "bz": ("BZ_GSM1800", "double", "nT", "999.9"),
    "speed": ("V1800", "double", "Km/s", "9999.0"),
    "dst": ("DST1800", "integer", "nT", "99999"),
}
ROOT = Path(__file__).resolve().parents[1]
HOUR = timedelta(hours=1)
MAX_BYTES = 2 * 1024 * 1024


def iso(t):
    return t.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class Window:
    start: str
    end: str

    def __post_init__(self):
        for v in (self.start, self.end):
            t = datetime.fromisoformat(v)
            if (
                not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:00:00Z", v)
                or t.minute
                or t.second
                or t.microsecond
            ):
                raise ValueError("UTC whole-hour bounds required")
        if not timedelta(0) < self.stop - self.begin <= timedelta(days=31):
            raise ValueError("window must be positive and at most 31 days")

    @property
    def begin(self):
        return datetime.fromisoformat(self.start)

    @property
    def stop(self):
        return datetime.fromisoformat(self.end)


def selected(fields):
    if (
        not fields
        or len(set(fields)) != len(fields)
        or not set(fields) <= FIELDS.keys()
    ):
        raise ValueError("unique supported fields required")
    return [k for k in FIELDS if k in fields]


def omni_url(window, fields):
    return (
        HAPI
        + "/data?"
        + urlencode(
            {
                "id": DATASET,
                "parameters": ",".join(FIELDS[k][0] for k in selected(fields)),
                "time.min": window.start,
                "time.max": window.end,
                "format": "csv",
                "include": "header",
            }
        )
    )


def parse_omni(raw, window, fields):
    fields = selected(fields)
    lines = raw.decode("utf-8").splitlines()
    header_lines = []
    for line in lines:
        if not line.startswith("#"):
            break
        header_lines.append(line[1:])
    header = json.loads("\n".join(header_lines))
    if header.get("HAPI") != "2.0" or header.get("status", {}).get("code") != 1200:
        raise ValueError("unexpected HAPI status/version")
    params = header["parameters"]
    actual = [
        tuple(p.get(k) for k in ("name", "type", "units", "fill")) for p in params
    ]
    if actual != [("Time", "isotime", "UTC", None), *(FIELDS[k] for k in fields)]:
        raise ValueError("HAPI parameter schema drift")
    rows = []
    missing = dict.fromkeys(fields, 0)
    previous = None
    for row in csv.reader(lines[len(header_lines) :]):
        if len(row) != len(fields) + 1:
            raise ValueError("HAPI row width mismatch")
        t = datetime.fromisoformat(row[0])
        if not row[0].endswith("Z") or t.minute != 30 or t.second or t.microsecond:
            raise ValueError("unexpected OMNI time midpoint")
        start = t - HOUR / 2
        if not window.begin <= start < window.stop or (
            previous is not None and t <= previous
        ):
            raise ValueError("out of range or unordered/duplicate time")
        previous = t
        record = {"interval_start": iso(start), "interval_end": iso(start + HOUR)}
        for k, s in zip(fields, row[1:], strict=True):
            try:
                n = Decimal(s)
                if not n.is_finite():
                    raise ValueError("nonfinite HAPI value")
                if n == Decimal(FIELDS[k][3]):
                    record[k] = None
                    missing[k] += 1
                elif FIELDS[k][1] == "integer":
                    if n != n.to_integral_value():
                        raise ValueError("fractional integer")
                    record[k] = int(n)
                else:
                    value = float(n)
                    if not math.isfinite(value):
                        raise ValueError("nonfinite float")
                    record[k] = value
            except InvalidOperation as exc:
                raise ValueError("invalid numeric value") from exc
        rows.append(record)
    expected = (window.stop - window.begin) // HOUR
    missing = {field: count + expected - len(rows) for field, count in missing.items()}
    return {
        "rows": rows,
        "expected_rows": expected,
        "missing": missing,
        "coverage": "complete"
        if len(rows) == expected and not any(missing.values())
        else "partial",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "response_bytes": len(raw),
        "parameters": params,
    }


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_omni(window, fields):
    url = omni_url(window, fields)
    with build_opener(NoRedirect).open(url, timeout=20) as f:
        raw = f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("response exceeds bound")
    return {
        "source": "nasa-omni-hourly",
        "route": "remote-hapi",
        "url": url,
        "retrieved_at": iso(datetime.now(timezone.utc)),
        **parse_omni(raw, window, fields),
    }


def read_gfz(window):
    import duckdb

    m = json.loads((ROOT / "experiments/historical/gfz/storage.json").read_text())
    url = (
        "https://supabase.int.exe.xyz/storage/v1/object/authenticated/"
        + m["bucket"]
        + "/"
        + m["object"]
    )
    if (
        not re.fullmatch(r"[0-9a-f]{64}", m["projection_sha256"])
        or m["bucket"] != "observatory-archives"
        or m["object"] != "gfz/kp-ap/" + m["projection_sha256"] + ".parquet"
    ):
        raise ValueError("unexpected GFZ object identity")
    with duckdb.connect() as c:
        c.execute("LOAD httpfs")
        c.execute("set timezone='UTC'")
        rows = c.execute(
            """
            select interval_start::varchar, interval_end::varchar, kp, ap, source_line
            from read_parquet(?) where status='definitive' and
              interval_start >= ?::timestamptz and interval_end <= ?::timestamptz
            order by interval_start
        """,
            [url, window.start, window.end],
        ).fetchall()
    records = [
        {
            "interval_start": iso(datetime.fromisoformat(a)),
            "interval_end": iso(datetime.fromisoformat(b)),
            "kp": kp,
            "ap": ap,
            "source_line": line,
        }
        for a, b, kp, ap, line in rows
    ]
    return {
        "source": "gfz-kp-ap",
        "route": "remote-parquet",
        "projection_sha256": m["projection_sha256"],
        "raw_sha256": m["raw_sha256"],
        "retrieved_at": iso(datetime.now(timezone.utc)),
        **validate_gfz(records, window),
    }


def validate_gfz(records, window):
    expected = {
        iso(window.begin + HOUR * h)
        for h in range((window.stop - window.begin) // HOUR)
        if (window.begin + HOUR * h).hour % 3 == 0
        and window.begin + HOUR * (h + 3) <= window.stop
    }
    seen = set()
    missing = {"kp": 0, "ap": 0}
    for row in records:
        start = row["interval_start"]
        if (
            start not in expected
            or start in seen
            or row["interval_end"] != iso(datetime.fromisoformat(start) + HOUR * 3)
        ):
            raise ValueError("invalid or duplicate GFZ interval")
        seen.add(start)
        for field, limit in (("kp", 9), ("ap", 400)):
            value = row[field]
            if value is None:
                missing[field] += 1
            elif type(value) not in (int, float) or not 0 <= value <= limit:
                raise ValueError("invalid GFZ value")
    missing = {field: count + len(expected - seen) for field, count in missing.items()}
    return {
        "rows": records,
        "expected_rows": len(expected),
        "missing": missing,
        "coverage": "complete"
        if expected and seen == expected and not any(missing.values())
        else "partial",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "source",
        choices=[
            "nasa-omni-hourly",
            "gfz-kp-ap",
            "intermagnet-minute",
            "schumann-nck-frequency",
            "schumann-sierra-nevada",
            "wglc-daily-density",
        ],
    )
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--fields", nargs="+", choices=list(FIELDS))
    p.add_argument("--station", choices=STATIONS)
    p.add_argument("--quality", choices=QUALITIES)
    p.add_argument("--sensor", type=int, choices=(0, 1))
    p.add_argument(
        "--bbox", type=float, nargs=4, metavar=("SOUTH", "NORTH", "WEST", "EAST")
    )
    a = p.parse_args()
    if (a.source == "wglc-daily-density") != (a.bbox is not None):
        p.error("--bbox required only for WGLC")
    if a.source == "schumann-sierra-nevada" and a.sensor is None:
        p.error("--sensor required for Sierra Nevada")
    if a.source != "schumann-sierra-nevada" and a.sensor is not None:
        p.error("--sensor only for Sierra Nevada")
    w = Window(a.start, a.end)
    if a.source != "nasa-omni-hourly" and a.fields:
        p.error("--fields is available only for OMNI")
    if a.source == "intermagnet-minute":
        if not a.station:
            p.error("--station required")
        result = read_magnetic(w.begin, w.stop, a.station, a.quality or "definitive")
    else:
        if a.station or a.quality:
            p.error("station/quality only for INTERMAGNET")
        if a.source == "wglc-daily-density":
            if w.begin.hour or w.stop.hour:
                p.error("WGLC requires whole UTC days")
            result = read_wglc(Selection(w.begin.date(), w.stop.date(), *a.bbox))
        elif a.source == "schumann-sierra-nevada":
            result = read_sierra(w.begin, w.stop, a.sensor)
        elif a.source == "schumann-nck-frequency":
            result = read_nck(w.begin, w.stop)
        else:
            result = (
                read_omni(w, a.fields or list(FIELDS))
                if a.source == "nasa-omni-hourly"
                else read_gfz(w)
            )
    print(
        json.dumps(
            {
                "window": {"start": w.start, "end": w.end},
                "slice_sha256": hashlib.sha256(
                    json.dumps(
                        result["rows"],
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode()
                ).hexdigest(),
                **result,
            },
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
