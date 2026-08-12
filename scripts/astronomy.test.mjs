import test from "node:test";
import assert from "node:assert/strict";

import {
  ASTRONOMY_OBSERVER,
  buildAstronomySources,
  summarizeUsnoMoonPhases,
  summarizeUsnoSolarEclipses,
  summarizeUsnoSunMoon,
} from "./astronomy.mjs";

const usnoSunMoonFixture = {
  geometry: { coordinates: [20.4522, 54.7104] },
  properties: {
    data: {
      curphase: "New Moon",
      fracillum: "0%",
      closestphase: {
        day: 12,
        month: 8,
        phase: "New Moon",
        time: "19:37",
        year: 2026,
      },
      moondata: [
        { phen: "Rise", time: "04:14" },
        { phen: "Upper Transit", time: "12:29" },
        { phen: "Set", time: "20:17" },
      ],
      sundata: [
        { phen: "Begin Civil Twilight", time: "04:26" },
        { phen: "Rise", time: "05:08" },
        { phen: "Upper Transit", time: "12:43" },
        { phen: "Set", time: "20:17" },
        { phen: "End Civil Twilight", time: "20:59" },
      ],
      tz: 2,
    },
  },
};

test("buildAstronomySources keeps the observer and date in public USNO URLs", () => {
  const sources = buildAstronomySources(new Date("2026-08-12T10:00:00Z"));

  assert.deepEqual(ASTRONOMY_OBSERVER, {
    id: "kaliningrad",
    label: "Kaliningrad, Russia",
    latitude: 54.7104,
    longitude: 20.4522,
    timezoneOffsetHours: 2,
  });
  assert.deepEqual(sources.map((source) => source.id), [
    "usno_sun_moon",
    "usno_moon_phases",
    "usno_solar_eclipses",
  ]);
  assert.match(sources[0].url, /rstt\/oneday\?date=2026-08-12/);
  assert.match(sources[0].url, /coords=54\.7104%2C20\.4522/);
  assert.match(sources[1].url, /moon\/phases\/date\?date=2026-08-12&nump=4/);
  assert.equal(sources[2].url, "https://aa.usno.navy.mil/api/eclipses/solar/year?year=2026");
});

test("buildAstronomySources uses the observer local date near UTC midnight", () => {
  const sources = buildAstronomySources(new Date("2026-08-12T23:00:00Z"));

  assert.equal(sources[0].observer_local_date, "2026-08-13");
  assert.match(sources[0].url, /rstt\/oneday\?date=2026-08-13/);
  assert.match(sources[1].url, /moon\/phases\/date\?date=2026-08-13/);
});

test("summarizeUsnoSunMoon preserves moon phase and local sun/moon events", () => {
  assert.deepEqual(summarizeUsnoSunMoon(usnoSunMoonFixture), {
    observer: ASTRONOMY_OBSERVER,
    moon: {
      current_phase: "New Moon",
      illumination_percent: 0,
      closest_primary_phase: usnoSunMoonFixture.properties.data.closestphase,
      events: { rise: "04:14", upper_transit: "12:29", set: "20:17" },
    },
    sun: {
      events: {
        begin_civil_twilight: "04:26",
        rise: "05:08",
        upper_transit: "12:43",
        set: "20:17",
        end_civil_twilight: "20:59",
      },
    },
    timezone_offset_hours: 2,
  });
});

test("summarizeUsnoMoonPhases and summarizeUsnoSolarEclipses retain event provenance", () => {
  const phases = summarizeUsnoMoonPhases({
    year: 2026,
    phasedata: [{ phase: "New Moon", year: 2026, month: 8, day: 12, time: "17:37" }],
  });
  assert.deepEqual(phases, {
    year: 2026,
    phases: [{ phase: "New Moon", year: 2026, month: 8, day: 12, time: "17:37" }],
  });

  const eclipses = summarizeUsnoSolarEclipses({
    year: 2026,
    eclipses_in_year: [
      { day: 12, event: "Total Solar Eclipse of 12 August 2026", month: 8, year: 2026 },
    ],
  }, "2026-08-12");
  assert.deepEqual(eclipses, {
    year: 2026,
    events: [{ day: 12, event: "Total Solar Eclipse of 12 August 2026", month: 8, year: 2026 }],
    event_today: { day: 12, event: "Total Solar Eclipse of 12 August 2026", month: 8, year: 2026 },
    local_visibility: "not-provided-by-usno-year-endpoint",
  });
});
