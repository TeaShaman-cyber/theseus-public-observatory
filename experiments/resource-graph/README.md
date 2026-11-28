# Observatory resource graph — research #33

**Scope:** a decision model, not a service discovery or a measured outage graph.
Source: Observatory main baff6716c0b67d44baf39202c88f29c37fa74656,
Repo Search main d364c09dad35d50c7878f2ef6f23971a0263e7ac,
[research #31](https://github.com/TeaShaman-cyber/theseus-public-observatory/issues/31).
Current GitHub collector and journal are verified. D1 is a verified
temporary canary, not an active database. Ducklings is emulation-only;
R2 entitlement is blocked. Independent VM, checkpoint sync and agent CLI
are candidates. Existing Dreaming Worker was observed; its actual quota
consumption is unknown. Shared account capacity/limits are not assumed to
be exhausted or independent.

Edges go from a capability to a modeled dependency. A common provider node
is a coarse common-risk domain, not proof that two services fail together.
Reachability is possible exposure, not a probability, and not an availability
prediction. Repo Search edges describe its resource footprint, not that all
its operations require every resource simultaneously. A query can execute
in D1 without native DuckDB on exe.dev; the agent control plane may still
use exe.dev to invoke that API. "agent_history" represents local analysis
of the Git journal, not a deployed historical CLI. Independent probe
execution on a VM does not imply independent persistence: direct D1 writes
share the Cloudflare domain. Test a bounded local spool/replay before
claiming independent failure observations. Graph roots distinguish live
queries, historical analysis, sync and collection so a GitHub outage
does not automatically mean existing D1 rows cannot be queried.
Freshness can still degrade. Source families are coarse; per-sensor
availability and correlation coverage are separate from this graph.

## Reproduce

```sh
python experiments/resource-graph/analyze.py current
python experiments/resource-graph/analyze.py d1_candidate --kql
python -m unittest discover -s experiments/resource-graph -v
```

The generated KQL starts with an inline datatable, uses make-graph and
graph-match up to depth 6, and returns distinct root/dependency pairs and
minimum hop count. Run it through an authorized Kusto query endpoint, not
a management endpoint. No cluster, schema, ingestion or corpus table is
needed. Independent Python BFS evaluates the same graph; compare all rows.
The graph is deliberately small; the bound covers its current paths,
not all possible future architectures.

## Verified comparison

2026-11-28: existing governed Repo Search Kusto client, read-only inline
queries, all rows equal independent BFS. Current: 25 edges / 22 reachable
pairs; D1 candidate: 34 / 42; Worker candidate: 37 / 47. Total 111 matched
pairs, 30 nodes across scenarios. Counts are of modeled root reachability,
not an architecture quality score. Kusto used only for this experiment,
not a required dependency of Observatory.

| Dependency | Current | D1 candidate | Worker candidate |
|---|---|---|---|
| D1 SQL for live query | no | yes | yes |
| Workers shared quota for collection/live query | no | no | yes |
| R2 for live query | no | no | yes (blocked) |
| exe.dev compute for live SQL | n/a | no | no |
| GitHub for recovery/history | yes | yes | yes |
| Turso/MotherDuck/Kusto in Observatory production routes | no | no | no |

## Candidate selection

Prefer the smallest next experiment: GitHub collector and durable journal
unchanged; D1 serving projection fed by idempotent replay. Keep heavy native
DuckDB analysis on demand (hosted runner or analyst's runtime). A fresh
read-only CLI should expose coverage, timestamps, source availability and
query provenance. Do not use a second primary store without an explicit
authority change. Separate ingestion and querying from future faster probes;
if lower latency is required, validate independent probe execution and a
bounded retry spool. Worker Ducklings remains a research alternative, not
an obligatory component. No production migration accepted here.
