"""Bounded read-only ZIP member retrieval; never download the whole archive."""

import io
import re
import zipfile
from urllib.request import HTTPRedirectHandler, Request, build_opener

SIERRA_URL = (
    "https://digibug.ugr.es/bitstream/handle/10481/71563/Npz.zip?sequence=1&isAllowed=y"
)
SIERRA_SIZE = 3579685616
SIERRA_MODIFIED = "Tue, 16 Nov 2021 18:51:19 GMT"
BUDGET = 64 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RangeFile(io.RawIOBase):
    def __init__(self, size, fetch, *, budget=BUDGET):
        super().__init__()
        self.size = size
        self.fetch = fetch
        self.budget = budget
        self.transferred = 0
        self.requests = 0
        self.pos = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        if whence not in (0, 1, 2):
            raise ValueError("invalid seek mode")
        position = (0, self.pos, self.size)[whence] + offset
        if position < 0:
            raise ValueError("negative seek")
        self.pos = position
        return position

    def read(self, size=-1):
        remaining = max(0, self.size - self.pos)
        n = remaining if size < 0 else min(size, remaining)
        if not n:
            return b""
        if n > self.budget - self.transferred or self.requests >= 64:
            raise ValueError("remote archive read budget exceeded")
        self.requests += 1
        self.transferred += n
        data = self.fetch(self.pos, self.pos + n)
        if len(data) != n:
            raise ValueError("short remote range")
        self.pos += n
        return data


def sierra_file():
    opener = build_opener(NoRedirect)

    def fetch(a, b):
        req = Request(
            SIERRA_URL,
            headers={
                "Range": f"bytes={a}-{b - 1}",
                "Accept-Encoding": "identity",
                "If-Unmodified-Since": SIERRA_MODIFIED,
            },
        )
        with opener.open(req, timeout=30) as response:
            if (
                response.status != 206
                or response.headers.get("Content-Range")
                != f"bytes {a}-{b - 1}/{SIERRA_SIZE}"
                or response.headers.get("Last-Modified") != SIERRA_MODIFIED
                or response.headers.get("Content-Encoding", "identity") != "identity"
                or response.headers.get("Content-Length") != str(b - a)
            ):
                raise ValueError("remote range identity mismatch")
            return response.read(b - a + 1)

    return RangeFile(SIERRA_SIZE, fetch)


def read_member(file, name, max_size):
    with zipfile.ZipFile(file) as z:
        matches = [info for info in z.infolist() if info.filename == name]
        if len(matches) != 1:
            raise ValueError("member absent or ambiguous")
        info = matches[0]
        if (
            info.is_dir()
            or not 0 < info.file_size <= max_size
            or info.compress_size > max_size
        ):
            raise ValueError("member size outside bound")
        if info.flag_bits & 1:
            raise ValueError("encrypted member unsupported")
        with z.open(info) as member:
            data = member.read(max_size + 1)
        if len(data) != info.file_size:
            raise ValueError("member size mismatch")
        return data


def sierra_member(month, sensor):
    if (
        not re.fullmatch(r"(13|14|15|16|17)(0[1-9]|1[0-2])", month)
        or not "1303" <= month <= "1702"
        or type(sensor) is not int
        or sensor not in (0, 1)
    ):
        raise ValueError("month/sensor outside archive")
    remote = sierra_file()
    name = f"Npz/SN_{month}_LO_6_1_{sensor}.npz"
    data = read_member(remote, name, 48 * 1024 * 1024)
    return data, {
        "member": name,
        "network_bytes": remote.transferred,
        "range_requests": remote.requests,
    }
