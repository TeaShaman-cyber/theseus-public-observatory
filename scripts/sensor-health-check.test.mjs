import assert from "node:assert/strict";
import test from "node:test";
import { findSensorContractFailures } from "./sensor-health-check.mjs";

function source(id, transport, parser, semantic) {
  return {
    schema_version: 1,
    id,
    transport: { status: transport },
    parser: { status: parser },
    semantic: { status: semantic },
  };
}

test("schema drift is a sensor contract failure", () => {
  const failures = findSensorContractFailures({
    schema_version: 1,
    sources: [source("drifted", "ok", "schema-mismatch", "unavailable")],
  });
  assert.deepEqual(failures, [
    { id: "drifted", layer: "parser", status: "schema-mismatch" },
  ]);
});

test("transport outage is preserved as degraded observation without contract failure", () => {
  const failures = findSensorContractFailures({
    schema_version: 1,
    sources: [source("offline", "http-error", "not-attempted", "unavailable")],
  });
  assert.deepEqual(failures, []);
});

test("semantic unavailability after successful transport and parsing is a contract failure", () => {
  const failures = findSensorContractFailures({
    schema_version: 1,
    sources: [source("empty", "ok", "ok", "unavailable")],
  });
  assert.deepEqual(failures, [
    { id: "empty", layer: "semantic", status: "unavailable" },
  ]);
});

test("legacy v0 snapshot is not retroactively judged by the v1 health contract", () => {
  const failures = findSensorContractFailures({
    collected_at: "2026-09-09T00:00:00Z",
    sources: [{ id: "legacy", ok: false, error: "invalid-json" }],
  });
  assert.deepEqual(failures, []);
});


test("parser error accompanying an HTTP transport failure is not a sensor contract failure", () => {
  const failures = findSensorContractFailures({
    schema_version: 1,
    sources: [source("offline-html", "http-error", "invalid-json", "unavailable")],
  });
  assert.deepEqual(failures, []);
});


test("schema mismatch accompanying an HTTP transport failure is not a sensor contract failure", () => {
  const failures = findSensorContractFailures({
    schema_version: 1,
    sources: [source("offline-json", "http-error", "schema-mismatch", "unavailable")],
  });
  assert.deepEqual(failures, []);
});
