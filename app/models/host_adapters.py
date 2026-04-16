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


class HostAdapterRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: HostAdapterKind
    enabled: bool
    description: str | None = None


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
    message: str | None = None
