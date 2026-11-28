#!/usr/bin/env node
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { join } from "node:path";
import { validateRadarCohort } from "./radar-collection.mjs";
import { summarizeSource } from "./source-adapters.mjs";

function walk(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return walk(path);
    return [path];
  });
}


const TRANSPORT_STATUSES = new Set(["ok", "http-error", "timeout", "fetch-error"]);
const PARSER_STATUSES = new Set(["ok", "invalid-json", "schema-mismatch", "not-attempted"]);
const SEMANTIC_STATUSES = new Set(["available", "unavailable"]);

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function nonempty(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function validateTransport(item, source) {
  const t = item.transport.status;
  const p = item.parser.status;
  const code = item.http_status;
  const validCode = Number.isInteger(code) && code >= 100 && code <= 599;
  const successCode = validCode && code >= 200 && code < 300;
  const hasHash = item.payload_sha256 !== null;
  if (t === "ok" || t === "http-error") {
    if (!validCode || successCode !== (t === "ok") || !hasHash) {
      throw new Error(`${source}: inconsistent HTTP status or payload identity`);
    }
    if (t === "ok" && p === "not-attempted") {
      throw new Error(`${source}: successful transport without parser result`);
    }
    // Historical HTTP errors may have been parsed before interpretation was skipped.
    return;
  }
  if ((code !== null && !validCode) || hasHash || p !== "not-attempted") {
    throw new Error(`${source}: inconsistent failed transport receipt`);
  }
}

function validateScienceMeasurement(item, source) {
  const summary = item.summary;
  let valid = true;
  switch (item.id) {
    case "noaa_planetary_k_index":
      valid = Number.isSafeInteger(summary?.rows) && summary.rows > 0 &&
        summarizeSource({ adapter: "noaa-kp-v1" }, [summary.latest]).ok;
      break;
    case "noaa_scales":
      valid = summarizeSource({ adapter: "noaa-scales-v1" }, summary).ok;
      break;
    case "usno_sun_moon": {
      const value = summary?.moon?.illumination_percent;
      valid = typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100;
      break;
    }
  }
  if (!valid) throw new Error(`${source}: invalid science measurement: ${item.id}`);
}

function validateV1Source(item, source) {
  if (item.schema_version !== 1) throw new Error(`${source}: v1 source schema_version must be 1`);
  if (!nonempty(item.adapter)) throw new Error(`${source}: v1 source missing adapter`);
  if (!TRANSPORT_STATUSES.has(item.transport?.status)) throw new Error(`${source}: invalid transport status`);
  if (!PARSER_STATUSES.has(item.parser?.status)) throw new Error(`${source}: invalid parser status`);
  if (!SEMANTIC_STATUSES.has(item.semantic?.status)) throw new Error(`${source}: invalid semantic status`);
  if (item.payload_sha256 !== null && !/^[0-9a-f]{64}$/.test(item.payload_sha256 ?? "")) {
    throw new Error(`${source}: invalid payload_sha256`);
  }
  validateTransport(item, source);
  const available = item.semantic.status === "available";
  if (item.ok !== available || (available && (item.transport.status !== "ok" || item.parser.status !== "ok"))) {
    throw new Error(`${source}: inconsistent semantic availability`);
  }
  if (item.summary !== undefined && !isObject(item.summary)) {
    throw new Error(`${source}: invalid summary`);
  }
  if (available) validateScienceMeasurement(item, source);
  if (!available && item.summary && Object.keys(item.summary).length) {
    throw new Error(`${source}: unavailable source has measurement summary`);
  }
}

export function validateSnapshot(snapshot, source) {
  if (!isObject(snapshot)) throw new Error(`${source}: snapshot must be object`);
  if (!nonempty(snapshot.collected_at) || Number.isNaN(Date.parse(snapshot.collected_at))) {
    throw new Error(`${source}: missing valid collected_at`);
  }
  if (!Array.isArray(snapshot.sources)) throw new Error(`${source}: sources must be array`);
  const isV1 = snapshot.schema_version === 1;
  if (snapshot.schema_version !== undefined && !isV1) {
    throw new Error(`${source}: unsupported snapshot schema_version`);
  }
  if (isV1 && (!snapshot.run || snapshot.run.collector !== "collect-public-status-v1")) {
    throw new Error(`${source}: v1 snapshot missing run metadata`);
  }
  const ids = new Set();
  for (const item of snapshot.sources) {
    if (!isObject(item) || !nonempty(item.id) || !nonempty(item.label) || !nonempty(item.url)) {
      throw new Error(`${source}: source item missing id/label/url`);
    }
    if (ids.has(item.id)) throw new Error(`${source}: duplicate source identity`);
    ids.add(item.id);
    if (!/^https:\/\//.test(item.url) || !URL.canParse(item.url)) throw new Error(`${source}: source URL must be HTTPS`);
    if (typeof item.ok !== "boolean") throw new Error(`${source}: source ok must be boolean`);
    if (!Number.isFinite(item.latency_ms) || item.latency_ms < 0) throw new Error(`${source}: invalid latency_ms`);
    if (isV1) validateV1Source(item, source);
  }
  const radar = snapshot.sources.filter(item => item.adapter === "cloudflare-radar-origins-v1" || item.id.startsWith("radar_"));
  if (radar.length) validateRadarCohort(radar);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  for (const file of walk("data").filter((path) => path.endsWith(".json") || path.endsWith(".jsonl"))) {
    if (statSync(file).size === 0) continue;
    const text = readFileSync(file, "utf8");
    const lines = file.endsWith(".jsonl") ? text.split(/\r?\n/).filter(Boolean) : [text];
    for (const [index, line] of lines.entries()) {
      validateSnapshot(JSON.parse(line), `${file}:${index + 1}`);
    }
  }

  console.log("public data validation ok");
}
