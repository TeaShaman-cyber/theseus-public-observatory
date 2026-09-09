#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export function findSensorContractFailures(snapshot) {
  if (snapshot?.schema_version !== 1 || !Array.isArray(snapshot?.sources)) return [];
  const failures = [];
  for (const source of snapshot.sources) {
    const transport = source?.transport?.status;
    const parser = source?.parser?.status;
    const semantic = source?.semantic?.status;
    if (parser === "invalid-json" || parser === "schema-mismatch") {
      failures.push({ id: source.id, layer: "parser", status: parser });
      continue;
    }
    if (transport === "ok" && parser === "ok" && semantic !== "available") {
      failures.push({ id: source.id, layer: "semantic", status: semantic || "unknown" });
    }
  }
  return failures;
}

export function checkLatestSensorHealth(path = "data/latest/public-status.json") {
  const snapshot = JSON.parse(readFileSync(path, "utf8"));
  const failures = findSensorContractFailures(snapshot);
  if (failures.length > 0) {
    throw new Error(`sensor contract failures: ${JSON.stringify(failures)}`);
  }
  return { checked: snapshot.sources?.length ?? 0, failures: 0 };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const result = checkLatestSensorHealth(process.argv[2]);
  console.log(`sensor health ok ${JSON.stringify(result)}`);
}
