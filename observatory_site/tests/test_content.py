from datetime import datetime, timezone
from pathlib import Path
import unittest

from observatory_site.content import load_experiments, load_latest_snapshot, load_reports
from observatory_site.model import ExperimentSummary

FIX = Path(__file__).parent / "fixtures"

class ContentTests(unittest.TestCase):
    def test_snapshot_marks_stale_and_keeps_collector_failure_separate(self):
        snap = load_latest_snapshot(FIX, now=datetime(2026,7,24,13,30,tzinfo=timezone.utc), freshness_budget_seconds=3600)
        self.assertEqual(snap.freshness, "STALE")
        self.assertTrue(snap.sources[0].collector_ok)
        self.assertFalse(snap.sources[1].collector_ok)
        self.assertEqual(snap.sources[1].source_status, "UNKNOWN")

    def test_reports_are_newest_first(self):
        reports = load_reports(FIX)
        self.assertEqual(reports[0].slug, "2026-07-24")

    def test_experiment_keeps_stage_and_epistemic_status_separate(self):
        exp = load_experiments(FIX)[0]
        self.assertEqual(exp.stage, "PILOT")
        self.assertEqual(exp.epistemic_status, "MEASUREMENT_ONLY")

    def test_generic_verified_status_is_rejected(self):
        with self.assertRaises(ValueError):
            ExperimentSummary(slug="x", title="x", question="x", stage="PILOT", epistemic_status="VERIFIED", result_summary="x", does_not_establish="x")

if __name__ == "__main__":
    unittest.main()
