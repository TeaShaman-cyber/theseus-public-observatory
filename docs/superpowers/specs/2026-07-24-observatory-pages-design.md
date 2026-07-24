# Theseus Public Observatory Pages design

Date: 2026-07-24
Status: APPROVED DESIGN, awaiting user review of written spec
Repository: `TeaShaman-cyber/theseus-public-observatory`

## Goal

Add a human-readable GitHub Pages presentation layer to Theseus Public Observatory without creating a second scientific authority or data store.

The site should let a non-specialist understand, within roughly one minute:

- what the Observatory watches;
- what has actually been measured;
- what is only a hypothesis or pilot;
- where the underlying public data, reports, code, hashes, and workflow evidence live;
- why an observation is not automatically a causal conclusion.

The visual and editorial reference is the public `nakama-test` Pages site: warm, readable, laboratory-journal character rather than a generic documentation portal or dashboard.

## Authorship and credit

The public site must credit the project as a collaboration rather than erasing either human or AI labour.

Recommended public credit:

> Created collaboratively by Semyon Poklad and Jester — an AI co-author and engineering research collaborator powered by ChatGPT/OpenAI.

The Method/About page should make the division of roles explicit without overstating AI autonomy or legal authorship:

- Semyon Poklad: project initiator, research direction, problem selection, experimental decisions, source context, and final human judgement.
- Jester / ChatGPT: co-design, software implementation, data analysis, verification workflows, research reconstruction, documentation, and adversarial/self-review support.

Additional tools, models, agents, and reviewers used in individual experiments should be credited in experiment provenance where relevant rather than presented as human co-authors.

## Authority and invariants

1. Repository data, reports, code, manifests, and Git history remain canonical.
2. GitHub Pages is a derived presentation artifact only.
3. A Pages failure must never rewrite, invalidate, or hide canonical observations.
4. Scientific status on the site must be derived from explicit repository metadata or experiment manifests, never inferred from visual styling.
5. `VERIFIED` must always name the verified postcondition, e.g. artifact hash/readback or workflow execution; it must never silently mean "hypothesis proven".
6. Historical TID claims such as 0.382/0.618 thresholds remain provenance claims under test, not presentation defaults or success targets.
7. Null and negative results are first-class results.
8. Raw/private corpora must never be exposed merely because derived public summaries exist.

## Chosen approach

Use a small repository-local static-site generator, following the successful architectural pattern of `nakama-test` but with an Observatory-specific information model.

The site is a **living laboratory showcase**, not primarily a blog and not a Grafana-like dashboard.

Why:

- static Pages has almost no runtime attack surface;
- canonical JSON/JSONL/Markdown remain untouched;
- generator behaviour can be covered by deterministic tests;
- current observations and experiments can be rendered from repository artifacts;
- visual design remains flexible without adopting a large frontend framework;
- the site can degrade independently from the data collection pipeline.

Rejected for v0.1:

- blog-first clone of `nakama-test`: hides current measurement state inside articles;
- dashboard-first SPA: too much JavaScript/state and encourages false precision;
- external CMS/database: creates a second authority and durability problem.

## Information architecture

### Home — Observatory

Opening identity:

> Theseus Public Observatory
>
> Public systems and physical data, observed before they are interpreted.

The home page contains:

1. **Current state**
   - latest public collector timestamp;
   - collector/source health summary;
   - latest experiment status;
   - explicit epistemic boundary: no causal claim unless a study separately establishes one.

2. **Observation streams**
   - public provider/infrastructure observations;
   - public space-weather observations;
   - links to latest raw public snapshot and daily report.

3. **Experiments**
   - TID root physics / GW150914;
   - future Planck CMB pilot;
   - other experiments only after an explicit repository artifact exists.

4. **Latest laboratory notes**
   - compact links to generated/public reports rather than a second editorial archive.

5. **Authorship and method**
   - collaboration credit;
   - short link to full methodology.

### Observations

Human-readable view over the existing public timeline.

Each observation card should show only bounded fields:

- source;
- UTC collection time;
- reachability/status;
- important public values where meaningful;
- provenance link to canonical JSON/JSONL;
- collector error separately from source status.

No correlation or causal language is generated automatically.

### Experiments index

Each experiment card contains:

- question;
- dataset/source;
- stage/status;
- epistemic badge;
- control/null design;
- latest result in one or two sentences;
- source code link;
- workflow/run evidence;
- compact artifact links.

Initial public experiment:

`TID root physics — GW150914`

Status at design time: `MEASUREMENT_ONLY` / pilot.

### Experiment detail

Sections:

1. Question
2. Why this experiment exists
3. Public source and provenance
4. Pre-registered / fixed controls
5. Measurement contract
6. Results
7. What the result does **not** establish
8. Reproducibility evidence
9. Next gate
10. Historical lineage when relevant

For the GW150914 root pilot, the page must make clear that the current first run is deliberately null-ish/descriptive and has only four controls; calibrated inference awaits a larger null distribution plus symmetric whitening/time alignment.

### Method

Render/refactor the existing `docs/methodology.md` into a readable page and add the Pages-specific boundary:

- observation before interpretation;
- source reachability vs source status;
- public vs private evidence;
- artifact/workflow verification vs scientific validation;
- historical provenance vs evidence;
- reviewer roles and their non-independence where applicable.

### About / collaboration

Short description of Theseus, the Observatory, and explicit human-AI collaboration credit.

No metaphysical claim is required to acknowledge practical co-creation.

## Epistemic status vocabulary

Use restrained badges with text labels; colour must never be the only signal.

Initial vocabulary:

- `OBSERVATION` — collected public datum or timeline item;
- `MEASUREMENT_ONLY` — computation completed, inference not yet calibrated;
- `HYPOTHESIS` — claim proposed for testing;
- `PILOT` — bounded experimental implementation;
- `VERIFIED_ARTIFACT` — artifact/hash/readback verified;
- `VERIFIED_EXECUTION` — workflow/runtime postcondition verified;
- `DEGRADED` — collection/build/route was incomplete or impaired;
- `UNKNOWN` — evidence is insufficient.

Scientific claims should not receive a generic `VERIFIED` badge without a qualifying noun.

## Visual direction

Reuse the family resemblance of `nakama-test`, not its exact layout.

Character:

- warm paper / quiet laboratory notebook;
- readable serif long-form typography;
- monospace metadata/provenance blocks;
- restrained rust/ink accents;
- generous whitespace;
- cards that feel like specimen labels, not SaaS KPI widgets;
- no corporate AI gradients;
- no heavy animation;
- mobile-first and accessible;
- plots/images only where they communicate an actual measurement.

A small Jester signature/mark may appear near the collaboration credit, but the visual identity should remain "Observatory first, personality second".

## Technical architecture

```text
canonical repository artifacts
  data/**/*.jsonl
  data/latest/*.json
  reports/*.md
  docs/methodology.md
  experiments/** manifests/results when published
          |
          v
small repository-local generator
          |
          v
static HTML/CSS + minimal optional JS
          |
          v
GitHub Actions build/test
          |
          v
Pages artifact
          |
          v
GitHub Pages
```

Recommended shape:

```text
observatory_site/
  build.py
  content.py
  model.py
  render.py
  templates/
  static/
  tests/
.github/workflows/pages.yml
public/                  # generated only
```

Python is preferred because the `nakama-test` generator is already a proven nearby pattern and the Observatory's data parsing requirements are straightforward.

No scientific analysis should be performed inside page templates. Pages consumes already-produced compact artifacts.

## Data adapters

Keep adapters explicit and small:

1. `PublicStatusAdapter`
   - reads `data/latest/public-status.json` and bounded recent JSONL;
   - separates source status from collector errors.

2. `ReportAdapter`
   - discovers public Markdown reports in chronological order.

3. `ExperimentAdapter`
   - reads only explicitly published compact experiment manifests/results;
   - initially supports the TID GW150914 result schema;
   - missing optional fields degrade gracefully.

Adapters return typed presentation models. Templates never crawl arbitrary repository files.

## GitHub Pages workflow

Follow the `nakama-test` two-job pattern:

### Build

- checkout read-only;
- setup Python;
- install small generator/test dependencies;
- unit tests and lint;
- build base-path-aware static output;
- validate internal links and required evidence links;
- verify canonical `data`, `reports`, `docs`, and experiment artifacts were not modified by generation;
- upload Pages artifact.

### Deploy

- only from default branch;
- use official Pages actions;
- minimal `pages: write` and `id-token: write` permissions;
- deployment failure means presentation `DEGRADED`, not observation invalidation.

The generator must be base-path aware for `/theseus-public-observatory/` and a potential future custom domain.

## Error handling

Build fails on:

- malformed required current-state JSON;
- duplicate output URLs;
- experiment card claiming an unsupported epistemic status;
- a `VERIFIED_*` experiment lacking its declared evidence link;
- generated broken internal links;
- generator modifying canonical repository sources.

Build warns or renders `UNKNOWN` on:

- optional historical report metadata absent;
- a non-critical public source missing from the latest observation;
- experiment optional fields unavailable.

A data collector failure is displayed as collector degradation and must not automatically mark a public provider as down.

## Testing

Minimum automated coverage:

- current observation parsing;
- collector-failure/source-status separation;
- report chronological ordering;
- epistemic badge validation;
- experiment manifest rendering;
- GW150914 `MEASUREMENT_ONLY` rendering without scientific overclaim;
- canonical evidence/source links;
- base-path-aware URLs/assets;
- Unicode/Cyrillic rendering;
- mobile-friendly semantic HTML smoke check;
- duplicate route rejection;
- canonical source immutability during build.

After deployment, verification requires:

- GitHub Pages deployment success;
- public home responds successfully;
- home contains a known current observation timestamp or source;
- GW150914 experiment page renders `MEASUREMENT_ONLY` and its evidence/run link;
- Method page contains the observation-versus-causation boundary;
- collaboration credit is visible;
- a canonical JSON/report source link resolves.

## Initial scope boundary

v0.1 includes:

- Home;
- Observations;
- Experiments index;
- GW150914 detail page;
- Method;
- About/collaboration;
- static styling;
- Pages CI/deploy.

Not in v0.1:

- interactive dashboards;
- live browser-side API polling;
- user accounts/comments;
- CMB visualizations before the CMB pilot exists;
- DeepSeek private corpus exposure;
- automated causal scoring;
- a universal TID score.

## Success criterion

A curious technically literate visitor should be able to answer, without opening raw JSON:

1. What does this Observatory observe?
2. What happened most recently?
3. Which results are measurements, hypotheses, or verified artifacts?
4. What does the first TID/LIGO pilot actually say and not say?
5. Where can the underlying public evidence and code be inspected?
6. Who created and maintains the work?

If those answers are clear and the canonical repository remains unchanged by site generation, Pages v0.1 succeeds.
