# Observatory review contract

Run `bash tools/dev/check` before model review. Required deterministic
CI checks must pass on the current PR head; advisory CRAP scores are not
merge thresholds. Follow issue-first change control.

## Codex review

For material changes inspect the bot-authored PR comments and reviews for
the exact current head SHA, not only the GitHub review decision. A
`codex-review-state:v1` receipt with completed code_review and no unresolved
findings is evidence of completed review. If absent or stale after CI,
request `@codex review` on the PR and check the exact head again. An older
review, reaction alone, or empty review list is not proof of completion.
Resolve material findings and repeat review on changed heads.

Codex availability is not a hard dependency for routine Observatory changes.
On quota rejection, service failure or a bounded wait without a terminal
receipt, inspect the current bot state first; allow one manual re-request
when reasonable (do not loop or hammer a quota limit). Record the exact head,
observed failure or absence, attempt(s), deterministic QA evidence and
risk-proportional alternative review/disposition in the covering issue/PR.
Use CODEX_UNAVAILABLE or CODEX_DEFERRED, never claim CODEX_PASS without
a receipt. A routine merge may proceed with that explicit disposition
only when all other applicable gates pass and no unresolved material
findings or blockers remain. High-risk changes requiring independent
review need a suitable independent reviewer; lack of Codex does not
waive that requirement. Do not change branch protections or app
permissions to force promotion. Later findings remain actionable debt.
This is Observatory-specific, not a change to other repositories.

## Review focus

- Preserve append-only raw evidence, source identities, timestamps and hashes;
  projections must not silently replace or rewrite observations.
- Distinguish unavailable, missing, zero, provisional and definitive data.
  Failed transport/parser/semantic receipts must not become measurements.
- Check bounded remote reads, source terms, and honest coverage/causality
  claims. Mechanical lint, fixtures and mutation checks belong in CI.
