#!/usr/bin/env node
import { appendFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { buildAstronomySources, interpretAstronomy } from "./astronomy.mjs";
import { summarizeSource } from "./source-adapters.mjs";
import { fetchRadar } from "./radar-collection.mjs";
import { createSnapshot, createSourceReceipt } from "./observation-receipt.mjs";

const SOURCES = [
  {
    id: "openai_status",
    label: "OpenAI Status",
    url: "https://status.openai.com/api/v2/status.json",
    adapter: "statuspage-status-v1",
  },
  {
    id: "github_status",
    label: "GitHub Status",
    url: "https://www.githubstatus.com/api/v2/summary.json",
    adapter: "statuspage-summary-v1",
  },
  {
    id: "huggingface_status",
    label: "Hugging Face Status",
    url: "https://status.huggingface.co/index.json",
    adapter: "huggingface-status-v1",
  },
  {
    id: "noaa_planetary_k_index",
    label: "NOAA Planetary K Index",
    url: "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    adapter: "noaa-kp-v1",
  },
  {
    id: "noaa_scales",
    label: "NOAA Scales",
    url: "https://services.swpc.noaa.gov/products/noaa-scales.json",
    adapter: "noaa-scales-v1",
  },
];

function today(date = new Date()) {
  return date.toISOString().slice(0, 10);
}

export async function fetchJson(source, timeoutMs = 30000, interpret = summarizeSource) {
  const started = Date.now();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  let httpStatus = null;
  let contentType = null;
  let text;
  let transportStatus;
  try {
    const response = await fetch(source.url, {
      signal: controller.signal,
      headers: { "user-agent": "theseus-public-observatory/0.1" },
    });
    httpStatus = response.status;
    contentType = response.headers.get("content-type");
    text = await response.text();
    transportStatus = response.ok ? "ok" : "http-error";
  } catch (error) {
    const timedOut = controller.signal.aborted || error?.name === "AbortError";
    return createSourceReceipt({
      source, httpStatus, contentType, latencyMs: Date.now() - started,
      transportStatus: timedOut ? "timeout" : "fetch-error",
      parserStatus: "not-attempted",
      transportError: timedOut ? "timeout" : "fetch-failed",
    });
  } finally {
    clearTimeout(timeout);
  }
  const base = {
    source, httpStatus, contentType, latencyMs: Date.now() - started,
    payloadText: text, transportStatus,
  };
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    return createSourceReceipt({ ...base, parserStatus: "invalid-json" });
  }
  // A plausible error body is not an observation, even if it parses.
  if (transportStatus !== "ok") {
    return createSourceReceipt({ ...base, parserStatus: "not-attempted" });
  }
  let interpreted;
  try {
    interpreted = interpret(source, json);
  } catch {
    // Malformed provider data must not be mislabeled as a network failure.
    return createSourceReceipt({ ...base, parserStatus: "schema-mismatch" });
  }
  return createSourceReceipt({
    ...base,
    parserStatus: interpreted.ok ? "ok" : "schema-mismatch",
    adapterResult: interpreted.ok ? interpreted : null,
  });
}

async function fetchAstronomy(date) {
  return Promise.all(buildAstronomySources(date).map(async (source) => ({
    ...await fetchJson(source, 30000, (item, json) =>
      interpretAstronomy(item, json, source.observer_local_date)),
    observer_local_date: source.observer_local_date,
  })));
}

function appendSourceHealth(lines, sources) {
  for (const source of sources) {
    const state = source.ok ? "ok" : "error";
    lines.push(`- ${source.label}: ${state}, ${source.latency_ms} ms`);
    if (source.summary?.indicator || source.summary?.description) {
      lines.push(`  - status: ${source.summary.indicator || "unknown"} / ${source.summary.description || "n/a"}`);
    }
    if (source.error) lines.push(`  - error: ${source.error}`);
  }
}

function appendRadar(lines, sources) {
  const radar = sources.filter(source => source.adapter === "cloudflare-radar-origins-v1");
  if (!radar.length) return;

  lines.push("", "## Cloudflare Radar Origins", "",
    "- Source: Cloudflare Radar (https://radar.cloudflare.com/), CC BY-NC 4.0.",
    "- Values are fractions of the maximum in each response window, not absolute counts, error rates, or GPU utilization.");
  for (const source of radar) {
    if (!source.ok) {
      lines.push(`- ${source.label}: unavailable (${source.error}).`);
      continue;
    }
    const s = source.summary;
    lines.push(`- ${s.provider} ${s.metric}: ${s.samples}/${s.expected_samples} samples (${s.coverage}), window ${s.window_start} – ${s.window_end}, updated ${s.last_updated}.`);
  }
}

function appendMoon(lines, sunMoon) {
  if (sunMoon?.observer_local_date) {
    lines.push(`- Observer local date: ${sunMoon.observer_local_date} (Kaliningrad, UTC+2)`);
  }
  const moon = sunMoon?.summary?.moon;
  if (!moon) return;

  lines.push(`- Moon: ${moon.current_phase || "unknown"}, ${moon.illumination_percent ?? "unknown"}% illuminated`);
  const phase = moon.closest_primary_phase;
  if (!phase) return;

  lines.push(`  - closest primary phase: ${phase.phase || "unknown"}, ${phase.year}-${String(phase.month).padStart(2, "0")}-${String(phase.day).padStart(2, "0")} ${phase.time || ""} local time`);
}

function appendEclipse(lines, solarEclipse) {
  if (solarEclipse?.summary?.event_today) {
    lines.push(`- Solar eclipse event on this date (global list): ${solarEclipse.summary.event_today.event}`);
    lines.push(`  - local visibility: ${solarEclipse.summary.local_visibility || "not recorded"}`);
    return;
  }
  if (solarEclipse?.semantic?.status === "available") {
    lines.push("- Solar eclipse event on this date (global list): none");
  } else {
    lines.push("- Solar eclipse event on this date (global list): unknown (source unavailable)");
  }
}

function appendAstronomy(lines, sources) {
  const sunMoon = sources.find((source) => source.id === "usno_sun_moon");
  const solarEclipse = sources.find((source) => source.id === "usno_solar_eclipses");
  if (!sunMoon && !solarEclipse) return;

  lines.push("", "## Astronomy Context", "");
  appendMoon(lines, sunMoon);
  appendEclipse(lines, solarEclipse);
  lines.push("- Astronomy values are contextual observations; this report does not claim effects on AI or infrastructure.");
}

export function renderReport(snapshot) {
  const lines = [
    `# Public Observatory Report ${today(new Date(snapshot.collected_at))}`,
    "",
    `Collected at: ${snapshot.collected_at}`,
    "",
    "## Source Health",
    "",
  ];

  appendSourceHealth(lines, snapshot.sources);
  appendRadar(lines, snapshot.sources);
  appendAstronomy(lines, snapshot.sources);

  lines.push(
    "",
    "## Interpretation Boundary",
    "",
    "This report describes public source availability and status only. It does not claim causal links between sources.",
    "",
  );
  return lines.join("\n");
}

export async function appendJsonl(path, value) {
  await mkdir(dirname(path), { recursive: true });
  await appendFile(path, `${JSON.stringify(value)}\n`, "utf8");
}

export async function collectSnapshot(now, radarReader = fetchRadar) {
  return createSnapshot({
    collectedAt: now.toISOString(),
    sources: [
      ...(await Promise.all(SOURCES.map((source) => fetchJson(source)))),
      ...(await fetchAstronomy(now)),
      ...(await radarReader()),
    ],
  });
}

async function main() {
  const now = new Date();
  const snapshot = await collectSnapshot(now);

  const day = today(now);
  const jsonlPath = join("data", day, "public-status.jsonl");
  const latestPath = join("data", "latest", "public-status.json");
  const reportPath = join("reports", `${day}.md`);

  await appendJsonl(jsonlPath, snapshot);
  await mkdir(dirname(latestPath), { recursive: true });
  await writeFile(latestPath, `${JSON.stringify(snapshot, null, 2)}\n`, "utf8");
  await mkdir(dirname(reportPath), { recursive: true });
  await writeFile(reportPath, renderReport(snapshot), "utf8");

  const failed = snapshot.sources.filter((source) => !source.ok);
  console.log(JSON.stringify({ jsonlPath, latestPath, reportPath, sources: snapshot.sources.length, failed: failed.length }, null, 2));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
