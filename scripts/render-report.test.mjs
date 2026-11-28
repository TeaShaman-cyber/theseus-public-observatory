import assert from "node:assert/strict";
import test from "node:test";
import { renderReport } from "./collect-public-status.mjs";

const base = { collected_at: "2026-09-10T06:00:00Z" };
const render = (...sources) => renderReport({ ...base, sources });
const source = (fields = {}) => ({ id: "example", label: "Example", ok: true, latency_ms: 7, ...fields });

test("empty report preserves exact section order and interpretation boundary", () => {
  assert.equal(render(), [
    "# Public Observatory Report 2026-09-10", "", "Collected at: 2026-09-10T06:00:00Z",
    "", "## Source Health", "", "", "## Interpretation Boundary", "",
    "This report describes public source availability and status only. It does not claim causal links between sources.", "",
  ].join("\n"));
});

test("source health keeps missing fields distinct from explicit values", () => {
  const report = render(
    source({ summary: { indicator: "minor" } }),
    source({ label: "Description only", summary: { description: "degraded" } }),
    source({ label: "Both", summary: { indicator: "none", description: "healthy" } }),
    source({ label: "Unavailable", ok: false, error: "timeout", summary: {} }),
  );
  assert.match(report, /- Example: ok, 7 ms\n  - status: minor \/ n\/a\n- Description only: ok, 7 ms\n  - status: unknown \/ degraded\n- Both: ok, 7 ms\n  - status: none \/ healthy\n- Unavailable: error, 7 ms\n  - error: timeout/);
  assert.doesNotMatch(report, /Radar Origins|Astronomy Context/);
});

test("radar reports coverage and units without interpreting unavailable samples", () => {
  const adapter = "cloudflare-radar-origins-v1";
  const report = render(
    source({ adapter, summary: { provider: "Example", metric: "requests", samples: 3, expected_samples: 4,
      coverage: "partial", window_start: "start", window_end: "end", last_updated: "updated" } }),
    source({ adapter, label: "No radar", ok: false, error: "timeout" }),
  );
  assert.match(report, /## Cloudflare Radar Origins/);
  assert.match(report, /CC BY-NC 4\.0/);
  assert.match(report, /fractions of the maximum in each response window, not absolute counts, error rates, or GPU utilization/);
  assert.match(report, /- Example requests: 3\/4 samples \(partial\), window start – end, updated updated\./);
  assert.match(report, /- No radar: unavailable \(timeout\)\./);
  assert.doesNotMatch(report, /Astronomy Context/);
});

test("moon zero illumination, primary phase and local date remain visible", () => {
  const report = render(source({ id: "usno_sun_moon", observer_local_date: "2026-09-10",
    summary: { moon: { current_phase: "New Moon", illumination_percent: 0,
      closest_primary_phase: { phase: "New Moon", year: 2026, month: 9, day: 3, time: "04:05" } } } }));
  assert.match(report, /Observer local date: 2026-09-10 \(Kaliningrad, UTC\+2\)/);
  assert.match(report, /Moon: New Moon, 0% illuminated/);
  assert.match(report, /closest primary phase: New Moon, 2026-09-03 04:05 local time/);
  assert.match(report, /Solar eclipse event on this date \(global list\): unknown \(source unavailable\)/);
  assert.match(report, /does not claim effects on AI or infrastructure/);
});

test("moon missing fields and optional primary phase do not invent observations", () => {
  const missing = render(source({ id: "usno_sun_moon", summary: { moon: {} } }));
  assert.match(missing, /Moon: unknown, unknown% illuminated/);
  assert.doesNotMatch(missing, /closest primary phase|Observer local date/);
  const phase = render(source({ id: "usno_sun_moon", summary: { moon: { closest_primary_phase: { year: 2026, month: 9, day: 3 } } } }));
  assert.match(phase, /closest primary phase: unknown, 2026-09-03  local time/);
});

test("eclipse event preserves local visibility and its explicit missing fallback", () => {
  const eclipse = { id: "usno_solar_eclipses", semantic: { status: "available" } };
  const event_today = { event: "Solar Eclipse" };
  for (const [summary, expected] of [
    [{ event_today, local_visibility: "not-provided" }, "not-provided"],
    [{ event_today }, "not recorded"],
  ]) {
    const report = render(source({ ...eclipse, summary }));
    assert.match(report, /Solar eclipse event on this date \(global list\): Solar Eclipse/);
    assert.ok(report.includes("local visibility: " + expected));
    assert.doesNotMatch(report, /Moon:|Radar Origins/);
  }
});
