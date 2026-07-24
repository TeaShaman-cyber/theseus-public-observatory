#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

EVENT_CENTER_S = 16.4
DURATION_S = 32.0
WINDOW_WIDTH_S = 4.0
CONTROL_WINDOWS = [(2.0, 6.0), (7.0, 11.0), (21.0, 25.0), (26.0, 30.0)]

GWOSC_FILES = {
    "H1": "https://gwosc.org/eventapi/json/O1_O2-Preliminary/GW150914/v2/H-H1_LOSC_16_V2-1126259446-32.hdf5",
    "L1": "https://gwosc.org/eventapi/json/O1_O2-Preliminary/GW150914/v2/L-L1_LOSC_16_V2-1126259446-32.hdf5",
}


def fixed_windows(event_center_s: float = EVENT_CENTER_S, duration_s: float = DURATION_S,
                  width_s: float = WINDOW_WIDTH_S) -> Dict[str, object]:
    half = width_s / 2.0
    event = (round(event_center_s - half, 10), round(event_center_s + half, 10))
    controls = list(CONTROL_WINDOWS)
    for start, end in controls:
        if start < 0 or end > duration_s or start >= end:
            raise ValueError("control window outside data duration")
        if not (end <= event[0] or start >= event[1]):
            raise ValueError("control window overlaps event window")
    return {"event": event, "controls": controls}


def build_manifest(source_sha256: Dict[str, str], sample_rate_hz: int, samples: int) -> Dict[str, object]:
    windows = fixed_windows()
    return {
        "experiment": "TID Observatory root pilot: GW150914 event vs pre-registered off-event controls",
        "epistemic_status": "MEASUREMENT_ONLY",
        "source": "GWOSC/LOSC public GW150914 32 s, 16 kHz HDF5 strain",
        "source_urls": GWOSC_FILES,
        "source_sha256": source_sha256,
        "sample_rate_hz": sample_rate_hz,
        "samples_per_detector": samples,
        "pre_registered_windows": {
            "event": list(windows["event"]),
            "controls": [list(x) for x in windows["controls"]],
        },
        "guardrails": [
            "historical TID target values are not used for selection or success criteria",
            "event and control windows are processed identically",
            "results are descriptive until null/permutation checks are complete",
        ],
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("manifest.json"))
    args = parser.parse_args()
    if not args.manifest_only:
        parser.error("full analysis is executed by run_ligo_analysis.py in the scientific runtime")
    manifest = build_manifest({"H1": "UNKNOWN", "L1": "UNKNOWN"}, 16384, 32 * 16384)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
