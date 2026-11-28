# Advisory change-risk measurements (#55)

Reference: Alberto Savoia, [This Code is CRAP](https://testing.googleblog.com/2011/02/this-code-is-crap.html), 2011; metric created with Bob Evans in 2007. The original uses basis-path coverage. This report is a **CRAP proxy**, using per-function LCOV branch opportunities (line fallback if there are none). It is a prioritization heuristic, not a defect count, proof of correctness, or replacement for mutation tests.

Aligned with session-search-lab#351 and dreaming-worker#128. Native Python unittest and Node test runner stay in place. Use coverage.py 7.13.5 with subprocess patch and actual installed site-packages, c8 12.0.0 locked, and pinned upstream crapper complexity parser commit fdd0c01387e4211c74b23c2cdd11c06d90883838. Do not use crapper's automatic runner or default missing-to-zero conversion. Exact relative path attribution, branch/line numerators and denominators, UNKNOWN if no corresponding opportunities, function spans and exact Git SHA in JSON. Nested functions/callbacks may be grouped with enclosing functions according to the pinned parser; line-based attribution can overlap on same-line functions. Distinct coverage kinds are not interchangeable. c8 --all may synthesize zero-hit lines for unvisited files. Zero coverage means only that this measured suite did not exercise the code.

Scope: tracked production .py and .mjs in scripts, observatory_site, experiments; exclude tests and CRAP tooling itself. The existing Python unit suites plus real synthetic HDF5 fixture, and npm test (including CLI validators). Existing mutation execution is excluded from the coverage lane to avoid measuring modified code as accepted source. Live remote calls, PostgreSQL SQL/PLpgSQL execution, edge service and archive pack build/verify smoke are not fully measured. No production credentials needed. This is not all possible execution paths. Dedicated workflow has no score threshold, no new branch protection and no changes to production dependencies. Tool errors/test failures remain visible.

## Baseline at 75baa05e0db82dc7c43787000bb48e9f40ef8c1b

Native Python 76 tests and JS 73 tests passed (Python includes real HDF5 fixture).
126 Python units, one UNKNOWN, 14 scores >30; 50 JS units, none UNKNOWN, eight >30. Exploratory threshold 30 only. Initial subprocess coverage was invalid: target-installed .pth was not processed, resulting in only four coverage fragments and a false high score for build_index (462). Repeated in a dedicated venv with subprocess coverage, 12 fragments combined; build_index CC21 / 25 of 26 branch opportunities / score21.03. HDF5 select_density CC20 / 12 of 14 / score21.17. Do not act on initial invalid ranking.

| Function | CC | Coverage kind and counts | CRAP proxy |
|---|---:|---|---:|
| science_read.py main | 20 | branch 0/22 | 420 |
| build_archive_pack.py verify | 15 | branch 0/20 | 240 |
| collect-public-status.mjs fetchJson | 11 | line 0/51 | 132 |
| collect-public-status.mjs fetchAstronomy | 11 | line 0/59 | 132 |
| validate-public-data.mjs validateV1Source | 14 | branch 2/10 | 114.35 |
| validate-public-data.mjs validateSnapshot | 22 | branch 8/17 | 93.82 |
| schumann_read.py read_nck | 15 | branch 3/10 | 92.17 |
| collect-public-status.mjs renderReport | 32 | branch 11/18 | 92.22 |
| magnetic_read.py parse_magnetic | 35 | branch 24/32 | 54.14 |

First add realistic offline CLI/failure fixtures and coverage of existing integration canaries before interpreting low scores as structural defects. Then prioritize complex parsers and validators with missing error paths. Removing else does not inherently reduce cyclomatic complexity. High CC can be justified; don't split functions merely to game the metric. No refactoring in this slice.

Reproduce using the advisory workflow, or clean checkout with Python 3.13,
Node 22, pinned dependencies in the three requirements files plus
experiments/crap/requirements.txt, locked npm ci in experiments/crap,
and CRAPPER_SOURCE pointing to the clean pinned upstream checkout.
Run bash experiments/crap/run.sh with an absolute fresh output directory.
CI retains JSON, text, LCOV and coverage.json for 14 days.

### Collector failure-isolation follow-up

Issue #55: native Node fixtures exercise mixed successful/unavailable
sources, HTTP failure with plausible JSON, malformed JSON, schema drift,
adapter exception, timeout, interrupted response body, sanitized transport
error and concurrent local journal appends. The old read/replace append
lost 19 of 20 concurrent records in the reproduction. Use appendFile
instead; no claim of crash-atomic writes or cross-run Git push serialization.
HTTP errors do not emit interpreted measurement summaries; received HTTP
metadata and completed-body digest survive when available. Astronomy
uses the same transport path and retains observer-local date. Existing
historical receipts are unchanged. Tests use synthetic transport and
temporary files, no external network requests or credentials. No changes
to source catalogue or collection cadence.

### Receipt validation and index admission (#55)

Validation is now import-safe and tests cross-layer invariants: unique source
identity, finite nonnegative latency, HTTP status consistent with transport,
payload digest presence for completed responses, unavailable sources cannot
carry nonempty measurement summaries, and availability requires successful
transport and parser. Historical HTTP errors with invalid JSON remain valid
failure receipts; interrupted body reads can retain their known HTTP status.
The index additionally gates v1 usability on both schema versions, explicit
ok/transport/parser/semantic success, 2xx status and digest shape. Unknown
legacy semantics are not upgraded. Failed weather/astronomy receipts retain
health/provenance but emit no typed measurements; timeline status UNKNOWN.
This validates receipt consistency, not the underlying physical instrument
or cryptographic authenticity of a digest. No changes to canonical data.
Historical comparison at main ea9a6a8: 2840 v1 source receipts, no nonempty
unavailable summaries; all five base index tables identical as multisets
(7653 observations, 3267 provider, 2178 weather, 2184 astronomy, 2184 Radar
samples). 90 previously misleading unavailable timeline labels corrected;
832 unavailable timeline rows now UNKNOWN. Archive projection format and
published packs unchanged; broader archive admission, source-specific value
validation and Git push concurrency remain separate follow-ups.
