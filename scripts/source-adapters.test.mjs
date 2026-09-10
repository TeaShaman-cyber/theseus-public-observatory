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

test("Statuspage adapters reject empty source-status fields", () => {
  for (const adapter of ["statuspage-status-v1", "statuspage-summary-v1"]) {
    const result = summarizeSource(
      { id: "statuspage", adapter },
      { status: { indicator: "   ", description: "" } },
    );
    assert.equal(result.ok, false, adapter);
    assert.equal(result.error, "schema-mismatch", adapter);
  }
});

test("NOAA Kp adapter rejects values outside the physical 0-9 scale", () => {
  for (const Kp of [-1, 9.01, 999]) {
    const result = summarizeSource(
      { id: "noaa_planetary_k_index", adapter: "noaa-kp-v1" },
      [{ time_tag: "2026-09-10T04:30:00", Kp }],
    );
    assert.equal(result.ok, false, String(Kp));
    assert.equal(result.error, "schema-mismatch", String(Kp));
  }
});


test("Hugging Face adapter rejects blank aggregate states", () => {
  for (const indicator of ["", "   "]) {
    const result = summarizeSource(
      { id: "huggingface_status", adapter: "huggingface-status-v1" },
      { data: { attributes: { aggregate_state: indicator } }, included: [] },
    );
    assert.equal(result.ok, false, JSON.stringify(indicator));
    assert.equal(result.error, "schema-mismatch", JSON.stringify(indicator));
  }
});

test("NOAA Kp adapter rejects blank or unparseable timestamps", () => {
  for (const time_tag of ["", "   ", "not-a-timestamp"]) {
    const result = summarizeSource(
      { id: "noaa_planetary_k_index", adapter: "noaa-kp-v1" },
      [{ time_tag, Kp: 4.67 }],
    );
    assert.equal(result.ok, false, JSON.stringify(time_tag));
    assert.equal(result.error, "schema-mismatch", JSON.stringify(time_tag));
  }
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

test("NOAA scales adapter rejects null measured scale values", () => {
  for (const slot of ["-1", "0"]) {
    const payload = {
      "-1": noaaScaleEntry("0"),
      "0": noaaScaleEntry("1"),
      "1": noaaScaleEntry(null),
    };
    payload[slot].R.Scale = null;
    const result = summarizeSource(
      { id: "noaa_scales", adapter: "noaa-scales-v1" },
      payload,
    );
    assert.equal(result.ok, false);
    assert.equal(result.error, "schema-mismatch");
  }
});

test("NOAA scales adapter rejects non-scale measured strings", () => {
  const result = summarizeSource(
    { id: "noaa_scales", adapter: "noaa-scales-v1" },
    { "0": noaaScaleEntry("banana") },
  );
  assert.equal(result.ok, false);
  assert.equal(result.error, "schema-mismatch");
});

test("NOAA scales adapter rejects measured values outside the NOAA 0-5 scale", () => {
  for (const scale of ["6", "-1", "01"]) {
    const result = summarizeSource(
      { id: "noaa_scales", adapter: "noaa-scales-v1" },
      { "0": noaaScaleEntry(scale) },
    );
    assert.equal(result.ok, false, scale);
    assert.equal(result.error, "schema-mismatch", scale);
  }
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

test("NOAA scales adapter rejects forecast-only payloads without a measured scale", () => {
  const result = summarizeSource(
    { id: "noaa_scales", adapter: "noaa-scales-v1" },
    { "1": noaaScaleEntry(null) },
  );
  assert.equal(result.ok, false);
  assert.equal(result.error, "schema-mismatch");
});


test("NOAA scales adapter rejects invalid observation timestamps", () => {
  const badEntries = [
    { ...noaaScaleEntry("1"), DateStamp: "" },
    { ...noaaScaleEntry("1"), DateStamp: "banana" },
    { ...noaaScaleEntry("1"), DateStamp: "2026-02-30" },
    { ...noaaScaleEntry("1"), TimeStamp: "" },
    { ...noaaScaleEntry("1"), TimeStamp: "25:99:00" },
  ];
  for (const entry of badEntries) {
    const result = summarizeSource(
      { id: "noaa_scales", adapter: "noaa-scales-v1" },
      { "0": entry },
    );
    assert.equal(result.ok, false, JSON.stringify(entry));
    assert.equal(result.error, "schema-mismatch", JSON.stringify(entry));
  }
});
