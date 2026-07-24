from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Sequence

ALLOWED_EPISTEMIC = {
    "OBSERVATION",
    "MEASUREMENT_ONLY",
    "HYPOTHESIS",
    "VERIFIED_ARTIFACT",
    "VERIFIED_EXECUTION",
    "DEGRADED",
    "STALE",
    "UNKNOWN",
}
ALLOWED_STAGES = {"PILOT", "RUNNING", "COMPLETE", "ARCHIVED"}


@dataclass(frozen=True)
class SourceObservation:
    source_id: str
    label: str
    url: str
    collector_ok: bool
    source_status: str
    http_status: int | None
    latency_ms: float | None
    summary: Mapping[str, object] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class ObservationSnapshot:
    collected_at: datetime
    freshness: str
    age_seconds: float
    sources: Sequence[SourceObservation]


@dataclass(frozen=True)
class ReportSummary:
    slug: str
    title: str
    path: str


@dataclass(frozen=True)
class ExperimentSummary:
    slug: str
    title: str
    question: str
    stage: str
    epistemic_status: str
    result_summary: str
    does_not_establish: str
    source_urls: Sequence[str] = ()
    source_hashes: Mapping[str, str] = field(default_factory=dict)
    artifact_hashes: Mapping[str, str] = field(default_factory=dict)
    workflow_url: str | None = None
    code_url: str | None = None
    next_gate: str | None = None

    def __post_init__(self) -> None:
        if self.stage not in ALLOWED_STAGES:
            raise ValueError(f"unsupported lifecycle stage: {self.stage}")
        if self.epistemic_status not in ALLOWED_EPISTEMIC:
            raise ValueError(f"unsupported epistemic status: {self.epistemic_status}")
        if self.epistemic_status.startswith("VERIFIED_") and not (
            self.source_hashes or self.artifact_hashes
        ):
            raise ValueError("verified experiment requires durable hashes")
