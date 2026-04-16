from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import generate_id
from app.models.runs import RunStatus
from app.models.turns import TurnStatus

MissionControlThreadStatus = Literal["open", "waiting", "closed"]
MissionControlMessageDirection = Literal["inbound", "outbound", "internal"]
MissionControlApprovalRisk = Literal["low", "medium", "high"]
MissionControlAssetStatus = Literal["connected", "attention", "unbound"]
MissionControlProviderName = Literal["textgrid", "resend"]
MissionControlProviderChannel = Literal["sms", "email"]
MissionControlOutboundSendStatus = Literal["queued", "sent", "failed"]


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
    booking_status: str | None = None
    sequence_status: str | None = None
    next_sequence_step: str | None = None
    manual_call_due_at: str | None = None
    recent_reply_preview: str | None = None
    reply_needs_review: bool = False
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class MissionControlDashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_count: int = Field(ge=0)
    active_run_count: int = Field(ge=0)
    failed_run_count: int = Field(ge=0)
    active_agent_count: int = Field(ge=0)
    unread_conversation_count: int = Field(ge=0)
    busy_channel_count: int = Field(ge=0)
    recent_completed_count: int = Field(ge=0)
    pending_lead_count: int = Field(ge=0)
    booked_lead_count: int = Field(ge=0)
    active_non_booker_enrollment_count: int = Field(ge=0)
    due_manual_call_count: int = Field(ge=0)
    replies_needing_review_count: int = Field(ge=0)
    system_status: str
    updated_at: datetime


class MissionControlProviderStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: MissionControlProviderName
    configured: bool
    can_send: bool
    sender_identity: str | None = None
    endpoint: str | None = None
    details: str | None = None
    checked_at: datetime


class MissionControlProvidersStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sms: MissionControlProviderStatus
    email: MissionControlProviderStatus


class MissionControlSmsTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: str = Field(min_length=1)
    body: str = Field(min_length=1)


class MissionControlEmailTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    text: str = Field(min_length=1)
    html: str | None = None


class MissionControlOutboundSendResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: MissionControlProviderChannel
    provider: MissionControlProviderName
    status: MissionControlOutboundSendStatus
    provider_message_id: str | None = None
    to: str
    from_identity: str | None = None
    attempted_at: datetime
    error_message: str | None = None


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
    booking_status: str | None = None
    sequence_status: str | None = None
    next_sequence_step: str | None = None
    manual_call_due_at: str | None = None
    recent_reply_preview: str | None = None
    reply_needs_review: bool = False


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
    booking_status: str | None = None
    sequence_status: str | None = None
    next_sequence_step: str | None = None
    manual_call_due_at: str | None = None
    recent_reply_preview: str | None = None
    reply_needs_review: bool = False
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


class MissionControlTurnSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    org_id: str
    business_id: str
    environment: str
    agent_id: str
    agent_revision_id: str
    turn_number: int = Field(ge=1)
    state: TurnStatus
    retry_count: int = Field(default=0, ge=0)
    resumed_from_turn_id: str | None = None
    updated_at: datetime


class MissionControlTurnsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turns: list[MissionControlTurnSummary] = Field(default_factory=list)


class MissionControlApprovalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    reason: str
    risk_level: MissionControlApprovalRisk
    status: str
    command_type: str
    requested_at: datetime
    payload_preview: str


class MissionControlApprovalsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approvals: list[MissionControlApprovalSummary] = Field(default_factory=list)


class MissionControlTaskSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    lead_name: str
    channel: str
    booking_status: str
    sequence_status: str
    next_sequence_step: str
    manual_call_due_at: str
    recent_reply_preview: str | None = None
    reply_needs_review: bool = False


class MissionControlTasksResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    due_count: int = Field(ge=0)
    tasks: list[MissionControlTaskSummary] = Field(default_factory=list)


class MissionControlAgentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    active_revision_id: str | None = None
    active_revision_state: str
    environment: str
    live_session_count: int = Field(ge=0)
    delegated_work_count: int = Field(ge=0)


class MissionControlAgentsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agents: list[MissionControlAgentSummary] = Field(default_factory=list)


class MissionControlAssetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    category: str
    status: MissionControlAssetStatus
    binding_target: str
    updated_at: datetime


class MissionControlAssetsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assets: list[MissionControlAssetSummary] = Field(default_factory=list)
