import json
import unittest

from scripts.science_read import Window, omni_url, parse_omni


def response(rows, names=("BZ_GSM1800", "V1800", "DST1800"), code=1200):
    definitions = {
        "Time": ("isotime", "UTC", None),
        "BZ_GSM1800": ("double", "nT", "999.9"),
        "V1800": ("double", "Km/s", "9999.0"),
        "DST1800": ("integer", "nT", "99999"),
    }
    params = []
    for name in ("Time", *names):
        kind, unit, fill = definitions[name]
        params.append(dict(name=name, type=kind, units=unit, fill=fill))
    header = dict(HAPI="2.0", status={"code": code}, parameters=params)
    return ("#" + json.dumps(header) + "\n" + "\n".join(rows) + "\n").encode()


class ScienceReadTests(unittest.TestCase):
    def setUp(self):
        self.w = Window("2024-05-10T00:00:00Z", "2024-05-10T02:00:00Z")

    def test_request_bounds_and_parameter_order(self):
        self.assertIn(
            "parameters=BZ_GSM1800%2CV1800%2CDST1800",
            omni_url(self.w, ["dst", "bz", "speed"]),
        )
        for args in [
            ("2024-05-10T00:30:00Z", "2024-05-10T02:00:00Z"),
            ("2024-05-10T00:00:00Z", "2024-07-10T00:00:00Z"),
            ("2024-05-10T02:00:00Z", "2024-05-10T00:00:00Z"),
        ]:
            with self.assertRaises(ValueError):
                Window(*args)
        with self.assertRaises(ValueError):
            omni_url(self.w, ["bogus"])

    def test_fill_is_not_zero_and_midpoint_becomes_interval(self):
        got = parse_omni(
            response(
                [
                    "2024-05-10T00:30:00.000Z,0,9999,12",
                    "2024-05-10T01:30:00.000Z,999.9,400,-3",
                ]
            ),
            self.w,
            ["bz", "speed", "dst"],
        )
        self.assertEqual(
            got["rows"][0],
            {
                "interval_start": "2024-05-10T00:00:00Z",
                "interval_end": "2024-05-10T01:00:00Z",
                "bz": 0.0,
                "speed": None,
                "dst": 12,
            },
        )
        self.assertEqual(got["missing"], {"bz": 1, "speed": 1, "dst": 0})
        self.assertEqual(got["coverage"], "partial")

    def test_invalid_order_time_header_and_numeric_values(self):
        for raw in [
            response(["2024-05-10T00:30:00Z,0,400,1"], code=1411),
            response(
                ["2024-05-10T00:30:00Z,0,400,1"],
                names=("V1800", "BZ_GSM1800", "DST1800"),
            ),
            response(["2024-05-10T00:00:00Z,0,400,1"]),
            response(["2024-05-10T00:30:00Z,NaN,400,1"]),
            response(["2024-05-10T00:30:00Z,0,400,1"] * 2),
            b"error",
        ]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_omni(raw, self.w, ["bz", "speed", "dst"])

    def test_gfz_duplicate_and_missing_are_not_complete(self):
        from scripts.science_read import validate_gfz

        w = Window("2024-05-10T00:00:00Z", "2024-05-10T06:00:00Z")
        r = {
            "interval_start": "2024-05-10T00:00:00Z",
            "interval_end": "2024-05-10T03:00:00Z",
            "kp": 0.0,
            "ap": 0,
        }
        self.assertEqual(validate_gfz([r], w)["coverage"], "partial")
        with self.assertRaises(ValueError):
            validate_gfz([r, r], w)
        r2 = dict(
            r,
            interval_start="2024-05-10T03:00:00Z",
            interval_end="2024-05-10T06:00:00Z",
        )
        self.assertEqual(validate_gfz([r, r2], w)["coverage"], "complete")
        self.assertEqual(validate_gfz([r, dict(r2, kp=None)], w)["missing"]["kp"], 1)
