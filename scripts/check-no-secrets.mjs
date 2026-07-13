#!/usr/bin/env node
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const SKIP_DIRS = new Set([".git", "node_modules"]);
const SECRET_PATTERNS = [
  /sk-[A-Za-z0-9_-]{20,}/,
  /gh[pousr]_[A-Za-z0-9_]{20,}/,
  /xox[baprs]-[A-Za-z0-9-]{20,}/,
  /(api[_-]?key|token|password|secret)\s*[:=]\s*["']?[^"',\s}]+/i,
  /-----BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----/,
];

function walk(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    if (SKIP_DIRS.has(entry.name)) return [];
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return walk(path);
    return [path];
  });
}

const hits = [];
for (const file of walk(".")) {
  if (statSync(file).size > 1_000_000) continue;
  const text = readFileSync(file, "utf8");
  for (const pattern of SECRET_PATTERNS) {
    if (pattern.test(text)) hits.push(file);
  }
}

if (hits.length) {
  console.error("Potential secret-like content found:");
  for (const hit of [...new Set(hits)]) console.error(`- ${hit}`);
  process.exit(1);
}

console.log("no secret-like content found");
