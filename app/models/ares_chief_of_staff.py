from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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


class AresChiefOfStaffRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: AresChiefOfStaffBrief
    artifacts: dict[str, str] = Field(default_factory=dict)
    slack_notification: dict[str, Any] = Field(default_factory=lambda: {"status": "not_requested"})
