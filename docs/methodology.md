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
| USNO Sun and Moon one-day data | `https://aa.usno.navy.mil/api/rstt/oneday` | Local Sun/Moon rise, transit, set, phase, and illumination |
| USNO Moon phases | `https://aa.usno.navy.mil/api/moon/phases/date` | Primary lunar phase events |
| USNO solar eclipses | `https://aa.usno.navy.mil/api/eclipses/solar/year` | Annual solar-eclipse event context |

The current observer configuration is Kaliningrad, Russia (`54.7104 N`,
`20.4522 E`, UTC+2). Astronomy requests use the observer's local calendar date
and retain it as `observer_local_date`; the snapshot timestamp remains UTC.
Astronomy data is a separate context layer. The collector does not infer lunar
or solar effects from a provider status change.

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

## Research Guardrails

This repository exists because temporal coincidences are easy to notice and
easy to over-interpret. The public collector should therefore make these checks
cheap before any claim is made:

- Was the event definition written down before looking at the overlap?
- Was the comparison window fixed before inspection?
- Were lagged windows handled symmetrically?
- Were null days and missing data included?
- Was source reachability separated from source status?
- Was local network/proxy failure separated from public service failure?
- Were lunar phase, eclipse visibility, and local Sun/Moon horizon conditions
  recorded as context rather than treated as explanations?
- Would a shuffled or permuted timeline produce similar coincidences?

If the answer is unknown, the correct report language is "needs analysis", not
"confirmed".

Future biological or ecological signals such as SIF should enter as separate
public-data streams with their own source documentation and caveats. They must
not be mixed into infrastructure interpretation until the baseline timeline is
stable.

Research leads are kept in the versioned
[research index](research/README.md), not in a separate Wiki. A lead may record
a source claim, a proposed mechanism, or an open question; it is not an
observation and does not become a causal conclusion merely by being listed.

## Later Checks

Once the public timeline is stable, useful checks may include:

- event co-occurrence windows defined before inspection;
- lagged visual overlays;
- permutation tests with shuffled timestamps;
- separate accounting for collector failures;
- public/private separation where private local signals are analyzed only in a
  private lab.

These checks should be documented before conclusions are drawn.
