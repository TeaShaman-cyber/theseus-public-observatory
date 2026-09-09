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

function noaaScaleEntry(scale = "0") {
  return {
    DateStamp: "2026-09-09",
    TimeStamp: "14:50:00",
    R: { Scale: scale, Text: scale === null ? null : "none" },
    S: { Scale: scale, Text: scale === null ? null : "none" },
    G: { Scale: scale, Text: scale === null ? null : "none" },
  };
}

test("NOAA scales adapter accepts structured R/S/G measurements", () => {
  const result = summarizeSource(
    { id: "noaa_scales", adapter: "noaa-scales-v1" },
    { "-1": noaaScaleEntry("0"), "0": noaaScaleEntry("1"), "1": noaaScaleEntry(null) },
  );
  assert.equal(result.ok, true);
  assert.equal(result.error, null);
  assert.equal(result.summary.current.G.Scale, "1");
});

test("NOAA scales adapter rejects an empty selected measurement", () => {
  const result = summarizeSource(
    { id: "noaa_scales", adapter: "noaa-scales-v1" },
    { "0": {} },
  );
  assert.equal(result.ok, false);
  assert.equal(result.error, "schema-mismatch");
});

test("NOAA scales adapter rejects R/S/G shells without scale fields", () => {
  const result = summarizeSource(
    { id: "noaa_scales", adapter: "noaa-scales-v1" },
    { "0": { DateStamp: "2026-09-09", TimeStamp: "14:50:00", R: {}, S: {}, G: {} } },
  );
  assert.equal(result.ok, false);
  assert.equal(result.error, "schema-mismatch");
});
