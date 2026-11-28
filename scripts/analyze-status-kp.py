#!/usr/bin/env python3
"""Descriptive archive canary; not the complete #11 experiment."""

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

import duckdb

from temporal_matching import Sample, match, summarize

LAGS = (-6, -3, 0, 3, 6)
MAX_AGE = timedelta(hours=3)
STATUS = {"none": 0, "minor": 1, "major": 1, "critical": 1}


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() == args.index.resolve():
        parser.error("output must differ from input")
    before = digest(args.index)
    with duckdb.connect(str(args.index), read_only=True) as con:
        # ISO strings avoid optional Python timezone conversion dependencies.
        from datetime import datetime

        exposures = [
            Sample(datetime.fromisoformat(t), datetime.fromisoformat(a), v, f"{p}:{n}")
            for t, a, v, p, n in con.execute("""
                select kp_measured_at::varchar, collected_at::varchar, kp_value,
                       provenance_path, provenance_line
                from space_weather where kp_measurement_state='available'
                order by kp_measured_at, collected_at, provenance_path, provenance_line
            """).fetchall()
        ]
        receipt = {
            "method": "status-kp-descriptive-v1",
            "index_sha256": before,
            "code_sha256": {
                "analyze-status-kp.py": digest(Path(__file__)),
                "temporal_matching.py": digest(
                    Path(__file__).with_name("temporal_matching.py")
                ),
            },
            "lags_hours": list(LAGS),
            "max_age_hours": MAX_AGE.total_seconds() / 3600,
            "availability_policy": "exposure available by outcome time minus lag",
            "measurement_semantics": "NOAA operational Kp time tag; not inferred interval midpoint",
            "input_exposure_receipts": len(exposures),
            "source_coverage": con.execute("""
                select kp_measurement_state, count(*) from space_weather
                where source_id='noaa_planetary_k_index' group by 1 order by 1
            """).fetchall(),
            "inference": "NONE",
            "series": [],
        }
        for provider in ("openai_status", "github_status"):
            outcomes = [
                Sample(
                    datetime.fromisoformat(t),
                    datetime.fromisoformat(t),
                    STATUS.get(s) if usable else None,
                    f"{p}:{n}",
                )
                for t, s, usable, p, n in con.execute(
                    """
                    select collected_at::varchar, source_status, usable,
                           provenance_path, provenance_line from provider_status
                    where source_id=? order by collected_at, provenance_path, provenance_line
                """,
                    [provider],
                ).fetchall()
            ]
            for lag in LAGS:
                rows = match(
                    exposures, outcomes, lag=timedelta(hours=lag), max_age=MAX_AGE
                )
                receipt["series"].append(
                    {
                        "provider": provider,
                        "lag_hours": lag,
                        **summarize(rows),
                        "pairs": [asdict(row) for row in rows],
                    }
                )
    if before != digest(args.index):
        raise RuntimeError("input changed during analysis")
    # Use a new artifact, never silently overwrite evidence.
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(
            receipt, out, default=lambda t: t.isoformat(), allow_nan=False, indent=2
        )
        out.write("\n")


if __name__ == "__main__":
    main()
