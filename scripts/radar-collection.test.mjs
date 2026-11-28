import assert from "node:assert/strict";
import test from "node:test";
import { fetchRadar, radarRoles } from "./radar-collection.mjs";

test("missing worker output records each planned source as unavailable", async () => {
  const rows = await fetchRadar(async () => { throw new Error("sensitive diagnostic"); });
  assert.equal(rows.length, 8);
  assert.deepEqual(rows.map(r => r.id), radarRoles.map(r => r.id));
  assert.ok(rows.every(r => !r.ok && r.error === "radar-worker-failed" && r.semantic.status === "unavailable"));
  assert.doesNotMatch(JSON.stringify(rows), /sensitive diagnostic/);
});

test("incomplete or duplicate worker receipts fail closed", async () => {
  for (const bad of [[], [radarRoles[0]], Array(8).fill(radarRoles[0])]) {
    const rows = await fetchRadar(async () => ({stdout: JSON.stringify(bad)}));
    assert.equal(rows.length, 8);
    assert.ok(rows.every(r => r.error === "radar-worker-failed"));
  }
});

test("real worker without credential preserves all eight failure receipts", async () => {
  const rows = await fetchRadar(undefined, {...process.env, CLOUDFLARE_RADAR_TOKEN: ""});
  assert.equal(rows.length, 8);
  assert.ok(rows.every(r => !r.ok && r.error === "auth-required" && r.observed_at));
});

test("archive validation rejects invalid normalized data and unavailable measurements", async () => {
  const { validateRadarReceipt } = await import("./radar-collection.mjs");
  const role = radarRoles[0];
  const row = {
    ...role, schema_version: 1, ok: true, http_status: 200, latency_ms: 5,
    observed_at: "2026-11-28T10:30:00Z", payload_sha256: "a".repeat(64),
    transport: {status: "ok"}, parser: {status: "ok"}, semantic: {status: "available"},
    summary: {
      provider: role.provider, metric: role.metric, normalization: "MIN0_MAX",
      agg_interval: "FIFTEEN_MINUTES", source_unit: "requests", value_unit: "window_max_fraction",
      attribution: "Cloudflare Radar", license: "CC BY-NC 4.0",
      window_start: "2026-11-27T10:00:00Z", window_end: "2026-11-28T10:00:00Z",
      last_updated: "2026-11-28T10:00:00Z", expected_samples: 97,
      samples: 1, coverage: "partial", points: [{measured_at: "2026-11-28T09:45:00Z", value: 0.5}],
    },
  };
  validateRadarReceipt(row);
  for (const patch of [{value: 1.01}, {value: -0.01}, {value: null}, {measured_at: "2026-11-28T09:46:00Z"}]) {
    const bad = structuredClone(row);
    Object.assign(bad.summary.points[0], patch);
    assert.throws(() => validateRadarReceipt(bad));
  }
  assert.throws(() => validateRadarReceipt({...row, ok: false, semantic: {status: "unavailable"}}));
});
