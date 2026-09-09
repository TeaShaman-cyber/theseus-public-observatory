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
       +-> DuckDB research index
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
- `data/index/observatory.duckdb` — disposable research projection.
- GitHub Pages — presentation.
- Issues/PRs/Git refs — durable coordination and accepted repository state.
- GitHub Actions — reproducible compute/verification plane.

`latest` and the daily report are checked against the final canonical JSONL record.

## Compute and Verification

Substantive reproducible checks belong in **GitHub Actions**.

MarcoPolo is an operational workbench for repository inspection, code preparation, MCP probes, bounded canaries, orchestration, and readback. It is not treated as scientific compute authority.

GitHub Codespaces is an optional interactive repo-local Linux environment for dependency-heavy debugging or reproducing CI failures. It is not an acceptance authority.

The separate claim-verification lane can use:

- repository-owned exact/Open Source checks in CI;
- Precise Special Functions MCP for high-precision zeta/Bessel/Gamma/hypergeometric/elliptic calculations;
- remote Wolfram as an optional independent cross-check when available;
- Lean certificates when a claim is worth and suitable for formalization.

Verifier availability and claim truth are separate states.

## Reproduce

Repository contract:

```bash
npm test
python -m unittest discover -s observatory_site/tests -v
python -m ruff check observatory_site scripts
python -m ruff format --check observatory_site scripts
```

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
docs/research/         research leads, not observations
.github/workflows/     collection and Pages execution
```

## Scope and Safety

Only public data belongs in this repository. No private chat history, account telemetry, credentials, local machine telemetry, or private Theseus lab state should enter the public collector.

If a future source requires authentication, its design must be reviewed before it is added.

See [Methodology](docs/methodology.md), [Data](data/README.md), [Reports](reports/README.md), and the [research index](docs/research/README.md).
