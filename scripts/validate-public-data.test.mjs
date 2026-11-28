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

test("available science receipts enforce measurement domains without inventing missing values", () => {
  const kp = { ...good(), id:"noaa_planetary_k_index", adapter:"noaa-kp-v1",
    summary:{ rows:1, latest:{ Kp:0, time_tag:"2026-11-28T09:00:00" } } };
  const scale = { ...good(), id:"noaa_scales", adapter:"noaa-scales-v1",
    summary:{current:{DateStamp:"2026-11-28",TimeStamp:"09:00:00",R:{Scale:"0"},S:{Scale:"5"},G:{Scale:"1"}}} };
  const moon = { ...good(), id:"usno_sun_moon", adapter:"usno-sun-moon-v1",
    summary:{moon:{illumination_percent:0}} };
  for (const row of [kp,scale,moon]) assert.doesNotThrow(() => check(row));
  for (const value of [-1,10,true,"3",null]) {
    assert.throws(() => check({...kp,summary:{...kp.summary,latest:{...kp.summary.latest,Kp:value}}}), /measurement/);
  }
  for (const rows of [0,-1,1.5,true,"1"]) {
    assert.throws(() => check({...kp,summary:{...kp.summary,rows}}), /measurement/);
  }
  for (const value of ["6","-1",1.5,true,"01",null]) {
    assert.throws(() => check({...scale,summary:{current:{...scale.summary.current,R:{Scale:value}}}}), /measurement/);
  }
  for (const value of [-1,101,true,"80",null]) {
    assert.throws(() => check({...moon,summary:{moon:{illumination_percent:value}}}), /measurement/);
  }
  for (const row of [kp,scale,moon]) assert.throws(() => check({...row,summary:{}}), /measurement/);
});

test("available Kp row counts fit the signed integer index column", () => {
  const row = {...good(), id:"noaa_planetary_k_index", adapter:"noaa-kp-v1",
    summary:{rows:2147483647,latest:{Kp:0,time_tag:"2026-11-28T09:00:00"}}};
  assert.doesNotThrow(() => check(row));
  assert.throws(() => check({...row,summary:{...row.summary,rows:2147483648}}), /measurement/);
});
