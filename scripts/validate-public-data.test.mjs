import assert from "node:assert/strict";
import test from "node:test";
import { validateSnapshot } from "./validate-public-data.mjs";

const good = () => ({
  schema_version:1,id:"openai_status",label:"OpenAI",url:"https://example.test",
  adapter:"statuspage-status-v1",ok:true,http_status:200,latency_ms:1,
  payload_sha256:"a".repeat(64),transport:{status:"ok"},parser:{status:"ok"},
  semantic:{status:"available"},summary:{indicator:"none"},
});
const snapshot = (...sources) => ({
  schema_version:1,collected_at:"2026-11-28T12:00:00Z",
  run:{collector:"collect-public-status-v1"},sources,
});
const check = (...rows) => validateSnapshot(snapshot(...rows),"fixture");
const bad = (changes) => assert.throws(() => check({...good(),...changes}));

test("available receipt requires successful transport, parser, HTTP status and payload identity", () => {
  assert.doesNotThrow(() => check(good()));
  bad({transport:{status:"http-error"}});
  bad({parser:{status:"invalid-json"}});
  bad({http_status:503});
  bad({payload_sha256:null});
  bad({ok:false});
});

test("unavailable responses cannot carry nonempty measurement summaries", () => {
  const unavailable = {...good(),ok:false,semantic:{status:"unavailable"},
    parser:{status:"schema-mismatch"}};
  assert.throws(() => check(unavailable));
  assert.doesNotThrow(() => check({...unavailable,summary:{}}));
  assert.doesNotThrow(() => check({...unavailable,summary:undefined}));
});

test("transport failure preserves known HTTP metadata but cannot claim a parsed body", () => {
  const failed = {...good(),ok:false,transport:{status:"fetch-error"},
    parser:{status:"not-attempted"},semantic:{status:"unavailable"},
    payload_sha256:null,summary:undefined};
  assert.doesNotThrow(() => check(failed));
  assert.doesNotThrow(() => check({...failed,http_status:null}));
  assert.throws(() => check({...failed,parser:{status:"ok"}}));
  assert.throws(() => check({...failed,payload_sha256:"a".repeat(64)}));
  assert.doesNotThrow(() => check({...failed,transport:{status:"timeout"}}));
});

test("HTTP error receipts retain legacy invalid JSON and new skipped interpretation", () => {
  const failed = {...good(),ok:false,http_status:502,transport:{status:"http-error"},
    semantic:{status:"unavailable"},summary:undefined};
  for (const status of ["invalid-json","not-attempted"]) {
    assert.doesNotThrow(() => check({...failed,parser:{status}}));
  }
  assert.throws(() => check({...failed,http_status:200}));
  assert.throws(() => check({...failed,payload_sha256:null}));
});

test("snapshot rejects duplicate sources, nonobjects and invalid latency", () => {
  assert.throws(() => check(good(),good()), /duplicate/);
  assert.throws(() => check(null));
  for (const latency_ms of [-1,NaN,Infinity,"1"]) bad({latency_ms});
  bad({id:1});
  bad({url:"https://"});
});

test("unsupported schema and malformed run metadata fail validation", () => {
  for (const value of [
    null, [], {...snapshot(good()),collected_at:"not a date"},
    {...snapshot(good()),sources:null}, {...snapshot(good()),schema_version:2},
    {...snapshot(good()),run:null},
  ]) assert.throws(() => validateSnapshot(value,"fixture"));
  for (const change of [
    {schema_version:0}, {adapter:" "}, {transport:{status:"unknown"}},
    {parser:{status:"unknown"}}, {semantic:{status:"unknown"}},
    {payload_sha256:"bad"}, {summary:[]}, {summary:null},
    {parser:{status:"not-attempted"}},
    {latency_ms:-1}, {label:" "},
  ]) bad(change);
});
