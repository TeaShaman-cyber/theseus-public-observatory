import { createHash } from "node:crypto";

function payloadHash(payloadText) {
  if (typeof payloadText !== "string") return null;
  return createHash("sha256").update(payloadText, "utf8").digest("hex");
}

export function buildRunMetadata(env = process.env) {
  const attempt = Number.parseInt(env.GITHUB_RUN_ATTEMPT ?? "", 10);
  return {
    github_run_id: env.GITHUB_RUN_ID || null,
    github_run_attempt: Number.isFinite(attempt) ? attempt : null,
    github_repository: env.GITHUB_REPOSITORY || null,
    github_workflow: env.GITHUB_WORKFLOW || null,
    github_ref: env.GITHUB_REF || null,
    github_sha: env.GITHUB_SHA || null,
    collector: "collect-public-status-v1",
  };
}

export function createSourceReceipt({
  source,
  httpStatus,
  latencyMs,
  contentType = null,
  payloadText = null,
  transportStatus,
  parserStatus,
  adapterResult = null,
  transportError = null,
}) {
  const semanticAvailable =
    transportStatus === "ok" && parserStatus === "ok" && adapterResult?.ok === true;

  let error = null;
  if (transportStatus !== "ok") {
    error = transportError || transportStatus;
  } else if (parserStatus !== "ok") {
    error = parserStatus;
  } else if (!semanticAvailable) {
    error = adapterResult?.error || "semantic-unavailable";
  }

  return {
    schema_version: 1,
    id: source.id,
    label: source.label,
    url: source.url,
    adapter: source.adapter,
    ok: semanticAvailable,
    http_status: httpStatus,
    latency_ms: latencyMs,
    content_type: contentType,
    payload_sha256: payloadHash(payloadText),
    transport: { status: transportStatus },
    parser: { status: parserStatus },
    semantic: { status: semanticAvailable ? "available" : "unavailable" },
    ...(adapterResult?.summary ? { summary: adapterResult.summary } : {}),
    ...(error ? { error } : {}),
  };
}

export function createSnapshot({ collectedAt, sources, env = process.env }) {
  return {
    schema_version: 1,
    collected_at: collectedAt,
    run: buildRunMetadata(env),
    sources,
  };
}
