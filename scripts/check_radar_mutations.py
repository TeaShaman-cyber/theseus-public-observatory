"""Run scoped, deterministic adversarial mutations of Radar pilot contracts."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MUTANTS = {
    "accept_duplicate_keys": ("if key in result:", "if False:"),
    "accept_nonfinite": ("if not math.isfinite(number):", "if False:"),
    "allow_unsuccessful_envelope": ('envelope.get("success") is not True', "False"),
    "allow_misaligned_samples": ("or len(timestamps) != len(values)", "or False"),
    "allow_duplicate_timestamps": (
        "if any(a >= b for a, b in zip(times, times[1:])):",
        "if False:",
    ),
    "ignore_window": (
        "if start >= end or times[0] < start or times[-1] > end:",
        "if False:",
    ),
    "ignore_missing_auth": ("if not token.strip():", "if False:"),
    "ignore_catalogue_failure": ('if catalogue["status"] != "SCHEMA_OK":', "if False:"),
}


COLLECTION_MUTANTS = {
    "accept_other_normalization": (
        'if summary["normalization"] != "MIN0_MAX":',
        "if False:",
    ),
    "accept_other_units": (
        'if units != [{"name": "*", "value": "requests"}]:',
        "if False:",
    ),
    "accept_offgrid_or_outofrange": (
        "if stamp.timestamp() % INTERVAL_SECONDS or not 0 <= value <= 1:",
        "if False:",
    ),
}


def main():
    scripts = Path(__file__).resolve().parent
    killed = 0
    cases = [
        ("radar_pilot.py", "test_radar_pilot", MUTANTS),
        ("radar_collection.py", "test_radar_collection", COLLECTION_MUTANTS),
    ]
    for filename, test_module, mutants in cases:
        source = (scripts / filename).read_text(encoding="utf-8")
        for name, (old, new) in mutants.items():
            if source.count(old) != 1:
                raise RuntimeError(f"Mutation anchor drift: {name}")
            mutant = source.replace(old, new, 1)
            compile(mutant, "radar_pilot.py", "exec")
            with tempfile.TemporaryDirectory(prefix="radar-mut-") as tmp:
                root = Path(tmp)
                target = root / "scripts"
                target.mkdir()
                for file in (
                    "radar_pilot.py",
                    "radar_collection.py",
                    "test_radar_pilot.py",
                    "test_radar_collection.py",
                ):
                    shutil.copy(scripts / file, target)
                (target / filename).write_text(mutant, encoding="utf-8")
                run = subprocess.run(
                    [sys.executable, "-m", "unittest", f"scripts.{test_module}"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                if (
                    run.returncode == 1
                    and "FAIL:" in run.stderr
                    and "ERROR:" not in run.stderr
                ):
                    print(name, "KILLED")
                    killed += 1
                else:
                    print(name, "SURVIVED_OR_INVALID", run.returncode)
                    print(run.stderr)
    total = len(MUTANTS) + len(COLLECTION_MUTANTS)
    print(f"{killed}/{total} targeted mutants killed")
    return 0 if killed == total else 1


if __name__ == "__main__":
    sys.exit(main())
