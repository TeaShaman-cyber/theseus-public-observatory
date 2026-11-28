import assert from "node:assert/strict";
import test from "node:test";
import { renderReport } from "./collect-public-status.mjs";

function eclipseSource({ available, eventToday = null }) {
  return {
    id: "usno_solar_eclipses",
    label: "USNO Solar Eclipses",
    ok: available,
    latency_ms: 1,
    semantic: { status: available ? "available" : "unavailable" },
    ...(available
      ? { summary: { year: 2026, events: [], event_today: eventToday, local_visibility: "not-provided-by-usno-year-endpoint" } }
      : { error: "schema-mismatch" }),
  };
}

test("eclipse report keeps unavailable distinct from verified none", () => {
  const base = { schema_version: 1, collected_at: "2026-09-10T06:00:00Z" };
  const unavailable = renderReport({ ...base, sources: [eclipseSource({ available: false })] });
  assert.match(unavailable, /Solar eclipse event on this date \(global list\): unknown \(source unavailable\)/);
  assert.doesNotMatch(unavailable, /Solar eclipse event on this date \(global list\): none/);

  const verifiedNone = renderReport({ ...base, sources: [eclipseSource({ available: true })] });
  assert.match(verifiedNone, /Solar eclipse event on this date \(global list\): none/);
});

test("HTTP failures never publish a plausible success body as measurement", async (t) => {
  const { fetchJson } = await import("./collect-public-status.mjs");
  t.mock.method(globalThis, "fetch", async () => new Response(
    '{"status":{"indicator":"none"}}', { status: 503, headers: {"content-type":"application/json"} },
  ));
  const receipt = await fetchJson({id:"test", label:"Test", url:"https://example.test", adapter:"statuspage-status-v1"});
  assert.equal(receipt.http_status, 503);
  assert.equal(receipt.transport.status, "http-error");
  assert.equal(receipt.semantic.status, "unavailable");
  assert.equal(receipt.summary, undefined);
  assert.match(receipt.payload_sha256, /^[a-f0-9]{64}$/);
});

test("network failure does not persist arbitrary upstream error text", async (t) => {
  const { fetchJson } = await import("./collect-public-status.mjs");
  t.mock.method(globalThis, "fetch", async () => { throw new Error("private diagnostic marker"); });
  const receipt = await fetchJson({id:"test", label:"Test", url:"https://example.test", adapter:"statuspage-status-v1"});
  assert.equal(receipt.transport.status, "fetch-error");
  assert.equal(receipt.parser.status, "not-attempted");
  assert.equal(receipt.error, "fetch-failed");
  assert.equal(receipt.http_status, null);
});

test("JSON, schema, timeout and body failures remain distinct", async (t) => {
  const { fetchJson } = await import("./collect-public-status.mjs");
  const source = {id:"test", label:"Test", url:"https://example.test", adapter:"statuspage-status-v1"};
  const fetch = t.mock.method(globalThis, "fetch", async () => new Response("<html>", {status:200}));
  let row = await fetchJson(source);
  assert.equal(row.parser.status, "invalid-json");
  assert.equal(row.transport.status, "ok");
  assert.match(row.payload_sha256, /^[a-f0-9]{64}$/);
  fetch.mock.mockImplementation(async () => new Response("{}", {status:200}));
  row = await fetchJson(source);
  assert.equal(row.parser.status, "schema-mismatch");
  assert.equal(row.semantic.status, "unavailable");
  fetch.mock.mockImplementation(async (_url, {signal}) => new Promise((_resolve,reject) =>
    signal.addEventListener("abort", () => reject(signal.reason), {once:true})));
  row = await fetchJson(source, 5);
  assert.equal(row.transport.status, "timeout");
  fetch.mock.mockImplementation(async () => ({
    status:200, ok:true, headers:new Headers({"content-type":"application/json"}),
    text:async () => { throw new Error("body interrupted"); },
  }));
  row = await fetchJson(source);
  assert.equal(row.transport.status, "fetch-error");
  assert.equal(row.http_status, 200);
  assert.equal(row.payload_sha256, null);
});

test("mixed source outcomes preserve good observations and astronomy date", async (t) => {
  const { collectSnapshot } = await import("./collect-public-status.mjs");
  t.mock.method(globalThis, "fetch", async (url) => {
    if (url.includes("status.openai.com")) return new Response('{"status":{"indicator":"none"}}');
    if (url.includes("githubstatus")) throw new Error("disconnected");
    if (url.includes("huggingface")) return new Response("not json");
    if (url.includes("planetary-k-index")) return new Response('[{"time_tag":"2026-09-10T00:00:00","Kp":0}]');
    return new Response("{}", {status:503});
  });
  const snapshot = await collectSnapshot(new Date("2026-09-10T23:00:00Z"), async () => []);
  assert.equal(snapshot.sources.length, 8);
  const byId = Object.fromEntries(snapshot.sources.map(s => [s.id,s]));
  assert.equal(byId.openai_status.semantic.status, "available");
  assert.equal(byId.github_status.transport.status, "fetch-error");
  assert.equal(byId.huggingface_status.parser.status, "invalid-json");
  assert.equal(byId.noaa_planetary_k_index.summary.latest.Kp, 0);
  assert.equal(byId.usno_sun_moon.observer_local_date, "2026-09-11");
  assert.equal(byId.usno_sun_moon.summary, undefined);
  assert.equal(snapshot.sources.filter(s => s.ok).length, 2);
});

test("concurrent appends preserve existing journal and every new row", async () => {
  const { appendJsonl } = await import("./collect-public-status.mjs");
  const { mkdtemp, readFile, rm, writeFile } = await import("node:fs/promises");
  const { tmpdir } = await import("node:os");
  const { join } = await import("node:path");
  const root = await mkdtemp(join(tmpdir(),"observatory-append-"));
  try {
    const path = join(root,"journal.jsonl");
    await writeFile(path,'{"id":0}\n');
    await Promise.all(Array.from({length:20},(_,i) => appendJsonl(path,{id:i+1})));
    const text = await readFile(path,"utf8");
    assert.ok(text.startsWith('{"id":0}\n'));
    assert.deepEqual(text.trimEnd().split("\n").map(JSON.parse).map(r=>r.id).sort((a,b)=>a-b), Array.from({length:21},(_,i)=>i));
  } finally { await rm(root,{recursive:true,force:true}); }
});

test("adapter exception preserves response provenance and does not claim network outage", async (t) => {
  const { fetchJson } = await import("./collect-public-status.mjs");
  t.mock.method(globalThis, "fetch", async () => new Response('{"unexpected":true}'));
  const row = await fetchJson({id:"test", label:"Test", url:"https://example.test", adapter:"test-v1"}, 30000, () => {
    throw new TypeError("malformed provider data");
  });
  assert.equal(row.http_status, 200);
  assert.equal(row.transport.status, "ok");
  assert.equal(row.parser.status, "schema-mismatch");
  assert.equal(row.semantic.status, "unavailable");
  assert.match(row.payload_sha256, /^[a-f0-9]{64}$/);
  assert.equal(row.summary, undefined);
});

test("append failure does not truncate an existing journal", async () => {
  const { appendJsonl } = await import("./collect-public-status.mjs");
  const { mkdtemp, readFile, rm, writeFile } = await import("node:fs/promises");
  const { tmpdir } = await import("node:os");
  const { join } = await import("node:path");
  const root = await mkdtemp(join(tmpdir(),"observatory-append-error-"));
  try {
    const path = join(root,"journal.jsonl");
    await writeFile(path,'{"id":0}\n');
    await assert.rejects(appendJsonl(path,{value:1n}), TypeError);
    assert.equal(await readFile(path,"utf8"), '{"id":0}\n');
  } finally { await rm(root,{recursive:true,force:true}); }
});
