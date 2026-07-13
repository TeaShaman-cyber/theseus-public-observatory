# Methodology

This observatory is a public-data collection layer, not a causal inference
engine.

## Motivation

Theseus Public Observatory was created to test a narrower version of a broader
research intuition: public digital infrastructure signals and public
space-weather signals can be collected in a shared timeline without making
premature causal claims.

The useful artifact is the timeline itself. A clean public timeline can support
later questions:

- Were public AI/vendor incidents clustered around any public space-weather
  intervals?
- How often do apparent overlaps happen under random timestamp shuffling?
- How much missing data comes from collector/network problems rather than the
  source being down?
- Which apparent anomalies disappear once local/private confounds are removed?

The repository therefore starts with boring public data collection, not
interpretation.

## Principles

1. Public sources only.
2. Timestamp every collection run in UTC.
3. Keep raw public snapshots separate from interpretation.
4. Report source health and availability before discussing anomalies.
5. Do not infer causal links from temporal overlap.
6. Prefer boring null results over narrative overfitting.
7. Treat collector failures as data about the collector, not as source events.

## Initial Sources

| Source | URL | Purpose |
|---|---|---|
| OpenAI status | `https://status.openai.com/api/v2/status.json` | Public vendor status |
| GitHub status | `https://www.githubstatus.com/api/v2/summary.json` | Public developer infrastructure status |
| Hugging Face status | `https://status.huggingface.co/api/v2/summary.json` | Public AI platform status |
| NOAA planetary K index | `https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json` | Space-weather context |
| NOAA scales | `https://services.swpc.noaa.gov/products/noaa-scales.json` | Space-weather context |

## Interpretation Boundary

Daily reports may say:

- a source was reachable or unreachable;
- a public status indicator changed;
- NOAA values were collected;
- data was missing or malformed.

Daily reports must not say:

- solar activity caused an AI outage;
- model behavior changed because of space weather;
- private local observations confirm public-source anomalies.

Those questions belong to private analysis or a later pre-registered study.

## Later Checks

Once the public timeline is stable, useful checks may include:

- event co-occurrence windows defined before inspection;
- lagged visual overlays;
- permutation tests with shuffled timestamps;
- separate accounting for collector failures;
- public/private separation where private local signals are analyzed only in a
  private lab.

These checks should be documented before conclusions are drawn.
