"""Strict minute-scale INTERMAGNET reads and private capture reconciliation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, build_opener

BASE = "https://imag-data.bgs.ac.uk/GIN_V1/hapi"
STATIONS = ("irt", "kak", "lzh", "had")
QUALITIES = ("definitive", "best-avail")
FIELDS = ("x", "y", "z", "f")
MINUTE = timedelta(minutes=1)
MAX_BODY = 256 * 1024
MAX_ATTEMPTS = 200


def iso(t):
    return t.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_window(start, end, days=1):
    if any(
        t.utcoffset() != timedelta(0) or t.second or t.microsecond for t in (start, end)
    ):
        raise ValueError("UTC minute-aligned bounds required")
    if not timedelta(0) < end - start <= timedelta(days=days):
        raise ValueError("invalid window duration")


def parse_magnetic(body, station, quality, start, end):
    validate_window(start, end)
    if station not in STATIONS or quality not in QUALITIES:
        raise ValueError("unknown station or quality")
    if not isinstance(body, str) or not 0 < len(body.encode()) <= MAX_BODY:
        raise ValueError("invalid body size")
    lines = body.splitlines()
    header = []
    for line in lines:
        if not line.startswith("#"):
            break
        header.append(line[1:])
    h = json.loads("\n".join(header))
    if (
        not isinstance(h, dict)
        or h.get("HAPI") != "3.1"
        or h.get("status", {}).get("code") != 1200
    ):
        raise ValueError("invalid HAPI header/status")
    description = h.get("description", "")
    if (
        h.get("format") != "csv"
        or h.get("cadence") != "PT1M"
        or h.get("timeStampLocation") != "begin"
        or not description.lower().startswith(
            quality + " minute data in xyzf orientation"
        )
        or f"({station.upper()})" not in description
    ):
        raise ValueError("station, quality, or time semantics drift")
    parameters = h.get("parameters", [])
    if len(parameters) != 3:
        raise ValueError("unexpected parameter count")
    time, vec, magnitude = parameters
    expected = (
        (time, {"name": "Time", "type": "isotime", "units": "UTC", "fill": None}),
        (
            vec,
            {
                "name": "Field_Vector",
                "type": "double",
                "units": ["nT"] * 3,
                "size": [3],
                "vectorComponents": ["x", "y", "z"],
                "coordinateSystemName": "Cartesian",
                "fill": "99999.0",
            },
        ),
        (
            magnitude,
            {
                "name": "Field_Magnitude",
                "type": "double",
                "units": "nT",
                "vectorComponents": "r",
                "fill": "99999.0",
            },
        ),
    )
    if any(
        not isinstance(p, dict) or any(k not in p or p[k] != v for k, v in spec.items())
        for p, spec in expected
    ):
        raise ValueError("magnetic parameter schema drift")
    coordinates = {k: h.get("x_" + k) for k in ("latitude", "longitude", "elevation")}
    if any(
        type(v) not in (int, float) or not math.isfinite(v)
        for v in coordinates.values()
    ):
        raise ValueError("missing coordinates")
    if (
        not -90 <= coordinates["latitude"] <= 90
        or not -180 <= coordinates["longitude"] <= 360
    ):
        raise ValueError("invalid coordinates")
    rows = []
    previous = None
    for row in csv.reader(lines[len(header) :], strict=True):
        if len(row) != 5 or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::00(?:\.0+)?)?Z", row[0]
        ):
            raise ValueError("invalid row width or minute tag")
        t = datetime.fromisoformat(row[0])
        if not start <= t < end or (previous is not None and t <= previous):
            raise ValueError("out of range or unordered/duplicate minute")
        previous = t
        values = {}
        for field, value in zip(FIELDS, row[1:], strict=True):
            try:
                number = Decimal(value)
                if not number.is_finite():
                    raise ValueError("nonfinite field")
                n = float(number)
                if not math.isfinite(n):
                    raise ValueError("nonfinite field")
                values[field] = None if number == Decimal("99999.0") else n
            except InvalidOperation as exc:
                raise ValueError("invalid numeric field") from exc
        rows.append(
            {"interval_start": iso(t), "interval_end": iso(t + MINUTE), **values}
        )
    expected_rows = (end - start) // MINUTE
    missing = {
        field: expected_rows - sum(r[field] is not None for r in rows)
        for field in FIELDS
    }
    return {
        "rows": rows,
        "expected_rows": expected_rows,
        "missing": missing,
        "coverage": "complete" if not any(missing.values()) else "partial",
        "station": station,
        "quality": quality,
        "coordinates": coordinates,
        "units": "nT",
        "source_time_semantics": "begin of UTC minute",
        "sha256": hashlib.sha256(body.encode()).hexdigest(),
    }


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_magnetic(start, end, station, quality):
    validate_window(start, end)
    if station not in STATIONS or quality not in QUALITIES:
        raise ValueError("unknown station or quality")
    url = (
        BASE
        + "/data?"
        + urlencode(
            {
                "id": f"{station}/{quality}/PT1M/xyzf",
                "time.min": iso(start),
                "time.max": iso(end),
                "format": "csv",
                "include": "header",
            }
        )
    )
    with build_opener(NoRedirect).open(url, timeout=20) as response:
        raw = response.read(MAX_BODY + 1)
    if len(raw) > MAX_BODY:
        raise ValueError("response exceeds bound")
    return {
        "source": "intermagnet-minute",
        "route": "remote-hapi",
        "url": url,
        "retrieved_at": iso(datetime.now(timezone.utc)),
        "response_bytes": len(raw),
        **parse_magnetic(raw.decode("utf-8"), station, quality, start, end),
    }


def channels(rows):
    return {
        (r["interval_start"], f): r[f] for r in rows for f in FIELDS if r[f] is not None
    }


def reconcile(attempts):
    grouped = defaultdict(list)
    for a in attempts:
        body = a.get("body")
        digest = a.get("payload_sha256")
        if (body is None) != (digest is None) or (
            body is not None and hashlib.sha256(body.encode()).hexdigest() != digest
        ):
            raise ValueError("capture digest mismatch")
        grouped[(a["station"], datetime.fromisoformat(a["window_start"]))].append(a)
    summaries = []
    for (station, start), group in sorted(grouped.items()):
        end = start + timedelta(hours=6)
        group.sort(key=lambda a: datetime.fromisoformat(a["captured_at"]))
        seen = set()
        previous = None
        previous_at = None
        all_channels = set()
        snapshots = 0
        transitions = []
        audit = []
        latest_coverage = None
        latest_missing = None
        first_valid = None
        for a in group:
            captured = datetime.fromisoformat(a["captured_at"])
            if captured in seen or captured < end:
                raise ValueError("invalid attempt chronology")
            seen.add(captured)
            item = {
                k: a.get(k)
                for k in ("captured_at", "outcome", "http_status", "payload_sha256")
            }
            if a["outcome"] == "received_unvalidated" and a["http_status"] == 200:
                try:
                    parsed = parse_magnetic(
                        a["body"], station, "best-avail", start, end
                    )
                except (ValueError, TypeError, KeyError, AttributeError, csv.Error):
                    item["validation"] = "invalid_payload"
                else:
                    item["validation"] = parsed["coverage"]
                    item["missing"] = parsed["missing"]
                    current = channels(parsed["rows"])
                    if previous is not None:
                        common = previous.keys() & current.keys()
                        transitions.append(
                            {
                                "from": previous_at,
                                "to": iso(captured),
                                "changed": sum(
                                    previous[k] != current[k] for k in common
                                ),
                                "unchanged": sum(
                                    previous[k] == current[k] for k in common
                                ),
                                "recovered": len(current.keys() - previous.keys()),
                                "lost": len(previous.keys() - current.keys()),
                            }
                        )
                    all_channels.update(current)
                    previous = current
                    previous_at = iso(captured)
                    snapshots += 1
                    first_valid = first_valid or previous_at
                    latest_coverage = parsed["coverage"]
                    latest_missing = parsed["missing"]
            else:
                item["validation"] = "not_available"
            audit.append(item)
        summaries.append(
            {
                "station": station,
                "window_start": iso(start),
                "window_end": iso(end),
                "attempt_count": len(group),
                "latest_attempt_outcome": group[-1]["outcome"],
                "latest_attempt_validation": audit[-1]["validation"],
                "valid_snapshots": snapshots,
                "first_valid_at": first_valid,
                "latest_valid_at": previous_at,
                "latest_valid_coverage": latest_coverage,
                "latest_valid_missing": latest_missing,
                "expected_channels": 360 * 4,
                "ever_observed_channels": len(all_channels),
                "transitions": transitions,
                "attempts": audit,
            }
        )
    return summaries


def read_buffer(project, start, end):
    validate_window(start, end, days=7)
    if not re.fullmatch(r"[a-z0-9]{20}", project):
        raise ValueError("explicit project ref required")
    if any(t.minute or t.hour % 6 for t in (start, end)):
        raise ValueError("capture windows must be aligned to six hours")
    # Bounds are canonical UTC datetime values, not arbitrary SQL input.
    query = f"""select a.station,a.window_start,a.captured_at,a.http_status,a.outcome,
              a.payload_sha256,p.body from observatory_sync.magnetic_attempts a
              left join observatory_sync.magnetic_payloads p on p.sha256=a.payload_sha256
              where a.window_start >= '{iso(start)}'::timestamptz
              and a.window_start < '{iso(end)}'::timestamptz
              order by a.station,a.window_start,a.captured_at limit {MAX_ATTEMPTS + 1}"""
    completed = subprocess.run(
        [
            "supabase",
            "db",
            "query",
            f"--remote={project}",
            "--read-only",
            "--output-format",
            "json",
            query,
        ],
        capture_output=True,
        timeout=40,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError("read-only Supabase capture query failed")
    attempts = json.loads(completed.stdout)
    if not isinstance(attempts, list) or len(attempts) > MAX_ATTEMPTS:
        raise ValueError("attempt bound exceeded or unexpected response")
    return {
        "source": "private-magnetic-buffer",
        "window_start": iso(start),
        "window_end": iso(end),
        "retrieved_at": iso(datetime.now(timezone.utc)),
        "attempt_count": len(attempts),
        "windows": reconcile(attempts),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-ref", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    a = parser.parse_args()
    print(
        json.dumps(
            read_buffer(
                a.project_ref,
                datetime.fromisoformat(a.start),
                datetime.fromisoformat(a.end),
            ),
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
