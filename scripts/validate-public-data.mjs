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

function validateSnapshot(snapshot, source) {
  if (!snapshot || typeof snapshot !== "object") throw new Error(`${source}: snapshot must be object`);
  if (!snapshot.collected_at || Number.isNaN(Date.parse(snapshot.collected_at))) {
    throw new Error(`${source}: missing valid collected_at`);
  }
  if (!Array.isArray(snapshot.sources)) throw new Error(`${source}: sources must be array`);
  for (const item of snapshot.sources) {
    if (!item.id || !item.label || !item.url) throw new Error(`${source}: source item missing id/label/url`);
    if (!/^https:\/\//.test(item.url)) throw new Error(`${source}: source URL must be HTTPS`);
    if (typeof item.ok !== "boolean") throw new Error(`${source}: source ok must be boolean`);
    if (typeof item.latency_ms !== "number") throw new Error(`${source}: source latency_ms must be number`);
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
