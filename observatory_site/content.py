from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .model import (
    ExperimentSummary,
    ObservationSnapshot,
    ReportSummary,
    SourceObservation,
)


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_latest_snapshot(
    repo_root: Path, *, now: datetime, freshness_budget_seconds: int
) -> ObservationSnapshot:
    path = repo_root / "data" / "latest" / "public-status.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    collected_at = _parse_dt(data["collected_at"])
    age = max(0.0, (now.astimezone(timezone.utc) - collected_at).total_seconds())
    freshness = "STALE" if age > freshness_budget_seconds else "OBSERVATION"
    sources = []
    for item in data.get("sources", []):
        is_v1 = data.get("schema_version") == 1 and item.get("schema_version") == 1
        summary = item.get("summary") or {}
        if is_v1:
            transport_status = str(
                (item.get("transport") or {}).get("status") or "unknown"
            )
            parser_status = str((item.get("parser") or {}).get("status") or "unknown")
            semantic_status = str(
                (item.get("semantic") or {}).get("status") or "unknown"
            )
            collector_ok = semantic_status == "available"
        else:
            http_status = item.get("http_status")
            transport_status = (
                "ok"
                if isinstance(http_status, int) and 200 <= http_status < 300
                else "legacy-unknown"
            )
            parser_status = (
                "invalid-json"
                if item.get("error") == "invalid-json"
                else "legacy-unknown"
            )
            collector_ok = bool(item.get("ok", False))
            semantic_status = "legacy-usable" if collector_ok else "legacy-unavailable"
        if collector_ok:
            source_status = str(
                summary.get("indicator") or summary.get("description") or "OBSERVED"
            )
        else:
            source_status = "UNKNOWN"
        sources.append(
            SourceObservation(
                source_id=item["id"],
                label=item["label"],
                url=item["url"],
                collector_ok=collector_ok,
                source_status=source_status,
                http_status=item.get("http_status"),
                latency_ms=item.get("latency_ms"),
                transport_status=transport_status,
                parser_status=parser_status,
                semantic_status=semantic_status,
                legacy=not is_v1,
                summary=summary,
                error=item.get("error"),
            )
        )
    return ObservationSnapshot(
        collected_at=collected_at,
        freshness=freshness,
        age_seconds=age,
        sources=tuple(sources),
    )


def load_reports(repo_root: Path) -> list[ReportSummary]:
    reports = []
    for path in sorted((repo_root / "reports").glob("*.md"), reverse=True):
        if path.name.lower() == "readme.md":
            continue
        first = path.read_text(encoding="utf-8").splitlines()
        title = next(
            (line[2:].strip() for line in first if line.startswith("# ")), path.stem
        )
        reports.append(
            ReportSummary(
                slug=path.stem, title=title, path=str(path.relative_to(repo_root))
            )
        )
    return reports


def load_experiments(repo_root: Path) -> list[ExperimentSummary]:
    base = repo_root / "experiments" / "public"
    if not base.exists():
        return []
    out = []
    for path in sorted(base.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        out.append(ExperimentSummary(**d))
    return out
