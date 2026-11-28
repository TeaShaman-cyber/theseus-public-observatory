# Observatory research roadmap — 2026-11-28

Coordination: [Public Research Program](https://github.com/users/TeaShaman-cyber/projects/1),
[#9](https://github.com/TeaShaman-cyber/theseus-public-observatory/issues/9),
[#13](https://github.com/TeaShaman-cyber/theseus-public-observatory/issues/13),
[#14](https://github.com/TeaShaman-cyber/theseus-public-observatory/issues/14).
This is the research sequence within the existing notebook, not a parallel
task board. Issues own acceptance and execution status.

## Purpose

Investigate coupled dynamics across physical, biological and engineered
systems. Increase the diversity and usable duration of independently measured
signals, not merely their row count. AI status is one outcome family, not
the scientific scope. Keep historical ideas as hypotheses and controls;
no presumption that a universal TID model or threshold is valid.

| Stage | Research deliverable | Exit condition |
|---|---|---|
| 1. Evidence substrate | Correlation-ready projection (#13); preserve numeric Kp, event versus observation time, unknown, provenance; extend to other families | Rebuild from pinned inputs, typed units and time, coverage and repeated-measurement accounting |
| 2. Method templates | Lagged association, matched windows, autocorrelation-preserving nulls, event deduplication, sensitivity and multiplicity | Synthetic positive/negative controls and reproducible receipts; exact mathematical assumptions and limits |
| 3. Existing retrospective | #11, OpenAI/GitHub versus Kp/G/R/S | Original predeclared windows and stop rule; no additional sensors to rescue a null result |
| 4. Independent physical controls | Archived definitive GFZ Kp/ap; evaluate solar wind/IMF, geomagnetic response and GNSS/TEC for physically established pathway controls | Defined timestamp semantics, source/license, finite acquisition canary and known response recovered against null controls |
| 5. Biological branch | SIF versus space weather after environmental adjustment (SW-LLM-004, #14); microbial/fungal datasets separately | Public reproducible data, QA flags and comparable acquisition support; matched environmental controls; null results retained |
| 6. Multiscale analysis | Spectral coherence, DFA/MFDFA, change points, entropy and topology where sampling and power justify them; compare TID-derived candidates to simpler baselines | Method-specific synthetic benchmark, independent holdout, assumptions and failure cases; no universal threshold fitting |
| 7. Operationalization | Scheduled probes and bounded derived SQL/Parquet, independent compute, reproducible analysis runs | Measured coverage/cost, versioned artifacts, retention and recovery; no DB or runtime used as implicit scientific authority |

Stages 4 and 5 can progress independently of the #11 result. Keep the
existing source admission policy. Do not widen #11 after seeing outcomes.

## Corpus-driven method workflow

Session Search reconstructs hypotheses and failed paths, not scientific
evidence. Repository Search retrieves accepted formal declarations and
dependency neighborhoods; it neither proves an empirical claim nor certifies
the applicability of a theorem to observations. For each candidate method:
record exact question, search receipt and source revision, declaration and
dependency context where available, assumptions (e.g. independence,
stationarity, finite variance, mixing), counterexamples, computational
implementation and benchmark. Verify applicable external statistical
literature and data documentation separately. Formal proof work belongs
to the owning mathematics research project.

Initial live search on 2026-11-28: 34 corpora, no unavailable corpora;
catalog SHA-256
7c5dc04ed2d56593144017373bee8176689df90e00b1b4f8bc7c4a6c5af7776b.
Discovery query "conditional expectation" returned lexical candidates
unrelated to the requested statistical method; evidence query
"ProbabilityTheory.condExp" returned UNKNOWN, no hits. This is a bounded
retrieval coverage gap, not evidence that conditional expectation is absent
from all formal mathematics. Prioritize probability, measure theory,
statistics, time-series/spectral methods and dynamical systems in future
corpus evaluation by concrete method witnesses; do not expand or mutate
the Repo Search service solely to make this query green.

## First biological data canary (proposed, not admitted)

Use the existing SIF source card, not fixed global stress thresholds.
Candidate primary archives:
- [NASA OCO-2 SIF Lite](https://oco.caltech.edu/science/data-access),
  daily files, retrospective V11r Sep 2014–Mar 2024, V11.2r Apr 2024–May 2026;
  daily file packaging is not daily revisit for every location.
- [ESA TROPOSIF L2B](https://eo4society.esa.int/results/l2b-data-access/),
  TROPOMI ungridded daily products May 2018–Mar 2021, netCDF-4.
- [GFZ Kp/ap](https://kp.gfz.de/en/data), definitive 3-hour historical index
  distinct from NOAA operational estimates.

First obtain metadata and one bounded sample, verify license, access,
acquisition time, footprint, uncertainty, quality flags, units and actual
coverage; choose an independently justified region/period before outcomes.
Assess illumination/PAR, season/phenology, temperature, water stress,
clouds/aerosols, retrieval geometry and land cover; avoid treating SIF
alone as a direct measure of geomagnetic response. Compare matched
quiet/storm intervals and region/season controls, with temporal block
resampling and spatial dependence accounted for. Hold out events/regions.
If coverage or comparability fails, report INSUFFICIENT_COVERAGE; do not
silently interpolate daily records or interpret absence of data as zero.
The previously withdrawn SIF preprint is not supporting evidence.
No live satellite collector or Earthdata account has yet been provisioned.

## Method receipt minimum

Versioned hypothesis and method identity; source revision/asset checksums;
measurement support, observation and availability times; units, region and
sampling; exclusions and missingness; predeclared estimand, lags, baseline,
null model, seed and multiple-test family; sample/event counts; effect and
uncertainty; control and sensitivity results; disposition and limitations.
Report exploratory discoveries separately from confirmatory tests.

## Current implementation boundary

First #13 slice adds numeric Kp, measurement-time tag and availability state
to the rebuildable DuckDB projection. NOAA offset-free time tags are UTC;
future tags relative to collection, invalid values and unusable sources
remain UNKNOWN. Valid zero is zero. Duplicate time tags are retained
with line provenance; subsequent analysis must resolve revisions and
measurement intervals deliberately, not count them as independent points.
Neither archival source data nor existing Supabase collectors are changed.

### Temporal matching canary (#13)

The reusable `scripts/temporal_matching.py` matches at target time
(outcome time minus lag) using the newest measurement tag already observed
by that target. A maximum age is explicit. Repeated identical observations
retain their provenance but share a measurement identity. Conflicting known
revisions are excluded, not averaged; unknown or stale latest tags are not
replaced by older values. A negative lag is retrospective, never predictive.
This is a tag-based as-of join, not an interval-overlap estimator. Missing
measurement tags cannot establish an unknown interval: coverage is bounded
by recorded tagged observations. Source availability is conservatively
approximated by the first recorded observation, not actual publication time.

The status/Kp CLI canary uses the existing #11 lags −6, −3, 0, +3, +6 h
and a provisional 3 h maximum tag age, fixed before examining its output.
It emits per-pair provenance, repeated-exposure counts, input/index and code
digests, and descriptive Pearson r only when both matched variables vary.
Provider maintenance and unknown indicators are excluded, not coded healthy.
The old irregular snapshot series is not a regular measurement grid.
No p-value or complete #11 verdict is emitted.

```sh
python3 scripts/build-observatory-index.py --repo-root . --output /tmp/obs-index.duckdb
python3 scripts/analyze-status-kp.py --index /tmp/obs-index.duckdb --output /tmp/obs-receipt.json
```

The separate circular-shift reference accepts only equal, complete,
nonconstant regular grids of 4–2048 points. It enumerates every rotation
including identity in the reference fraction. The circular null requires
cyclic shift invariance to justify inferential calibration; ordinary
stationarity alone is not enough. Synthetic positive and rejection
fixtures verify mechanics; do not apply it to the irregular archive or
claim causal significance. Block resampling, event-level analysis, G/R/S,
multiple-testing and motivating-window sensitivity remain open.

Initial archive canary, source tree 3f3749c9ae3a7a42bb7ce808644f2a5fb3a17357:
1089 provider rows each, 352 numeric Kp receipts. At lag 0 only one pair
per provider meets the 3 h age/availability contract; at other lags zero
or one. No correlation estimate is defined. This is insufficient coverage
for this strict tag-based canary, not NO_SIGNAL or a completed #11 study.
Do not relax tolerances after looking at outcomes. Next evaluate definitive
historical GFZ Kp/ap with explicit 3 h interval semantics and a separately
declared retrospective design; distinguish measurement support from
publication latency. This can serve independent physical and biological
studies regardless of the #11 outcome.
