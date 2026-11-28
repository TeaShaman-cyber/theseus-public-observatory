import json
import unittest

from sync import records, verify


class ProjectionTest(unittest.TestCase):
    def test_provenance_and_unknown_preserved(self):
        raw = (
            b'{"collected_at":"2026-11-28T00:00:00Z","sources":[{"id":"x","ok":false}]}'
        )
        row = records(raw + b"\n", "2026-11-28", "a" * 40)[0]
        self.assertEqual(row["journal_line"], 1)
        self.assertEqual(row["receipt"], json.loads(raw))
        self.assertEqual(len(row["line_sha256"]), 64)

    def test_conflicting_existing_row_fails_readback(self):
        raw = b'{"collected_at":"2026-11-28T00:00:00Z","sources":[]}'
        row = records(raw, "2026-11-28", "a" * 40)[0]
        verify(row, dict(row, source_commit="b" * 40))
        with self.assertRaises(ValueError):
            verify(row, dict(row, receipt={}))
