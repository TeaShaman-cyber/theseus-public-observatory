"""Bounded temporal matching, with no implicit interpolation or inference."""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from statistics import correlation


@dataclass(frozen=True)
class Sample:
    measured_at: datetime
    available_at: datetime
    value: float | None
    ref: str

    def __post_init__(self):
        if any(t.utcoffset() is None for t in (self.measured_at, self.available_at)):
            raise ValueError("timezone-aware timestamps required")
        if self.available_at < self.measured_at:
            raise ValueError("availability precedes measurement")
        if self.value is not None and (
            type(self.value) not in (int, float) or not isfinite(self.value)
        ):
            raise ValueError("finite numeric value or None required")
        if not self.ref:
            raise ValueError("provenance required")


@dataclass(frozen=True)
class Match:
    outcome: Sample
    target: datetime
    state: str
    exposure: Sample | None = None
    candidate_refs: tuple[str, ...] = ()


def match(exposures, outcomes, *, lag: timedelta, max_age: timedelta):
    """At outcome time minus lag, use the newest tag already available then.

    A later revision cannot rewrite the past. Known conflicting versions at
    that cutoff are unresolved. A negative lag is retrospective, not predictive.
    """
    if max_age < timedelta(0):
        raise ValueError("max_age must be nonnegative")
    grouped = defaultdict(list)
    for item in exposures:
        grouped[item.measured_at].append(item)
    times = sorted(grouped)
    rows = []
    for outcome in outcomes:
        target = outcome.measured_at - lag
        if outcome.value is None:
            rows.append(Match(outcome, target, "unknown_outcome"))
            continue
        idx = bisect_right(times, target) - 1
        while idx >= 0:
            known = [s for s in grouped[times[idx]] if s.available_at <= target]
            if known:
                break
            idx -= 1
        if idx < 0:
            rows.append(Match(outcome, target, "no_measurement"))
            continue
        known.sort(key=lambda s: (s.available_at, s.ref))
        refs = tuple(s.ref for s in known)
        values = {s.value for s in known}
        if target - times[idx] > max_age:
            state = "stale"
        elif len(values) > 1:
            state = "conflict"
        elif None in values:
            state = "unknown_exposure"
        else:
            rows.append(Match(outcome, target, "matched", known[0], refs))
            continue
        rows.append(Match(outcome, target, state, candidate_refs=refs))
    return rows


def summarize(rows):
    pairs = [r for r in rows if r.exposure is not None]
    xs = [r.exposure.value for r in pairs]
    ys = [r.outcome.value for r in pairs]
    r = correlation(xs, ys) if len(set(xs)) > 1 and len(set(ys)) > 1 else None
    counts = Counter(row.state for row in rows)
    distinct = len({row.exposure.measured_at for row in pairs})
    return {
        "outcomes": len(rows),
        "states": dict(sorted(counts.items())),
        "distinct_exposure_tags": distinct,
        "reused_exposure_pairs": len(pairs) - distinct,
        "descriptive_r": r,
        "inference": "NONE",
    }


def circular_reference(x, y, *, step: timedelta):
    """Exact rotation reference, not an automatically calibrated p-value.

    Requires complete aligned regular grids. Validity as a randomization test
    depends on cyclic shift invariance under the scientific null.
    """
    x, y = list(x), list(y)
    n = len(x)
    if not 4 <= n <= 2048 or len(y) != n or step <= timedelta(0):
        raise ValueError("equal grids of 4–2048 points with positive step required")
    times = [s.measured_at for s in x]
    if (
        times != [s.measured_at for s in y]
        or any(b - a != step for a, b in zip(times, times[1:]))
        or any(s.value is None for s in x + y)
    ):
        raise ValueError("complete aligned regular grids required")
    xs, ys = [s.value for s in x], [s.value for s in y]
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        raise ValueError("nonconstant series required")
    observed = correlation(xs, ys)
    shifted = [correlation(xs, ys[k:] + ys[:k]) for k in range(1, n)]
    extreme = 1 + sum(abs(v) >= abs(observed) - 1e-12 for v in shifted)
    return {
        "observed_r": observed,
        "shift_count": n - 1,
        "extreme_fraction": extreme / n,
        "inference": "REFERENCE_ONLY",
    }
