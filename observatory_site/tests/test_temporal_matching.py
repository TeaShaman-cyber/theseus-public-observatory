import unittest
from datetime import datetime, timedelta, timezone

from scripts.temporal_matching import Sample, match, circular_reference, summarize

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def sample(hour, value, seen=None, ref=None):
    return Sample(
        BASE + timedelta(hours=hour),
        BASE + timedelta(hours=hour if seen is None else seen),
        value,
        ref or str(hour),
    )


class TemporalTests(unittest.TestCase):
    def test_positive_lag_uses_only_measurement_known_at_target(self):
        x = [sample(0, 1), sample(3, 5, seen=4), sample(6, 7)]
        y = [sample(5, 1), sample(6, 0)]
        rows = match(x, y, lag=timedelta(hours=3), max_age=timedelta(hours=3))
        self.assertEqual([r.state for r in rows], ["matched", "matched"])
        self.assertEqual([r.exposure.value for r in rows], [1, 1])
        self.assertEqual([r.exposure.measured_at for r in rows], [BASE, BASE])

    def test_conflicting_revisions_are_unknown_not_averaged(self):
        x = [sample(0, 1), sample(3, 2), sample(3, 4, seen=4, ref="revision")]
        rows = match(x, [sample(4, 1)], lag=timedelta(0), max_age=timedelta(hours=4))
        self.assertEqual(rows[0].state, "conflict")
        self.assertIsNone(rows[0].exposure)
        self.assertEqual(rows[0].candidate_refs, ("3", "revision"))

    def test_identical_repeat_has_one_measurement_identity(self):
        x = [sample(0, 2), sample(0, 2, seen=1, ref="repeat")]
        rows = match(
            x,
            [sample(1, 0), sample(2, 1)],
            lag=timedelta(0),
            max_age=timedelta(hours=2),
        )
        self.assertEqual([r.exposure.ref for r in rows], ["0", "0"])
        self.assertEqual(rows[1].candidate_refs, ("0", "repeat"))

    def test_missing_stale_and_unknown_outcome_are_distinct(self):
        x = [sample(1, 0), sample(3, None)]
        y = [sample(0, 0), sample(2, None), sample(3, 1), sample(6, 1)]
        rows = match(x, y, lag=timedelta(0), max_age=timedelta(hours=2))
        self.assertEqual(
            [r.state for r in rows],
            ["no_measurement", "unknown_outcome", "unknown_exposure", "stale"],
        )

    def test_negative_lag_can_be_retrospective_but_not_after_target(self):
        rows = match(
            [sample(3, 4)],
            [sample(1, 1)],
            lag=timedelta(hours=-2),
            max_age=timedelta(0),
        )
        self.assertEqual(rows[0].exposure.value, 4)

    def test_circular_reference_recovers_aligned_signal(self):
        x = [sample(i, v) for i, v in enumerate([3, 1, 5, 0, 4, 2, 7, 1])]
        result = circular_reference(x, x, step=timedelta(hours=1))
        self.assertAlmostEqual(result["observed_r"], 1)
        self.assertEqual(result["shift_count"], 7)
        self.assertEqual(result["extreme_fraction"], 1 / 8)

    def test_circular_reference_rejects_irregular_or_unknown_grid(self):
        x = [sample(i, i) for i in range(8)]
        for y in (
            x[:3] + x[4:],
            [*x[:7], sample(7, None)],
            [sample(i, 1) for i in range(8)],
        ):
            with self.assertRaises(ValueError):
                circular_reference(x, y, step=timedelta(hours=1))

    def test_summary_reports_reused_tags_without_independence_claim(self):
        rows = match(
            [sample(0, 1), sample(2, 2)],
            [sample(0, 0), sample(1, 1), sample(2, 1)],
            lag=timedelta(0),
            max_age=timedelta(hours=1),
        )
        result = summarize(rows)
        self.assertEqual(result["states"], {"matched": 3})
        self.assertEqual(result["distinct_exposure_tags"], 2)
        self.assertEqual(result["reused_exposure_pairs"], 1)
        self.assertEqual(result["inference"], "NONE")

    def test_later_revision_does_not_change_earlier_match(self):
        x = [sample(0, 2), sample(0, 3, seen=2, ref="later")]
        y = [sample(1, 1), sample(2, 1)]
        rows = match(x, y, lag=timedelta(0), max_age=timedelta(hours=2))
        self.assertEqual([r.state for r in rows], ["matched", "conflict"])
