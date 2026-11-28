#!/usr/bin/env python3
from __future__ import annotations

import argparse
import calendar
import gzip
import hashlib
import io
import json
import platform
import re
import subprocess
import tarfile
from collections import Counter
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


def capture_inputs(root: Path, period: str, head: str) -> dict[str, bytes]:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", period):
        raise SystemExit("invalid period")
    year, month = map(int, period.split("-"))
    if not 1 <= month <= 12 or year == 0:
        raise SystemExit("invalid period")
    expected_days = calendar.monthrange(year, month)[1]
    pattern = re.compile(r"data/" + period + r"-([0-9]{2})/public-status[.]jsonl")
    tree = subprocess.check_output(
        ["git", "-C", str(root), "ls-tree", "-r", "-z", head, "--", "data"]
    )
    blobs = {}
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        meta, name = entry.split(b"\t", 1)
        rel = name.decode("utf-8", errors="surrogateescape")
        match = pattern.fullmatch(rel)
        if not match:
            continue
        mode, kind, oid = meta.split()
        if not 1 <= int(match[1]) <= expected_days:
            raise SystemExit(f"invalid raw member path: {rel}")
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            raise SystemExit(f"nonregular Git input: {rel}")
        blobs[rel] = oid.decode("ascii")
    files = {
        f.relative_to(root).as_posix(): f
        for f in (root / "data").glob(f"{period}-??/public-status.jsonl")
    }
    if files.keys() != blobs.keys():
        raise SystemExit("input set differs from Git")
    if not blobs:
        raise SystemExit(f"no canonical data for {period}")
    captured = {}
    for rel, oid in sorted(blobs.items()):
        path = files[rel]
        if (
            path.is_symlink()
            or path.parent.is_symlink()
            or (root / "data").is_symlink()
            or not path.is_file()
        ):
            raise SystemExit(f"nonregular working-tree input: {rel}")
        data = subprocess.check_output(
            ["git", "-C", str(root), "cat-file", "blob", oid]
        )
        if path.read_bytes() != data:
            raise SystemExit(f"input differs from Git: {rel}")
        captured[rel] = data
    return captured


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


def project_rows(inputs) -> tuple[list[tuple], list[tuple], dict]:
    obs, sig = [], []
    collection_versions, source_versions, source_counts = (
        Counter(),
        Counter(),
        Counter(),
    )
    first = last = None
    collections = 0

    for rel, content in inputs:
        for lineno, raw in enumerate(content.splitlines(), 1):
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


def projection_tables(con, obs, sig):
    con.execute("set timezone='UTC'")
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
    if obs:
        con.executemany(
            "insert into observations values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            obs,
        )
    if sig:
        con.executemany("insert into signals values (?,?,?,?,?,?,?,?,?,?,?,?)", sig)


def write_parquet(
    obs_path: Path, sig_path: Path, obs: list[tuple], sig: list[tuple]
) -> None:
    with duckdb.connect() as con:
        projection_tables(con, obs, sig)
        con.execute(
            "COPY observations TO ? (FORMAT PARQUET, COMPRESSION ZSTD)", [str(obs_path)]
        )
        con.execute(
            "COPY signals TO ? (FORMAT PARQUET, COMPRESSION ZSTD)", [str(sig_path)]
        )


def write_raw(inputs: dict[str, bytes], target: Path) -> None:
    with target.open("wb") as raw_out:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_out, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tf:
                for rel, data in inputs.items():
                    info = tarfile.TarInfo(rel)
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
    root = root.resolve()
    # Resolve the parent, not a potentially existing output symlink.
    out = out.parent.resolve() / out.name
    if out.exists() or out.is_symlink():
        raise SystemExit(f"output already exists: {out}")
    head = git_value(root, "HEAD")
    tree = git_value(root, f"{head}^{{tree}}")
    captured = capture_inputs(root, period, head)
    obs, sig, stats = project_rows(
        (rel, data.decode("utf-8")) for rel, data in captured.items()
    )
    # Exclusive creation also catches another builder winning the race.
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise SystemExit(f"output already exists: {out}") from exc

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

    write_raw(captured, raw_path)
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
    for rel, data in captured.items():
        dates.append(rel.split("/")[1])
        inputs.append(
            {
                "path": rel,
                "bytes": len(data),
                "lines": sum(1 for line in data.splitlines() if line.strip()),
                "sha256": sha_bytes(data),
            }
        )

    year, month = map(int, period.split("-"))
    expected_days = calendar.monthrange(year, month)[1]
    observed = sorted({int(d[-2:]) for d in dates})
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
        "git_tree": tree,
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


def verify_checksums(pack):
    sums = {}
    expected = {
        "raw-jsonl.tar.gz",
        "observations.parquet",
        "signals.parquet",
        "schema.json",
        "manifest.json",
    }
    for line in (pack / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if name in sums:
            raise SystemExit("duplicate checksum record")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise SystemExit("invalid checksum digest")
        sums[name] = digest
    if set(sums) != expected:
        raise SystemExit("SHA256SUMS file set mismatch")
    for name, digest in sums.items():
        path = pack / name
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"missing or nonregular asset: {name}")
        if sha_file(path) != digest:
            raise SystemExit(f"hash mismatch: {name}")
    return sums


def verify_raw(pack, manifest):
    period = manifest["period"]
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", period):
        raise SystemExit("invalid period")
    expected_days = calendar.monthrange(*map(int, period.split("-")))[1]
    expected_raw = {}
    for item in manifest["inputs"]:
        name = item["path"]
        if name in expected_raw:
            raise SystemExit("duplicate manifest input")
        match = re.fullmatch(
            r"data/(" + period + r"-[0-9]{2})/public-status[.]jsonl", name
        )
        if not match or not 1 <= int(match[1][-2:]) <= expected_days:
            raise SystemExit("invalid raw member path")
        expected_raw[name] = {k: item[k] for k in ("bytes", "lines", "sha256")}
    if not expected_raw:
        raise SystemExit("empty raw manifest")
    raw = {}
    with tarfile.open(pack / "raw-jsonl.tar.gz", "r:gz") as tf:
        for member in tf:
            if not member.isfile() or member.name not in expected_raw:
                raise SystemExit("unexpected or nonregular raw member")
            if member.name in raw:
                raise SystemExit("duplicate raw member")
            if member.size != expected_raw[member.name]["bytes"]:
                raise SystemExit("raw archive differs from manifest")
            with tf.extractfile(member) as f:
                data = f.read()
            meta = {
                "bytes": len(data),
                "lines": sum(1 for line in data.splitlines() if line.strip()),
                "sha256": sha_bytes(data),
            }
            if meta != expected_raw[member.name]:
                raise SystemExit("raw archive differs from manifest")
            raw[member.name] = data.decode("utf-8")
    if raw.keys() != expected_raw.keys():
        raise SystemExit("raw archive differs from manifest")
    obs, sig, stats = project_rows(sorted(raw.items()))
    dates = [name.split("/")[1] for name in sorted(raw)]
    expected_coverage = {
        **stats,
        "observed_dates": dates,
        "observed_days": len(dates),
        "expected_days": expected_days,
    }
    if manifest["coverage"] != json.loads(json.dumps(expected_coverage)) or manifest[
        "period_complete"
    ] is not (len(dates) == expected_days):
        raise SystemExit("coverage differs from raw archive")
    return obs, sig


def verify_projection(pack, obs, sig):
    with duckdb.connect() as con:
        projection_tables(con, obs, sig)
        for table in ("observations", "signals"):
            path = str(pack / (table + ".parquet"))
            actual = con.execute(
                "describe select * from read_parquet(?)", [path]
            ).fetchall()
            expected = con.execute(f"describe select * from {table}").fetchall()
            if [(r[0], r[1]) for r in actual] != [(r[0], r[1]) for r in expected]:
                raise SystemExit(f"projection schema differs: {table}")
            # EXCEPT ALL compares multisets in both directions, including duplicate rows and NULL.
            mismatch = con.execute(
                f"""select exists (
                    (select * from {table} except all select * from read_parquet(?))
                    union all
                    (select * from read_parquet(?) except all select * from {table})
                )""",
                [path, path],
            ).fetchone()[0]
            if mismatch:
                raise SystemExit(f"projection differs from raw archive: {table}")
        kp_count, bad_legacy = con.execute("""
            select count(*) filter(where signal_name='kp' and value_num is not null),
                count(*) filter(where signal_name='kp' and source_schema_version=0)
            from signals
        """).fetchone()
        if bad_legacy:
            raise SystemExit("legacy v0 was incorrectly converted to Kp")
    return kp_count


def verify(pack: Path) -> dict:
    pack = pack.resolve()
    sums = verify_checksums(pack)
    manifest = json.loads((pack / "manifest.json").read_text())
    if manifest["archive_schema_version"] != ARCHIVE_VERSION:
        raise SystemExit("unsupported archive schema version")
    expected_assets = {
        name: {"bytes": (pack / name).stat().st_size, "sha256": digest}
        for name, digest in sums.items()
        if name != "manifest.json"
    }
    if manifest["assets"] != expected_assets:
        raise SystemExit("asset metadata differs from checksums")
    obs, sig = verify_raw(pack, manifest)
    kp_count = verify_projection(pack, obs, sig)
    return {
        "status": "VERIFIED",
        "pack_id": manifest["pack_id"],
        "period": manifest["period"],
        "period_complete": manifest["period_complete"],
        "collection_rows": manifest["coverage"]["collection_rows"],
        "source_observations": len(obs),
        "signal_rows": len(sig),
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
