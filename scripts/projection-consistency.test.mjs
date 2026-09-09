import assert from "node:assert/strict";
import test from "node:test";
import {
  assertLatestMatchesCanonical,
  assertReportMatchesSnapshot,
} from "./projection-consistency.mjs";

const first = { schema_version: 1, collected_at: "2026-09-09T06:00:00Z", sources: [] };
const second = { schema_version: 1, collected_at: "2026-09-09T07:00:00Z", sources: [] };

test("latest projection matches the final canonical JSONL record", () => {
  const canonical = `${JSON.stringify(first)}\n${JSON.stringify(second)}\n`;
  const latest = `${JSON.stringify(second, null, 2)}\n`;
  const snapshot = assertLatestMatchesCanonical(canonical, latest);
  assert.deepEqual(snapshot, second);
});

test("mismatched latest projection fails loudly", () => {
  const canonical = `${JSON.stringify(first)}\n${JSON.stringify(second)}\n`;
  const latest = `${JSON.stringify(first, null, 2)}\n`;
  assert.throws(
    () => assertLatestMatchesCanonical(canonical, latest),
    /latest projection does not match canonical final row/,
  );
});

test("daily report must identify the exact projected collection timestamp", () => {
  const report = `# Public Observatory Report 2026-09-09\n\nCollected at: ${second.collected_at}\n`;
  assert.doesNotThrow(() => assertReportMatchesSnapshot(report, second));
  assert.throws(
    () => assertReportMatchesSnapshot("# stale report\n", second),
    /report does not identify projected collected_at/,
  );
});
