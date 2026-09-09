import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { summarizeSource } from "./source-adapters.mjs";

async function fixture(name) {
  return JSON.parse(await readFile(new URL(`./fixtures/${name}`, import.meta.url), "utf8"));
}

test("Hugging Face adapter extracts aggregate state and resource count", async () => {
  const json = await fixture("huggingface-status.json");
  const result = summarizeSource(
    { id: "huggingface_status", adapter: "huggingface-status-v1" },
    json,
  );
  assert.equal(result.ok, true);
  assert.equal(result.error, null);
  assert.equal(result.summary.indicator, "operational");
  assert.equal(result.summary.description, "Hugging Face status page");
  assert.equal(result.summary.resources, 8);
});

test("Hugging Face adapter rejects a payload without aggregate state", () => {
  const result = summarizeSource(
    { id: "huggingface_status", adapter: "huggingface-status-v1" },
    { data: { attributes: {} }, included: [] },
  );
  assert.equal(result.ok, false);
  assert.equal(result.error, "schema-mismatch");
});

test("NOAA Kp adapter preserves the latest measured Kp value", async () => {
  const json = await fixture("noaa-kp.json");
  const result = summarizeSource(
    { id: "noaa_planetary_k_index", adapter: "noaa-kp-v1" },
    json,
  );
  assert.equal(result.ok, true);
  assert.equal(result.error, null);
  assert.equal(result.summary.rows, 3);
  assert.equal(result.summary.latest.Kp, 4.67);
  assert.equal(result.summary.latest.time_tag, "2026-09-09T06:00:00");
  assert.equal(result.summary.latest.a_running, 30);
  assert.equal(result.summary.latest.station_count, 8);
});

test("NOAA Kp adapter rejects legacy array-row payloads", () => {
  const result = summarizeSource(
    { id: "noaa_planetary_k_index", adapter: "noaa-kp-v1" },
    [["time_tag", "Kp"], ["2026-09-09T06:00:00", "4.67"]],
  );
  assert.equal(result.ok, false);
  assert.equal(result.error, "schema-mismatch");
});
