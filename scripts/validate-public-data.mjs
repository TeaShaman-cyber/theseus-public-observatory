#!/usr/bin/env node
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

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

function validateV1Source(item, source) {
  if (item.schema_version !== 1) throw new Error(`${source}: v1 source schema_version must be 1`);
  if (!item.adapter || typeof item.adapter !== "string") throw new Error(`${source}: v1 source missing adapter`);
  if (!TRANSPORT_STATUSES.has(item.transport?.status)) throw new Error(`${source}: invalid transport status`);
  if (!PARSER_STATUSES.has(item.parser?.status)) throw new Error(`${source}: invalid parser status`);
  if (!SEMANTIC_STATUSES.has(item.semantic?.status)) throw new Error(`${source}: invalid semantic status`);
  if (item.payload_sha256 !== null && !/^[0-9a-f]{64}$/.test(item.payload_sha256 ?? "")) {
    throw new Error(`${source}: invalid payload_sha256`);
  }
  if (item.ok !== (item.semantic.status === "available")) {
    throw new Error(`${source}: v1 source ok must equal semantic availability`);
  }
}

function validateSnapshot(snapshot, source) {
  if (!snapshot || typeof snapshot !== "object") throw new Error(`${source}: snapshot must be object`);
  if (!snapshot.collected_at || Number.isNaN(Date.parse(snapshot.collected_at))) {
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
  for (const item of snapshot.sources) {
    if (!item.id || !item.label || !item.url) throw new Error(`${source}: source item missing id/label/url`);
    if (!/^https:\/\//.test(item.url)) throw new Error(`${source}: source URL must be HTTPS`);
    if (typeof item.ok !== "boolean") throw new Error(`${source}: source ok must be boolean`);
    if (typeof item.latency_ms !== "number") throw new Error(`${source}: source latency_ms must be number`);
    if (isV1) validateV1Source(item, source);
  }
}

for (const file of walk("data").filter((path) => path.endsWith(".json") || path.endsWith(".jsonl"))) {
  if (statSync(file).size === 0) continue;
  const text = readFileSync(file, "utf8");
  const lines = file.endsWith(".jsonl") ? text.split(/\r?\n/).filter(Boolean) : [text];
  for (const [index, line] of lines.entries()) {
    validateSnapshot(JSON.parse(line), `${file}:${index + 1}`);
  }
}

console.log("public data validation ok");
