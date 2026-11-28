import unittest
from datetime import date

from scripts.wglc_read import BlockFile, Selection, density_value, axes


class WglcTests(unittest.TestCase):
    def test_block_cache_and_budget(self):
        data = bytes(range(100))
        requests = []

        def fetch(a, b):
            requests.append((a, b))
            return data[a:b]

        with BlockFile(100, fetch, block_size=16, budget=32) as f:
            self.assertEqual(f.read(5), data[:5])
            f.seek(3)
            self.assertEqual(f.read(5), data[3:8])
            self.assertEqual(requests, [(0, 16)])
            f.seek(15)
            self.assertEqual(f.read(3), data[15:18])
            self.assertEqual(f.transferred, 32)
            f.seek(32)
            with self.assertRaises(ValueError):
                f.read(1)

    def test_short_block_rejected(self):
        with BlockFile(100, lambda a, b: b"", block_size=16, budget=32) as f:
            with self.assertRaises(ValueError):
                f.read(1)

    def test_selection_bounds_and_half_open_cell_centers(self):
        q = Selection(date(2023, 2, 10), date(2023, 2, 12), 46, 48, 16, 18)
        t, y, x = axes(q)
        self.assertEqual(
            (t.stop - t.start, y.stop - y.start, x.stop - x.start), (2, 4, 4)
        )
        for args in [
            (date(2023, 2, 10), date(2023, 4, 12), 46, 48, 16, 18),
            (date(2009, 1, 1), date(2010, 1, 1), 46, 48, 16, 18),
            (date(2023, 2, 10), date(2023, 2, 12), 46, 48, 179, -179),
            (date(2023, 2, 10), date(2023, 2, 12), 0, 30, 0, 1),
        ]:
            with self.assertRaises(ValueError):
                Selection(*args)

    def test_fill_zero_and_invalid_density(self):
        self.assertIsNone(density_value(-9999))
        self.assertEqual(density_value(0), 0)
        for v in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                density_value(v)
