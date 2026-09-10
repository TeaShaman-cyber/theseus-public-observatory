const USNO_BASE = "https://aa.usno.navy.mil/api";

export const ASTRONOMY_OBSERVER = Object.freeze({
  id: "kaliningrad",
  label: "Kaliningrad, Russia",
  latitude: 54.7104,
  longitude: 20.4522,
  timezoneOffsetHours: 2,
});

export function observerLocalDate(date = new Date()) {
  const localMillis = date.getTime() + ASTRONOMY_OBSERVER.timezoneOffsetHours * 60 * 60 * 1000;
  return new Date(localMillis).toISOString().slice(0, 10);
}

function mapPhenomena(items = []) {
  return Object.fromEntries(
    items
      .filter((item) => item && item.phen)
      .map((item) => [
        item.phen
          .toLowerCase()
          .replace(/\s+/g, "_")
          .replace(/[^a-z0-9_]/g, ""),
        item.time ?? null,
      ]),
  );
}

function illuminationPercent(value) {
  if (typeof value === "number") {
    return Number.isFinite(value) && value >= 0 && value <= 100 ? value : null;
  }
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  if (!/^\d+(?:\.\d+)?%?$/.test(normalized)) return null;
  const parsed = Number(normalized.replace("%", ""));
  return Number.isFinite(parsed) && parsed >= 0 && parsed <= 100 ? parsed : null;
}

function datePartNumber(value) {
  if (typeof value === "number" && Number.isInteger(value)) return value;
  if (typeof value === "string" && /^\d+$/.test(value.trim())) return Number(value.trim());
  return null;
}

function isCalendarDate(yearValue, monthValue, dayValue) {
  const year = datePartNumber(yearValue);
  const month = datePartNumber(monthValue);
  const day = datePartNumber(dayValue);
  if (year === null || year < 1000 || year > 9999) return false;
  if (month === null || month < 1 || month > 12) return false;
  if (day === null || day < 1 || day > 31) return false;
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

function hasPhaseRecord(record) {
  return Boolean(
    record &&
      typeof record === "object" &&
      typeof record.phase === "string" &&
      record.phase.trim() &&
      isCalendarDate(record.year, record.month, record.day) &&
      typeof record.time === "string" &&
      record.time.trim(),
  );
}

function hasEclipseRecord(record) {
  return Boolean(
    record &&
      typeof record === "object" &&
      typeof record.event === "string" &&
      record.event.trim() &&
      isCalendarDate(record.year, record.month, record.day),
  );
}

export function buildAstronomySources(date = new Date()) {
  const day = observerLocalDate(date);
  const year = day.slice(0, 4);
  const coords = `${ASTRONOMY_OBSERVER.latitude},${ASTRONOMY_OBSERVER.longitude}`;
  const encodedCoords = encodeURIComponent(coords);
  const tz = ASTRONOMY_OBSERVER.timezoneOffsetHours;

  return [
    {
      id: "usno_sun_moon",
      label: "USNO Sun and Moon Data",
      url: `${USNO_BASE}/rstt/oneday?date=${day}&coords=${encodedCoords}&tz=${tz}`,
      kind: "usno-sun-moon",
      adapter: "usno-sun-moon-v1",
      observer_local_date: day,
    },
    {
      id: "usno_moon_phases",
      label: "USNO Moon Phases",
      url: `${USNO_BASE}/moon/phases/date?date=${day}&nump=4`,
      kind: "usno-moon-phases",
      adapter: "usno-moon-phases-v1",
      observer_local_date: day,
    },
    {
      id: "usno_solar_eclipses",
      label: "USNO Solar Eclipses",
      url: `${USNO_BASE}/eclipses/solar/year?year=${year}`,
      kind: "usno-solar-eclipses",
      adapter: "usno-solar-eclipses-v1",
      observer_local_date: day,
    },
  ];
}

export function summarizeUsnoSunMoon(payload) {
  const data = payload?.properties?.data ?? {};
  return {
    observer: ASTRONOMY_OBSERVER,
    moon: {
      current_phase: data.curphase ?? null,
      illumination_percent: illuminationPercent(data.fracillum),
      closest_primary_phase: data.closestphase ?? null,
      events: mapPhenomena(data.moondata),
    },
    sun: {
      events: mapPhenomena(data.sundata),
    },
    timezone_offset_hours: data.tz ?? ASTRONOMY_OBSERVER.timezoneOffsetHours,
  };
}

export function summarizeUsnoMoonPhases(payload) {
  return {
    year: payload?.year ?? null,
    phases: Array.isArray(payload?.phasedata) ? payload.phasedata : [],
  };
}

export function summarizeUsnoSolarEclipses(payload, localDate) {
  const events = Array.isArray(payload?.eclipses_in_year)
    ? payload.eclipses_in_year
    : [];
  const eventToday = events.find((event) => {
    if (!localDate) return false;
    const year = String(event.year).padStart(4, "0");
    const month = String(event.month).padStart(2, "0");
    const day = String(event.day).padStart(2, "0");
    return `${year}-${month}-${day}` === localDate;
  }) ?? null;
  return {
    year: payload?.year ?? null,
    events,
    event_today: eventToday,
    local_visibility: "not-provided-by-usno-year-endpoint",
  };
}

export function summarizeAstronomy(source, payload, localDate) {
  if (source.kind === "usno-sun-moon") return summarizeUsnoSunMoon(payload);
  if (source.kind === "usno-moon-phases") return summarizeUsnoMoonPhases(payload);
  if (source.kind === "usno-solar-eclipses") return summarizeUsnoSolarEclipses(payload, localDate);
  return { type: Array.isArray(payload) ? "array" : typeof payload };
}

function exactYear(value) {
  if (Number.isInteger(value) && value >= 1000 && value <= 9999) return value;
  if (typeof value === "string" && /^\d{4}$/.test(value)) return Number(value);
  return null;
}

function hasUsnoSchema(source, payload, localDate) {
  if (source.kind === "usno-sun-moon") {
    const data = payload?.properties?.data;
    return Boolean(
      data &&
        typeof data === "object" &&
        typeof data.curphase === "string" &&
        illuminationPercent(data.fracillum) !== null &&
        Array.isArray(data.moondata) &&
        Array.isArray(data.sundata),
    );
  }

  if (source.kind === "usno-moon-phases") {
    return (
      Array.isArray(payload?.phasedata) &&
      payload.phasedata.length > 0 &&
      payload.phasedata.every(hasPhaseRecord)
    );
  }

  if (source.kind === "usno-solar-eclipses") {
    const requestedDate = source.observer_local_date ?? localDate ?? "";
    const requestedYear = exactYear(String(requestedDate).slice(0, 4));
    const payloadYear = exactYear(payload?.year);
    return (
      payloadYear !== null &&
      (requestedYear === null || payloadYear === requestedYear) &&
      Array.isArray(payload?.eclipses_in_year) &&
      payload.eclipses_in_year.every(hasEclipseRecord)
    );
  }

  return false;
}

export function interpretAstronomy(source, payload, localDate) {
  if (!hasUsnoSchema(source, payload, localDate)) {
    return { ok: false, error: "schema-mismatch", summary: null };
  }
  return {
    ok: true,
    error: null,
    summary: summarizeAstronomy(source, payload, localDate),
  };
}
