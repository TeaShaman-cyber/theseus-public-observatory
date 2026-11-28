import unittest

from scripts.gfz_archive import parse


def row(
    hour="00.0",
    mid="01.50",
    days="0.00000",
    midpoint="0.06250",
    kp="3.333",
    ap="18",
    flag="1",
):
    return f"1932 01 01 {hour} {mid} {days} {midpoint} {kp} {ap} {flag}"


class GFZTests(unittest.TestCase):
    def test_interval_and_missing_preliminary_are_distinct(self):
        rows = list(
            parse(
                [
                    "# header",
                    row(),
                    row("03.0", "04.50", "0.12500", "0.18750", "-1.000", "-1"),
                    row("06.0", "07.50", "0.25000", "0.31250", "0.000", "0", "0"),
                ]
            )
        )
        self.assertEqual(
            rows[0],
            (
                "1932-01-01T00:00:00Z",
                "1932-01-01T03:00:00Z",
                3.333,
                18,
                "definitive",
                2,
            ),
        )
        self.assertEqual(rows[1][2:5], (None, None, "definitive"))
        self.assertEqual(rows[2][2:5], (0.0, 0, "preliminary"))

    def test_rejects_duplicate_gap_and_invalid_fields(self):
        for lines in (
            [row(), row()],
            [row(), row("06.0", "07.50", "0.25000", "0.31250")],
            [row(flag="2")],
            [row(kp="NaN")],
            [row(ap="-2")],
            [row(mid="02.00")],
            [row(days="1.00000")],
            [row(kp="10.0")],
            [row(kp="-1.000")],
        ):
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                list(parse(lines))

    def test_pinned_snapshot_roundtrip_and_corrupt_manifest(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory

        import duckdb

        from scripts.gfz_archive import project

        source = Path(__file__).resolve().parents[2] / "experiments/historical/gfz"
        manifest = source / "manifest.json"
        archive = source / "Kp_ap_since_1932.txt.gz"
        with TemporaryDirectory() as td:
            output = Path(td) / "gfz.parquet"
            stats = project(archive, manifest, output)
            self.assertEqual(stats[:3], (277320, 277104, 0))
            with duckdb.connect() as con:
                self.assertEqual(
                    con.execute(
                        "select count(distinct interval_start), count(*) filter (where interval_end-interval_start != interval '3 hours') from read_parquet(?)",
                        [str(output)],
                    ).fetchone(),
                    (277320, 0),
                )
            meta = json.loads(manifest.read_text())
            meta["gzip_sha256"] = "0" * 64
            bad = Path(td) / "bad.json"
            bad.write_text(json.dumps(meta))
            rejected = Path(td) / "bad.parquet"
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                project(archive, bad, rejected)
            self.assertFalse(rejected.exists())
            with self.assertRaises(FileExistsError):
                project(archive, manifest, output)
