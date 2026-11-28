"""Read the versioned Nagycenk measured frequency matrices without mirroring."""

from datetime import datetime, timedelta, timezone
import hashlib
import math
from urllib.request import build_opener, HTTPRedirectHandler

UTC = timezone.utc
START = datetime(2023, 2, 10, tzinfo=UTC)
END = datetime(2023, 2, 21, tzinfo=UTC)
STEP = timedelta(minutes=30)
BASE = "https://zenodo.org/api/records/13220677/files/"
DIGESTS = {
    1: "62b793fc25918a7f532e93c037cacc74446fac556cabecfb139f5bac1b5a6db6",
    2: "20569ad6764b8318c7fc52e787e5e76d07c2a1223f6c91a72debf4d9ee76d2c8",
    3: "b38c4174240ef9c4cf1a9d9a95bde25f46fec8173ee8bd7529c46a9558884c5e",
}


def iso(t):
    return t.isoformat().replace("+00:00", "Z")


def parse_matrix(raw):
    lines = [
        line.removesuffix("\t").split("\t") for line in raw.decode("ascii").splitlines()
    ]
    dates = [START + timedelta(days=i) for i in range(11)]
    if len(lines) != 49 or lines[0] != [
        "Time [UT]",
        *[d.strftime("%Y/%m/%d") for d in dates],
    ]:
        raise ValueError("unexpected NCK date/time matrix")
    result = {}
    for i, row in enumerate(lines[1:]):
        if len(row) != 12 or float(row[0]) != i / 2:
            raise ValueError("invalid half-hour grid")
        for day, token in zip(dates, row[1:], strict=True):
            v = float(token)
            if token.lower() == "nan":
                v = None
            elif not math.isfinite(v) or not 0 < v < 100:
                raise ValueError("invalid measured frequency")
            result[iso(day + i * STEP)] = v
    return result


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_nck(start, end, modes=(1, 2, 3)):
    if not START <= start < end <= END or any(
        t.utcoffset() != timedelta(0) or t.minute % 30 or t.second or t.microsecond
        for t in (start, end)
    ):
        raise ValueError("select half-hour UTC tags within 2023-02-10 through 20")
    if (
        not modes
        or len(set(modes)) != len(modes)
        or any(type(m) is not int or m not in DIGESTS for m in modes)
    ):
        raise ValueError("select unique measured modes 1–3")
    data = {}
    assets = []
    for m in sorted(modes):
        url = BASE + f"NCK_f{m}_2023_02_10-20.txt/content"
        with build_opener(NoRedirect).open(url, timeout=15) as f:
            raw = f.read(5663)
        digest = hashlib.sha256(raw).hexdigest()
        if len(raw) != 5662 or digest != DIGESTS[m]:
            raise ValueError("NCK asset identity mismatch")
        data[m] = parse_matrix(raw)
        assets.append({"mode": m, "url": url, "sha256": digest, "bytes": len(raw)})
    rows = []
    t = start
    while t < end:
        tag = iso(t)
        rows.append(
            {"sample_at": tag, **{f"f{m}_hz": data[m][tag] for m in sorted(modes)}}
        )
        t += STEP
    missing = {f"f{m}_hz": sum(r[f"f{m}_hz"] is None for r in rows) for m in modes}
    return {
        "source": "schumann-nck-frequency",
        "route": "remote-versioned-text",
        "doi": "10.5281/zenodo.13220677",
        "license": "CC BY 4.0",
        "station": "NCK",
        "component": "Ez",
        "kind": "measured",
        "coordinates": {"latitude": 47.6, "longitude": 16.7},
        "time_semantics": "UTC half-hour labels; averaging support not established",
        "retrieved_at": iso(datetime.now(UTC)),
        "assets": assets,
        "rows": rows,
        "expected_rows": len(rows),
        "missing": missing,
        "coverage": "partial" if any(missing.values()) else "complete",
    }
