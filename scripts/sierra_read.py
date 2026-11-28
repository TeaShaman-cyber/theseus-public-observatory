"""Private research reader for Sierra Nevada fitted peaks, with exact UTC tags."""

import ast
import hashlib
import io
import math
import re
import struct
from datetime import datetime, timezone

if __package__:
    from .remote_zip import SIERRA_URL, sierra_member, read_member
else:
    from remote_zip import SIERRA_URL, sierra_member, read_member


def array(z, name, dtype, columns=None):
    # Only the small, explicitly selected numeric/string arrays are accepted.
    raw = read_member(z, name, 1024 * 1024)
    if raw[:8] != b"\x93NUMPY\x01\x00":
        raise ValueError("unsupported NPY version")
    n = struct.unpack_from("<H", raw, 8)[0]
    if not 1 <= n <= 4096 or len(raw) < 10 + n:
        raise ValueError("invalid NPY header size")
    h = ast.literal_eval(raw[10 : 10 + n].decode("ascii").strip())
    shape = h.get("shape")
    if (
        h.get("descr") != dtype
        or h.get("fortran_order") is not False
        or not isinstance(shape, tuple)
        or len(shape) != (2 if columns else 1)
        or type(shape[0]) is not int
        or not 0 < shape[0] <= 4464
        or (columns and shape[1] != columns)
    ):
        raise ValueError("unsupported array schema")
    data = raw[10 + n :]
    count = shape[0]
    if dtype == "<f8":
        width = columns or 1
        if len(data) != count * width * 8:
            raise ValueError("array byte count mismatch")
        return list(struct.iter_unpack("<" + "d" * width, data))
    if len(data) != count * 104:
        raise ValueError("time array byte count mismatch")
    return [
        data[i : i + 104].decode("utf-32-le").rstrip("\x00")
        for i in range(0, len(data), 104)
    ]


def parse_sierra(data, month):
    with io.BytesIO(data) as z:
        saturation = array(z, "arr_0.npy", "<f8")
        chi2 = array(z, "arr_6.npy", "<f8")
        peaks = array(z, "arr_8.npy", "<f8", 6)
        times = array(z, "arr_9.npy", "<U26")
    rows = []
    previous = None
    for t, s, c, p in zip(times, saturation, chi2, peaks, strict=True):
        if not re.fullmatch(r"20\d\d-\d\d-\d\d \d\d:\d\d:\d\d(?:\.\d{1,6})?", t):
            raise ValueError("unexpected source UTC time")
        tag = datetime.fromisoformat(t)
        if tag.strftime("%y%m") != month or (previous is not None and tag <= previous):
            raise ValueError("invalid or duplicate timestamp")
        previous = tag
        row = {"sample_at": tag.isoformat() + "Z"}
        for k, v in zip(
            (
                "saturation_pct",
                "fit_chi2",
                "peak1",
                "f1_hz",
                "peak2",
                "f2_hz",
                "peak3",
                "f3_hz",
            ),
            (*s, *c, *p),
            strict=True,
        ):
            row[k] = v if math.isfinite(v) else None
        rows.append(row)
    return rows


def read_sierra(start, end, sensor):
    if (
        start.utcoffset() != end.utcoffset()
        or start.utcoffset() != timezone.utc.utcoffset(start)
        or start >= end
    ):
        raise ValueError("ordered UTC bounds required")
    month = start.strftime("%y%m")
    if (end - datetime.resolution).strftime("%y%m") != month:
        raise ValueError("one month per read")
    data, receipt = sierra_member(month, sensor)
    rows = [
        r
        for r in parse_sierra(data, month)
        if start <= datetime.fromisoformat(r["sample_at"]) < end
    ]
    return {
        "source": "schumann-sierra-nevada",
        "route": "remote-zip-member",
        "url": SIERRA_URL,
        "sensor": sensor,
        "orientation": "NS" if sensor == 0 else "EW",
        "kind": "measured-spectrum fitted peak",
        "license": "CC BY-NC-ND 3.0",
        "time_semantics": "exact UTC start tag; nominal 10-minute support, no regular-grid assumption",
        "coverage": "unknown",
        "rows": rows,
        "missing": {
            k: sum(r[k] is None for r in rows) for k in ("f1_hz", "f2_hz", "f3_hz")
        },
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "member_sha256": hashlib.sha256(data).hexdigest(),
        **receipt,
    }
