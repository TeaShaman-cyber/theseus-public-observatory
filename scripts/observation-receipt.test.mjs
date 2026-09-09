import assert from "node:assert/strict";
import test from "node:test";
import { buildRunMetadata, createSourceReceipt } from "./observation-receipt.mjs";

const source = {
  id: "example",
  label: "Example",
  url: "https://example.test/status",
  adapter: "example-v1",
};

test("healthy source receipt separates transport parser and semantic health", () => {
  const receipt = createSourceReceipt({
    source,
    httpStatus: 200,
    latencyMs: 12,
    contentType: "application/json",
    payloadText: '{"value":1}',
    transportStatus: "ok",
    parserStatus: "ok",
    adapterResult: { ok: true, summary: { value: 1 }, error: null },
  });

  assert.equal(receipt.schema_version, 1);
  assert.equal(receipt.ok, true);
  assert.equal(receipt.transport.status, "ok");
  assert.equal(receipt.parser.status, "ok");
  assert.equal(receipt.semantic.status, "available");
  assert.match(receipt.payload_sha256, /^[0-9a-f]{64}$/);
  assert.equal(receipt.summary.value, 1);
});

test("schema mismatch remains distinct from successful transport", () => {
  const receipt = createSourceReceipt({
    source,
    httpStatus: 200,
    latencyMs: 7,
    contentType: "application/json",
    payloadText: '{"unexpected":true}',
    transportStatus: "ok",
    parserStatus: "schema-mismatch",
    adapterResult: { ok: false, summary: {}, error: "schema-mismatch" },
  });

  assert.equal(receipt.ok, false);
  assert.equal(receipt.transport.status, "ok");
  assert.equal(receipt.parser.status, "schema-mismatch");
  assert.equal(receipt.semantic.status, "unavailable");
  assert.equal(receipt.error, "schema-mismatch");
});

test("invalid JSON preserves payload identity without claiming semantic data", () => {
  const receipt = createSourceReceipt({
    source,
    httpStatus: 200,
    latencyMs: 5,
    contentType: "text/html",
    payloadText: "<html>not json</html>",
    transportStatus: "ok",
    parserStatus: "invalid-json",
    adapterResult: null,
  });

  assert.equal(receipt.ok, false);
  assert.equal(receipt.parser.status, "invalid-json");
  assert.equal(receipt.semantic.status, "unavailable");
  assert.match(receipt.payload_sha256, /^[0-9a-f]{64}$/);
  assert.equal(receipt.error, "invalid-json");
});

test("run metadata names GitHub execution identity when available", () => {
  const run = buildRunMetadata({
    GITHUB_RUN_ID: "123",
    GITHUB_RUN_ATTEMPT: "2",
    GITHUB_REPOSITORY: "TeaShaman-cyber/example",
    GITHUB_WORKFLOW: "Collect",
    GITHUB_REF: "refs/heads/main",
    GITHUB_SHA: "0123456789abcdef",
  });

  assert.deepEqual(run, {
    github_run_id: "123",
    github_run_attempt: 2,
    github_repository: "TeaShaman-cyber/example",
    github_workflow: "Collect",
    github_ref: "refs/heads/main",
    github_sha: "0123456789abcdef",
    collector: "collect-public-status-v1",
  });
});
