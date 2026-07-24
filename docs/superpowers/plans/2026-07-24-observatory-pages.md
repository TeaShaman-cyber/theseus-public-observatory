# Theseus Public Observatory Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a human-readable GitHub Pages presentation layer plus a disposable DuckDB research index over the Observatory's canonical JSON/JSONL history.

**Architecture:** Canonical `data/`, `reports/`, methodology, and durable experiment artifacts remain authoritative. A small Python static-site generator renders bounded presentation models into static HTML, while a separate Python indexer rebuilds `observatory.duckdb` from canonical JSONL for research queries; Pages never depends on the database at runtime.

**Tech Stack:** Python 3.13, standard library, Markdown 3.10.2, DuckDB Python package, unittest, Ruff, GitHub Actions/Pages.

## Global Constraints

- GitHub Pages is a derived presentation artifact only; generator code must never modify canonical repository sources.
- Lifecycle stage and epistemic status are separate fields.
- `VERIFIED_ARTIFACT` and `VERIFIED_EXECUTION` require durable evidence and never imply a hypothesis is proven.
- Latest observations must render freshness against an explicit budget and show `STALE` when exceeded.
- Collector failure must remain distinct from public-source failure.
- Null/negative results are first-class output.
- Private corpora must never be exposed by the site.
- Raw JSON/JSONL remains canonical; DuckDB is disposable and reproducible.
- No ORM, database server, live browser API, SPA framework, or interactive dashboard in v0.1.

---

## File Structure

```text
observatory_site/
  __init__.py            package marker
  build.py               CLI orchestration and output validation
  content.py             repository discovery and adapters
  model.py               typed presentation dataclasses/status validation
  render.py              HTML rendering helpers/templates
  static/style.css       warm Observatory styling
  requirements.txt       Markdown + DuckDB runtime dependencies
  requirements-dev.txt   Ruff
  tests/
    fixtures/...         bounded synthetic repository fixtures
    test_content.py
    test_render.py
    test_build.py
    test_index.py
scripts/
  build-observatory-index.py
.github/workflows/
  pages.yml
data/index/
  README.md               documents disposable DuckDB index, database ignored
experiments/public/
  gw150914.json           durable public experiment descriptor/result summary
```

Generated `public/` and `data/index/observatory.duckdb` are ignored.

---

### Task 1: Presentation models and canonical adapters

**Files:**
- Create: `observatory_site/__init__.py`
- Create: `observatory_site/model.py`
- Create: `observatory_site/content.py`
- Create: `observatory_site/tests/fixtures/data/latest/public-status.json`
- Create: `observatory_site/tests/fixtures/reports/2026-07-24.md`
- Create: `observatory_site/tests/fixtures/experiments/public/gw150914.json`
- Create: `observatory_site/tests/test_content.py`

**Interfaces:**
- Produces `ObservationSnapshot`, `SourceObservation`, `ExperimentSummary`, `load_latest_snapshot()`, `load_reports()`, `load_experiments()`.
- Freshness is calculated from `collected_at` and a caller-supplied `now`/budget.

- [ ] Write failing tests proving source/collector separation, `STALE`, report ordering, stage/epistemic separation, and durable-evidence validation.
- [ ] Run `python -m unittest observatory_site.tests.test_content -v`; expect failures because package modules do not exist.
- [ ] Implement minimal dataclasses/adapters using `json`, `datetime`, `pathlib` only.
- [ ] Re-run the test module; expect PASS.
- [ ] Commit: `feat: add observatory presentation models`.

### Task 2: Static renderer and Pages build

**Files:**
- Create: `observatory_site/render.py`
- Create: `observatory_site/build.py`
- Create: `observatory_site/static/style.css`
- Create: `observatory_site/tests/test_render.py`
- Create: `observatory_site/tests/test_build.py`
- Create: `observatory_site/requirements.txt`
- Create: `observatory_site/requirements-dev.txt`

**Interfaces:**
- `build_site(repo_root: Path, output: Path, base_path: str, now: datetime) -> None`.
- Routes: `/`, `/observations/`, `/experiments/`, `/experiments/gw150914/`, `/method/`, `/about/`.

- [ ] Write failing renderer/build tests for base-path-aware links, collaboration credit, `MEASUREMENT_ONLY`, `STALE`, canonical source links, method boundary, duplicate routes, and canonical-source immutability.
- [ ] Run `python -m unittest observatory_site.tests.test_render observatory_site.tests.test_build -v`; expect FAIL.
- [ ] Implement minimal semantic HTML renderer and build CLI. Use Markdown only for existing Markdown bodies; no template framework.
- [ ] Add warm paper/laboratory CSS derived in spirit, not copied structurally, from `nakama-test`.
- [ ] Run all site tests; expect PASS.
- [ ] Commit: `feat: add public observatory static site`.

### Task 3: Durable GW150914 public evidence descriptor

**Files:**
- Create: `experiments/public/gw150914.json`
- Modify: `observatory_site/tests/test_content.py`
- Modify: `observatory_site/tests/test_render.py`

**Interfaces:**
- Descriptor fields: `slug`, `title`, `question`, `stage`, `epistemic_status`, `result_summary`, `does_not_establish`, `source_urls`, `source_hashes`, `artifact_hashes`, `workflow_url`, `code_url`, `next_gate`.

- [ ] Add failing tests that reject generic `VERIFIED`, missing durable hashes for `VERIFIED_*`, or unsupported stage/status combinations.
- [ ] Add the current GW150914 measurement-only descriptor using already verified source/artifact hashes and workflow URL; do not copy raw strain.
- [ ] Run content/render tests; expect PASS and page text explicitly says the four-control result is descriptive/null-ish.
- [ ] Commit: `data: publish GW150914 pilot descriptor`.

### Task 4: Disposable DuckDB research index

**Files:**
- Create: `scripts/build-observatory-index.py`
- Create: `observatory_site/tests/test_index.py`
- Create: `data/index/README.md`
- Modify: `.gitignore`
- Modify: `observatory_site/requirements.txt`

**Interfaces:**
- CLI: `python scripts/build-observatory-index.py --repo-root . --output data/index/observatory.duckdb`.
- Tables: `observations`, `provider_status`, `space_weather`.
- Views: `v_source_health`, `v_provider_events`, `v_space_weather`, `v_probe_timeline`.
- Each row carries `collected_at`, `source_id`, `collector_ok`, `provenance_path`; domain tables add only bounded typed fields already present in source JSON.

- [ ] Write failing test creating two synthetic JSONL snapshots and asserting deterministic row counts plus source/collector distinction.
- [ ] Run `python -m unittest observatory_site.tests.test_index -v`; expect FAIL because indexer is absent.
- [ ] Implement a rebuild-from-scratch DuckDB indexer; no migrations and no incremental state.
- [ ] Add useful SQL views for timestamp-window joins; do not calculate correlations automatically.
- [ ] Rebuild index twice in test and assert identical logical rows.
- [ ] Run test; expect PASS.
- [ ] Commit: `feat: add disposable DuckDB observatory index`.

### Task 5: GitHub Pages and reproducibility CI

**Files:**
- Create: `.github/workflows/pages.yml`
- Modify: `package.json` only if a convenience script is useful; do not replace existing collector scripts.
- Create/Modify: `observatory_site/tests/test_build.py` for workflow text invariants if needed.

**Interfaces:**
- Build job: checkout, Python 3.13, install requirements, run unittest + Ruff, build DuckDB as reproducibility check, build Pages output, verify canonical Git diff, upload Pages artifact.
- Deploy job: default branch only, official Pages actions, least privileges.

- [ ] Add failing workflow-structure test checking build/deploy split and default-branch-only deployment.
- [ ] Add workflow modeled on the verified `nakama-test` Pages pipeline.
- [ ] Run `npm test`, site unit tests, Ruff, DuckDB rebuild, and bounded local site build.
- [ ] Verify `git diff --exit-code -- data reports docs/methodology.md experiments/public` after build/index generation (generated DB is ignored).
- [ ] Commit: `ci: deploy public observatory Pages`.

### Task 6: Final verification

- [ ] Run `npm test`.
- [ ] Run `python -m unittest discover -s observatory_site/tests -v`.
- [ ] Run `ruff check observatory_site scripts` and `ruff format --check observatory_site scripts`.
- [ ] Rebuild `data/index/observatory.duckdb` from the real repository and execute row-count/timeline smoke queries with DuckDB.
- [ ] Build Pages to `public/` with base path `/theseus-public-observatory/`.
- [ ] Check generated home contains current canonical timestamp/source, collaboration credit, and freshness state.
- [ ] Check GW150914 page contains `MEASUREMENT_ONLY`, durable hashes/evidence, and “does not establish” text.
- [ ] Confirm `git status --short` shows only intended source changes, never generated `public/` or DuckDB.
- [ ] Push feature branch and require GitHub Actions build success before merge/deploy decision.
