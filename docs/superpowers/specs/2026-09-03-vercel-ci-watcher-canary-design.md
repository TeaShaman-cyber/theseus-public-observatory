# Vercel CI Watcher Canary Design

## Status

Approved direction: test Vercel first as an external CI watcher substrate that does not depend on ChatGPT Tasks.

Related research issue: #7 `Research: free external scheduler and webhook substrate for CI monitoring`.

## Goal

Build a minimal, independently observable Vercel canary that can receive GitHub workflow-style events, normalize them into compact receipts, expose readback, and run a cron-based reconciliation check for stale or missed events.

This is **not** a production watcher yet. It is a bounded research canary for Vercel capability, cost, persistence, and operability from the ChatGPT Vercel connector.

## Architecture

```text
synthetic GitHub-like workflow_run event
              |
              v
      POST /api/github-event
              |
              v
 validate + normalize receipt
              |
              v
       append durable state
              |
              +-------------------+
              |                   |
              v                   v
      GET /api/receipts     GET /api/reconcile
                                  ^
                                  |
                             Vercel Cron
```

Event-first is the primary path. Cron exists only as a reconciliation safety net.

## Canary scope

### Included

- one new Vercel project under the already-authorized Hobby team;
- one minimal HTTP receiver for synthetic GitHub `workflow_run`-shaped payloads;
- deterministic normalization into a compact JSON receipt;
- durable append/readback storage suitable for the canary;
- a reconciliation endpoint that reports whether the latest expected event is fresh, stale, or absent;
- one Vercel cron invoking reconciliation;
- runtime logging sufficient to verify execution without exposing secrets;
- synthetic event tests only;
- measurement of Vercel requests, execution behavior, latency, and storage operations where observable;
- connector-based deployment/readback/log inspection when supported.

### Excluded

- no GitHub webhook secret yet;
- no live GitHub webhook registration yet;
- no GitHub write-back, issue comments, `repository_dispatch`, or workflow reruns;
- no Needle experiment authority changes;
- no ChatGPT Task dependency;
- no Cloudflare/Deno/Netlify integration in this canary;
- no production SLA claim.

## Endpoints

### `POST /api/github-event`

Accepts a synthetic payload shaped like the subset of GitHub `workflow_run` needed by the watcher.

Required logical fields:

```json
{
  "repository": "owner/repo",
  "workflow_run": {
    "id": 33722433205,
    "name": "Needle Stage B full",
    "status": "in_progress",
    "conclusion": null,
    "head_sha": "...",
    "run_started_at": "...",
    "updated_at": "..."
  }
}
```

The receiver must reject malformed inputs and must not silently invent missing authority fields.

### Normalized receipt

```json
{
  "schema_version": 1,
  "source": "synthetic_github_workflow_run",
  "repository": "owner/repo",
  "workflow_run_id": 33722433205,
  "workflow_name": "Needle Stage B full",
  "status": "in_progress",
  "conclusion": null,
  "head_sha": "...",
  "source_updated_at": "...",
  "received_at": "...",
  "receipt_id": "sha256:..."
}
```

`receipt_id` is deterministic over canonical normalized content excluding `received_at`, so duplicate delivery can be detected without pretending two receipts are different events.

### `GET /api/receipts`

Returns a bounded newest-first view of stored canary receipts. It is for research readback, not an unbounded public event log.

### `GET /api/reconcile`

Returns one of:

- `FRESH` — a matching latest receipt exists inside the configured freshness window;
- `STALE` — latest matching receipt exists but is older than the freshness window;
- `ABSENT` — no matching receipt exists;
- `INCONCLUSIVE_STORAGE` — storage/readback failed.

The endpoint must preserve `ABSENT` vs `STALE`; they are not equivalent.

## Persistence

The canary requires durable state that survives Vercel function invocations and deployments.

Preferred order:

1. use a free Vercel-native durable store available to the authorized Hobby account if it can be created without paid commitment;
2. if no suitable free native durable store is available through the connector, use a minimal GitHub-backed receipt path only if it can remain read-only/write-bounded and does not blur watcher authority;
3. otherwise stop at `INCONCLUSIVE_STORAGE` rather than pretending ephemeral function filesystem is durable.

Ephemeral local filesystem is explicitly **not** accepted as durable evidence.

## Cron

Cron invokes `/api/reconcile`; it does not poll GitHub directly in the first canary.

Reason: the first experiment isolates Vercel scheduling and state behavior from GitHub API authentication/quotas.

The schedule must be low frequency and Hobby-compatible. Exact cadence is selected only after current Vercel Hobby cron limits are verified from authoritative docs/runtime behavior.

## Security

Initial canary uses synthetic events and therefore requires no GitHub secrets.

If `CRON_SECRET` is used, it must live in Vercel environment configuration and must never appear in receipts, source code, logs, issue comments, or ChatGPT output.

Public endpoints must not accept arbitrary command execution, URLs to fetch, or code payloads.

## Authority model

```text
Vercel deployment success
        != watcher correctness

HTTP 2xx from receiver
        != durable receipt verified

cron invocation
        != reconciliation correctness

synthetic canary success
        != live GitHub watcher accepted
```

Primary acceptance authority comes from deterministic tests plus independent readback of the deployed behavior and durable receipt state.

## Acceptance criteria

The Vercel canary is successful only if all are true:

1. project deploys successfully on the existing Hobby team;
2. malformed synthetic event is rejected;
3. valid synthetic event returns a deterministic `receipt_id`;
4. duplicate event delivery does not create a semantically distinct event identity;
5. receipt remains readable across a separate function invocation;
6. reconciliation distinguishes `FRESH`, `STALE`, and `ABSENT` in tests;
7. deployed reconciliation endpoint can be manually invoked and read back;
8. one Vercel cron is visible/configured and invokes reconciliation under the allowed Hobby cadence;
9. runtime logs can be read through the Vercel connector without exposing secrets;
10. the canary records observed request/runtime/storage cost or quota evidence sufficient to classify suitability for #7.

If durable state cannot be established without introducing a paid commitment, final disposition is `INCONCLUSIVE_STORAGE`, not success.

## Expected disposition labels

- `VERCEL_CANARY_ACCEPTED`
- `VERCEL_CANARY_REJECTED_RUNTIME`
- `VERCEL_CANARY_REJECTED_CRON_LIMIT`
- `INCONCLUSIVE_STORAGE`
- `INCONCLUSIVE_CONNECTOR_BOUNDARY`

## Follow-up boundary

Only after an accepted synthetic canary may a second design add:

- real GitHub webhook registration;
- webhook signature verification;
- authenticated GitHub API reconciliation;
- optional issue/repository_dispatch write-back;
- Needle-specific routing.

Those are deliberately not smuggled into this first experiment.
