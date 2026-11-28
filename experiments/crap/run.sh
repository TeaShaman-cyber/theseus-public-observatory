#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
out="$(realpath "${1:?absolute output directory required}")"
: "${CRAPPER_SOURCE:?path to pinned crapper source checkout required}"
test "$(git -C "$CRAPPER_SOURCE" rev-parse HEAD)" = fdd0c01387e4211c74b23c2cdd11c06d90883838
test -z "$(git -C "$CRAPPER_SOURCE" status --porcelain --untracked-files=no)"
mkdir -p "$out"
test ! -e "$out/report.json"
test -z "$(git status --porcelain --untracked-files=no)"
export PYTHONPATH="$CRAPPER_SOURCE/src"
export COVERAGE_RCFILE="$out/coverage.ini"
cat > "$COVERAGE_RCFILE" <<CFG
[run]
branch = True
source = scripts,observatory_site,experiments
patch = subprocess
parallel = True
data_file = $out/.coverage
CFG
python -m unittest discover -s experiments/crap -v
python -m coverage run -m unittest discover -s observatory_site/tests -v
python -m coverage run -m unittest scripts.test_radar_pilot scripts.test_radar_collection scripts.test_archive_pack -v
python -m coverage run -m unittest discover -s experiments/resource-graph -v
python -m coverage run -m unittest discover -s experiments/supabase-projection -v
python -m coverage run -m unittest discover -s experiments/wglc -v
python -m coverage combine
python -m coverage lcov -o "$out/python.lcov"
python -m coverage json -o "$out/python.json"
experiments/crap/node_modules/.bin/c8 --all --include='scripts/*.mjs' --include='experiments/**/*.mjs' --exclude='**/*.test.mjs' --reporter=lcovonly --report-dir="$out/js" --temp-directory="$out/v8" npm test
python experiments/crap/report.py --python-lcov "$out/python.lcov" --js-lcov "$out/js/lcov.info" --output "$out/report.json" | tee "$out/summary.txt"
