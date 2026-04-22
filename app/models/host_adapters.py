from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.skills import SkillRecord


class HostAdapterKind(StrEnum):
    TRIGGER_DEV = "trigger_dev"
    CODEX = "codex"
    ANTHROPIC = "anthropic"


class HostAdapterDispatchStatus(StrEnum):
    ACCEPTED = "accepted"
    DISABLED = "disabled"


class HostAdapterCapabilityRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dispatch: bool = False
    status_correlation: bool = False
    artifact_reporting: bool = False
    cancellation: bool = False


class HostAdapterCorrelationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dispatch_id: str | None = None
    run_id: str | None = None
    session_id: str | None = None
    external_reference: str | None = None
    adapter_reference: str | None = None
    adapter_details: dict[str, Any] = Field(default_factory=dict)


class HostAdapterArtifactRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str = Field(min_length=1)
    uri: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    adapter_artifact_id: str | None = None
    adapter_details: dict[str, Any] = Field(default_factory=dict)


class HostAdapterRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: HostAdapterKind
    enabled: bool
    display_name: str
    description: str | None = None
    adapter_details_label: str = "Adapter details"
    capabilities: HostAdapterCapabilityRecord = Field(default_factory=HostAdapterCapabilityRecord)
    disabled_reason: str | None = None


class HostAdapterDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)
    agent_revision_id: str = Field(min_length=1)
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    host_adapter_config: dict[str, Any] = Field(default_factory=dict)
    skills: list[SkillRecord] = Field(default_factory=list)
    run_id: str | None = None
    session_id: str | None = None


class HostAdapterDispatchRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    adapter_kind: HostAdapterKind
    agent_id: str
    agent_revision_id: str
    business_id: str
    environment: str
    skill_ids: list[str] = Field(default_factory=list)
    host_adapter_config: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    status: HostAdapterDispatchStatus
    run_id: str | None = None
    session_id: str | None = None
    external_reference: str | None = None
    created_at: datetime
    updated_at: datetime


class HostAdapterDispatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_kind: HostAdapterKind
    enabled: bool
    status: HostAdapterDispatchStatus
    dispatch_id: str | None = None
    external_reference: str | None = None
    correlation: HostAdapterCorrelationRecord | None = None
    adapter_details: dict[str, Any] = Field(default_factory=dict)
    disabled_reason: str | None = None
    message: str | None = None


class HostAdapterStatusCorrelationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dispatch_id: str | None = None
    run_id: str | None = None
    session_id: str | None = None
    external_reference: str | None = None
    adapter_reference: str | None = None
    adapter_details: dict[str, Any] = Field(default_factory=dict)


class HostAdapterStatusCorrelationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_kind: HostAdapterKind
    enabled: bool
    supported: bool
    correlation: HostAdapterCorrelationRecord | None = None
    disabled_reason: str | None = None
    message: str | None = None


class HostAdapterArtifactReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation: HostAdapterCorrelationRecord
    artifact: HostAdapterArtifactRecord


class HostAdapterArtifactReportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_kind: HostAdapterKind
    enabled: bool
    supported: bool
    accepted: bool
    correlation: HostAdapterCorrelationRecord | None = None
    artifact: HostAdapterArtifactRecord | None = None
    disabled_reason: str | None = None
    message: str | None = None


class HostAdapterCancellationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation: HostAdapterCorrelationRecord
    reason: str | None = None


class HostAdapterCancellationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_kind: HostAdapterKind
    enabled: bool
    supported: bool
    cancelled: bool
    correlation: HostAdapterCorrelationRecord | None = None
    disabled_reason: str | None = None
    message: str | None = None
