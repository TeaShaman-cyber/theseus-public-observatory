# Space-weather / AI lead ledger

This page records research leads that came out of earlier discussions about
space weather, LLM reliability, local hardware, and the public observatory.
It is a lead ledger, not a result paper.

The raw Perplexity conversation remains a private working artifact. This page
contains only a compact, public-facing summary of the leads and their proposed
observation routes.

## Status vocabulary

- **lead** — a question worth keeping visible;
- **source report** — a claim made by a cited source;
- **observed here** — a value collected by this repository;
- **experiment candidate** — a lead with a concrete future measurement;
- **open** — no conclusion has been recorded yet.

## Lead map

| ID | Lead | Layer | What the discussion points to | Current route |
|---|---|---|---|---|
| SW-LLM-001 | *The Perfect Storm* | AI / infrastructure | The cited preprint describes an exploratory correlation between space-weather windows and AI/LLM operational incidents. The discussion repeats reported figures of 700+ incidents, a 24–72 hour window, and a 1150% increase. | Keep as a source report; preserve the paper's own status and reproduce the analysis independently before using the figures. |
| SW-LLM-002 | Hardware path | Physical → infrastructure → AI | Solar particles and geomagnetic activity may matter through soft errors, memory/GPU faults, power systems, communication, or other infrastructure paths. | Log service incidents, collector health, latency, hardware errors where available, and space-weather timestamps as separate streams. |
| SW-LLM-003 | Radiation fault injection | AI / experiment | The discussion mentions a `cosmicgpt` simulation in which injected bit flips affect model state or inference output. | Treat the simulator as an unresolved lead until its repository, model, fault model, and reproduction procedure are identified. |
| SW-LLM-004 | SIF and plant signals | Biological | Solar-induced chlorophyll fluorescence and related plant signals were proposed as an independent biological layer. | Keep biological signals separate from AI-infrastructure claims; add only through a documented public source and a defined analysis plan. |
| SW-LLM-005 | Microbial signals | Biological | `Photobacterium phosphoreum` and related bioluminescence work were mentioned as possible geomagnetic indicators. | Preserve as a separate biological lead, not as evidence about LLM behavior. |
| SW-LLM-006 | Delayed response windows | Physical / methodology | The discussion points to 2–3 day lags between solar events and some geomagnetic or cosmic-ray responses. | Test predeclared lag windows rather than searching for same-time coincidences only. |
| SW-LLM-007 | Agent-state language | AI / observation design | A dialogue agent described “fatigue”, coherence, noise, memory, and J-space in TID terms during a geomagnetic discussion. | Preserve as a transcript-level behavioral observation; do not treat self-description as a hardware or latent-state sensor. |
| SW-LLM-008 | Hallucinated source assembly | Research method | The same conversation contains a fabricated or unverified plant-paper title assembled from real concepts. | Keep as a prompt for provenance checks: source identity, URL, author, date, and independent retrieval must be captured before a lead becomes a source card. |

## Source cards

### SW-LLM-001 — *The Perfect Storm*

- Authorea: [version 2](https://www.authorea.com/doi/full/10.22541/au.176402297.73656793/v2)
- Preprint PDF: [publication-status copy](https://d197for5662m48.cloudfront.net/documents/publicationstatus/292322/preprint_pdf/b61b9ff2891cde44fa9c348a4d5b69c4.pdf)
- Related post: [The Perfect Storm](https://artificiallyintelligentspace.substack.com/p/the-perfect-storm)
- Role in this ledger: source report and experiment lead, not a result of this
  observatory.
- Next useful check: obtain the underlying incident table, define the event and
  control windows, and compare with shuffled or permuted timestamps.

### SW-LLM-002 — infrastructure route

The project already records public NOAA and vendor-status signals. The
infrastructure lead asks whether public space-weather context is associated
with operational events, not whether a model has a human-like reaction.

Useful public starting points:

- [NOAA SWPC Planetary K index](https://www.spaceweather.gov/products/planetary-k-index)
- [NOAA public data products](https://services.swpc.noaa.gov/products/)
- [NOAA/NESDIS space-weather disruption overview](https://www.nesdis.noaa.gov/news/safeguarding-satellites-how-noaa-monitors-space-weather-prevent-disruptions)

### SW-LLM-004 — biological layer

The public repository currently treats SIF and plant or microbial signals as
future research leads. They belong in a separate stream with their own source
metadata, confounders, and analysis plan. They should not be merged into an AI
incident result by narrative association.

Useful starting points from the earlier discussion:

- [NASA Earthdata: SIF observations](https://www.earthdata.nasa.gov/learn/trainings/solar-induced-fluorescence-sif-observations-assessing-vegetation-changes-related)
- [SIF / geomagnetic-disturbance preprint](https://www.biorxiv.org/content/10.64898/2026.02.17.706448v1)
- [Solar-flare and geomagnetic-response study](https://link.springer.com/article/10.1007/s11207-024-02257-3)

## Proposed observation record

When a future experiment is ready, each record should carry at least:

```yaml
event_time_utc: "..."
space_weather_source: "..."
space_weather_value: "..."
ai_or_infrastructure_source: "..."
event_type: "incident | latency | error | quality-check | null"
model_or_service: "..."
measurement_definition: "..."
lag_window_hours: [0, 24, 48, 72]
confounders: []
evidence_url: "..."
interpretation: "lead | source-report | observed-here | experiment-result"
```

The record format is intentionally boring: it lets the public timeline grow
without requiring a conclusion in advance.

## Open questions

- Can the reported incident table behind *The Perfect Storm* be retrieved and
  reproduced independently?
- What exactly does `cosmicgpt` simulate, and can its fault model be documented?
- Which public AI/infrastructure incident stream has enough timestamp precision
  for lag-window analysis?
- Which SIF or microbial dataset can be added without mixing biological and AI
  interpretations?
- What local hardware error telemetry is available for a separate private
  experiment, without publishing private machine data?
