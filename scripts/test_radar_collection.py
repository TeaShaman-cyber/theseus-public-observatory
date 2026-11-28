import json
import unittest
from unittest.mock import patch

from scripts import radar_pilot as radar


def payload():
    return {
        "success": True,
        "result": {
            "meta": {
                "aggInterval": "FIFTEEN_MINUTES",
                "normalization": "MIN0_MAX",
                "lastUpdated": "2026-11-28T09:30:00Z",
                "dateRange": [
                    {
                        "startTime": "2026-11-27T10:00:00Z",
                        "endTime": "2026-11-28T10:00:00Z",
                    }
                ],
                "units": [{"name": "*", "value": "requests"}],
            },
            "serie_0": {
                "timestamps": ["2026-11-28T09:00:00Z", "2026-11-28T09:30:00Z"],
                "values": ["0", "0.235"],
            },
        },
    }


class CollectionTest(unittest.TestCase):
    def test_window_and_samples_are_retained_without_filling_gaps(self):
        from scripts.radar_collection import series_summary

        s = series_summary(json.dumps(payload()))
        self.assertEqual(
            s["points"],
            [
                {"measured_at": "2026-11-28T09:00:00Z", "value": 0.0},
                {"measured_at": "2026-11-28T09:30:00Z", "value": 0.235},
            ],
        )
        self.assertEqual(s["window_start"], "2026-11-27T10:00:00Z")
        self.assertEqual(s["window_end"], "2026-11-28T10:00:00Z")
        self.assertEqual(s["expected_samples"], 97)
        self.assertEqual(s["coverage"], "partial")
        self.assertEqual(s["source_unit"], "requests")
        self.assertEqual(s["normalization"], "MIN0_MAX")

    def test_rejects_wrong_normalization_range_and_grid(self):
        from scripts.radar_collection import series_summary

        for path, value in [
            (("meta", "normalization"), "PERCENTAGE"),
            (("meta", "units"), []),
            (("serie_0", "values"), ["0", "1.01"]),
            (
                ("serie_0", "timestamps"),
                ["2026-11-28T09:01:00Z", "2026-11-28T09:30:00Z"],
            ),
        ]:
            data = payload()
            data["result"][path[0]][path[1]] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                series_summary(json.dumps(data))

    def test_missing_auth_records_all_eight_unavailable(self):
        from scripts.radar_collection import collect_sources

        with patch.object(radar, "open_response") as req:
            rows = collect_sources("")
        req.assert_not_called()
        self.assertEqual(len(rows), 8)
        self.assertEqual(len({r["id"] for r in rows}), 8)
        self.assertTrue(
            all(
                not r["ok"] and r["error"] == "auth-required" and "summary" not in r
                for r in rows
            )
        )

    def test_http_failure_does_not_admit_points(self):
        from scripts.radar_collection import source_receipt

        with patch.object(
            radar,
            "open_response",
            side_effect=radar.HTTPError(
                "https://api.cloudflare.com", 429, "", {}, None
            ),
        ):
            row = source_receipt("microsoft", "REQUESTS", "fake")
        self.assertEqual(row["transport"]["status"], "http-error")
        self.assertEqual(row["http_status"], 429)
        self.assertFalse(row["ok"])
        self.assertNotIn("summary", row)

    def test_success_receipt_preserves_role_and_payload_hash(self):
        from scripts.radar_collection import source_receipt
        from scripts.test_radar_pilot import Response
        import hashlib

        raw = json.dumps(payload()).encode()
        with patch.object(radar, "open_response", return_value=Response(raw)):
            row = source_receipt("microsoft", "REQUESTS", "fake")
        self.assertTrue(row["ok"])
        self.assertEqual(row["payload_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(row["summary"]["provider"], "microsoft")
        self.assertEqual(row["summary"]["metric"], "REQUESTS")
        self.assertEqual(row["summary"]["attribution"], "Cloudflare Radar")
        self.assertNotIn("fake", json.dumps(row))
