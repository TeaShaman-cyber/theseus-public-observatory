from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("build_archive_pack.py")
SPEC = importlib.util.spec_from_file_location("build_archive_pack", MODULE)
assert SPEC and SPEC.loader
archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(archive)


class ArchivePackSignals(unittest.TestCase):
    def test_legacy_kp_keeps_row_count_without_inventing_kp(self):
        rows = archive.signals(
            {"collected_at": "2026-09-01T00:00:00Z"},
            {"id": "noaa_planetary_k_index", "ok": True, "summary": {"rows": 58}},
            True,
            "data/2026-09-01/public-status.jsonl",
            1,
        )
        by_name = {row[4]: row for row in rows}
        self.assertIn("kp_row_count", by_name)
        self.assertNotIn("kp", by_name)
        self.assertEqual(by_name["kp_row_count"][5], 58.0)

    def test_v1_kp_preserves_value_and_measurement_time(self):
        rows = archive.signals(
            {"schema_version": 1, "collected_at": "2026-09-24T10:06:35Z"},
            {
                "schema_version": 1,
                "id": "noaa_planetary_k_index",
                "summary": {"latest": {"time_tag": "2026-09-24T06:00:00", "Kp": 3}},
            },
            True,
            "data/2026-09-24/public-status.jsonl",
            1,
        )
        kp = {row[4]: row for row in rows}["kp"]
        self.assertEqual(kp[1], "2026-09-24T06:00:00")
        self.assertEqual(kp[5], 3.0)

    def test_noaa_scales_use_measurement_timestamp(self):
        rows = archive.signals(
            {"collected_at": "2026-09-24T10:06:35Z"},
            {
                "id": "noaa_scales",
                "summary": {
                    "current": {
                        "DateStamp": "2026-09-24",
                        "TimeStamp": "10:04:00",
                        "R": {"Scale": "0"},
                        "S": {"Scale": "1"},
                        "G": {"Scale": "2"},
                    }
                },
            },
            True,
            "data/2026-09-24/public-status.jsonl",
            1,
        )
        scales = [row for row in rows if row[4].startswith("noaa_")]
        self.assertEqual(
            {row[4] for row in scales}, {"noaa_r_scale", "noaa_s_scale", "noaa_g_scale"}
        )
        self.assertTrue(all(row[1] == "2026-09-24T10:04:00Z" for row in scales))


if __name__ == "__main__":
    unittest.main()
