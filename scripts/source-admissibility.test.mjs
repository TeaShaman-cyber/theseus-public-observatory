import assert from "node:assert/strict";
import test from "node:test";
import { buildAstronomySources, interpretAstronomy } from "./astronomy.mjs";
import { summarizeSource } from "./source-adapters.mjs";

function statuspagePayload() {
  return {
    status: { indicator: "none", description: "All Systems Operational" },
    page: { name: "Example Status" },
    components: [],
    incidents: [],
  };
}

function huggingFacePayload() {
  return {
    data: {
      attributes: {
        aggregate_state: "operational",
        company_name: "Hugging Face",
        updated_at: "2026-09-24T14:18:28.297Z",
      },
    },
    included: [],
  };
}

function kpPayload() {
  return [
    { time_tag: "2026-09-24T12:00:00", Kp: 2.0, a_running: 7, station_count: 8 },
    { time_tag: "2026-09-24T15:00:00", Kp: 3.0, a_running: 12, station_count: 8 },
  ];
}

function noaaScaleEntry(scale = "0") {
  return {
    DateStamp: "2026-09-24",
    TimeStamp: "15:09:00",
    R: { Scale: scale, Text: scale === null ? null : "none" },
    S: { Scale: scale, Text: scale === null ? null : "none" },
    G: { Scale: scale, Text: scale === null ? null : "none" },
  };
}

function noaaScalesPayload() {
  return {
    "-1": noaaScaleEntry("0"),
    "0": noaaScaleEntry("1"),
    "1": noaaScaleEntry(null),
  };
}

function usnoSunMoonPayload() {
  return {
    properties: {
      data: {
        curphase: "Waxing Gibbous",
        fracillum: "80%",
        moondata: [{ phen: "Rise", time: "16:00" }],
        sundata: [{ phen: "Rise", time: "06:30" }],
      },
    },
  };
}

function usnoMoonPhasesPayload() {
  return {
    year: 2026,
    phasedata: [
      { phase: "Full Moon", year: 2026, month: 9, day: 26, time: "16:49" },
    ],
  };
}

function usnoSolarEclipsesPayload() {
  return {
    year: 2026,
    eclipses_in_year: [
      { event: "Total Solar Eclipse", year: 2026, month: 8, day: 12 },
    ],
  };
}

const ordinaryCases = [
  {
    name: "OpenAI-style Statuspage status",
    source: { id: "openai_status", adapter: "statuspage-status-v1" },
    good: statuspagePayload,
    bad: [
      ["status metadata without admissible status fields", () => ({
        status: { indicator: "   ", description: "" },
        incidents: [{ name: "historical incident" }],
      })],
    ],
  },
  {
    name: "GitHub-style Statuspage summary",
    source: { id: "github_status", adapter: "statuspage-summary-v1" },
    good: statuspagePayload,
    bad: [
      ["component presence without aggregate status", () => ({
        status: {},
        components: [{ name: "API", status: "operational" }],
      })],
    ],
  },
  {
    name: "Hugging Face status",
    source: { id: "huggingface_status", adapter: "huggingface-status-v1" },
    good: huggingFacePayload,
    bad: [
      ["resource rows without aggregate provider state", () => ({
        data: { attributes: {} },
        included: [{ type: "status_page_resource", attributes: { status: "operational" } }],
      })],
    ],
  },
  {
    name: "NOAA planetary Kp",
    source: { id: "noaa_planetary_k_index", adapter: "noaa-kp-v1" },
    good: kpPayload,
    bad: [
      ["valid-looking row with out-of-domain Kp", () => [
        { time_tag: "2026-09-24T15:00:00", Kp: 9.5, station_count: 8 },
      ]],
      ["measurement value without admissible timestamp", () => [
        { time_tag: "not-a-timestamp", Kp: 3.0, station_count: 8 },
      ]],
    ],
  },
  {
    name: "NOAA R/S/G scales",
    source: { id: "noaa_scales", adapter: "noaa-scales-v1" },
    good: noaaScalesPayload,
    bad: [
      ["forecast-only scale is not an observation", () => ({
        "1": noaaScaleEntry("2"),
      })],
      ["measured scale outside declared domain", () => ({
        "0": noaaScaleEntry("6"),
      })],
    ],
  },
];

for (const item of ordinaryCases) {
  test(`admissibility matrix: ${item.name} accepts the known-good semantic role`, () => {
    const result = summarizeSource(item.source, item.good());
    assert.equal(result.ok, true, item.name);
  });

  for (const [label, makePayload] of item.bad) {
    test(`admissibility matrix: ${item.name} rejects ${label}`, () => {
      const result = summarizeSource(item.source, makePayload());
      assert.equal(result.ok, false, `${item.name}: ${label}`);
    });
  }
}

const astronomySources = buildAstronomySources(new Date("2026-09-24T12:00:00Z"));
const astronomyByKind = Object.fromEntries(astronomySources.map((source) => [source.kind, source]));

const astronomyCases = [
  {
    name: "USNO Sun/Moon",
    source: astronomyByKind["usno-sun-moon"],
    good: usnoSunMoonPayload,
    bad: [
      ["non-measurement illumination metadata", () => {
        const payload = usnoSunMoonPayload();
        payload.properties.data.fracillum = "unknown";
        return payload;
      }],
    ],
  },
  {
    name: "USNO Moon phases",
    source: astronomyByKind["usno-moon-phases"],
    good: usnoMoonPhasesPayload,
    bad: [
      ["phase record with invalid clock time", () => ({
        year: 2026,
        phasedata: [
          { phase: "Full Moon", year: 2026, month: 9, day: 26, time: "25:99" },
        ],
      })],
    ],
  },
  {
    name: "USNO solar eclipses",
    source: astronomyByKind["usno-solar-eclipses"],
    good: usnoSolarEclipsesPayload,
    bad: [
      ["well-formed event from the wrong requested year", () => ({
        year: 2025,
        eclipses_in_year: [
          { event: "Solar Eclipse", year: 2025, month: 9, day: 21 },
        ],
      })],
    ],
  },
];

for (const item of astronomyCases) {
  test(`admissibility matrix: ${item.name} accepts the known-good semantic role`, () => {
    const result = interpretAstronomy(
      item.source,
      item.good(),
      item.source.observer_local_date,
    );
    assert.equal(result.ok, true, item.name);
  });

  for (const [label, makePayload] of item.bad) {
    test(`admissibility matrix: ${item.name} rejects ${label}`, () => {
      const result = interpretAstronomy(
        item.source,
        makePayload(),
        item.source.observer_local_date,
      );
      assert.equal(result.ok, false, `${item.name}: ${label}`);
    });
  }
}
