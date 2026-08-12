import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build-observatory-index.py"


class IndexTests(unittest.TestCase):
    def test_rebuild_is_deterministic_and_preserves_collector_source_distinction(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            day = root / "data" / "2026-07-24"
            day.mkdir(parents=True)
            rows = [
                {
                    "collected_at": "2026-07-24T10:00:00Z",
                    "sources": [
                        {
                            "id": "github_status",
                            "label": "GitHub",
                            "url": "https://example.test",
                            "ok": True,
                            "http_status": 200,
                            "latency_ms": 100,
                            "summary": {"indicator": "none", "description": "All good"},
                        },
                        {
                            "id": "noaa_scales",
                            "label": "NOAA Scales",
                            "url": "https://example.test/noaa",
                            "ok": True,
                            "http_status": 200,
                            "latency_ms": 80,
                            "summary": {
                                "current": {
                                    "R": {"Scale": "0"},
                                    "S": {"Scale": "0"},
                                    "G": {"Scale": "1"},
                                }
                            },
                        },
                    ],
                },
                {
                    "collected_at": "2026-07-24T11:00:00Z",
                    "sources": [
                        {
                            "id": "github_status",
                            "label": "GitHub",
                            "url": "https://example.test",
                            "ok": False,
                            "http_status": 200,
                            "latency_ms": 150,
                            "error": "invalid-json",
                        }
                    ],
                },
            ]
            p = day / "public-status.jsonl"
            p.write_text(
                "\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8"
            )
            db = root / "data" / "index" / "observatory.duckdb"
            for _ in range(2):
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--repo-root",
                        str(root),
                        "--output",
                        str(db),
                    ],
                    check=True,
                )
            con = duckdb.connect(str(db), read_only=True)
            self.assertEqual(
                con.execute("select count(*) from observations").fetchone()[0], 3
            )
            self.assertEqual(
                con.execute("select count(*) from provider_status").fetchone()[0], 2
            )
            self.assertEqual(
                con.execute("select count(*) from space_weather").fetchone()[0], 1
            )
            bad = con.execute(
                "select collector_ok, source_status from provider_status where collected_at='2026-07-24 11:00:00+00'"
            ).fetchone()
            self.assertEqual(bad, (False, "UNKNOWN"))
            con.close()

    def test_indexes_lunar_astronomy_separately_from_space_weather(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            day = root / "data" / "2026-08-12"
            day.mkdir(parents=True)
            row = {
                "collected_at": "2026-08-12T17:37:00Z",
                "sources": [
                    {
                        "id": "usno_sun_moon",
                        "label": "USNO Sun and Moon Data",
                        "url": "https://aa.usno.navy.mil/api/rstt/oneday",
                        "ok": True,
                        "http_status": 200,
                        "latency_ms": 80,
                        "summary": {
                            "moon": {
                                "current_phase": "New Moon",
                                "illumination_percent": 0,
                                "events": {"rise": "04:14", "set": "20:17"},
                            },
                            "sun": {"events": {"rise": "05:08", "set": "20:17"}},
                        },
                    },
                    {
                        "id": "usno_solar_eclipses",
                        "label": "USNO Solar Eclipses",
                        "url": "https://aa.usno.navy.mil/api/eclipses/solar/year",
                        "ok": True,
                        "http_status": 200,
                        "latency_ms": 80,
                        "summary": {
                            "year": 2026,
                            "events": [],
                            "event_today": {
                                "event": "Total Solar Eclipse of 12 August 2026"
                            },
                            "local_visibility": "not-provided-by-usno-year-endpoint",
                        },
                    },
                ],
            }
            (day / "public-status.jsonl").write_text(
                json.dumps(row) + "\n", encoding="utf-8"
            )
            db = root / "data" / "index" / "observatory.duckdb"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo-root",
                    str(root),
                    "--output",
                    str(db),
                ],
                check=True,
            )
            con = duckdb.connect(str(db), read_only=True)
            self.assertEqual(
                con.execute("select count(*) from astronomy").fetchone()[0], 2
            )
            moon = con.execute(
                "select current_phase, illumination_percent, moon_rise, moon_set, sun_rise, sun_set from astronomy where source_id='usno_sun_moon'"
            ).fetchone()
            self.assertEqual(
                moon, ("New Moon", 0.0, "04:14", "20:17", "05:08", "20:17")
            )
            eclipse = con.execute(
                "select solar_eclipse_event, local_visibility from astronomy where source_id='usno_solar_eclipses'"
            ).fetchone()
            self.assertEqual(
                eclipse,
                (
                    "Total Solar Eclipse of 12 August 2026",
                    "not-provided-by-usno-year-endpoint",
                ),
            )
            con.close()


if __name__ == "__main__":
    unittest.main()
