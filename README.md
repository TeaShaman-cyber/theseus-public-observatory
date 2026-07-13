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

## What This Is Trying To Check

The observatory was started after repeated local observations and discussions
around a simple but slippery question:

> When public AI/developer infrastructure feels unstable, are there public
> external signals that should be logged beside the incident timeline before
> anyone starts telling a story?

The project is deliberately built as a check against narrative overfitting. It
does not assume that solar or geomagnetic activity changes AI behavior. It only
creates a public timeline that can later support stricter questions:

- Did a public vendor incident overlap with elevated public space-weather
  indices?
- Did the apparent overlap survive lag-window and permutation-style checks?
- Did the collector itself fail because of local network or proxy conditions?
- Did a "signal" disappear after adding null days and missing-data records?
- Are biological or ecological public signals worth adding as separate,
  clearly labeled research leads?

The first useful output is therefore not a conclusion. It is a boring,
timestamped dataset that makes future conclusions harder to fake.

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
  scales, alerts, and JSON products for operational use. Kp is used to
  characterize geomagnetic disturbance and to support alerts and warnings for
  affected users.
- **Known technology exposure**: space weather is an established operational
  risk for satellites, navigation, communication, radio propagation, and power
  grids. That does not prove an AI-infrastructure effect, but it makes external
  space-weather context a reasonable public covariate to log.
- **Public infrastructure status pages**: many AI/developer platforms expose
  current operational status through public status APIs. These are coarse,
  vendor-authored signals, not complete telemetry.
- **Baseline-first anomaly research**: before testing any hypothesis, define
  sources, timestamps, missing-data behavior, and null periods.
- **Event-time-series methodology**: overlaps between two event streams need
  explicit windows, lag assumptions, false-positive control, and randomization
  or permutation-style null checks before they are interpreted.
- **Goodhart/Clever-Hans caution**: if an AI assistant is told what pattern to
  expect, it may narrate that pattern. The collector therefore stays boring and
  mechanical.
- **Stateful-agent observability**: public status streams can later become one
  external layer in a larger stateful-agent observatory, while private local
  signals remain private.
- **Biological-signal leads**: ideas such as solar-induced chlorophyll
  fluorescence (SIF), magnetoreception, or microbial/plant stress responses are
  treated here only as future public-data leads. They are not used as evidence
  for infrastructure claims unless added through separate sources and a
  documented analysis plan.

The private Theseus lab may import public daily reports later, but private
analysis and local signals stay outside this public repository.

## Public Works And Data Sources To Start From

These links define the first layer of the project and make the README easier to
index for people working on similar questions:

- NOAA SWPC Planetary K-index:
  <https://www.spaceweather.gov/products/planetary-k-index>
- NOAA SWPC public JSON products:
  <https://services.swpc.noaa.gov/products/>
- NOAA/NESDIS overview of space-weather disruption risks:
  <https://www.nesdis.noaa.gov/news/safeguarding-satellites-how-noaa-monitors-space-weather-prevent-disruptions>
- NOAA report on social and economic impacts of space weather:
  <https://www.weather.gov/media/news/SpaceWeatherEconomicImpactsReportOct-2017.pdf>
- OpenAI public status:
  <https://status.openai.com/>
- GitHub Status API:
  <https://www.githubstatus.com/api>
- Hugging Face public status:
  <https://status.huggingface.co/>
- Event coincidence analysis for event time series:
  <https://www.stockholmresilience.org/publications/publications/2017-01-04-event-coincidence-analysis-for-quantifying-statistical-interrelationships-between-event-time-series.html>
- False-positive control in time-series coincidence detection:
  <https://arxiv.org/html/2512.17372v2>
- NASA Earthdata introduction to SIF as a vegetation-stress/productivity signal:
  <https://www.earthdata.nasa.gov/learn/trainings/solar-induced-fluorescence-sif-observations-assessing-vegetation-changes-related>

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
