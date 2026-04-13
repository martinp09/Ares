from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import generate_id
from app.models.runs import RunStatus

MissionControlThreadStatus = Literal["open", "waiting", "closed"]
MissionControlMessageDirection = Literal["inbound", "outbound", "internal"]


class MissionControlContactRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("mc_contact"))
    display_name: str = Field(min_length=1)
    phone: str | None = None
    email: str | None = None


class MissionControlMessageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("mc_msg"))
    direction: MissionControlMessageDirection
    channel: str = Field(min_length=1)
    body: str = Field(min_length=1)
    created_at: datetime
    message_type: str = Field(default="message", min_length=1)
    approval_id: str | None = None
    run_id: str | None = None


class MissionControlThreadRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("mc_thread"))
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    status: MissionControlThreadStatus = "open"
    unread_count: int = Field(default=0, ge=0)
    contact: MissionControlContactRecord
    messages: list[MissionControlMessageRecord] = Field(default_factory=list)
    requires_approval: bool = False
    related_run_id: str | None = None
    related_approval_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class MissionControlDashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_count: int = Field(ge=0)
    active_run_count: int = Field(ge=0)
    failed_run_count: int = Field(ge=0)
    active_agent_count: int = Field(ge=0)


class MissionControlInboxSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_count: int = Field(ge=0)
    unread_count: int = Field(ge=0)
    approval_required_count: int = Field(ge=0)


class MissionControlThreadSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    channel: str
    status: MissionControlThreadStatus
    unread_count: int = Field(ge=0)
    last_message_preview: str | None = None
    last_message_at: datetime | None = None
    requires_approval: bool = False
    related_run_id: str | None = None
    related_approval_id: str | None = None
    contact: MissionControlContactRecord


class MissionControlThreadDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    channel: str
    status: MissionControlThreadStatus
    unread_count: int = Field(ge=0)
    requires_approval: bool = False
    related_run_id: str | None = None
    related_approval_id: str | None = None
    contact: MissionControlContactRecord
    messages: list[MissionControlMessageRecord] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class MissionControlInboxResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: MissionControlInboxSummary
    threads: list[MissionControlThreadSummary] = Field(default_factory=list)
    selected_thread_id: str | None = None
    selected_thread: MissionControlThreadDetail | None = None


class MissionControlRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    command_id: str
    business_id: str
    environment: str
    command_type: str
    status: RunStatus
    parent_run_id: str | None = None
    child_run_ids: list[str] = Field(default_factory=list)
    trigger_run_id: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_classification: str | None = None
    error_message: str | None = None


class MissionControlRunsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runs: list[MissionControlRunSummary] = Field(default_factory=list)
