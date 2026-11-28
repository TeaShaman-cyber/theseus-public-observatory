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


class ArchivePackIntegrity(unittest.TestCase):
    def setUp(self):
        import tempfile
        import subprocess
        import json

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.pack = Path(self.tmp.name) / "pack"
        self.raw = self.root / "data/2026-09-01/public-status.jsonl"
        self.raw.parent.mkdir(parents=True)
        self.snapshot = {
            "schema_version": 1,
            "collected_at": "2026-09-01T03:00:00Z",
            "sources": [
                {
                    "id": "noaa_planetary_k_index",
                    "schema_version": 1,
                    "semantic": {"status": "available"},
                    "summary": {"latest": {"Kp": 3, "time_tag": "2026-09-01T00:00:00"}},
                },
                {
                    "id": "openai_status",
                    "schema_version": 1,
                    "semantic": {"status": "available"},
                    "summary": {"indicator": "none"},
                },
            ],
        }
        self.raw.write_text(json.dumps(self.snapshot) + "\n")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
            check=True,
        )
        archive.build(self.root, "2026-09", self.pack)

    def manifest(self):
        import json

        return json.loads((self.pack / "manifest.json").read_text())

    def rewrite(self, manifest=None):
        import json

        if manifest is not None:
            (self.pack / "manifest.json").write_text(json.dumps(manifest))
        names = (
            "raw-jsonl.tar.gz",
            "observations.parquet",
            "signals.parquet",
            "schema.json",
            "manifest.json",
        )
        (self.pack / "SHA256SUMS").write_text(
            "".join(f"{archive.sha_file(self.pack / name)}  {name}\n" for name in names)
        )

    def test_real_pack_and_incomplete_period(self):
        result = archive.verify(self.pack)
        self.assertEqual(result["status"], "VERIFIED")
        self.assertFalse(result["period_complete"])
        self.assertEqual(result["kp_measurements"], 1)

    def test_corrupted_asset_without_rehash(self):
        with (self.pack / "schema.json").open("a") as f:
            f.write("damage")
        with self.assertRaisesRegex(SystemExit, "hash mismatch"):
            archive.verify(self.pack)

    def test_duplicate_checksum_record(self):
        p = self.pack / "SHA256SUMS"
        p.write_text(p.read_text() + p.read_text().splitlines()[0] + "\n")
        with self.assertRaisesRegex(SystemExit, "duplicate checksum"):
            archive.verify(self.pack)

    def test_duplicate_manifest_input(self):
        m = self.manifest()
        m["inputs"].append(m["inputs"][0])
        self.rewrite(m)
        with self.assertRaisesRegex(SystemExit, "duplicate manifest input"):
            archive.verify(self.pack)

    def test_rehashed_asset_metadata_mismatch(self):
        m = self.manifest()
        m["assets"]["schema.json"]["bytes"] += 1
        self.rewrite(m)
        with self.assertRaisesRegex(SystemExit, "asset metadata"):
            archive.verify(self.pack)

    def test_rehashed_false_period_completeness(self):
        m = self.manifest()
        m["period_complete"] = True
        self.rewrite(m)
        with self.assertRaisesRegex(SystemExit, "coverage"):
            archive.verify(self.pack)

    def test_duplicate_tar_member(self):
        import io
        import tarfile

        raw = self.raw.read_bytes()
        name = self.raw.relative_to(self.root).as_posix()
        p = self.pack / "raw-jsonl.tar.gz"
        with tarfile.open(p, "w:gz") as t:
            for _ in range(2):
                info = tarfile.TarInfo(name)
                info.size = len(raw)
                t.addfile(info, io.BytesIO(raw))
        m = self.manifest()
        m["assets"][p.name] = {"bytes": p.stat().st_size, "sha256": archive.sha_file(p)}
        self.rewrite(m)
        with self.assertRaisesRegex(SystemExit, "duplicate raw member"):
            archive.verify(self.pack)

    def test_rehashed_same_count_wrong_measurement(self):
        import duckdb

        path = self.pack / "signals.parquet"
        with duckdb.connect() as con:
            con.execute(
                "create table changed as select * from read_parquet(?)", [str(path)]
            )
            con.execute("update changed set value_num=9 where signal_name='kp'")
            con.execute("copy changed to ? (format parquet)", [str(path)])
        m = self.manifest()
        m["assets"][path.name] = {
            "bytes": path.stat().st_size,
            "sha256": archive.sha_file(path),
        }
        self.rewrite(m)
        with self.assertRaisesRegex(SystemExit, "projection differs"):
            archive.verify(self.pack)

    def test_missing_checksum_entry(self):
        p = self.pack / "SHA256SUMS"
        p.write_text("\n".join(p.read_text().splitlines()[1:]) + "\n")
        with self.assertRaisesRegex(SystemExit, "file set mismatch"):
            archive.verify(self.pack)

    def test_raw_member_hash_mismatch(self):
        import io
        import tarfile

        p = self.pack / "raw-jsonl.tar.gz"
        raw = self.raw.read_bytes().replace(b'"Kp": 3', b'"Kp": 4')
        with tarfile.open(p, "w:gz") as t:
            info = tarfile.TarInfo(self.raw.relative_to(self.root).as_posix())
            info.size = len(raw)
            t.addfile(info, io.BytesIO(raw))
        m = self.manifest()
        m["assets"][p.name] = {"bytes": p.stat().st_size, "sha256": archive.sha_file(p)}
        self.rewrite(m)
        with self.assertRaisesRegex(SystemExit, "raw archive differs"):
            archive.verify(self.pack)

    def test_rehashed_wrong_input_path(self):
        m = self.manifest()
        m["inputs"][0]["path"] = "data/2026-09-31/public-status.jsonl"
        self.rewrite(m)
        with self.assertRaisesRegex(SystemExit, "invalid raw member path"):
            archive.verify(self.pack)

    def test_duplicate_projection_row_is_rejected(self):
        import duckdb

        path = self.pack / "observations.parquet"
        with duckdb.connect() as con:
            con.execute(
                "create table changed as select * from read_parquet(?)", [str(path)]
            )
            con.execute("insert into changed select * from changed limit 1")
            con.execute("copy changed to ? (format parquet)", [str(path)])
        m = self.manifest()
        m["assets"][path.name] = {
            "bytes": path.stat().st_size,
            "sha256": archive.sha_file(path),
        }
        self.rewrite(m)
        with self.assertRaisesRegex(SystemExit, "projection differs"):
            archive.verify(self.pack)

    def test_valid_v1_without_kp_not_rejected(self):
        import json

        self.snapshot["sources"][0]["semantic"]["status"] = "unavailable"
        self.snapshot["sources"][0]["summary"] = {"rows": 0}
        self.raw.write_text(json.dumps(self.snapshot) + "\n")
        import subprocess

        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qam",
                "unavailable Kp",
            ],
            check=True,
        )
        archive.build(self.root, "2026-09", self.pack)
        self.assertEqual(archive.verify(self.pack)["kp_measurements"], 0)


if __name__ == "__main__":
    unittest.main()
