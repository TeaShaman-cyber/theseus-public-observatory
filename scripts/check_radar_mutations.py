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


def main():
    scripts = Path(__file__).resolve().parent
    source = (scripts / "radar_pilot.py").read_text(encoding="utf-8")
    killed = 0
    for name, (old, new) in MUTANTS.items():
        if source.count(old) != 1:
            raise RuntimeError(f"Mutation anchor drift: {name}")
        mutant = source.replace(old, new, 1)
        compile(mutant, "radar_pilot.py", "exec")
        with tempfile.TemporaryDirectory(prefix="radar-mut-") as tmp:
            root = Path(tmp)
            target = root / "scripts"
            target.mkdir()
            (target / "radar_pilot.py").write_text(mutant, encoding="utf-8")
            shutil.copy(scripts / "test_radar_pilot.py", target)
            run = subprocess.run(
                [sys.executable, "-m", "unittest", "scripts.test_radar_pilot"],
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
    print(f"{killed}/{len(MUTANTS)} targeted mutants killed")
    return 0 if killed == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
