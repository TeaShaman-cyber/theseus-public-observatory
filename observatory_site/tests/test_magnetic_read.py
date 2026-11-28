import hashlib
import json
import unittest
from datetime import datetime, timezone

from scripts.magnetic_read import parse_magnetic, reconcile

START = datetime(2017, 9, 8, 0, 0, tzinfo=timezone.utc)
END = datetime(2017, 9, 8, 6, 0, tzinfo=timezone.utc)


def payload(rows, station="irt", **overrides):
    h = {
        "HAPI": "3.1",
        "status": {"code": 1200},
        "format": "csv",
        "description": f"Best-avail minute data in XYZF orientation, provided by Test ({station.upper()}) observatory.",
        "timeStampLocation": "begin",
        "cadence": "PT1M",
        "x_latitude": 52.17,
        "x_longitude": 104.45,
        "x_elevation": 478,
        "parameters": [
            {"name": "Time", "type": "isotime", "units": "UTC", "fill": None},
            {
                "name": "Field_Vector",
                "type": "double",
                "units": ["nT"] * 3,
                "size": [3],
                "vectorComponents": ["x", "y", "z"],
                "coordinateSystemName": "Cartesian",
                "fill": "99999.0",
            },
            {
                "name": "Field_Magnitude",
                "type": "double",
                "units": "nT",
                "vectorComponents": "r",
                "fill": "99999.0",
            },
        ],
    }
    h.update(overrides)
    return "#" + json.dumps(h) + "\n" + "\n".join(rows) + "\n"


def attempt(body, time, outcome="received_unvalidated"):
    return dict(
        station="irt",
        window_start="2017-09-08 00:00:00+00",
        captured_at=time,
        outcome=outcome,
        http_status=200 if outcome == "received_unvalidated" else 400,
        payload_sha256=hashlib.sha256(body.encode()).hexdigest(),
        body=body,
    )


class MagneticTests(unittest.TestCase):
    def test_fill_and_gap_are_not_zero(self):
        result = parse_magnetic(
            payload(
                [
                    "2017-09-08T00:00Z,0,99999.0000,-12,345",
                    "2017-09-08T00:02Z,1,2,3,4",
                ]
            ),
            "irt",
            "best-avail",
            START,
            END,
        )
        self.assertEqual(result["rows"][0]["x"], 0)
        self.assertIsNone(result["rows"][0]["y"])
        self.assertEqual(result["missing"]["x"], 358)
        self.assertEqual(result["missing"]["y"], 359)
        self.assertEqual(result["coverage"], "partial")

    def test_reject_invalid_schema_station_time_and_numeric(self):
        for body in [
            payload(["2017-09-08T00:00Z,1,2,3,4"], station="kak"),
            payload(["2017-09-08T00:00Z,1,2,3,4"], cadence="PT1S"),
            payload(["2017-09-08T00:00Z,1,2,3,4"], status={"code": 1408}),
            payload(["2017-09-08T00:00Z,1,2,3,4"] * 2),
            payload(["2017-09-08T06:00Z,1,2,3,4"]),
            payload(["2017-09-08T00:00:30Z,1,2,3,4"]),
            payload(["2017-09-08T00:00Z,NaN,2,3,4"]),
            payload(["2017-09-08T00:00Z,1,2,3"]),
        ]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse_magnetic(body, "irt", "best-avail", START, END)

    def test_revisions_and_failures_do_not_erase_valid_snapshot(self):
        first = payload(["2017-09-08T00:00Z,1,99999,3,4"])
        next_ = payload(["2017-09-08T00:00Z,2,5,99999,4"])
        attempts = [
            attempt("not available", "2017-09-08 06:01:00+00", "http_error"),
            attempt(first, "2017-09-08 07:00:00+00"),
            attempt(next_, "2017-09-11 07:00:00+00"),
            attempt("error again", "2017-09-12 07:00:00+00", "http_error"),
        ]
        r = reconcile(attempts)[0]
        self.assertEqual(r["latest_attempt_outcome"], "http_error")
        self.assertEqual(r["valid_snapshots"], 2)
        self.assertEqual(r["transitions"][0]["changed"], 1)
        self.assertEqual(r["transitions"][0]["recovered"], 1)
        self.assertEqual(r["transitions"][0]["lost"], 1)
        self.assertEqual(r["latest_valid_coverage"], "partial")
        self.assertEqual(r["ever_observed_channels"], 4)

    def test_hash_mismatch_is_rejected(self):
        a = attempt("x", "2017-09-08 07:00:00+00")
        a["payload_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "digest"):
            reconcile([a])
