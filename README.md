# Theseus Public Observatory

Public, versioned observations of external systems and physical context.

> **Invariant:** observation is evidence, not interpretation. A green workflow is not proof that every sensor produced usable data.

## What the Observatory Does

The repository collects public signals, preserves each collection run, exposes source/sensor health, and publishes rebuildable human and analytical views.

Current public streams include:

- OpenAI status;
- GitHub status;
- Hugging Face status;
- NOAA SWPC planetary K index;
- NOAA SWPC scales;
- USNO Sun/Moon, lunar-phase, and solar-eclipse context.

The repository does **not** claim that space weather, astronomy, or any other external signal causes AI or infrastructure behavior. Those relationships remain research questions until tested.

## Data Flow

```text
public source
  -> source adapter
  -> v1 observation receipt
  -> canonical JSONL journal
       |
       +-> latest JSON
       +-> daily report
       +-> immutable archive packs (raw + Parquet + manifest)
       +-> DuckDB research index / temporary analysis cache
       +-> GitHub Pages
```

Canonical observation history:

```text
data/YYYY-MM-DD/public-status.jsonl
```

Everything else is a projection or presentation.

## Sensor Health

For v1 observations, each source keeps separate states for:

```text
transport
parser / schema
semantic measurement availability
source-reported status
```

Examples:

```text
HTTP 200 + schema mismatch
!= healthy sensor

HTTP 503
= degraded source observation
!= proof that the parser is broken
```

New v1 rows use `ok` to mean **semantic data is available**. Historical v0 rows remain readable and are not rewritten.

A collection run can therefore preserve a degraded observation and still fail a later sensor-contract gate when the adapter/schema itself is broken.

## Trust Model

- `data/YYYY-MM-DD/public-status.jsonl` — durable observation journal.
- `data/latest/public-status.json` — latest projection.
- `reports/YYYY-MM-DD.md` — human projection.
- immutable GitHub Release packs — durable packaged evidence for long-window reuse; they do not replace canonical JSONL authority.
- `data/index/observatory.duckdb` — disposable research projection / temporary analysis cache.
- GitHub Pages — presentation.
- Issues/PRs/Git refs — durable coordination and accepted repository state.
- GitHub Actions — reproducible collection, packaging, and verification plane.

`latest` and the daily report are checked against the final canonical JSONL record.

## Compute and Verification

The canonical local pre-review gate is:

```bash
bash tools/dev/check
```

GitHub Actions reruns that deterministic baseline and owns heavier repository acceptance steps such as rebuilding projections, archive-pack canaries, and Pages.

MarcoPolo is an operational workbench for repository inspection, code preparation, bounded canaries, orchestration, and readback. It is not treated as scientific compute authority.

GitHub Codespaces is an optional interactive repo-local Linux environment for dependency-heavy debugging or reproducing CI failures. It is not an acceptance authority.

The Observatory verifies evidence integrity, source/sensor contracts, projections, packaging, and reproducible analysis inputs. General mathematical/theorem verification belongs in the research repository that owns the claim (for example the math research lab), not in an Observatory-owned verifier framework.

## Reproduce

Repository contract:

```bash
bash tools/dev/check
```

This is the cheap deterministic pre-review gate. CI additionally rebuilds the disposable research index, historical archive-pack canary, and static site.

Rebuild disposable research index:

```bash
python scripts/build-observatory-index.py  --repo-root .   --output /tmp/observatory.duckdb
```

Build Pages locally:

```bash
python -m observatory_site.build   --repo-root .   --output /tmp/observatory-public   --base-path /theseus-public-observatory/
```

Collection itself is normally executed by GitHub Actions:

```bash
npm run collect
```

## Repository Map

```text
data/                  canonical observations + rebuildable index
reports/               human daily projections
scripts/               collectors, adapters, validators, health checks
observatory_site/      static Pages builder
experiments/public/    public experiment descriptors
docs/methodology.md    trust and interpretation contract
docs/archive-packs.md  durable archive-pack contract
docs/research/         research leads, not observations
tools/dev/check        canonical local deterministic QA entrypoint
.github/workflows/     collection and Pages execution
```

## Scope and Safety

Only public data belongs in this repository. No private chat history, account telemetry, credentials, local machine telemetry, or private Theseus lab state should enter the public collector.

If a future source requires authentication, its design must be reviewed before it is added.

See [Methodology](docs/methodology.md), [Data](data/README.md), [Reports](reports/README.md), and the [research index](docs/research/README.md).
