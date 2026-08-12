import unittest
from datetime import datetime, timezone
from pathlib import Path

from observatory_site.content import (
    load_experiments,
    load_latest_snapshot,
    load_reports,
)
from observatory_site.render import render_experiment, render_home

FIX = Path(__file__).parent / "fixtures"


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.snap = load_latest_snapshot(
            FIX,
            now=datetime(2026, 7, 24, 13, 30, tzinfo=timezone.utc),
            freshness_budget_seconds=3600,
        )
        self.reports = load_reports(FIX)
        self.exp = load_experiments(FIX)[0]

    def test_home_is_base_path_aware_and_shows_credit_and_stale(self):
        html = render_home(
            self.snap,
            self.reports,
            [self.exp],
            base_path="/theseus-public-observatory/",
        )
        self.assertIn("/theseus-public-observatory/experiments/", html)
        self.assertIn("STALE", html)
        self.assertIn("Semyon Poklad", html)
        self.assertIn("Jester", html)
        self.assertIn("2026-07-24T10:00:00Z", html)

    def test_experiment_shows_epistemic_boundary(self):
        html = render_experiment(self.exp, base_path="/theseus-public-observatory/")
        self.assertIn("MEASUREMENT_ONLY", html)
        self.assertIn("Does not establish", html)
        self.assertNotIn("hypothesis proven", html.lower())


if __name__ == "__main__":
    unittest.main()
