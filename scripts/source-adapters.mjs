function schemaMismatch() {
  return { ok: false, summary: {}, error: "schema-mismatch" };
}

function statuspage(json) {
  const indicator = json?.status?.indicator;
  const description = json?.status?.description;
  if (typeof indicator !== "string" && typeof description !== "string") {
    return schemaMismatch();
  }
  return {
    ok: true,
    error: null,
    summary: {
      indicator: typeof indicator === "string" ? indicator : null,
      description: typeof description === "string" ? description : null,
      page_name: typeof json?.page?.name === "string" ? json.page.name : null,
      components: Array.isArray(json?.components) ? json.components.length : undefined,
      incidents: Array.isArray(json?.incidents) ? json.incidents.length : undefined,
    },
  };
}

function huggingFace(json) {
  const indicator = json?.data?.attributes?.aggregate_state;
  if (typeof indicator !== "string") return schemaMismatch();
  const included = Array.isArray(json?.included) ? json.included : [];
  const resources = included.filter((item) => item?.type === "status_page_resource");
  const reports = included.filter((item) => item?.type === "status_report");
  return {
    ok: true,
    error: null,
    summary: {
      indicator,
      description: "Hugging Face status page",
      page_name: json?.data?.attributes?.company_name ?? "Hugging Face",
      resources: resources.length,
      incidents: reports.length,
      updated_at: json?.data?.attributes?.updated_at ?? null,
    },
  };
}

function noaaKp(json) {
  if (!Array.isArray(json)) return schemaMismatch();
  const rows = json.filter(
    (row) =>
      row &&
      !Array.isArray(row) &&
      typeof row === "object" &&
      typeof row.time_tag === "string" &&
      typeof row.Kp === "number",
  );
  if (rows.length === 0) return schemaMismatch();
  const latest = rows.at(-1);
  return {
    ok: true,
    error: null,
    summary: {
      rows: rows.length,
      latest: {
        time_tag: latest.time_tag,
        Kp: latest.Kp,
        a_running: latest.a_running ?? null,
        station_count: latest.station_count ?? null,
      },
    },
  };
}

function isNoaaScaleEntry(entry) {
  if (!entry || typeof entry !== "object" || Array.isArray(entry)) return false;
  if (typeof entry.DateStamp !== "string" || typeof entry.TimeStamp !== "string") return false;
  return ["R", "S", "G"].every((kind) => {
    const scale = entry[kind];
    return (
      scale &&
      typeof scale === "object" &&
      !Array.isArray(scale) &&
      Object.hasOwn(scale, "Scale") &&
      (typeof scale.Scale === "string" || scale.Scale === null)
    );
  });
}

function noaaScales(json) {
  if (!json || typeof json !== "object" || Array.isArray(json)) return schemaMismatch();
  const observed = json["-1"] ?? json.observed ?? null;
  const current = json["0"] ?? json.current ?? null;
  const forecast = json["1"] ?? json.forecast ?? null;
  const selected = [observed, current, forecast].filter((entry) => entry !== null);
  if (selected.length === 0 || selected.some((entry) => !isNoaaScaleEntry(entry))) {
    return schemaMismatch();
  }
  return { ok: true, error: null, summary: { observed, current, forecast } };
}

export function summarizeSource(source, json) {
  switch (source.adapter) {
    case "statuspage-status-v1":
    case "statuspage-summary-v1":
      return statuspage(json);
    case "huggingface-status-v1":
      return huggingFace(json);
    case "noaa-kp-v1":
      return noaaKp(json);
    case "noaa-scales-v1":
      return noaaScales(json);
    default:
      return { ok: false, summary: {}, error: "unsupported-adapter" };
  }
}
