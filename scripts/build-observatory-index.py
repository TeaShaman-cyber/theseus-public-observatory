#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

PROVIDERS = {"openai_status", "github_status", "huggingface_status"}
SPACE_WEATHER = {"noaa_scales", "noaa_planetary_k_index"}
ASTRONOMY = {"usno_sun_moon", "usno_moon_phases", "usno_solar_eclipses"}


def _iter_snapshots(repo_root: Path):
    for path in sorted((repo_root / "data").glob("????-??-??/public-status.jsonl")):
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            yield path, line_no, json.loads(line)


def _source_status(item: dict, usable: bool) -> str:
    if not usable:
        return "UNKNOWN"
    summary = item.get("summary") or {}
    return str(summary.get("indicator") or summary.get("description") or "OBSERVED")


def _health_fields(snapshot: dict, item: dict):
    is_v1 = snapshot.get("schema_version") == 1 and item.get("schema_version") == 1
    if is_v1:
        transport_status = (item.get("transport") or {}).get("status")
        parser_status = (item.get("parser") or {}).get("status")
        semantic_status = (item.get("semantic") or {}).get("status")
        usable = semantic_status == "available"
        return 1, None, transport_status, parser_status, semantic_status, usable

    collector_ok = bool(item.get("ok", False))
    return 0, collector_ok, None, None, None, collector_ok


def _scale(summary: dict, key: str):
    cur = (summary.get("current") or {}).get(key) or {}
    raw = cur.get("Scale")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _event(summary: dict, body: str, name: str):
    return ((summary.get(body) or {}).get("events") or {}).get(name)


def build_index(repo_root: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    con = duckdb.connect(str(output))
    try:
        con.execute("""
            create table observations(
              collected_at timestamptz,
              source_id varchar,
              label varchar,
              schema_version integer,
              collector_ok boolean,
              transport_status varchar,
              parser_status varchar,
              semantic_status varchar,
              usable boolean,
              source_status varchar,
              http_status integer,
              latency_ms double,
              provenance_path varchar,
              provenance_line integer
            )
        """)
        con.execute("""
            create table provider_status(
              collected_at timestamptz,
              source_id varchar,
              schema_version integer,
              collector_ok boolean,
              transport_status varchar,
              parser_status varchar,
              semantic_status varchar,
              usable boolean,
              source_status varchar,
              http_status integer,
              latency_ms double,
              provenance_path varchar,
              provenance_line integer
            )
        """)
        con.execute("""
            create table space_weather(
              collected_at timestamptz,
              source_id varchar,
              schema_version integer,
              collector_ok boolean,
              transport_status varchar,
              parser_status varchar,
              semantic_status varchar,
              usable boolean,
              r_scale integer,
              s_scale integer,
              g_scale integer,
              kp_rows integer,
              provenance_path varchar,
              provenance_line integer
            )
        """)
        con.execute("""
            create table astronomy(
              collected_at timestamptz,
              source_id varchar,
              schema_version integer,
              collector_ok boolean,
              transport_status varchar,
              parser_status varchar,
              semantic_status varchar,
              usable boolean,
              current_phase varchar,
              illumination_percent double,
              moon_rise varchar,
              moon_set varchar,
              sun_rise varchar,
              sun_set varchar,
              solar_eclipse_event varchar,
              local_visibility varchar,
              provenance_path varchar,
              provenance_line integer
            )
        """)

        obs_rows = []
        provider_rows = []
        weather_rows = []
        astronomy_rows = []
        for path, line_no, snap in _iter_snapshots(repo_root):
            rel = path.relative_to(repo_root).as_posix()
            ts = snap["collected_at"]
            for item in snap.get("sources", []):
                sid = item["id"]
                (
                    schema_version,
                    collector_ok,
                    transport_status,
                    parser_status,
                    semantic_status,
                    usable,
                ) = _health_fields(snap, item)
                status = _source_status(item, usable)
                health = (
                    schema_version,
                    collector_ok,
                    transport_status,
                    parser_status,
                    semantic_status,
                    usable,
                )
                base = (
                    ts,
                    sid,
                    item.get("label", sid),
                    *health,
                    status,
                    item.get("http_status"),
                    item.get("latency_ms"),
                    rel,
                    line_no,
                )
                obs_rows.append(base)
                if sid in PROVIDERS:
                    provider_rows.append(
                        (
                            ts,
                            sid,
                            *health,
                            status,
                            item.get("http_status"),
                            item.get("latency_ms"),
                            rel,
                            line_no,
                        )
                    )
                if sid in SPACE_WEATHER:
                    summary = item.get("summary") or {}
                    weather_rows.append(
                        (
                            ts,
                            sid,
                            *health,
                            _scale(summary, "R"),
                            _scale(summary, "S"),
                            _scale(summary, "G"),
                            summary.get("rows")
                            if sid == "noaa_planetary_k_index"
                            else None,
                            rel,
                            line_no,
                        )
                    )
                if sid in ASTRONOMY:
                    summary = item.get("summary") or {}
                    event_today = summary.get("event_today") or {}
                    astronomy_rows.append(
                        (
                            ts,
                            sid,
                            *health,
                            (summary.get("moon") or {}).get("current_phase"),
                            (summary.get("moon") or {}).get("illumination_percent"),
                            _event(summary, "moon", "rise"),
                            _event(summary, "moon", "set"),
                            _event(summary, "sun", "rise"),
                            _event(summary, "sun", "set"),
                            event_today.get("event"),
                            summary.get("local_visibility"),
                            rel,
                            line_no,
                        )
                    )
        if obs_rows:
            con.executemany(
                "insert into observations values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                obs_rows,
            )
        if provider_rows:
            con.executemany(
                "insert into provider_status values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                provider_rows,
            )
        if weather_rows:
            con.executemany(
                "insert into space_weather values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                weather_rows,
            )
        if astronomy_rows:
            con.executemany(
                "insert into astronomy values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                astronomy_rows,
            )

        con.execute(
            "create view v_source_health as select collected_at, source_id, schema_version, collector_ok, transport_status, parser_status, semantic_status, usable, source_status, latency_ms, provenance_path from observations"
        )
        con.execute(
            "create view v_provider_events as select * from provider_status where usable = false or source_status not in ('none','OBSERVED','All Systems Operational','operational')"
        )
        con.execute(
            "create view v_space_weather as select * from space_weather where usable = true"
        )
        con.execute("""
          create view v_probe_timeline as
          select collected_at, source_id, 'provider' as probe_family, schema_version, collector_ok, transport_status, parser_status, semantic_status, usable, source_status, provenance_path from provider_status
          union all
          select collected_at, source_id, 'space_weather' as probe_family, schema_version, collector_ok, transport_status, parser_status, semantic_status, usable, 'OBSERVED' as source_status, provenance_path from space_weather
          union all
          select collected_at, source_id, 'astronomy' as probe_family, schema_version, collector_ok, transport_status, parser_status, semantic_status, usable, coalesce(current_phase, solar_eclipse_event, 'OBSERVED') as source_status, provenance_path from astronomy
        """)
        con.execute("checkpoint")
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    build_index(args.repo_root.resolve(), args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
