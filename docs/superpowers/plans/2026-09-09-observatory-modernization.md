# Observatory Modernization A+ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the first-generation observatory without replacing its JSONL authority model: repair broken sensors, make semantic sensor health explicit, and verify projections against canonical observations.

**Architecture:** Keep `data/YYYY-MM-DD/public-status.jsonl` as the durable observation journal. Split source-specific interpretation into small adapters with deterministic fixtures, enrich new rows with v1 receipt metadata, preserve v0 readability, and keep GitHub Actions as the reproducible compute/acceptance plane. `latest`, reports, DuckDB, and Pages remain rebuildable projections.

**Tech Stack:** Node.js 22 built-ins (`node:test`, `crypto`, Fetch), Python 3.13 site/tests, GitHub Actions.

**Spec:** GitHub issue `TeaShaman-cyber/theseus-public-observatory#9`, especially the accepted Approach A+, runtime-boundary, verifier-backend, Codespaces, and weekly-load checkpoints.

## Global Constraints

- `data/YYYY-MM-DD/public-status.jsonl` remains the durable observation history; no new database authority.
- Historical v0 observations remain valid and readable; only new observations use schema v1.
- GitHub Actions is the default reproducible compute/verification plane; MarcoPolo is an operational workbench/canary runtime.
- Workflow execution success, transport health, parser/schema health, and semantic measurement availability remain distinct states.
- External verifier availability must not be collapsed into claim truth.
- Codespaces remains optional and is not part of acceptance authority in this slice.
- No new scheduler split or prebuild subsystem in this slice.

---

### Task 1: Source adapters and deterministic fixtures

**Files:**
- Create: `scripts/source-adapters.mjs`
- Create: `scripts/source-adapters.test.mjs`
- Create: `scripts/fixtures/huggingface-status.json`
- Create: `scripts/fixtures/noaa-kp.json`
- Modify: `scripts/collect-public-status.mjs`
- Modify: `package.json`

**Interfaces:**
- Consumes: source descriptors `{id, label, url, adapter}` and parsed JSON payloads.
- Produces: `summarizeSource(source, json) -> {ok: boolean, summary: object, error: string|null}`.

- [ ] **Step 1: Write the failing adapter tests**

Add Node tests asserting:

```js
const hf = summarizeSource({ id: "huggingface_status", adapter: "huggingface-status-v1" }, hfFixture);
assert.equal(hf.ok, true);
assert.equal(hf.summary.indicator, "operational");
assert.equal(hf.summary.resources, 8);

const kp = summarizeSource({ id: "noaa_planetary_k_index", adapter: "noaa-kp-v1" }, kpFixture);
assert.equal(kp.ok, true);
assert.equal(kp.summary.latest.Kp, 4.67);
assert.equal(kp.summary.latest.time_tag, "2026-09-09T06:00:00");
```

Also assert malformed HF/Kp payloads return `ok=false` with `error="schema-mismatch"`.

- [ ] **Step 2: Run the tests and verify RED**

Run: `node --test scripts/source-adapters.test.mjs`

Expected: FAIL because `source-adapters.mjs` does not exist.

- [ ] **Step 3: Implement the minimum adapters**

Implement explicit adapters for:

```text
statuspage-status-v1
statuspage-summary-v1
huggingface-status-v1
noaa-kp-v1
noaa-scales-v1
```

`huggingface-status-v1` must read `data.attributes.aggregate_state` and count `included` entries of type `status_page_resource`.

`noaa-kp-v1` must require an array of object rows, select the latest row with numeric `Kp`, and preserve `time_tag`, `Kp`, `a_running`, and `station_count`.

- [ ] **Step 4: Run adapter tests and verify GREEN**

Run: `node --test scripts/source-adapters.test.mjs`

Expected: PASS.

- [ ] **Step 5: Wire adapters into the collector and test script**

Update source URLs/adapter identities, especially:

```text
Hugging Face -> https://status.huggingface.co/index.json
NOAA Kp -> noaa-kp-v1
```

Update `npm test` to include `node --test scripts/*.test.mjs` before repository validation.

- [ ] **Step 6: Run the full current test surface**

Run: `npm test`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add package.json scripts/source-adapters.mjs scripts/source-adapters.test.mjs scripts/fixtures scripts/collect-public-status.mjs
git commit -m "fix: add explicit observatory sensor adapters"
```

---

### Task 2: ObservationReceipt v1 and semantic health

**Files:**
- Create: `scripts/observation-receipt.mjs`
- Create: `scripts/observation-receipt.test.mjs`
- Modify: `scripts/collect-public-status.mjs`
- Modify: `scripts/validate-public-data.mjs`

**Interfaces:**
- Consumes: transport result, JSON parser result, adapter result, source descriptor, current run environment.
- Produces: v1 source receipt fields and top-level snapshot metadata.

- [ ] **Step 1: Write failing receipt tests**

Test that a healthy source produces:

```js
{
  schema_version: 1,
  ok: true,
  transport: { status: "ok" },
  parser: { status: "ok" },
  semantic: { status: "available" },
  payload_sha256: "<64 lowercase hex chars>"
}
```

Test that HTTP success + adapter schema mismatch produces:

```js
ok === false
transport.status === "ok"
parser.status === "schema-mismatch"
semantic.status === "unavailable"
```

Test that an invalid JSON payload preserves a payload hash and returns `parser.status === "invalid-json"`.

- [ ] **Step 2: Run receipt tests and verify RED**

Run: `node --test scripts/observation-receipt.test.mjs`

Expected: FAIL because the receipt module does not exist.

- [ ] **Step 3: Implement minimal v1 receipt builders**

Top-level new snapshots must contain:

```js
{
  schema_version: 1,
  collected_at,
  run: {
    github_run_id,
    github_run_attempt,
    github_repository,
    github_workflow,
    github_ref,
    github_sha,
    collector: "collect-public-status-v1"
  },
  sources
}
```

Environment-derived fields may be `null` outside GitHub Actions.

- [ ] **Step 4: Make validator backward-compatible**

`validate-public-data.mjs` must continue accepting v0 rows without `schema_version`. For v1 rows require:

```text
schema_version == 1
source.adapter is non-empty
source.transport.status is known
source.parser.status is known
source.semantic.status is known
source.payload_sha256 is null or 64 lowercase hex
source.ok == (source.semantic.status == "available")
```

- [ ] **Step 5: Run receipt and full repository tests**

Run:

```bash
node --test scripts/observation-receipt.test.mjs
npm test
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/observation-receipt.mjs scripts/observation-receipt.test.mjs scripts/collect-public-status.mjs scripts/validate-public-data.mjs
git commit -m "feat: add semantic observation receipts"
```

---

### Task 3: Projection consistency and site semantic-health rendering

**Files:**
- Create: `scripts/projection-consistency.mjs`
- Create: `scripts/projection-consistency.test.mjs`
- Modify: `scripts/validate-public-data.mjs`
- Modify: `observatory_site/model.py`
- Modify: `observatory_site/content.py`
- Modify: `observatory_site/render.py`
- Modify: `observatory_site/tests/test_content.py`
- Modify: `observatory_site/tests/test_render.py`
- Add/modify fixtures under: `observatory_site/tests/fixtures/`

**Interfaces:**
- Consumes: canonical JSONL day file, `data/latest/public-status.json`, daily Markdown report.
- Produces: projection-consistency PASS/FAIL and presentation model fields `transport_status`, `parser_status`, `semantic_status`.

- [ ] **Step 1: Write failing projection tests**

Test that the final JSONL record equals `data/latest/public-status.json` as parsed JSON.

Test that a deliberately mismatched latest projection fails with a message containing `latest projection does not match canonical final row`.

- [ ] **Step 2: Verify projection RED**

Run: `node --test scripts/projection-consistency.test.mjs`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement projection check**

Export a pure function comparing parsed canonical/latest objects and a CLI path that checks the latest dated canonical file against `data/latest/public-status.json`.

Do not rewrite projections inside validation.

- [ ] **Step 4: Write failing Python content/render tests**

Add a v1 fixture where transport is OK but semantic state is unavailable. Assert Pages shows the sensor as degraded and distinguishes `transport OK`, `parser schema-mismatch`, and `semantic unavailable`.

- [ ] **Step 5: Verify Python RED**

Run:

```bash
python -m unittest observatory_site.tests.test_content observatory_site.tests.test_render -v
```

Expected: FAIL because the model does not expose v1 health dimensions.

- [ ] **Step 6: Implement v0/v1 site parsing and rendering**

For v0 fixtures, derive legacy-compatible statuses. For v1, render explicit transport/parser/semantic badges and count semantic availability rather than raw HTTP success.

- [ ] **Step 7: Run all projection/site tests**

Run:

```bash
node --test scripts/projection-consistency.test.mjs
npm test
python -m unittest discover -s observatory_site/tests -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add scripts/projection-consistency.mjs scripts/projection-consistency.test.mjs scripts/validate-public-data.mjs observatory_site
git commit -m "feat: verify observatory projections and sensor health"
```

---

### Task 4: CI gate and public documentation cleanup

**Files:**
- Modify: `.github/workflows/collect.yml`
- Modify: `.github/workflows/pages.yml`
- Modify: `README.md`
- Modify: `docs/methodology.md`
- Modify: `data/README.md`
- Modify: `reports/README.md`

**Interfaces:**
- Consumes: test/validation commands from Tasks 1-3.
- Produces: CI acceptance path where degraded observations can be persisted while schema/semantic contract failures remain visible.

- [ ] **Step 1: Add projection consistency to CI validation**

After collection, run repository tests and explicit projection consistency before commit/publish.

Pages must run the same repository contract checks before building.

- [ ] **Step 2: Shorten README front door**

README order:

```text
purpose/invariant
current data flow
sensor health semantics
canonical vs projections
reproduce/verify
repository map
verification lane status
```

Do not move the claim-verifier PR #2 implementation into this slice; document it as the next verification-lane reconciliation.

- [ ] **Step 3: Document schema transition**

State explicitly:

```text
v0 = historical legacy rows
v1 = semantic-health observation receipts
```

Document that `ok` means semantic availability for v1 rows and that transport/parser/semantic statuses are separately preserved.

- [ ] **Step 4: Run complete local acceptance**

Run:

```bash
npm test
python -m unittest discover -s observatory_site/tests -v
python -m ruff check observatory_site scripts
python -m ruff format --check observatory_site scripts
python scripts/build-observatory-index.py --repo-root . --output /tmp/observatory.duckdb
python -m observatory_site.build --repo-root . --output /tmp/observatory-public --base-path /theseus-public-observatory/
git diff --exit-code -- data reports experiments/public
```

Expected: all PASS and canonical data unchanged by build/test commands.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows README.md docs/methodology.md data/README.md reports/README.md
git commit -m "docs: clarify observatory trust and compute boundaries"
```

---

### Task 5: Remote branch, PR, CI, and exact-head review

**Files:**
- No new production files unless review findings require bounded fixes.

**Interfaces:**
- Consumes: completed Task 1-4 branch with clean acceptance.
- Produces: remote PR with green CI and exact-head Codex review disposition.

- [ ] **Step 1: Verify branch postcondition before publication**

Run:

```bash
git status --short
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
```

Expected: clean worktree and only modernization-slice changes.

- [ ] **Step 2: Publish branch and open one PR linked to issue #9**

Use the governed GitHub write route and record the exact remote head SHA after push.

- [ ] **Step 3: Verify GitHub Actions on exact head**

Require repository/Page checks to complete on the recorded SHA. Read job logs/artifacts for any failure; do not infer target failure from connector errors.

- [ ] **Step 4: Request Codex review only on the PR exact head**

Use the real bot trigger only after the PR exists and CI is green. Record reviewed commit SHA.

- [ ] **Step 5: Resolve/disposition P1/P2 findings, re-run CI, and re-request exact-head review if head changes**

Promotion remains blocked until the final exact head has green CI and no unresolved P1/P2 findings.
