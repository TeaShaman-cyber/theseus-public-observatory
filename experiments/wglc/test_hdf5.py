"""Offline real-HDF5 integration tests; no public data in fixtures."""

import io
import unittest
from datetime import date

import h5py
import numpy as np

from scripts.wglc_read import DAYS, BlockFile, Selection, axes, select_density


class Hdf5Tests(unittest.TestCase):
    def test_real_chunked_hdf5_selection_and_schema_drift(self):
        q = Selection(date(2023, 2, 10), date(2023, 2, 12), 46, 48, 16, 18)
        t, y, x = axes(q)
        memory = io.BytesIO()
        with h5py.File(memory, "w") as h:
            for name, data, unit in (
                ("lat", np.arange(360) * 0.5 - 89.75, b"degrees_north"),
                ("lon", np.arange(720) * 0.5 - 179.75, b"degrees_east"),
                ("time", np.arange(DAYS), b"days since 2010-01-01 00:00:00"),
            ):
                d = h.create_dataset(name, data=data)
                d.attrs["units"] = np.bytes_(unit)
            h["time"].attrs["calendar"] = np.bytes_("standard")
            h["time"].attrs["coordinate_defines"] = np.bytes_("start")
            h.attrs["DOI"] = np.bytes_("https://doi.org/10.5281/zenodo.20277101")
            d = h.create_dataset(
                "density",
                shape=(DAYS, 360, 720),
                dtype="f4",
                chunks=(12, 60, 60),
                compression="gzip",
                fillvalue=-9999,
            )
            d.attrs["units"] = np.bytes_("strokes km-2 d-1")
            d.attrs["_Netcdf4Coordinates"] = [2, 1, 0]
            d.attrs["_FillValue"] = [-9999.0]
            d.attrs["missing_value"] = [-9999.0]
            d[t.start, y.start, x.start] = 0
            d[t.start, y.start, x.start + 1] = 0.125
            h.flush()
        raw = memory.getvalue()
        with BlockFile(len(raw), lambda a, b: raw[a:b]) as remote:
            with h5py.File(remote, "r") as h:
                rows = select_density(h, q)
        self.assertEqual(len(rows), 32)
        self.assertEqual([r["density"] for r in rows[:3]], [0, 0.125, None])
        self.assertEqual(rows[0]["latitude"], 46.25)
        self.assertEqual(rows[0]["longitude"], 16.25)
        self.assertEqual(rows[0]["interval_start"], "2023-02-10T00:00:00Z")
        with h5py.File(memory, "r+") as h:
            h["time"][0] = 1
            with self.assertRaisesRegex(ValueError, "axis drift"):
                select_density(h, q)
