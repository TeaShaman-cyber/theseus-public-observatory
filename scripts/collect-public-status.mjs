#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

const SOURCES = [
  {
    id: "openai_status",
    label: "OpenAI Status",
    url: "https://status.openai.com/api/v2/status.json",
    kind: "statuspage-status",
  },
  {
    id: "github_status",
    label: "GitHub Status",
    url: "https://www.githubstatus.com/api/v2/summary.json",
    kind: "statuspage-summary",
  },
  {
    id: "huggingface_status",
    label: "Hugging Face Status",
    url: "https://status.huggingface.co/api/v2/summary.json",
    kind: "statuspage-summary",
  },
  {
    id: "noaa_planetary_k_index",
    label: "NOAA Planetary K Index",
    url: "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    kind: "noaa-table",
  },
  {
    id: "noaa_scales",
    label: "NOAA Scales",
    url: "https://services.swpc.noaa.gov/products/noaa-scales.json",
    kind: "noaa-json",
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
    let json = null;
    try {
      json = JSON.parse(text);
    } catch {
      return {
        id: source.id,
        label: source.label,
        url: source.url,
        ok: false,
        http_status: response.status,
        latency_ms: Date.now() - started,
        error: "invalid-json",
        excerpt: text.slice(0, 200),
      };
    }
    return {
      id: source.id,
      label: source.label,
      url: source.url,
      ok: response.ok,
      http_status: response.status,
      latency_ms: Date.now() - started,
      summary: summarize(source, json),
    };
  } catch (error) {
    return {
      id: source.id,
      label: source.label,
      url: source.url,
      ok: false,
      http_status: null,
      latency_ms: Date.now() - started,
      error: error?.name === "AbortError" ? "timeout" : error?.message || "fetch-failed",
    };
  } finally {
    clearTimeout(timeout);
  }
}

function summarize(source, json) {
  if (source.kind.startsWith("statuspage")) {
    return {
      indicator: json?.status?.indicator ?? null,
      description: json?.status?.description ?? null,
      page_name: json?.page?.name ?? null,
      components: Array.isArray(json?.components) ? json.components.length : undefined,
      incidents: Array.isArray(json?.incidents) ? json.incidents.length : undefined,
    };
  }

  if (source.id === "noaa_planetary_k_index" && Array.isArray(json)) {
    const header = Array.isArray(json[0]) ? json[0] : null;
    const latest = [...json].reverse().find((row) => Array.isArray(row) && row.length > 1);
    return { rows: json.length, header, latest };
  }

  if (source.id === "noaa_scales") {
    return {
      observed: json?.["-1"] ?? json?.observed ?? null,
      current: json?.["0"] ?? json?.current ?? null,
      forecast: json?.["1"] ?? json?.forecast ?? null,
    };
  }

  return { type: Array.isArray(json) ? "array" : typeof json };
}

function renderReport(snapshot) {
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
  const snapshot = {
    collected_at: now.toISOString(),
    sources: await Promise.all(SOURCES.map((source) => fetchJson(source))),
  };

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

await main();
