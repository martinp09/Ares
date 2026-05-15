from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import generate_id, utc_now


class SourceRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


SourceCounty = Literal["harris", "montgomery"]
SourceRunKind = Literal[
    "morning_catchup",
    "midday",
    "end_of_day",
    "daily_reconciliation",
    "weekly_reconciliation",
    "manual",
]
SourceLane = Literal[
    "harris_county_probate",
    "montgomery_county_probate",
    "hcad_estate_of",
    "hctax_delinquency_overlay",
    "harris_land_records",
    "harris_hcad_property_match",
    "montgomery_cad_property_match",
    "harris_hctax_overlay",
    "montgomery_act_tax_overlay",
    "montgomery_land_records",
    "skiptrace_contact_enrichment",
    "copy_asset_generation",
    "hubspot_crm_mirror",
]


class SourceRunArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    artifact_type: str = Field(min_length=1)
    record_count: int = Field(default=0, ge=0)
    checksum: str | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("source_run"))
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    source_key: str = Field(min_length=1)
    source_label: str = Field(min_length=1)
    source_lane: SourceLane
    county: SourceCounty | None = None
    run_kind: SourceRunKind | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    idempotency_key: str | None = None
    source_reported_count: int | None = Field(default=None, ge=0)
    raw_count: int | None = Field(default=None, ge=0)
    parsed_count: int | None = Field(default=None, ge=0)
    keep_now_count: int | None = Field(default=None, ge=0)
    status: SourceRunStatus = SourceRunStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    artifact_count: int = Field(default=0, ge=0)
    record_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    error_message: str | None = None
    artifacts: list[SourceRunArtifact] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceRunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str = Field(min_length=1)
    source_label: str = Field(min_length=1)
    source_lane: SourceLane
    county: SourceCounty | None = None
    run_kind: SourceRunKind | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    idempotency_key: str | None = None
    source_reported_count: int | None = Field(default=None, ge=0)
    raw_count: int | None = Field(default=None, ge=0)
    parsed_count: int | None = Field(default=None, ge=0)
    keep_now_count: int | None = Field(default=None, ge=0)
    artifacts: list[SourceRunArtifact] = Field(default_factory=list)
    record_count: int | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)
    failed: bool = False
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NightlySourcePullRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    run_id: str | None = None
    command_id: str | None = None
    idempotency_key: str | None = None
    trigger_run_id: str | None = None
    source_runs: list[SourceRunManifest] = Field(default_factory=list)
    live_source_calls: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class MorningBriefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    run_id: str | None = None
    command_id: str | None = None
    idempotency_key: str | None = None
    trigger_run_id: str | None = None
    source_run_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MorningBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("morning_brief"))
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=utc_now)
    source_runs: list[SourceRun] = Field(default_factory=list)
    new_record_count: int = Field(default=0, ge=0)
    hot_lead_count: int = Field(default=0, ge=0)
    warm_lead_count: int = Field(default=0, ge=0)
    blocked_count: int = Field(default=0, ge=0)
    approval_required_count: int = Field(default=0, ge=0)
    sections: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class NightlySourcePullResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed"] = "completed"
    would_call_external_sources: bool = False
    live_source_calls_enabled: bool = False
    source_runs: list[SourceRun] = Field(default_factory=list)
    morning_brief: MorningBrief
    warnings: list[str] = Field(default_factory=list)
    duplicate: bool = False
    replayed: bool = False


class SourceRunArtifactSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    artifact_type: str = Field(min_length=1)
    record_count: int = Field(default=0, ge=0)
    checksum: str | None = None
    warning_count: int = Field(default=0, ge=0)


class SourceRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    business_id: str
    environment: str
    source_key: str
    source_label: str
    source_lane: SourceLane
    county: SourceCounty | None = None
    run_kind: SourceRunKind | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    idempotency_key: str | None = None
    source_reported_count: int | None = Field(default=None, ge=0)
    raw_count: int | None = Field(default=None, ge=0)
    parsed_count: int | None = Field(default=None, ge=0)
    keep_now_count: int | None = Field(default=None, ge=0)
    status: SourceRunStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    artifact_count: int = Field(default=0, ge=0)
    record_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    error_message: str | None = None
    artifacts: list[SourceRunArtifactSummary] = Field(default_factory=list)


class MorningBriefSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    business_id: str
    environment: str
    generated_at: datetime
    source_runs: list[SourceRunSummary] = Field(default_factory=list)
    new_record_count: int = Field(default=0, ge=0)
    hot_lead_count: int = Field(default=0, ge=0)
    warm_lead_count: int = Field(default=0, ge=0)
    blocked_count: int = Field(default=0, ge=0)
    approval_required_count: int = Field(default=0, ge=0)
    sections: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class SourceRunsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_runs: list[SourceRunSummary] = Field(default_factory=list)


class LatestMorningBriefResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    morning_brief: MorningBriefSummary | None = None


class ProbateAutopilotHealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str
    environment: str
    status: str
    latest_brief_id: str | None = None
    generated_at: datetime | None = None
    brief_age_hours: float | None = None
    freshness_sla_hours: float | None = None
    freshness_ok: bool = True
    stale_brief: bool = False
    no_send_ok: bool = False
    outbound_allowed: bool = False
    source_run_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    new_record_count: int = Field(default=0, ge=0)
    sla_health: dict[str, Any] = Field(default_factory=dict)
    source_quality: dict[str, Any] = Field(default_factory=dict)
    enrichment_backlog: dict[str, Any] = Field(default_factory=dict)
    anomaly_count: int = Field(default=0, ge=0)
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    operator_next_actions: list[dict[str, Any]] = Field(default_factory=list)
