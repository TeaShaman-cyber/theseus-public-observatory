import io
import struct
import unittest
import zipfile

from scripts.sierra_read import parse_sierra


def npy(descr, shape, data):
    header = repr(dict(descr=descr, fortran_order=False, shape=shape)).encode() + b"\n"
    return b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header)) + header + data


def fixture(times=("2017-02-01 00:02:00", "2017-02-01 00:11:59.961600")):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("arr_0.npy", npy("<f8", (2,), struct.pack("<2d", 0, 0.1)))
        z.writestr("arr_6.npy", npy("<f8", (2,), struct.pack("<2d", 0.01, 0.02)))
        z.writestr(
            "arr_8.npy",
            npy(
                "<f8",
                (2, 6),
                struct.pack(
                    "<12d", 0.2, 8, 0.1, 14, 0.05, 20, 0.3, 8.1, 0.1, 14, 0.05, 20
                ),
            ),
        )
        z.writestr(
            "arr_9.npy",
            npy(
                "<U26",
                (2,),
                b"".join(t.encode("utf-32-le").ljust(104, b"\x00") for t in times),
            ),
        )
    return b.getvalue()


class SierraTests(unittest.TestCase):
    def test_exact_tags_and_peak_mapping(self):
        rows = parse_sierra(fixture(), "1702")
        self.assertEqual(rows[0]["f1_hz"], 8)
        self.assertEqual(rows[0]["f2_hz"], 14)
        self.assertEqual(rows[1]["sample_at"], "2017-02-01T00:11:59.961600Z")
        self.assertEqual(rows[0]["fit_chi2"], 0.01)

    def test_duplicate_or_wrong_month_rejected(self):
        for ts in (
            ("2017-02-01 00:02:00",) * 2,
            ("2017-03-01 00:02:00", "2017-03-01 00:12:00"),
        ):
            with self.assertRaises(ValueError):
                parse_sierra(fixture(ts), "1702")
