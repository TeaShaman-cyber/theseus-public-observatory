"""Offline CLI contract tests: real argument parsing, mocked remote boundary."""

import hashlib
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from unittest.mock import patch

from scripts import science_read as cli

START = "2023-02-10T00:00:00Z"
END = "2023-02-11T00:00:00Z"


class CliTests(unittest.TestCase):
    def test_routes_preserve_arguments_and_selection_digest(self):
        w = cli.Window(START, END)
        cases = [
            ("nasa-omni-hourly", [], "read_omni", (w, list(cli.FIELDS))),
            ("nasa-omni-hourly", ["--fields", "dst"], "read_omni", (w, ["dst"])),
            ("gfz-kp-ap", [], "read_gfz", (w,)),
            (
                "intermagnet-minute",
                ["--station", "irt"],
                "read_magnetic",
                (w.begin, w.stop, "irt", "definitive"),
            ),
            (
                "intermagnet-minute",
                ["--station", "kak", "--quality", "best-avail"],
                "read_magnetic",
                (w.begin, w.stop, "kak", "best-avail"),
            ),
            ("schumann-nck-frequency", [], "read_nck", (w.begin, w.stop)),
            (
                "schumann-sierra-nevada",
                ["--sensor", "0"],
                "read_sierra",
                (w.begin, w.stop, 0),
            ),
            (
                "wglc-daily-density",
                ["--bbox", "46", "48", "16", "18"],
                "read_wglc",
                (cli.Selection(date(2023, 2, 10), date(2023, 2, 11), 46, 48, 16, 18),),
            ),
        ]
        for source, options, reader, expected in cases:
            rows = [{"value": 0}, {"value": None}]
            receipt = {"source": source, "rows": rows, "coverage": "partial"}
            out = io.StringIO()
            with (
                self.subTest(source=source, options=options),
                patch.object(cli, reader, return_value=receipt) as call,
                patch(
                    "sys.argv",
                    [
                        "science_read.py",
                        source,
                        "--start",
                        START,
                        "--end",
                        END,
                        *options,
                    ],
                ),
                redirect_stdout(out),
            ):
                cli.main()
                call.assert_called_once_with(*expected)
                result = json.loads(out.getvalue())
                self.assertEqual(result["window"], {"start": START, "end": END})
                self.assertEqual(result["rows"], rows)
                self.assertEqual(result["coverage"], "partial")
                self.assertEqual(
                    result["slice_sha256"],
                    hashlib.sha256(b'[{"value":0},{"value":null}]').hexdigest(),
                )

    def test_invalid_options_fail_before_remote_access(self):
        cases = [
            ("wglc-daily-density", [], START),
            ("gfz-kp-ap", ["--bbox", "46", "48", "16", "18"], START),
            ("schumann-sierra-nevada", [], START),
            ("gfz-kp-ap", ["--sensor", "0"], START),
            ("gfz-kp-ap", ["--fields", "dst"], START),
            ("intermagnet-minute", [], START),
            ("gfz-kp-ap", ["--station", "irt"], START),
            ("gfz-kp-ap", ["--quality", "definitive"], START),
            (
                "wglc-daily-density",
                ["--bbox", "46", "48", "16", "18"],
                "2023-02-10T01:00:00Z",
            ),
        ]
        for source, options, start in cases:
            with (
                self.subTest(source=source, options=options),
                patch(
                    "sys.argv",
                    [
                        "science_read.py",
                        source,
                        "--start",
                        start,
                        "--end",
                        END,
                        *options,
                    ],
                ),
                patch(
                    "urllib.request.OpenerDirector.open",
                    side_effect=AssertionError("network called"),
                ),
                redirect_stderr(io.StringIO()),
                redirect_stdout(io.StringIO()) as out,
            ):
                with self.assertRaises(SystemExit) as e:
                    cli.main()
                self.assertEqual(e.exception.code, 2)
                self.assertEqual(out.getvalue(), "")

    def test_transport_error_does_not_emit_success_or_fallback(self):
        with (
            patch(
                "sys.argv",
                ["science_read.py", "nasa-omni-hourly", "--start", START, "--end", END],
            ),
            patch.object(cli, "read_omni", side_effect=TimeoutError("upstream")),
            patch.object(cli, "read_gfz") as fallback,
            redirect_stdout(io.StringIO()) as out,
        ):
            with self.assertRaises(TimeoutError):
                cli.main()
            fallback.assert_not_called()
            self.assertEqual(out.getvalue(), "")

    def test_invalid_window_rejected(self):
        with (
            patch(
                "sys.argv",
                ["science_read.py", "gfz-kp-ap", "--start", END, "--end", START],
            ),
            patch.object(cli, "read_gfz") as reader,
        ):
            with self.assertRaises(ValueError):
                cli.main()
            reader.assert_not_called()
