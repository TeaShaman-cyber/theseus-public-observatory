# Public Signal Registry

This registry is the versioned hypothesis-testing inventory for Observatory sources.
It records why a signal may be useful, how it can be observed, and what would stop
or advance its collection. A registry entry does not assert that the underlying
scientific hypothesis is true and does not authorize collector implementation by
itself.

Issue #14 governs this registry.

## Status vocabulary

- `ACCEPTED` — collected on current main under a defined source-health contract.
- `EVALUATING` — concrete public route exists, but collector admission or research
  use still needs a bounded check.
- `LEAD` — plausible measurable source family; exact public route or use is not
  yet sufficiently defined.
- `PARKED` — potentially useful, but current cost, availability, or research value
  does not justify implementation work.
- `REJECTED` — evaluated and intentionally not pursued; rationale must remain here.

## Admission rule

Exporters exist to test hypotheses, not only after a hypothesis is already
established. A new collector may be proposed when all of the following are true:

1. a bounded hypothesis or control names the observable it needs;
2. an authoritative or otherwise well-provenanced public route exists;
3. timestamp semantics are adequate for the intended test;
4. source-health failure can be observed rather than silently converted into data;
5. legal / licensing / ToS constraints permit sustainable collection;
6. the stream adds information not already captured more cheaply;
7. recurring collection/storage cost is proportionate to expected information value;
8. a narrow implementation issue defines success and stop criteria.

Scientific uncertainty is therefore expected. Missing observability, provenance,
or a bounded test is the blocker — not the fact that the hypothesis remains open.

## Current continuous sources

### OpenAI public status

- **Family:** AI/provider operational telemetry
- **Authority:** OpenAI Statuspage
- **Route:** https://status.openai.com/api/v2/status.json
- **Public boundary:** public vendor endpoint; no private-user telemetry
- **Observable:** aggregate provider status
- **Units/type:** categorical status text
- **Timestamp semantics:** collection receipt timestamp plus provider payload semantics
- **Cadence/latency:** repository scheduled collection; upstream update latency is provider-controlled
- **Retention:** canonical daily JSONL in `data/YYYY-MM-DD/public-status.jsonl`
- **Precision:** collector receipt precision; incident granularity is coarser than user reports
- **Health contract:** `statuspage-status-v1`; transport, parse, schema, and semantic health remain distinct
- **Known gaps/biases:** provider-confirmed state can lag or omit user-visible degradation; aggregate status is coarse
- **Cost:** low
- **Information value:** primary provider-confirmed comparator
- **Research consumers:** issue #11; provider-status lag; provider-vs-social comparisons
- **Privacy/ethics:** low; public aggregate telemetry only
- **Status:** `ACCEPTED`

### GitHub public status

- **Family:** infrastructure control / operational telemetry
- **Authority:** GitHub Status
- **Route:** https://www.githubstatus.com/api/v2/summary.json
- **Public boundary:** public vendor endpoint
- **Observable:** aggregate/component infrastructure status
- **Units/type:** categorical status plus component summary
- **Timestamp semantics:** collection receipt plus provider payload
- **Cadence/latency:** repository scheduled collection; upstream latency provider-controlled
- **Retention:** canonical daily JSONL
- **Precision:** collector receipt precision
- **Health contract:** `statuspage-summary-v1`
- **Known gaps/biases:** GitHub is a control/comparator, not a direct proxy for AI-provider state
- **Cost:** low
- **Information value:** distinguishes provider-specific anomalies from broader developer-infrastructure overlap
- **Research consumers:** issue #11 control; shared-infrastructure/common-mode tests
- **Privacy/ethics:** low
- **Status:** `ACCEPTED`

### Hugging Face public status

- **Family:** independent AI/provider operational telemetry
- **Authority:** Hugging Face Status
- **Route:** https://status.huggingface.co/index.json
- **Public boundary:** public provider endpoint
- **Observable:** aggregate service state and resource count
- **Units/type:** categorical state plus structured service/resource information
- **Timestamp semantics:** collection receipt plus upstream payload
- **Cadence/latency:** repository scheduled collection
- **Retention:** canonical daily JSONL
- **Precision:** collector receipt precision
- **Health contract:** dedicated Hugging Face adapter with semantic validation
- **Known gaps/biases:** status-page granularity; not a measurement of model quality
- **Cost:** low
- **Information value:** independent AI-provider comparator
- **Research consumers:** cross-provider synchrony; provider-specific vs common-mode tests
- **Privacy/ethics:** low
- **Status:** `ACCEPTED`

### NOAA planetary K index

- **Family:** space weather / geomagnetic measurement
- **Authority:** NOAA Space Weather Prediction Center
- **Route:** https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json
- **Public boundary:** public government data product
- **Observable:** planetary Kp
- **Units/type:** Kp on the physical 0–9 scale
- **Timestamp semantics:** upstream observation timestamp preserved by the adapter
- **Cadence/latency:** upstream product cadence; collected on the Observatory schedule
- **Retention:** canonical daily JSONL
- **Precision:** upstream timestamp retained
- **Health contract:** NOAA Kp adapter rejects malformed timestamps, legacy row shapes, and values outside 0–9
- **Known gaps/biases:** planetary aggregate; not a local magnetic-field measurement
- **Cost:** low
- **Information value:** direct geomagnetic covariate
- **Research consumers:** issue #11; lag/null tests; biological-signal hypotheses
- **Privacy/ethics:** low
- **Status:** `ACCEPTED`

### NOAA R/S/G scales

- **Family:** space-weather context
- **Authority:** NOAA Space Weather Prediction Center
- **Route:** https://services.swpc.noaa.gov/products/noaa-scales.json
- **Public boundary:** public government data product
- **Observable:** measured radio-blackout, solar-radiation-storm, and geomagnetic-storm scales
- **Units/type:** R/S/G categorical numeric scales, validated in range 0–5
- **Timestamp semantics:** upstream observation timestamp preserved
- **Cadence/latency:** upstream product cadence; collected on Observatory schedule
- **Retention:** canonical daily JSONL
- **Precision:** upstream timestamp retained
- **Health contract:** structured R/S/G adapter; forecast-only or malformed payloads do not masquerade as measurements
- **Known gaps/biases:** scale products compress physical detail
- **Cost:** low
- **Information value:** event/context discriminator beside Kp
- **Research consumers:** issue #11 event windows; space-weather context
- **Privacy/ethics:** low
- **Status:** `ACCEPTED`

### USNO Sun/Moon and eclipse context

- **Family:** astronomy/context control
- **Authority:** U.S. Naval Observatory Astronomical Applications
- **Routes:** https://aa.usno.navy.mil/api/rstt/oneday ; https://aa.usno.navy.mil/api/moon/phases/date ; https://aa.usno.navy.mil/api/eclipses/solar/year
- **Public boundary:** public government API
- **Observable:** local Sun/Moon events, lunar phases, annual solar-eclipse records
- **Units/type:** event times, phase metadata, eclipse records
- **Timestamp semantics:** requested observer-local date / event timestamps
- **Cadence/latency:** contextual rather than incident-driven; collected with Observatory snapshots
- **Retention:** canonical daily JSONL
- **Precision:** endpoint-specific calendar/time precision
- **Health contract:** USNO adapters validate response family, dates/times, requested year, and semantic availability
- **Known gaps/biases:** annual eclipse endpoint does not establish local visibility
- **Cost:** low
- **Information value:** context and negative-control covariates
- **Research consumers:** seasonality/context checks; negative controls
- **Privacy/ethics:** configured observer location is project context, not private-user telemetry
- **Status:** `ACCEPTED`

## Scientific and experimental source families

### GWOSC / GW150914

- **Family:** gravitational-wave / astrophysical events
- **Authority:** Gravitational Wave Open Science Center
- **Current routes:** GWOSC H1/L1 public strain files recorded in `experiments/public/gw150914.json`
- **Public boundary:** public scientific data
- **Observable:** bounded detector strain around GW150914
- **Units/type:** strain time series
- **Timestamp semantics:** detector/GPS event-window time
- **Cadence/latency:** event/dataset based, not a continuous Observatory collector
- **Retention:** durable experiment descriptor plus source/artifact hashes
- **Health contract:** experiment inputs and result descriptor are versioned; not part of the continuous status collector
- **Known gaps/biases:** one calibration object does not define an event-family distribution
- **Cost:** moderate per experiment; no recurring collection cost currently
- **Information value:** independent physical-event calibration/control stream
- **Research consumers:** GW event-control methods and bounded signal-analysis experiments
- **Privacy/ethics:** low
- **Status:** `ACCEPTED` as an experiment source, **not** as a continuous collector

### Planck / CMB products

- **Family:** cosmology / astrophysical reference data
- **Authority:** exact product/provider not yet selected
- **Route:** `UNKNOWN`
- **Observable:** exact CMB product/anomaly definition remains to be chosen
- **Timestamp semantics:** likely dataset/map based rather than live event time
- **Cadence/latency:** archival
- **Retention:** durable source design mentions a future Planck CMB pilot
- **Health contract:** not defined
- **Known gaps/biases:** may be useful only for bounded dataset experiments, not exporter-style collection
- **Cost:** unknown until a product is selected
- **Information value:** potential independent physical reference; hypothesis consumer still needs narrowing
- **Research consumers:** future bounded CMB experiment only
- **Privacy/ethics:** low
- **Status:** `LEAD`
- **Stop/advance condition:** select an authoritative product and a falsifiable experiment before implementation work

### CERN / LHC public data

- **Family:** accelerator / particle physics
- **Authority:** CERN; exact dataset/stream not selected
- **Route:** `UNKNOWN`
- **Observable:** no specific timestamped public series admitted
- **Timestamp semantics:** unknown until dataset selection
- **Cadence/latency:** unknown
- **Retention:** historical research line only; no current collector
- **Health contract:** not defined
- **Known gaps/biases:** “LHC” is too broad to be a source contract
- **Cost:** unknown
- **Information value:** potentially independent physical-event stream
- **Research consumers:** none sufficiently bounded yet
- **Privacy/ethics:** low
- **Status:** `LEAD`
- **Stop/advance condition:** identify one authoritative timestamped dataset and one research question that benefits from recurring or bounded collection

## Biological source families

These entries exist because biological response is itself an open hypothesis family.
They are not promoted or rejected based on whether the proposed geomagnetic mechanism
is already established.

### Satellite SIF / chlorophyll fluorescence

- **Family:** biological / vegetation remote sensing
- **Authority:** public Earth-observation products; exact production dataset/API still to be selected
- **Reference route:** https://www.earthdata.nasa.gov/learn/trainings/solar-induced-fluorescence-sif-observations-assessing-vegetation-changes-related
- **Observable:** solar-induced chlorophyll fluorescence and derived vegetation-response measures
- **Units/type:** product-dependent radiance/fluorescence variables
- **Timestamp semantics:** satellite acquisition/product time
- **Cadence/latency:** product-dependent
- **Retention:** potentially long historical coverage
- **Health contract:** not defined until a concrete product is selected
- **Known gaps/biases:** seasonality, illumination, temperature, water stress, cloud/retrieval effects, spatial aggregation
- **Cost:** moderate analytical/storage cost
- **Information value:** global biological layer orthogonal to provider telemetry
- **Research consumers:** geomagnetic-vs-biological-response tests; environmental controls
- **Privacy/ethics:** low
- **Status:** `EVALUATING`
- **Evidence note:** the recovered 2026 global SIF/geomagnetic preprint is withdrawn and must not be the sole admission rationale
- **Stop/advance condition:** choose a reproducible public SIF product, establish acquisition/timestamp semantics and controls, then open a narrow collector/experiment issue

### Photobacterium phosphoreum monitoring

- **Family:** biological / microbial bioluminescence
- **Authority:** experimental lineage including Zabolotny Institute of Microbiology and Virology NAS Ukraine, KPI, and Subbotin Institute geomagnetic data
- **Public route:** literature is public/recoverable; a live/raw public bacterial time-series route is not yet established
- **Observable:** luminescence intensity of `P. phosphoreum` (including IMV/UCM B-7071 lineage)
- **Units/type:** experiment-specific luminescence / bioluminescence index
- **Timestamp semantics:** experimental sampling time synchronized to geomagnetic observations
- **Cadence/latency:** experiments include minute/hour aggregations; public ongoing cadence unknown
- **Retention:** literature lineage recovered across 1995–2023; raw-data retention unknown
- **Health contract:** not defined for Observatory
- **Known gaps/biases:** temperature, pH, oxygen, culture density/phase, medium, instrumentation, lag selection, experimental drift
- **Cost:** low if a public stream exists; high if Observatory must run wet-lab culture
- **Information value:** direct biological-response observable with multi-decade experimental lineage
- **Research consumers:** microbial-response hypothesis; biological-vs-geomagnetic lag/control tests
- **Privacy/ethics:** low for public aggregate experimental data
- **Status:** `EVALUATING`
- **Stop/advance condition:** search for recoverable raw/near-raw public time series; if absent, retain as an experimental lead rather than pretending a normal exporter exists

### Fungal / mycelial response

- **Family:** biological / fungal physiology and electrophysiology
- **Authority:** multiple experimental lines; no single Observatory source selected
- **Public route:** papers/datasets vary; no recurring public time series established
- **Observable:** candidate morphology, growth, electrophysiological spikes, impedance/conductivity
- **Units/type:** experiment-dependent
- **Timestamp semantics:** experiment-dependent
- **Cadence/latency:** experiment-dependent
- **Retention:** fragmented scientific datasets/literature
- **Health contract:** not defined
- **Known gaps/biases:** species/strain dependence, moisture, temperature, substrate, electrode geometry, generation/exposure protocol
- **Cost:** potentially high if new wet-lab or hardware collection is required
- **Information value:** independent biological response family; useful for mechanism/disconfirmation as much as positive findings
- **Research consumers:** hypomagnetic-response and environmental-biosensor hypotheses
- **Privacy/ethics:** low
- **Status:** `LEAD`
- **Stop/advance condition:** identify a public dataset or narrowly justified experiment; hypomagnetic morphogenesis results do not by themselves establish a space-weather sensor

## Provider/context expansion leads

### Provider incident history

- **Family:** AI/provider operational telemetry
- **Authority:** provider status history APIs/pages
- **Route:** exact per-provider history route to be selected
- **Observable:** incident start/update/resolve timeline rather than only current aggregate state
- **Timestamp semantics:** provider event timestamps
- **Cadence/latency:** event-driven
- **Cost:** low
- **Information value:** materially improves official-status lag analysis
- **Research consumers:** provider-status lag; historical incident reconstruction
- **Privacy/ethics:** low
- **Status:** `EVALUATING`
- **Stop/advance condition:** prove stable authoritative history route and dedup/update semantics

### Public rollout / changelog timestamps

- **Family:** provider/context
- **Authority:** provider release notes/changelogs
- **Route:** provider-specific; not selected
- **Observable:** documented rollout/change timestamps
- **Timestamp semantics:** publication time is not automatically deployment time
- **Cadence/latency:** irregular
- **Cost:** low to moderate
- **Information value:** control for anomaly proximity to documented product/runtime changes
- **Research consumers:** rollout-proximity hypothesis
- **Privacy/ethics:** low
- **Status:** `LEAD`
- **Stop/advance condition:** select one provider with stable provenance and define publication-vs-deployment semantics

### Public infrastructure/network status control

- **Family:** infrastructure control
- **Authority:** exact provider(s) not selected
- **Route:** `UNKNOWN`
- **Observable:** independent network/cloud/infrastructure incident state
- **Timestamp semantics:** provider incident timeline
- **Cost:** low if status API exists
- **Information value:** separates provider-specific failures from broader infrastructure conditions
- **Research consumers:** shared-infrastructure/common-mode tests
- **Privacy/ethics:** low
- **Status:** `LEAD`

## Social/community signal family

### Public degradation reports

- **Family:** social/community reports
- **Authority:** platform-specific public posts; platform is not an authority for the truth of each report
- **Route:** no platform admitted yet
- **Observable:** bounded aggregate of public reports matching a fixed versioned query/classification contract
- **Units/type:** report receipts plus derived counts/clusters
- **Timestamp semantics:** platform post time; poster local time remains unknown unless independently evidenced
- **Cadence/latency:** potentially near-real-time; platform dependent
- **Retention:** must preserve only what platform/API/ToS and ethics permit
- **Health contract:** must expose search coverage, API failures, ranking changes where observable, and capture provenance
- **Known gaps/biases:** ranking/visibility, duplicate reports, bots/spam, language, selection bias, deleted/edited posts, correlated reposting
- **Cost:** moderate and platform-dependent
- **Information value:** potentially earlier user-visible degradation signal than official provider status
- **Research consumers:** provider-status lag; model/UI/connector/general degradation clustering; multi-platform robustness
- **Privacy/ethics:** elevated relative to other sources; no individual-account surveillance or targeting
- **Status:** `LEAD`
- **Evidence boundary:**

```text
public report != provider-confirmed incident
post count != affected-user count
engagement != severity
poster local time != known unless evidenced
deleted/edited post != stable source unless captured with permitted provenance
```

- **Stop/advance condition:** one platform, one fixed public-report contract, explicit dedup/spam/language handling, and API/ToS review before collector implementation

## Evaluation order

The registry does not rank hypotheses by enthusiasm. Work order follows expected
information gain, public observability, cost, and ability to falsify or distinguish
competing explanations.

Current near-term order:

1. structured/public sources that sharpen existing hypotheses or controls;
2. scientific sources with concrete public datasets and bounded consumers;
3. one social/community pilot after its evidence contract is explicit;
4. sources requiring new wet-lab infrastructure remain research leads unless a
   public dataset or collaboration changes the cost boundary.

## Tooling note

Specialized tools such as smarts.bio may support later biological mechanism or
dataset analysis (sequence, protein/domain, transcriptomic, or related workflows).
They are not Observatory exporters and do not substitute for the Observatory's
time-series, provenance, control, and statistical verification layer.
