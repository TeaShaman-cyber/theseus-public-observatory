import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import { createSourceReceipt } from "./observation-receipt.mjs";

const run = promisify(execFile);
const root = fileURLToPath(new URL("../", import.meta.url));
export const radarRoles = ["amazon", "google", "microsoft", "oracle"].flatMap(provider =>
  ["REQUESTS", "CONNECTION_FAILURES"].map(metric => ({
    provider, metric,
    id: `radar_${provider}_${metric.toLowerCase()}`,
    label: `Cloudflare Radar ${provider} ${metric}`,
    adapter: "cloudflare-radar-origins-v1",
    url: "https://api.cloudflare.com/client/v4/radar/origins/timeseries?" +
      new URLSearchParams({origin: provider.toUpperCase(), metric, dateRange: "1d", aggInterval: "15m", format: "JSON"}),
  }))
);

function utc(value) {
  if (typeof value !== "string" || !/(?:Z|\+00:00)$/.test(value)) return NaN;
  return Date.parse(value);
}

export function validateRadarReceipt(row) {
  const role = radarRoles.find(r => r.id === row?.id);
  if (!role || row.url !== role.url || row.adapter !== role.adapter ||
      row.schema_version !== 1 || typeof row.ok !== "boolean" ||
      row.ok !== (row.semantic?.status === "available") ||
      !Number.isFinite(row.latency_ms) || row.latency_ms < 0 ||
      !Number.isFinite(utc(row.observed_at))) {
    throw new Error("invalid Radar receipt identity");
  }
  if (!row.ok) {
    if (row.summary !== undefined) throw new Error("unavailable Radar receipt has measurements");
    return;
  }
  const s = row.summary;
  const start = utc(s?.window_start);
  const end = utc(s?.window_end);
  const lastUpdated = utc(s?.last_updated);
  if (row.http_status !== 200 || row.transport?.status !== "ok" ||
      row.parser?.status !== "ok" || !/^[a-f0-9]{64}$/.test(row.payload_sha256 ?? "") ||
      s?.provider !== role.provider || s.metric !== role.metric ||
      s.normalization !== "MIN0_MAX" || s.agg_interval !== "FIFTEEN_MINUTES" ||
      s.source_unit !== "requests" || s.value_unit !== "window_max_fraction" ||
      s.attribution !== "Cloudflare Radar" || s.license !== "CC BY-NC 4.0" ||
      end - start !== 86400000 || start % 900000 !== 0 || end % 900000 !== 0 ||
      !Number.isFinite(lastUpdated) || !Array.isArray(s.points) ||
      s.points.length === 0 || s.points.length > 97 || s.samples !== s.points.length ||
      s.expected_samples !== 97 ||
      s.coverage !== (s.points.length === 97 ? "complete" : "partial")) {
    throw new Error("invalid Radar window");
  }
  let previous = -Infinity;
  for (const point of s.points) {
    const stamp = utc(point?.measured_at);
    if (!Number.isFinite(stamp) || stamp < start || stamp > end || stamp <= previous ||
        stamp % 900000 !== 0 || !Number.isFinite(point.value) || point.value < 0 || point.value > 1) {
      throw new Error("invalid Radar measurement");
    }
    previous = stamp;
  }
}

export function validateRadarCohort(rows) {
  if (rows.length !== radarRoles.length ||
      new Set(rows.map(r => r.id)).size !== radarRoles.length) {
    throw new Error("incomplete or duplicate Radar cohort");
  }
  for (const row of rows) validateRadarReceipt(row);
}

export async function fetchRadar(execute = run, env = process.env) {
  const started = Date.now();
  try {
    const { stdout } = await execute("python3", ["-m", "scripts.radar_collection"], {
      cwd: root, env, timeout: 90000, maxBuffer: 2 * 1024 * 1024,
    });
    const rows = JSON.parse(stdout);
    if (!Array.isArray(rows)) throw new Error("invalid worker receipt");
    validateRadarCohort(rows);
    return rows;
  } catch {
    // Do not expose worker stderr or exception contents; they may contain credentials.
    return radarRoles.map(source => ({
      ...createSourceReceipt({
        source, httpStatus: null, latencyMs: Date.now() - started,
        transportStatus: "fetch-error", parserStatus: "not-attempted",
        transportError: "radar-worker-failed",
      }),
      observed_at: new Date().toISOString(),
    }));
  }
}
