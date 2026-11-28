"""Bounded daily WGLC density selection over a versioned remote HDF5 file."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from urllib.request import Request, build_opener

if __package__:
    from .remote_zip import NoRedirect
else:
    from remote_zip import NoRedirect

URL = (
    "https://zenodo.org/api/records/20277101/files/wglc_timeseries_30m_daily.nc/content"
)
SIZE = 1963832881
START = date(2010, 1, 1)
END = date(2026, 1, 1)
DAYS = (END - START).days
BLOCK = 256 * 1024
BUDGET = 32 * 1024 * 1024


class BlockFile(io.RawIOBase):
    """Seekable bounded range cache; no disk or full-body fallback."""

    def __init__(self, size, fetch, *, block_size=BLOCK, budget=BUDGET):
        super().__init__()
        self.size = size
        self.fetch = fetch
        self.block_size = block_size
        self.budget = budget
        self.transferred = 0
        self.requests = 0
        self.pos = 0
        self.cache = {}

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        if whence not in (0, 1, 2):
            raise ValueError("invalid seek mode")
        p = (0, self.pos, self.size)[whence] + offset
        if p < 0:
            raise ValueError("negative seek")
        self.pos = p
        return p

    def read(self, size=-1):
        n = max(0, self.size - self.pos)
        if size >= 0:
            n = min(n, size)
        if n > self.budget:
            raise ValueError("read exceeds budget")
        end = self.pos + n
        out = bytearray()
        for a in (
            range(self.pos // self.block_size * self.block_size, end, self.block_size)
            if n
            else ()
        ):
            b = min(a + self.block_size, self.size)
            if a not in self.cache:
                if self.transferred + b - a > self.budget or self.requests >= 128:
                    raise ValueError("network budget exceeded")
                self.requests += 1
                self.transferred += b - a
                raw = self.fetch(a, b)
                if len(raw) != b - a:
                    raise ValueError("short remote block")
                self.cache[a] = raw
            out.extend(self.cache[a][max(0, self.pos - a) : min(end - a, b - a)])
        self.pos = end
        return bytes(out)

    def readinto(self, b):
        raw = self.read(len(b))
        b[: len(raw)] = raw
        return len(raw)


def remote_file():
    op = build_opener(NoRedirect)

    def fetch(a, b):
        req = Request(
            URL, headers={"Range": f"bytes={a}-{b - 1}", "Accept-Encoding": "identity"}
        )
        with op.open(req, timeout=20) as response:
            if (
                response.status != 206
                or response.headers.get("Content-Range") != f"bytes {a}-{b - 1}/{SIZE}"
                or response.headers.get("Content-Length") != str(b - a)
                or response.headers.get("Content-Encoding", "identity") != "identity"
            ):
                raise ValueError("unexpected range response")
            return response.read(b - a + 1)

    return BlockFile(SIZE, fetch)


@dataclass(frozen=True)
class Selection:
    start: date
    end: date
    south: float
    north: float
    west: float
    east: float

    def __post_init__(self):
        if (
            not START <= self.start < self.end <= END
            or not 1 <= (self.end - self.start).days <= 31
        ):
            raise ValueError("select at most 31 days within 2010–2025")
        if not (
            -90 <= self.south < self.north <= 90
            and -180 <= self.west < self.east <= 180
            and self.north - self.south <= 10
            and self.east - self.west <= 10
        ):
            raise ValueError(
                "non-wrapping bounding box up to 10 degrees per axis required"
            )
        axes(self)


def axis_slice(lo, hi, origin, count):
    ids = [i for i in range(count) if lo <= origin + i * 0.5 < hi]
    if not ids:
        raise ValueError("selection contains no cell centers")
    return slice(ids[0], ids[-1] + 1)


def axes(q):
    return (
        slice((q.start - START).days, (q.end - START).days),
        axis_slice(q.south, q.north, -89.75, 360),
        axis_slice(q.west, q.east, -179.75, 720),
    )


def density_value(v):
    v = float(v)
    if v == -9999:
        return None
    if not math.isfinite(v) or v < 0:
        raise ValueError("invalid lightning density")
    return v


def select_density(h, q):
    # Optional dependencies, imported only by the WGLC path.
    import numpy as np

    for name, expected, units in (
        ("lat", np.arange(360) * 0.5 - 89.75, b"degrees_north"),
        ("lon", np.arange(720) * 0.5 - 179.75, b"degrees_east"),
        ("time", np.arange(DAYS), b"days since 2010-01-01 00:00:00"),
    ):
        d = h[name]
        if (
            d.shape != expected.shape
            or d.attrs["units"] != units
            or not np.array_equal(d[:], expected)
        ):
            raise ValueError("coordinate axis drift")
    if (
        h["time"].attrs["calendar"] != b"standard"
        or h["time"].attrs["coordinate_defines"] != b"start"
    ):
        raise ValueError("time semantics drift")
    d = h["density"]
    if (
        d.shape != (DAYS, 360, 720)
        or d.dtype != np.dtype("float32")
        or d.chunks != (12, 60, 60)
        or d.attrs["units"] != b"strokes km-2 d-1"
        or list(d.attrs["_Netcdf4Coordinates"]) != [2, 1, 0]
        or list(d.attrs["_FillValue"]) != [-9999]
        or list(d.attrs["missing_value"]) != [-9999]
        or "scale_factor" in d.attrs
        or "add_offset" in d.attrs
        or h.attrs["DOI"] != b"https://doi.org/10.5281/zenodo.20277101"
    ):
        raise ValueError("WGLC schema drift")
    t, y, x = axes(q)
    data = d[t, y, x]
    rows = []
    for i, day in enumerate(range(t.start, t.stop)):
        start = START + timedelta(days=day)
        for j, lat in enumerate(range(y.start, y.stop)):
            for k, lon in enumerate(range(x.start, x.stop)):
                rows.append(
                    {
                        "interval_start": start.isoformat() + "T00:00:00Z",
                        "interval_end": (start + timedelta(days=1)).isoformat()
                        + "T00:00:00Z",
                        "latitude": -89.75 + lat * 0.5,
                        "longitude": -179.75 + lon * 0.5,
                        "density": density_value(data[i, j, k]),
                    }
                )
    return rows


def read_wglc(q):
    import h5py

    with remote_file() as remote:
        with h5py.File(remote, "r") as h:
            rows = select_density(h, q)
        network = remote.transferred
        requests = remote.requests
    missing = sum(r["density"] is None for r in rows)
    return {
        "source": "wglc-daily-density",
        "route": "remote-hdf5-range",
        "doi": "10.5281/zenodo.20277101",
        "url": URL,
        "source_bytes": SIZE,
        "publisher_md5": "45d5d39387fe4a1748dac51a90f9fa4e",
        "units": "strokes km-2 d-1",
        "spatial_support": "0.5 degree cell, center coordinates",
        "time_support": "UTC daily",
        "license": "metadata CC BY 4.0; README CC BY-SA 4.0; internal research only pending clarification",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "network_bytes": network,
        "range_requests": requests,
        "expected_rows": len(rows),
        "missing": {"density": missing},
        "coverage": "partial" if missing else "complete",
        "slice_sha256": hashlib.sha256(
            json.dumps(
                rows, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        ).hexdigest(),
        "rows": rows,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", type=date.fromisoformat, required=True)
    p.add_argument("--end", type=date.fromisoformat, required=True)
    for name in ("south", "north", "west", "east"):
        p.add_argument("--" + name, type=float, required=True)
    a = p.parse_args()
    print(json.dumps(read_wglc(Selection(**vars(a))), allow_nan=False))


if __name__ == "__main__":
    main()
