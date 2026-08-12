# Research index

This is the human-readable front door for the observatory's research notes.
It is intentionally small and versioned with the repository.

## Canonical map

- [Methodology](../methodology.md) — collection rules and interpretation boundary.
- [Space-weather / AI lead ledger](space-weather-llm-leads.md) — leads extracted
  from prior discussions and public sources.
- [Daily reports](../../reports/README.md) — dated source-health summaries.
- [Machine-readable snapshots](../../data/README.md) — public collection output.
- [Public experiments](../../experiments/public/) — explicitly scoped experiment
  inputs and fixtures.

## How the project is organised

The repository uses one source of truth for each kind of material:

| Material | Home | Role |
|---|---|---|
| Collection rules | `docs/methodology.md` | Stable project contract |
| Research leads and source cards | `docs/research/` | Versioned research notebook |
| Public observations | `data/` and `reports/` | Timestamped collector output |
| Reproducible experiments | `experiments/public/` | Explicit inputs and fixtures |
| Concrete work | GitHub Issues / Projects | Tasks, questions, and review |
| Public presentation | GitHub Pages | Derived view, not a second source |

We do not use a separate GitHub Wiki for canonical content. A Wiki can be
added later for onboarding or discussion, but it must link back to these files
instead of becoming a parallel copy.

## Research-note convention

Each lead should say:

1. what was noticed;
2. what source or observation points to it;
3. what layer it belongs to (physical, infrastructure, biological, or AI);
4. what a future check would measure;
5. what remains open.

This keeps an interesting clue visible without silently promoting it into a
project conclusion.

## Small external examples

The shape is informed by a few public patterns:

- [AmberLJC/meta-research](https://github.com/AmberLJC/meta-research) keeps a
  chronological research log next to a structured hypothesis tree.
- [GitHub's planning guidance](https://docs.github.com/en/issues/tracking-your-work-with-issues/learning-about-issues/planning-and-tracking-work-for-your-team-or-project)
  separates durable repository material from Issues and Projects used to plan
  work.
- [juliensimon/space-datasets](https://github.com/juliensimon/space-datasets)
  keeps source-specific scripts, scheduled updates, and generated datasets
  distinct.
- [OpenSpace](https://github.com/OpenSpace/OpenSpace) separates the source
  repository from its larger user-facing documentation surface.

These are patterns to borrow, not dependencies of this project.
