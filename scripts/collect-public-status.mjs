#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { buildAstronomySources, interpretAstronomy } from "./astronomy.mjs";
import { summarizeSource } from "./source-adapters.mjs";
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

async function fetchJson(source, timeoutMs = 30000) {
  const started = Date.now();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(source.url, {
      signal: controller.signal,
      headers: { "user-agent": "theseus-public-observatory/0.1" },
    });
    const text = await response.text();
    const contentType = response.headers.get("content-type");
    const transportStatus = response.ok ? "ok" : "http-error";
    let json = null;
    try {
      json = JSON.parse(text);
    } catch {
      return createSourceReceipt({
        source,
        httpStatus: response.status,
        latencyMs: Date.now() - started,
        contentType,
        payloadText: text,
        transportStatus,
        parserStatus: "invalid-json",
      });
    }
    const interpreted = summarizeSource(source, json);
    return createSourceReceipt({
      source,
      httpStatus: response.status,
      latencyMs: Date.now() - started,
      contentType,
      payloadText: text,
      transportStatus,
      parserStatus: interpreted.ok ? "ok" : "schema-mismatch",
      adapterResult: interpreted,
    });
  } catch (error) {
    const transportStatus = error?.name === "AbortError" ? "timeout" : "fetch-error";
    return createSourceReceipt({
      source,
      httpStatus: null,
      latencyMs: Date.now() - started,
      transportStatus,
      parserStatus: "not-attempted",
      transportError: error?.name === "AbortError" ? "timeout" : error?.message || "fetch-failed",
    });
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchAstronomy(date) {
  const day = buildAstronomySources(date)[0].observer_local_date;
  return Promise.all(
    buildAstronomySources(date).map(async (source) => {
      const started = Date.now();
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30000);
      try {
        const response = await fetch(source.url, {
          signal: controller.signal,
          headers: { "user-agent": "theseus-public-observatory/0.1" },
        });
        const text = await response.text();
        const contentType = response.headers.get("content-type");
        const transportStatus = response.ok ? "ok" : "http-error";
        let json = null;
        try {
          json = JSON.parse(text);
        } catch {
          const receipt = createSourceReceipt({
            source,
            httpStatus: response.status,
            latencyMs: Date.now() - started,
            contentType,
            payloadText: text,
            transportStatus,
            parserStatus: "invalid-json",
          });
          return { ...receipt, observer_local_date: source.observer_local_date };
        }
        const interpreted = interpretAstronomy(source, json, day);
        const receipt = createSourceReceipt({
          source,
          httpStatus: response.status,
          latencyMs: Date.now() - started,
          contentType,
          payloadText: text,
          transportStatus,
          parserStatus: interpreted.ok ? "ok" : "schema-mismatch",
          adapterResult: interpreted,
        });
        return { ...receipt, observer_local_date: source.observer_local_date };
      } catch (error) {
        const transportStatus = error?.name === "AbortError" ? "timeout" : "fetch-error";
        const receipt = createSourceReceipt({
          source,
          httpStatus: null,
          latencyMs: Date.now() - started,
          transportStatus,
          parserStatus: "not-attempted",
          transportError: error?.name === "AbortError" ? "timeout" : error?.message || "fetch-failed",
        });
        return { ...receipt, observer_local_date: source.observer_local_date };
      } finally {
        clearTimeout(timeout);
      }
    }),
  );
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

  for (const source of snapshot.sources) {
    const state = source.ok ? "ok" : "error";
    lines.push(`- ${source.label}: ${state}, ${source.latency_ms} ms`);
    if (source.summary?.indicator || source.summary?.description) {
      lines.push(`  - status: ${source.summary.indicator || "unknown"} / ${source.summary.description || "n/a"}`);
    }
    if (source.error) lines.push(`  - error: ${source.error}`);
  }

  const sunMoon = snapshot.sources.find((source) => source.id === "usno_sun_moon");
  const solarEclipse = snapshot.sources.find((source) => source.id === "usno_solar_eclipses");
  if (sunMoon || solarEclipse) {
    lines.push("", "## Astronomy Context", "");
    if (sunMoon?.observer_local_date) {
      lines.push(`- Observer local date: ${sunMoon.observer_local_date} (Kaliningrad, UTC+2)`);
    }
    if (sunMoon?.summary?.moon) {
      const moon = sunMoon.summary.moon;
      lines.push(`- Moon: ${moon.current_phase || "unknown"}, ${moon.illumination_percent ?? "unknown"}% illuminated`);
      if (moon.closest_primary_phase) {
        const phase = moon.closest_primary_phase;
        lines.push(`  - closest primary phase: ${phase.phase || "unknown"}, ${phase.year}-${String(phase.month).padStart(2, "0")}-${String(phase.day).padStart(2, "0")} ${phase.time || ""} local time`);
      }
    }
    if (solarEclipse?.summary?.event_today) {
      lines.push(`- Solar eclipse event on this date (global list): ${solarEclipse.summary.event_today.event}`);
      lines.push(`  - local visibility: ${solarEclipse.summary.local_visibility || "not recorded"}`);
    } else if (solarEclipse?.semantic?.status === "available") {
      lines.push("- Solar eclipse event on this date (global list): none");
    } else {
      lines.push("- Solar eclipse event on this date (global list): unknown (source unavailable)");
    }
    lines.push("- Astronomy values are contextual observations; this report does not claim effects on AI or infrastructure.");
  }

  lines.push(
    "",
    "## Interpretation Boundary",
    "",
    "This report describes public source availability and status only. It does not claim causal links between sources.",
    "",
  );
  return lines.join("\n");
}

async function appendJsonl(path, value) {
  await mkdir(dirname(path), { recursive: true });
  let previous = "";
  try {
    previous = await readFile(path, "utf8");
  } catch {
    previous = "";
  }
  await writeFile(path, `${previous}${JSON.stringify(value)}\n`, "utf8");
}

async function main() {
  const now = new Date();
  const snapshot = createSnapshot({
    collectedAt: now.toISOString(),
    sources: [
      ...(await Promise.all(SOURCES.map((source) => fetchJson(source)))),
      ...(await fetchAstronomy(now)),
    ],
  });

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
