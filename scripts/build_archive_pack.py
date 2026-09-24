#!/usr/bin/env python3
from __future__ import annotations

import argparse
import calendar
import gzip
import hashlib
import io
import json
import platform
import subprocess
import tarfile
from collections import Counter
from datetime import datetime
from pathlib import Path

import duckdb

ARCHIVE_VERSION = 1
PROVIDERS = {"openai_status", "github_status", "huggingface_status"}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_value(root: Path, expr: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", expr],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def period_files(root: Path, period: str) -> list[Path]:
    datetime.strptime(period, "%Y-%m")
    files = sorted((root / "data").glob(f"{period}-??/public-status.jsonl"))
    if not files:
        raise SystemExit(f"no canonical data for {period}")
    return files


def health(snapshot: dict, item: dict) -> tuple:
    v1 = snapshot.get("schema_version") == 1 and item.get("schema_version") == 1
    if v1:
        semantic = (item.get("semantic") or {}).get("status")
        return (
            1,
            None,
            (item.get("transport") or {}).get("status"),
            (item.get("parser") or {}).get("status"),
            semantic,
            semantic == "available",
        )
    ok = bool(item.get("ok", False))
    return 0, ok, None, None, None, ok


def source_status(item: dict, usable: bool) -> str:
    if not usable:
        return "UNKNOWN"
    summary = item.get("summary") or {}
    return str(summary.get("indicator") or summary.get("description") or "OBSERVED")


def scale(summary: dict, key: str) -> int | None:
    raw = ((summary.get("current") or {}).get(key) or {}).get("Scale")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def signals(
    snapshot: dict, item: dict, usable: bool, path: str, line: int
) -> list[tuple]:
    out = []
    collected = snapshot["collected_at"]
    sid = item["id"]
    schema = int(item.get("schema_version") or snapshot.get("schema_version") or 0)
    summary = item.get("summary") or {}

    def add(name, num=None, text=None, measured=None, unit=None, signal_scale=None):
        out.append(
            (
                collected,
                measured,
                sid,
                schema,
                name,
                float(num) if num is not None else None,
                text,
                unit,
                signal_scale,
                usable,
                path,
                line,
            )
        )

    if item.get("latency_ms") is not None:
        add("collector_latency_ms", item["latency_ms"], measured=collected, unit="ms")
    if sid in PROVIDERS:
        add(
            "provider_status",
            text=source_status(item, usable),
            measured=collected,
            signal_scale="provider_status",
        )

    if sid == "noaa_planetary_k_index":
        latest = summary.get("latest") or {}
        if latest.get("Kp") is not None and latest.get("time_tag"):
            add(
                "kp",
                latest["Kp"],
                measured=str(latest["time_tag"]),
                unit="Kp",
                signal_scale="0-9",
            )
        elif summary.get("rows") is not None:
            # Legacy v0 never captured the actual Kp value.
            add("kp_row_count", summary["rows"], unit="rows")

    if sid == "noaa_scales":
        current = summary.get("current") or {}
        measured = None
        if current.get("DateStamp") and current.get("TimeStamp"):
            measured = f"{current['DateStamp']}T{current['TimeStamp']}Z"
        for key in ("R", "S", "G"):
            value = scale(summary, key)
            if value is not None:
                add(
                    f"noaa_{key.lower()}_scale",
                    value,
                    measured=measured,
                    unit="NOAA_scale",
                    signal_scale="0-5",
                )
    return out


def load_rows(root: Path, files: list[Path]) -> tuple[list[tuple], list[tuple], dict]:
    obs, sig = [], []
    collection_versions, source_versions, source_counts = (
        Counter(),
        Counter(),
        Counter(),
    )
    first = last = None
    collections = 0

    for file in files:
        rel = file.relative_to(root).as_posix()
        for lineno, raw in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            snap = json.loads(raw)
            collections += 1
            cv = int(snap.get("schema_version") or 0)
            collection_versions[cv] += 1
            first = first or snap["collected_at"]
            last = snap["collected_at"]
            run = snap.get("run") or {}

            for item in snap.get("sources", []):
                sv, legacy_ok, transport, parser, semantic, usable = health(snap, item)
                source_versions[sv] += 1
                source_counts[item["id"]] += 1
                obs.append(
                    (
                        snap["collected_at"],
                        run.get("github_run_id"),
                        run.get("github_sha"),
                        item["id"],
                        item.get("label"),
                        item.get("url"),
                        item.get("adapter"),
                        sv,
                        legacy_ok,
                        transport,
                        parser,
                        semantic,
                        usable,
                        source_status(item, usable),
                        item.get("http_status"),
                        item.get("latency_ms"),
                        item.get("payload_sha256"),
                        json.dumps(
                            item.get("summary") or {},
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                        rel,
                        lineno,
                    )
                )
                sig.extend(signals(snap, item, usable, rel, lineno))

    return (
        obs,
        sig,
        {
            "collection_rows": collections,
            "source_observations": len(obs),
            "signal_rows": len(sig),
            "first_collected_at": first,
            "last_collected_at": last,
            "collection_schema_versions": dict(sorted(collection_versions.items())),
            "source_schema_versions": dict(sorted(source_versions.items())),
            "source_counts": dict(sorted(source_counts.items())),
        },
    )


def write_parquet(
    obs_path: Path, sig_path: Path, obs: list[tuple], sig: list[tuple]
) -> None:
    con = duckdb.connect()
    try:
        con.execute("""create table observations(
          collected_at timestamptz, run_id varchar, run_sha varchar,
          source_id varchar, label varchar, url varchar, adapter varchar,
          source_schema_version integer, legacy_collector_ok boolean,
          transport_status varchar, parser_status varchar, semantic_status varchar,
          usable boolean, source_status varchar, http_status integer, latency_ms double,
          payload_sha256 varchar, summary_json varchar,
          provenance_path varchar, provenance_line integer)""")
        con.execute("""create table signals(
          collected_at timestamptz, measurement_at timestamptz,
          source_id varchar, source_schema_version integer, signal_name varchar,
          value_num double, value_text varchar, unit varchar, scale varchar,
          usable boolean, provenance_path varchar, provenance_line integer)""")
        con.executemany(
            "insert into observations values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            obs,
        )
        con.executemany("insert into signals values (?,?,?,?,?,?,?,?,?,?,?,?)", sig)
        o = str(obs_path).replace("'", "''")
        s = str(sig_path).replace("'", "''")
        con.execute(f"COPY observations TO '{o}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        con.execute(f"COPY signals TO '{s}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    finally:
        con.close()


def write_raw(root: Path, files: list[Path], target: Path) -> None:
    with target.open("wb") as raw_out:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_out, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tf:
                for file in files:
                    data = file.read_bytes()
                    info = tarfile.TarInfo(file.relative_to(root).as_posix())
                    info.size, info.mtime, info.uid, info.gid, info.mode = (
                        len(data),
                        0,
                        0,
                        0,
                        0o644,
                    )
                    info.uname = info.gname = ""
                    tf.addfile(info, io.BytesIO(data))


def build(root: Path, period: str, out: Path) -> Path:
    root, out = root.resolve(), out.resolve()
    files = period_files(root, period)
    out.mkdir(parents=True, exist_ok=True)
    for p in out.iterdir():
        if p.is_file():
            p.unlink()
        else:
            raise SystemExit(f"unexpected directory in output: {p}")

    obs, sig, stats = load_rows(root, files)
    raw_path, obs_path, sig_path = (
        out / "raw-jsonl.tar.gz",
        out / "observations.parquet",
        out / "signals.parquet",
    )
    schema_path, manifest_path, sums_path = (
        out / "schema.json",
        out / "manifest.json",
        out / "SHA256SUMS",
    )

    write_raw(root, files, raw_path)
    write_parquet(obs_path, sig_path, obs, sig)
    schema_path.write_text(
        json.dumps(
            {
                "archive_schema_version": ARCHIVE_VERSION,
                "authority": "data/YYYY-MM-DD/public-status.jsonl",
                "observations": "one row per collected source observation",
                "signals": "only explicitly observed typed values; missing legacy values remain absent",
                "duckdb": "analysis engine only; never archive authority",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    inputs, dates = [], []
    for file in files:
        data = file.read_bytes()
        dates.append(file.parent.name)
        inputs.append(
            {
                "path": file.relative_to(root).as_posix(),
                "bytes": len(data),
                "lines": sum(1 for line in data.splitlines() if line.strip()),
                "sha256": sha_bytes(data),
            }
        )

    year, month = map(int, period.split("-"))
    expected_days = calendar.monthrange(year, month)[1]
    observed = sorted({int(d[-2:]) for d in dates})
    head = git_value(root, "HEAD")
    assets = {
        p.name: {"bytes": p.stat().st_size, "sha256": sha_file(p)}
        for p in (raw_path, obs_path, sig_path, schema_path)
    }
    manifest = {
        "archive_schema_version": ARCHIVE_VERSION,
        "pack_id": f"observatory-data-{period}-v{ARCHIVE_VERSION}-{head[:12]}",
        "period": period,
        "period_complete": observed == list(range(1, expected_days + 1)),
        "repository": "TeaShaman-cyber/theseus-public-observatory",
        "git_head": head,
        "git_tree": git_value(root, "HEAD^{tree}"),
        "canonical_authority": "data/YYYY-MM-DD/public-status.jsonl",
        "coverage": {
            **stats,
            "observed_dates": dates,
            "observed_days": len(observed),
            "expected_days": expected_days,
        },
        "inputs": inputs,
        "assets": assets,
        "producer": {
            "script": "scripts/build_archive_pack.py",
            "python": platform.python_version(),
            "duckdb": duckdb.__version__,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hashed = (raw_path, obs_path, sig_path, schema_path, manifest_path)
    sums_path.write_text(
        "".join(f"{sha_file(p)}  {p.name}\n" for p in hashed), encoding="utf-8"
    )
    return out


def verify(pack: Path) -> dict:
    pack = pack.resolve()
    manifest = json.loads((pack / "manifest.json").read_text())
    sums = {}
    for line in (pack / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        sums[name] = digest
    expected = {
        "raw-jsonl.tar.gz",
        "observations.parquet",
        "signals.parquet",
        "schema.json",
        "manifest.json",
    }
    if set(sums) != expected:
        raise SystemExit("SHA256SUMS file set mismatch")
    for name, digest in sums.items():
        if sha_file(pack / name) != digest:
            raise SystemExit(f"hash mismatch: {name}")

    expected_raw = {x["path"]: x for x in manifest["inputs"]}
    with tarfile.open(pack / "raw-jsonl.tar.gz", "r:gz") as tf:
        actual_raw = {}
        for member in tf.getmembers():
            if not member.isfile():
                continue
            f = tf.extractfile(member)
            data = f.read() if f else b""
            actual_raw[member.name] = {
                "bytes": len(data),
                "lines": sum(1 for line in data.splitlines() if line.strip()),
                "sha256": sha_bytes(data),
            }
    if actual_raw != {
        k: {x: v[x] for x in ("bytes", "lines", "sha256")}
        for k, v in expected_raw.items()
    }:
        raise SystemExit("raw archive differs from manifest")

    con = duckdb.connect()
    try:
        obs = str(pack / "observations.parquet").replace("'", "''")
        sig = str(pack / "signals.parquet").replace("'", "''")
        obs_count = con.execute(
            f"select count(*) from read_parquet('{obs}')"
        ).fetchone()[0]
        sig_count = con.execute(
            f"select count(*) from read_parquet('{sig}')"
        ).fetchone()[0]
        kp_count = con.execute(
            f"select count(*) from read_parquet('{sig}') where signal_name='kp' and value_num is not null"
        ).fetchone()[0]
        bad_legacy = con.execute(
            f"select count(*) from read_parquet('{sig}') where signal_name='kp' and source_schema_version=0"
        ).fetchone()[0]
    finally:
        con.close()

    cov = manifest["coverage"]
    if obs_count != cov["source_observations"] or sig_count != cov["signal_rows"]:
        raise SystemExit("Parquet row counts differ from manifest")
    if bad_legacy:
        raise SystemExit("legacy v0 was incorrectly converted to Kp")
    if int(cov["source_schema_versions"].get("1", 0)) and not kp_count:
        raise SystemExit("v1 exists but typed Kp is missing")
    return {
        "status": "VERIFIED",
        "pack_id": manifest["pack_id"],
        "period": manifest["period"],
        "period_complete": manifest["period_complete"],
        "collection_rows": cov["collection_rows"],
        "source_observations": obs_count,
        "signal_rows": sig_count,
        "kp_measurements": kp_count,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--repo-root", type=Path, default=Path("."))
    b.add_argument("--period", required=True)
    b.add_argument("--output-dir", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--pack-dir", type=Path, required=True)
    args = p.parse_args()
    if args.cmd == "build":
        print(
            json.dumps(
                {
                    "status": "BUILT",
                    "pack_dir": str(
                        build(args.repo_root, args.period, args.output_dir)
                    ),
                },
                sort_keys=True,
            )
        )
    else:
        print(json.dumps(verify(args.pack_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
