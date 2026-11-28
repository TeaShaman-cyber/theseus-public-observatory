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

    def test_v1_health_dimensions_do_not_reuse_legacy_collector_ok(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            day = root / "data" / "2026-09-09"
            day.mkdir(parents=True)
            rows = [
                {
                    "collected_at": "2026-09-09T10:00:00Z",
                    "sources": [
                        {
                            "id": "github_status",
                            "label": "GitHub",
                            "url": "https://example.test/legacy",
                            "ok": True,
                            "http_status": 200,
                            "latency_ms": 100,
                            "summary": {"indicator": "none"},
                        }
                    ],
                },
                {
                    "schema_version": 1,
                    "collected_at": "2026-09-09T11:00:00Z",
                    "sources": [
                        {
                            "schema_version": 1,
                            "id": "github_status",
                            "label": "GitHub",
                            "url": "https://example.test/v1",
                            "ok": False,
                            "http_status": 200,
                            "latency_ms": 110,
                            "transport": {"status": "ok"},
                            "parser": {"status": "schema-mismatch"},
                            "semantic": {"status": "unavailable"},
                            "error": "schema-mismatch",
                        }
                    ],
                },
            ]
            p = day / "public-status.jsonl"
            p.write_text(
                "\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8"
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
            legacy = con.execute(
                "select schema_version, collector_ok, transport_status, parser_status, semantic_status "
                "from observations where collected_at='2026-09-09 10:00:00+00'"
            ).fetchone()
            v1 = con.execute(
                "select schema_version, collector_ok, transport_status, parser_status, semantic_status "
                "from observations where collected_at='2026-09-09 11:00:00+00'"
            ).fetchone()
            self.assertEqual(legacy, (0, True, None, None, None))
            self.assertEqual(v1, (1, None, "ok", "schema-mismatch", "unavailable"))
            health = con.execute(
                "select schema_version, collector_ok, transport_status, parser_status, semantic_status, usable "
                "from v_source_health order by collected_at"
            ).fetchall()
            self.assertEqual(
                health,
                [
                    (0, True, None, None, None, True),
                    (1, None, "ok", "schema-mismatch", "unavailable", False),
                ],
            )
            con.close()

    def test_healthy_huggingface_operational_status_is_not_a_provider_event(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            day = root / "data" / "2026-09-10"
            day.mkdir(parents=True)
            row = {
                "schema_version": 1,
                "collected_at": "2026-09-10T04:30:00Z",
                "sources": [
                    {
                        "schema_version": 1,
                        "id": "huggingface_status",
                        "label": "Hugging Face",
                        "url": "https://status.huggingface.co/",
                        "ok": True,
                        "http_status": 200,
                        "latency_ms": 90,
                        "transport": {"status": "ok"},
                        "parser": {"status": "ok"},
                        "semantic": {"status": "available"},
                        "payload_sha256": "a" * 64,
                        "summary": {
                            "indicator": "operational",
                            "description": "Operational",
                        },
                    }
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
                con.execute(
                    "select source_status, usable from provider_status"
                ).fetchone(),
                ("operational", True),
            )
            self.assertEqual(
                con.execute("select count(*) from v_provider_events").fetchone()[0], 0
            )
            con.close()


if __name__ == "__main__":
    unittest.main()


class RadarIndexTests(unittest.TestCase):
    def test_overlapping_normalized_windows_keep_separate_provenance(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            day = root / "data" / "2026-11-28"
            day.mkdir(parents=True)
            rows = []
            for hour, value in [(10, 0.5), (11, 0.7)]:
                rows.append(
                    {
                        "schema_version": 1,
                        "collected_at": f"2026-11-28T{hour}:00:00Z",
                        "sources": [
                            {
                                "id": "radar_microsoft_requests",
                                "adapter": "cloudflare-radar-origins-v1",
                                "schema_version": 1,
                                "ok": True,
                                "semantic": {"status": "available"},
                                "transport": {"status": "ok"},
                                "parser": {"status": "ok"},
                                "http_status": 200,
                                "payload_sha256": str(hour)[-1] * 64,
                                "observed_at": f"2026-11-28T{hour}:01:00Z",
                                "summary": {
                                    "provider": "microsoft",
                                    "metric": "REQUESTS",
                                    "window_start": f"2026-11-27T{hour}:00:00Z",
                                    "window_end": f"2026-11-28T{hour}:00:00Z",
                                    "last_updated": "2026-11-28T09:45:00Z",
                                    "normalization": "MIN0_MAX",
                                    "agg_interval": "FIFTEEN_MINUTES",
                                    "source_unit": "requests",
                                    "value_unit": "window_max_fraction",
                                    "samples": 1,
                                    "expected_samples": 97,
                                    "coverage": "partial",
                                    "points": [
                                        {
                                            "measured_at": "2026-11-28T09:45:00Z",
                                            "value": value,
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                )
            (day / "public-status.jsonl").write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
                encoding="utf-8",
            )
            db = root / "index.duckdb"
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
            try:
                got = con.execute(
                    "select value, provenance_line, normalization, coverage "
                    "from radar_window_samples order by window_end"
                ).fetchall()
                self.assertEqual(
                    got,
                    [(0.5, 1, "MIN0_MAX", "partial"), (0.7, 2, "MIN0_MAX", "partial")],
                )
            finally:
                con.close()


class KpMeasurementTests(unittest.TestCase):
    def test_kp_values_and_time_tags_are_preserved_only_when_valid(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            day = root / "data" / "2026-11-28"
            day.mkdir(parents=True)
            rows = []
            cases = [
                (3.33, "2026-11-28T09:00:00", True, 3.33),
                (0, "2026-11-28T09:00:00Z", True, 0.0),
                (False, "2026-11-28T09:00:00", True, None),
                (10, "2026-11-28T09:00:00", True, None),
                ("3.33", "2026-11-28T09:00:00", True, None),
                (3.33, "not-a-time", True, None),
                (3.33, "2026-11-28T15:00:00Z", True, None),
                (3.33, "2026-11-28T09:00:00", False, None),
                (None, None, True, None),
            ]
            for value, tag, available, _ in cases:
                rows.append(
                    {
                        "schema_version": 1,
                        "collected_at": "2026-11-28T13:00:00Z",
                        "sources": [
                            {
                                "schema_version": 1,
                                "id": "noaa_planetary_k_index",
                                "adapter": "noaa-kp-v1",
                                "ok": available,
                                "transport": {"status": "ok"},
                                "parser": {
                                    "status": "ok" if available else "schema-mismatch"
                                },
                                "http_status": 200,
                                "payload_sha256": "a" * 64,
                                "semantic": {
                                    "status": "available"
                                    if available
                                    else "unavailable"
                                },
                                "summary": {
                                    "rows": 1,
                                    "latest": {"Kp": value, "time_tag": tag},
                                },
                            }
                        ],
                    }
                )
            (day / "public-status.jsonl").write_text(
                "\n".join(map(json.dumps, rows)) + "\n", encoding="utf-8"
            )
            db = root / "index.duckdb"
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
            with duckdb.connect(str(db), read_only=True) as con:
                result = con.execute(
                    "select kp_value, epoch(kp_measured_at), kp_measurement_state,"
                    " provenance_line from space_weather order by provenance_line"
                ).fetchall()
            expected = [
                (
                    expected,
                    1795856400.0 if expected is not None else None,
                    "available" if expected is not None else "UNKNOWN",
                    i,
                )
                for i, (_, _, _, expected) in enumerate(cases, 1)
            ]
            self.assertEqual(result, expected)


class UnavailableMeasurementTests(unittest.TestCase):
    def test_unavailable_and_contradictory_receipts_do_not_emit_measurements(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            day = root / "data/2026-11-28"
            day.mkdir(parents=True)
            sources = [
                {
                    "id": "noaa_scales",
                    "ok": False,
                    "semantic": {"status": "unavailable"},
                    "transport": {"status": "ok"},
                    "parser": {"status": "schema-mismatch"},
                    "summary": {"current": {"R": {"Scale": "4"}, "S": {"Scale": "0"}}},
                },
                {
                    "id": "usno_sun_moon",
                    "ok": False,
                    "semantic": {"status": "unavailable"},
                    "transport": {"status": "ok"},
                    "parser": {"status": "schema-mismatch"},
                    "summary": {
                        "moon": {
                            "current_phase": "Full Moon",
                            "illumination_percent": 100,
                        }
                    },
                },
                {
                    "id": "noaa_planetary_k_index",
                    "ok": True,
                    "semantic": {"status": "available"},
                    "transport": {"status": "http-error"},
                    "parser": {"status": "ok"},
                    "summary": {
                        "rows": 1,
                        "latest": {"Kp": 4, "time_tag": "2026-11-28T09:00:00Z"},
                    },
                },
                {
                    "id": "openai_status",
                    "ok": True,
                    "semantic": {"status": "available"},
                    "transport": {"status": "ok"},
                    "parser": {"status": "invalid-json"},
                    "summary": {"indicator": "none"},
                },
            ]
            for source in sources:
                source.update(
                    schema_version=1,
                    http_status=503
                    if source["transport"]["status"] == "http-error"
                    else 200,
                    payload_sha256="a" * 64,
                )
            (day / "public-status.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "collected_at": "2026-11-28T12:00:00Z",
                        "sources": sources,
                    }
                )
                + "\n"
            )
            db = root / "index.duckdb"
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
            with duckdb.connect(str(db), read_only=True) as con:
                self.assertEqual(
                    con.execute(
                        "select count(*) from observations where not usable"
                    ).fetchone(),
                    (4,),
                )
                self.assertEqual(
                    con.execute(
                        "select r_scale,s_scale,g_scale from space_weather where source_id='noaa_scales'"
                    ).fetchone(),
                    (None, None, None),
                )
                self.assertEqual(
                    con.execute(
                        "select kp_rows,kp_value,kp_measurement_state from space_weather where source_id='noaa_planetary_k_index'"
                    ).fetchone(),
                    (None, None, "UNKNOWN"),
                )
                self.assertEqual(
                    con.execute(
                        "select current_phase,illumination_percent from astronomy"
                    ).fetchone(),
                    (None, None),
                )
                self.assertEqual(
                    con.execute(
                        "select source_status,usable from provider_status"
                    ).fetchone(),
                    ("UNKNOWN", False),
                )
                self.assertEqual(
                    con.execute(
                        "select count(*) from v_probe_timeline where not usable and source_status='UNKNOWN'"
                    ).fetchone(),
                    (4,),
                )
