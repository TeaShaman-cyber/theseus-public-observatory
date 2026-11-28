import io
import unittest
import zipfile
from scripts.remote_zip import RangeFile, read_member


class RemoteZipTests(unittest.TestCase):
    def setUp(self):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("a.npz", b"science" * 100)
            z.writestr("unrelated.bin", bytes(range(256)) * 1000)
        self.raw = b.getvalue()

    def test_select_member(self):
        f = RangeFile(len(self.raw), lambda a, b: self.raw[a:b], budget=10000)
        self.assertEqual(read_member(f, "a.npz", 1000), b"science" * 100)

    def test_short_range_and_budget(self):
        f = RangeFile(len(self.raw), lambda a, b: b"", budget=100)
        with self.assertRaises(ValueError):
            f.read(10)
        f = RangeFile(len(self.raw), lambda a, b: self.raw[a:b], budget=5)
        with self.assertRaises(ValueError):
            f.read(6)

    def test_member_bounds(self):
        f = RangeFile(len(self.raw), lambda a, b: self.raw[a:b], budget=10000)
        with self.assertRaises(ValueError):
            read_member(f, "a.npz", 10)
