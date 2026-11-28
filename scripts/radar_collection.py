"""Collect Cloudflare Radar window-relative measurements with v1 receipts."""

import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from urllib.parse import urlencode

from scripts import radar_pilot as radar

ATTRIBUTION = "Cloudflare Radar"
LICENSE = "CC BY-NC 4.0"
INTERVAL_SECONDS = 900


def series_summary(text):
    summary = radar.inspect_payload(text, "series")
    result = radar.strict_json(text)["result"]
    meta = result["meta"]
    window = meta["dateRange"][0]
    start = radar.utc_time(window["startTime"])
    end = radar.utc_time(window["endTime"])
    if summary["normalization"] != "MIN0_MAX":
        raise ValueError("unexpected normalization")
    if (end - start).total_seconds() != 86400:
        raise ValueError("unexpected window duration")
    if start.timestamp() % INTERVAL_SECONDS or end.timestamp() % INTERVAL_SECONDS:
        raise ValueError("unaligned window")
    units = meta.get("units")
    if units != [{"name": "*", "value": "requests"}]:
        raise ValueError("unexpected source unit")
    series = result["serie_0"]
    points = []
    for timestamp, raw in zip(series["timestamps"], series["values"], strict=True):
        stamp = radar.utc_time(timestamp)
        value = radar.finite_number(raw)
        if stamp.timestamp() % INTERVAL_SECONDS or not 0 <= value <= 1:
            raise ValueError("unaligned or invalid normalized sample")
        points.append({"measured_at": timestamp, "value": value})
    expected = int((end - start).total_seconds() / INTERVAL_SECONDS) + 1
    return {
        **summary,
        "window_start": window["startTime"],
        "window_end": window["endTime"],
        "expected_samples": expected,
        "coverage": "complete" if len(points) == expected else "partial",
        "source_unit": "requests",
        "value_unit": "window_max_fraction",
        "attribution": ATTRIBUTION,
        "license": LICENSE,
        "points": points,
    }


def source_receipt(provider, metric, token):
    if provider not in radar.PROVIDERS or metric not in radar.METRICS:
        raise ValueError("unsupported role")
    url = (
        radar.BASE
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
    started = time.monotonic()
    receipt = {
        "schema_version": 1,
        "id": f"radar_{provider}_{metric.lower()}",
        "label": f"Cloudflare Radar {provider} {metric}",
        "adapter": "cloudflare-radar-origins-v1",
        "url": url,
        "ok": False,
        "http_status": None,
        "content_type": None,
        "payload_sha256": None,
        "transport": {"status": "fetch-error"},
        "parser": {"status": "not-attempted"},
        "semantic": {"status": "unavailable"},
    }
    try:
        if not token.strip():
            receipt["error"] = "auth-required"
            return receipt
        req = radar.Request(
            url,
            headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
        )
        with radar.open_response(req) as response:
            receipt["http_status"] = response.status
            headers = getattr(response, "headers", {})
            receipt["content_type"] = headers.get("content-type")
            data = response.read(radar.MAX_BYTES + 1)
        if receipt["http_status"] != 200:
            receipt["transport"]["status"] = "http-error"
            receipt["error"] = "http-error"
            return receipt
        receipt["transport"]["status"] = "ok"
        if len(data) > radar.MAX_BYTES:
            receipt["parser"]["status"] = "schema-mismatch"
            receipt["error"] = "payload-too-large"
            return receipt
        receipt["payload_sha256"] = hashlib.sha256(data).hexdigest()
        try:
            text = data.decode("utf-8")
            radar.strict_json(text)
        except (ValueError, OverflowError):
            receipt["parser"]["status"] = "invalid-json"
            receipt["error"] = "invalid-json"
            return receipt
        try:
            summary = series_summary(text)
        except (ValueError, KeyError, TypeError, OverflowError):
            receipt["parser"]["status"] = "schema-mismatch"
            receipt["error"] = "schema-mismatch"
            return receipt
        receipt.update(
            ok=True,
            parser={"status": "ok"},
            semantic={"status": "available"},
            summary={**summary, "provider": provider, "metric": metric},
        )
        return receipt
    except radar.HTTPError as exc:
        receipt["http_status"] = exc.code
        receipt["transport"]["status"] = "http-error"
        receipt["error"] = "http-error"
        return receipt
    except (radar.URLError, TimeoutError, OSError) as exc:
        timeout = isinstance(exc, TimeoutError) or isinstance(
            getattr(exc, "reason", None), TimeoutError
        )
        receipt["transport"]["status"] = "timeout" if timeout else "fetch-error"
        receipt["error"] = receipt["transport"]["status"]
        return receipt
    finally:
        receipt["latency_ms"] = round((time.monotonic() - started) * 1000)
        receipt["observed_at"] = datetime.now(UTC).isoformat()


def collect_sources(token):
    roles = [(p, m) for p in radar.PROVIDERS for m in radar.METRICS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(lambda role: source_receipt(*role, token), roles))


if __name__ == "__main__":
    print(
        json.dumps(
            collect_sources(os.environ.get("CLOUDFLARE_RADAR_TOKEN", "")),
            allow_nan=False,
        )
    )
