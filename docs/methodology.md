# Methodology

Theseus Public Observatory is a public evidence layer. It preserves observations so later analysis can be stricter than the story that first motivated collection.

## 1. Core Principle

```text
observation
!= interpretation
!= causal claim
!= verified scientific result
```

The observatory may record that two public signals occurred near each other. It must not silently promote temporal overlap into mechanism or causation.

## 2. Authority and Projection

The durable observation authority is the dated JSONL journal:

```text
data/YYYY-MM-DD/public-status.jsonl
```

Each line is one collection run.

Derived surfaces are projections:

```text
data/latest/public-status.json
reports/YYYY-MM-DD.md
data/index/observatory.duckdb
GitHub Pages
```

The repository checks that `latest` equals the final canonical JSONL row and that the daily report names the same `collected_at` timestamp.

DuckDB and Pages are rebuildable and must not become independent truth stores.

## 3. Observation Schema

### v0 — historical rows

Rows created before the modernization retain the original compact fields such as:

```text
collected_at
sources[].ok
sources[].http_status
sources[].latency_ms
sources[].summary
sources[].error
```

They remain valid historical evidence and are not rewritten to simulate information that was never captured.

### v1 — semantic-health receipts

New rows add:

```text
schema_version: 1
run.*
sources[].schema_version
sources[].adapter
sources[].content_type
sources[].payload_sha256
sources[].transport.status
sources[].parser.status
sources[].semantic.status
```

For v1 rows:

```text
sources[].ok == (sources[].semantic.status == "available")
```

The payload hash identifies the received public bytes without storing a second raw-payload authority inside the observation row.

Run metadata records GitHub execution identity when collection runs in Actions. Outside GitHub, those fields may be null and the runtime must not be inferred.

## 4. Sensor Health Model

The following states are deliberately independent:

```text
run execution / persistence
transport health
JSON parsing / source-schema health
semantic measurement availability
source-reported operational state
```

This prevents two important false positives:

```text
workflow green
!= all sensors healthy

HTTP 200
!= expected measurement extracted
```

A schema change at a provider can therefore be represented as:

```text
transport.status = ok
parser.status = schema-mismatch
semantic.status = unavailable
ok = false
```

## 5. Failure Semantics

### Source/network failure

Timeout, 5xx, or other transport failure is a valid degraded observation.

It should be preserved. A public service being unreachable does not by itself mean the adapter is defective.

### Parser/schema failure

Invalid JSON or source-schema drift is also preserved, including payload identity when bytes were received.

After the degraded receipt is persisted, the dedicated sensor-contract health gate fails so the broken adapter becomes visible in CI.

### Semantic failure

If transport and parsing succeed but the expected measurement is absent, the sensor contract fails.

### Legacy data

v0 rows are not retroactively judged by the richer v1 contract.

## 6. Current Sources

| Source | Public endpoint | Adapter role |
|---|---|---|
| OpenAI status | `https://status.openai.com/api/v2/status.json` | vendor status |
| GitHub status | `https://www.githubstatus.com/api/v2/summary.json` | infrastructure status |
| Hugging Face status | `https://status.huggingface.co/index.json` | vendor status |
| NOAA planetary K index | `https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json` | geomagnetic measurement |
| NOAA scales | `https://services.swpc.noaa.gov/products/noaa-scales.json` | space-weather context |
| USNO Sun/Moon | `https://aa.usno.navy.mil/api/rstt/oneday` | astronomy context |
| USNO Moon phases | `https://aa.usno.navy.mil/api/moon/phases/date` | astronomy context |
| USNO solar eclipses | `https://aa.usno.navy.mil/api/eclipses/solar/year` | astronomy context |

The astronomy observer is currently Kaliningrad (`54.7104, 20.4522`, UTC+2). Astronomy requests retain `observer_local_date`; the collection timestamp remains UTC.

Astronomy is context, not a causal explanation.

## 7. Runtime Boundary

```text
GitHub control + authority plane
  = Git state / Issues / PRs / reviews / promotion state

MarcoPolo
  = operational workbench

Codespaces
  = optional interactive repo-local dev runtime

GitHub Actions
  = reproducible compute / collection / verification plane
```

MarcoPolo can run bounded canaries, but promoted scientific/verification evidence should come from the named target runtime with versions and artifacts recorded.

Codespaces can reduce development friction but does not replace CI acceptance.

## 8. Verification Lane

Claim verification is separate from continuous telemetry.

Candidate backends are selected by the claim:

```text
repository-owned exact/Open Source code in Actions
  -> default baseline

Precise Special Functions MCP
  -> high-precision special functions

remote Wolfram
  -> optional independent symbolic/knowledge cross-check

Lean
  -> formal certificate when the encoded theorem warrants it
```

A verifier outage is a backend-state observation, not a mathematical result.

```text
verifier unavailable
!= claim false
```

A Lean certificate establishes the encoded theorem under its formal assumptions. It does not automatically establish that the encoding captures the intended physical interpretation.

## 9. Interpretation Boundary

Daily/public reports may state:

- a source was reachable or unreachable;
- a parser/schema contract succeeded or failed;
- a public status indicator changed;
- a public physical measurement was collected;
- data was absent, malformed, or stale.

They must not state without separate evidence:

- that space weather caused an AI/infrastructure incident;
- that astronomy caused model behavior;
- that temporal overlap proves mechanism;
- that a model-generated hypothesis is scientifically verified.

## 10. Research Guardrails

Before interpreting two event streams together, define the analysis rather than narrating the picture after seeing it.

Useful gates include:

- explicit event definitions;
- fixed comparison and lag windows;
- null days and missing-data accounting;
- source outage vs collector/adapter failure separation;
- randomization/permutation baselines where appropriate;
- independent computation or formal checking for mathematical claims;
- explicit `FACT / INFERENCE / HYPOTHESIS / UNKNOWN` disposition.

Research leads live in [docs/research](research/README.md). Listing a lead does not turn it into an observation or conclusion.
