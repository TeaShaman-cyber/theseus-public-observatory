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
