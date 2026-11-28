"""Bounded Cloudflare Radar schema pilot; no canonical data writes."""

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = "https://api.cloudflare.com/client/v4/radar/origins"
PROVIDERS = ("amazon", "google", "microsoft", "oracle")
METRICS = ("REQUESTS", "CONNECTION_FAILURES")
MAX_BYTES = 2 * 1024 * 1024


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def finite_number(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite number")
    return number


def strict_json(text):
    return json.loads(
        text,
        object_pairs_hook=unique_pairs,
        parse_constant=finite_number,
        parse_float=finite_number,
    )


def utc_time(value):
    if not isinstance(value, str):
        raise ValueError("invalid timestamp")
    stamp = datetime.fromisoformat(value)
    if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
        raise ValueError("expected UTC")
    return stamp


def inspect_payload(text, kind):
    envelope = strict_json(text)
    if not isinstance(envelope, dict) or envelope.get("success") is not True:
        raise ValueError("unsuccessful envelope")
    result = envelope["result"]
    if kind == "catalogue":
        origins = result["origins"]
        if not isinstance(origins, list) or not origins:
            raise ValueError("empty catalogue")
        counts = {}
        for origin in origins:
            slug = origin["slug"]
            regions = origin["regions"]
            if (
                slug not in PROVIDERS
                or slug in counts
                or not isinstance(regions, list)
                or not regions
            ):
                raise ValueError("unknown, duplicate or empty origin")
            names = [r["region"] for r in regions]
            if any(not isinstance(n, str) or not n.strip() for n in names) or len(
                set(names)
            ) != len(names):
                raise ValueError("invalid or duplicate region")
            counts[slug] = len(names)
        return {"providers": sorted(counts), "region_counts": counts}
    if kind != "series":
        raise ValueError("unknown payload type")
    meta = result["meta"]
    series = result["serie_0"]
    timestamps, values = series["timestamps"], series["values"]
    if (
        not isinstance(timestamps, list)
        or not isinstance(values, list)
        or not timestamps
        or len(timestamps) != len(values)
    ):
        raise ValueError("missing or misaligned samples")
    times = [utc_time(t) for t in timestamps]
    if any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError("unordered or duplicate timestamps")
    date_range = meta["dateRange"]
    if not isinstance(date_range, list) or len(date_range) != 1:
        raise ValueError("unexpected time window")
    start, end = (
        utc_time(date_range[0]["startTime"]),
        utc_time(date_range[0]["endTime"]),
    )
    if start >= end or times[0] < start or times[-1] > end:
        raise ValueError("samples outside window")
    for value in values:
        if (
            not isinstance(value, (str, int, float))
            or isinstance(value, bool)
            or finite_number(value) < 0
        ):
            raise ValueError("invalid sample")
    normalization = meta["normalization"]
    interval = meta["aggInterval"]
    if (
        not isinstance(normalization, str)
        or not normalization
        or interval not in ("FIFTEEN_MINUTES", "15m")
    ):
        raise ValueError("unexpected metadata")
    utc_time(meta["lastUpdated"])
    return {
        "samples": len(times),
        "normalization": normalization,
        "agg_interval": interval,
        "first": timestamps[0],
        "last": timestamps[-1],
        "last_updated": meta["lastUpdated"],
    }


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def open_response(req):
    return build_opener(NoRedirect()).open(req, timeout=25)


def request(kind, token, *, provider=None, metric=None):
    if kind == "catalogue":
        url = BASE + "?" + urlencode({"format": "JSON", "limit": 100})
    elif kind == "series" and provider in PROVIDERS and metric in METRICS:
        url = (
            BASE
            + "/timeseries?"
            + urlencode(
                {
                    "origin": provider.upper(),
                    "metric": metric,
                    "dateRange": "1d",
                    "aggInterval": "15m",
                    "format": "JSON",
                }
            )
        )
    else:
        raise ValueError("unapproved request")
    receipt = {"kind": kind, "url": url}
    try:
        req = Request(
            url,
            headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
        )
        with open_response(req) as response:
            receipt["http_status"] = response.status
            data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            return {**receipt, "status": "PAYLOAD_TOO_LARGE"}
        receipt["payload_sha256"] = hashlib.sha256(data).hexdigest()
        summary = inspect_payload(data.decode("utf-8"), kind)
        return {**receipt, "status": "SCHEMA_OK", "summary": summary}
    except HTTPError as exc:
        return {**receipt, "http_status": exc.code, "status": "HTTP_ERROR"}
    except (URLError, TimeoutError, OSError):
        return {**receipt, "status": "TRANSPORT_ERROR"}
    except (ValueError, KeyError, TypeError, OverflowError):
        return {**receipt, "status": "SCHEMA_REJECTED"}


def collect(token):
    if not token.strip():
        return {"status": "AUTH_REQUIRED", "observations": []}
    catalogue = request("catalogue", token)
    observations = [catalogue]
    if catalogue["status"] != "SCHEMA_OK":
        return {"status": "DEGRADED", "observations": observations}
    for provider in catalogue["summary"]["providers"]:
        for metric in METRICS:
            observations.append(
                request("series", token, provider=provider, metric=metric)
            )
    status = (
        "SCHEMA_OK"
        if all(r["status"] == "SCHEMA_OK" for r in observations)
        else "DEGRADED"
    )
    return {"status": status, "observations": observations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = collect(os.environ.get("CLOUDFLARE_RADAR_TOKEN", ""))
    result["collected_at"] = datetime.now(UTC).isoformat()
    result["run_id"] = os.environ.get("GITHUB_RUN_ID")
    result["head"] = os.environ.get("GITHUB_SHA")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if result["status"] == "SCHEMA_OK" else 1


if __name__ == "__main__":
    sys.exit(main())
