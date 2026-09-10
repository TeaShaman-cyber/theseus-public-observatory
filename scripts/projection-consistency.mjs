#!/usr/bin/env node
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";

export function finalJsonlRecord(text) {
  const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length === 0) throw new Error("canonical JSONL has no records");
  return JSON.parse(lines.at(-1));
}

export function assertLatestMatchesCanonical(canonicalText, latestText) {
  const canonical = finalJsonlRecord(canonicalText);
  const latest = JSON.parse(latestText);
  if (!isDeepStrictEqual(canonical, latest)) {
    throw new Error("latest projection does not match canonical final row");
  }
  return canonical;
}

export function assertReportMatchesSnapshot(reportText, snapshot) {
  const marker = `Collected at: ${snapshot.collected_at}`;
  if (!reportText.includes(marker)) {
    throw new Error("report does not identify projected collected_at");
  }
}

function latestCanonicalDay(repoRoot) {
  const dataRoot = join(repoRoot, "data");
  const days = readdirSync(dataRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
    .map((entry) => entry.name)
    .filter((day) => existsSync(join(dataRoot, day, "public-status.jsonl")))
    .sort();
  if (days.length === 0) throw new Error("no canonical dated observation files found");
  return days.at(-1);
}

export function checkRepositoryProjections(repoRoot = ".") {
  const day = latestCanonicalDay(repoRoot);
  const canonicalPath = join(repoRoot, "data", day, "public-status.jsonl");
  const latestPath = join(repoRoot, "data", "latest", "public-status.json");
  const reportPath = join(repoRoot, "reports", `${day}.md`);
  const snapshot = assertLatestMatchesCanonical(
    readFileSync(canonicalPath, "utf8"),
    readFileSync(latestPath, "utf8"),
  );
  assertReportMatchesSnapshot(readFileSync(reportPath, "utf8"), snapshot);
  return { day, canonicalPath, latestPath, reportPath, collected_at: snapshot.collected_at };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const result = checkRepositoryProjections(process.argv[2] ?? ".");
  console.log(`projection consistency ok ${JSON.stringify(result)}`);
}
