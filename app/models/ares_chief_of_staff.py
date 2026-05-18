from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.commands import utc_now


class AresChiefOfStaffBucket(StrEnum):
    HOT = "hot"
    CONTACT_READY = "contact_ready"
    NEEDS_RESEARCH = "needs_research"
    NEEDS_SKIPTRACE = "needs_skiptrace"
    BLOCKED = "blocked"
    WATCHLIST = "watchlist"
    PASS = "pass"


class AresChiefOfStaffActionType(StrEnum):
    APPROVE_OUTREACH = "approve_outreach"
    APPROVE_SKIPTRACE = "approve_skiptrace"
    APPROVE_TITLE_RESEARCH = "approve_title_research"
    REVIEW_BLOCKERS = "review_blockers"


class AresChiefOfStaffActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    action_type: AresChiefOfStaffActionType
    title: str
    why: str
    queue: AresChiefOfStaffBucket
    lead_count: int
    risk_level: str = "approval_required"
    approval_required: bool = True
    slack_reply_command: str
    deny_reply_command: str
    safety_note: str


class AresChiefOfStaffLeadCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str
    display_name: str
    property_address: str | None = None
    county: str | None = None
    source: str
    primary_lane: str
    secondary_lanes: list[str] = Field(default_factory=list)
    score: float
    primary_bucket: AresChiefOfStaffBucket
    queue_tags: list[AresChiefOfStaffBucket] = Field(default_factory=list)
    contact_ready: bool = False
    has_phone: bool = False
    has_email: bool = False
    has_mailing_address: bool = False
    approval_required: bool = True
    reasons: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_action: str
    suggested_contact_angle: str | None = None
    risk_notes: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class AresChiefOfStaffBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = "ares_chief_of_staff_brief_v2"
    id: str
    business_id: str
    environment: str
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())
    employee_name: str = "Ares Chief of Staff"
    employee_role: str = "Real-estate lead desk operator"
    manager_name: str = "Martin"
    reporting_channel: str = "slack"
    shift_status: str = "online_read_only"
    input_lead_count: int = 0
    source_summary: dict[str, Any] = Field(default_factory=dict)
    operational_context: dict[str, Any] = Field(default_factory=dict)
    queue_counts: dict[str, int] = Field(default_factory=dict)
    queues: dict[str, list[AresChiefOfStaffLeadCard]] = Field(default_factory=dict)
    worklog: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    approval_requests: list[str] = Field(default_factory=list)
    manager_action_items: list[AresChiefOfStaffActionItem] = Field(default_factory=list)
    recommended_focus: list[str] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)
    artifact_path: str | None = None


class AresChiefOfStaffCheckInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=25)
    artifact_root: str | None = None
    write_artifacts: bool = True
    send_slack: bool = False
    idempotency_key: str | None = None
    no_send: bool = True
    provider_sends_enabled: bool = False
    live_source_calls: bool = False
    live_provider_writes: bool = False
    outreach_allowed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_read_only_employee_check_in(self) -> "AresChiefOfStaffCheckInRequest":
        if not self.no_send:
            raise ValueError("Chief of Staff check-in requires no_send=true")
        if self.provider_sends_enabled:
            raise ValueError("Chief of Staff check-in requires provider_sends_enabled=false")
        if self.live_source_calls:
            raise ValueError("Chief of Staff check-in cannot call live source systems")
        if self.live_provider_writes:
            raise ValueError("Chief of Staff check-in cannot write provider records")
        if self.outreach_allowed:
            raise ValueError("Chief of Staff check-in cannot allow seller outreach")
        return self


class AresChiefOfStaffCheckInResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed"] = "completed"
    kind: Literal["ares_chief_of_staff_check_in_v1"] = "ares_chief_of_staff_check_in_v1"
    brief_id: str
    business_id: str
    environment: str
    generated_at: str
    input_lead_count: int
    queue_counts: dict[str, int] = Field(default_factory=dict)
    manager_action_item_count: int
    artifacts: dict[str, str] = Field(default_factory=dict)
    slack_notification: dict[str, Any] = Field(default_factory=dict)
    no_send: bool = True
    provider_sends_enabled: bool = False
    outreach_allowed: bool = False
    live_source_calls_attempted: bool = False
    provider_writes_attempted: bool = False
    trigger_safe_summary: dict[str, Any] = Field(default_factory=dict)


class AresChiefOfStaffRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: AresChiefOfStaffBrief
    artifacts: dict[str, str] = Field(default_factory=dict)
    slack_notification: dict[str, Any] = Field(default_factory=lambda: {"status": "not_requested"})
