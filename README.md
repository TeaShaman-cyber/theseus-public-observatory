# Theseus Public Observatory

Public-data observatory for tracking external infrastructure and space-weather
signals. This repository collects only publicly available data and publishes
small, reproducible summaries.

## Why This Exists

Theseus Public Observatory is a small open experiment in **time-aligned public
signal collection**.

The motivating question is deliberately modest:

> Can we build a transparent public dataset that lets people inspect whether
> public AI/infrastructure incidents and public space-weather signals cluster in
> time more often than expected by chance?

This repository does not claim that space weather affects AI systems. It exists
to make that kind of claim harder to make casually: collect public signals,
preserve timestamps, expose source health, and separate observations from
interpretation.

The first phase is only a baseline observatory:

- collect public vendor status signals;
- collect public NOAA/SWPC space-weather context;
- publish daily machine-readable snapshots;
- make null days visible;
- document outages, timeouts, and missing data;
- support later statistical checks such as lag windows, permutation tests, and
  event co-occurrence analysis.

If you are working on similar public telemetry, anomaly observatories,
stateful-agent monitoring, space-weather correlations, or careful
correlation-vs-causation methodology, issues and discussions are welcome.

## Scope

Collected sources:

- OpenAI public status
- GitHub public status
- Hugging Face public status
- NOAA SWPC planetary K index
- NOAA SWPC scales

This project does not collect private user data, local machine telemetry,
account usage limits, API keys, chat logs, AutoMem data, or private Theseus lab
state.

## Method

The observatory is intentionally conservative:

- collect public data;
- store timestamped snapshots;
- generate short daily reports;
- avoid causal claims;
- keep interpretation separate from collection.

## Research Context

This project is grounded in a few practical ideas rather than one grand claim:

- **Public space-weather monitoring**: NOAA SWPC publishes planetary K-index,
  scales, and alerts as public JSON products.
- **Public infrastructure status pages**: many AI/developer platforms expose
  current operational status through public status APIs.
- **Baseline-first anomaly research**: before testing any hypothesis, define
  sources, timestamps, missing-data behavior, and null periods.
- **Goodhart/Clever-Hans caution**: if an AI assistant is told what pattern to
  expect, it may narrate that pattern. The collector therefore stays boring and
  mechanical.
- **Stateful-agent observability**: public status streams can later become one
  external layer in a larger stateful-agent observatory, while private local
  signals remain private.

The private Theseus lab may import public daily reports later, but private
analysis and local signals stay outside this public repository.

## Run Locally

```bash
npm test
npm run collect
```

Generated data is written to:

```text
data/YYYY-MM-DD/public-status.jsonl
data/latest/public-status.json
reports/YYYY-MM-DD.md
```

## Safety

No secrets are required. If any future source needs authentication, it does not
belong in this public collector until a separate review approves the design.

See [SECURITY.md](SECURITY.md) and [docs/methodology.md](docs/methodology.md).
