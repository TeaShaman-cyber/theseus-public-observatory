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


if __name__ == "__main__":
    unittest.main()
