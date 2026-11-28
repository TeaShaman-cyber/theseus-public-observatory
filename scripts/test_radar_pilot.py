import io
import json
import unittest
from unittest.mock import patch

from scripts import radar_pilot as radar


class Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class RadarPilotTest(unittest.TestCase):
    def test_catalogue_accepts_unique_providers_and_regions(self):
        result = radar.inspect_payload(
            '{"success":true,"result":{"origins":[{"slug":"microsoft","regions":[{"region":"eastus"}]}]}}',
            "catalogue",
        )
        self.assertEqual(
            result, {"providers": ["microsoft"], "region_counts": {"microsoft": 1}}
        )

    def test_catalogue_rejects_wrong_role_and_duplicate_regions(self):
        for value in (
            {"origins": []},
            {"origins": [{"slug": "microsoft", "regions": [{"region": "eastus"}] * 2}]},
            {"origins": [{"slug": "microsoft", "regions": [{"region": ""}]}]},
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                radar.inspect_payload(
                    json.dumps({"success": True, "result": value}), "catalogue"
                )

    def test_json_fail_closed(self):
        for text in (
            '{"success":false,"success":true,"result":{}}',
            '{"success":true,"result":{"x":NaN}}',
            '{"success":true,"result":{"x":Infinity}}',
            '{"success":true,"result":{"x":1e999}}',
            '{"success":false,"result":{"origins":[]}}',
            '{"success":1,"result":{"origins":[]}}',
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                radar.inspect_payload(text, "catalogue")

    def test_series_requires_actual_samples_with_matching_lengths(self):
        valid = {
            "success": True,
            "result": {
                "meta": {
                    "aggInterval": "FIFTEEN_MINUTES",
                    "normalization": "MIN0_MAX",
                    "lastUpdated": "2026-11-28T10:00:00Z",
                    "dateRange": [
                        {
                            "startTime": "2026-11-28T09:00:00Z",
                            "endTime": "2026-11-28T10:00:00Z",
                        }
                    ],
                },
                "serie_0": {
                    "timestamps": ["2026-11-28T09:00:00Z", "2026-11-28T09:15:00Z"],
                    "values": ["0", "23.5"],
                },
            },
        }
        summary = radar.inspect_payload(json.dumps(valid), "series")
        self.assertEqual(summary["samples"], 2)
        self.assertEqual(summary["normalization"], "MIN0_MAX")
        for key, value in (
            ("values", ["0"]),
            ("values", ["0", "NaN"]),
            ("values", ["0", None]),
            ("values", ["0", "-1"]),
            ("timestamps", ["2026-11-28T09:00:00Z"] * 2),
            ("timestamps", ["2026-11-28T08:00:00Z", "2026-11-28T09:15:00Z"]),
        ):
            bad = json.loads(json.dumps(valid))
            bad["result"]["serie_0"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                radar.inspect_payload(json.dumps(bad), "series")

    def test_missing_token_does_not_make_request(self):
        with patch.object(radar, "request") as req:
            result = radar.collect("")
        req.assert_not_called()
        self.assertEqual(result["status"], "AUTH_REQUIRED")

    def test_fixed_https_host_and_bearer_not_in_receipt(self):
        with patch.object(
            radar,
            "open_response",
            return_value=Response(
                b'{"success":true,"result":{"origins":[{"slug":"microsoft","regions":[{"region":"eastus"}]}]}}'
            ),
        ) as call:
            result = radar.request("catalogue", "secret-test-value")
        req = call.call_args.args[0]
        self.assertEqual(
            req.full_url,
            "https://api.cloudflare.com/client/v4/radar/origins?format=JSON&limit=100",
        )
        self.assertEqual(req.get_header("Authorization"), "Bearer secret-test-value")
        self.assertEqual(result["status"], "SCHEMA_OK")
        self.assertNotIn("secret-test-value", json.dumps(result))
        self.assertEqual(len(result["payload_sha256"]), 64)

    def test_failure_is_not_semantic_success(self):
        with patch.object(
            radar, "open_response", return_value=Response(b'{"success":false}')
        ):
            result = radar.request("catalogue", "secret-test-value")
        self.assertEqual(result["status"], "SCHEMA_REJECTED")
        self.assertNotIn("summary", result)
        self.assertNotIn("secret-test-value", json.dumps(result))

    def test_catalogue_failure_stops_series(self):
        with patch.object(
            radar, "request", return_value={"status": "HTTP_ERROR"}
        ) as req:
            result = radar.collect("secret-test-value")
        self.assertEqual(req.call_count, 1)
        self.assertEqual(result["status"], "DEGRADED")

    def test_series_plan_is_bounded_and_provider_specific(self):
        with patch.object(
            radar,
            "request",
            side_effect=lambda kind, token, **kw: {
                "status": "SCHEMA_OK",
                "summary": {"providers": ["microsoft", "oracle"]},
            },
        ):
            result = radar.collect("secret-test-value")
        self.assertEqual(result["status"], "SCHEMA_OK")
        self.assertEqual(len(result["observations"]), 5)


if __name__ == "__main__":
    unittest.main()
