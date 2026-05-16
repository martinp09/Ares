from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.commands import utc_now


def default_provider_gate_snapshot() -> dict[str, bool]:
    return {
        "instantly_enrollment_enabled": False,
        "email_sends_enabled": False,
        "sms_sends_enabled": False,
        "vapi_calls_enabled": False,
        "paid_skiptrace_enabled": False,
        "hubspot_batch_writes_enabled": False,
        "slack_provider_sends_enabled": False,
        "buyer_blasts_enabled": False,
        "esign_sends_enabled": False,
    }


class DealSourceLane(StrEnum):
    HARRIS_PROBATE = "harris_probate"
    MONTGOMERY_PROBATE = "montgomery_probate"
    PROBATE = "probate"
    LEASE_OPTION_INBOUND = "lease_option_inbound"
    MANUAL_IMPORT = "manual_import"
    REFERRAL = "referral"


class DealStrategyLane(StrEnum):
    WHOLESALE = "wholesale"
    WHOLETAIL = "wholetail"
    CURATIVE_TITLE = "curative_title"
    LEASE_OPTION = "lease_option"
    SUBJECT_TO = "subject_to"
    SELLER_FINANCE = "seller_finance"
    NOVATION = "novation"
    WRAP = "wrap"
    BUY_AND_HOLD = "buy_and_hold"
    PASS_NURTURE = "pass_nurture"
    UNKNOWN = "unknown"


class DealStage(StrEnum):
    QUALIFIED = "qualified"
    CONTACT_READY = "contact_ready"
    CONTACTED = "contacted"
    REPLIED = "replied"
    APPOINTMENT_SET = "appointment_set"
    APPOINTMENT_COMPLETED = "appointment_completed"
    OFFER_NEEDED = "offer_needed"
    OFFER_DRAFTED = "offer_drafted"
    OFFER_APPROVED = "offer_approved"
    OFFER_SENT = "offer_sent"
    VERBAL_YES = "verbal_yes"
    UNDER_CONTRACT = "under_contract"
    TITLE_OPENED = "title_opened"
    DISPO_READY = "dispo_ready"
    BUYER_SELECTED = "buyer_selected"
    CLEAR_TO_CLOSE = "clear_to_close"
    CLOSING_SCHEDULED = "closing_scheduled"
    FUNDED_CLOSED = "funded_closed"
    CLOSED = "closed"
    DEAD = "dead"
    NURTURE = "nurture"


class DealPartyRole(StrEnum):
    OWNER = "owner"
    DECEDENT = "decedent"
    APPLICANT = "applicant"
    EXECUTOR_CANDIDATE = "executor_candidate"
    HEIR_CANDIDATE = "heir_candidate"
    CONTACT_CANDIDATE = "contact_candidate"
    SELLER_VERIFIED = "seller_verified"
    TITLE_COMPANY = "title_company"
    ATTORNEY = "attorney"
    BUYER = "buyer"
    TENANT_BUYER = "tenant_buyer"
    UNKNOWN = "unknown"


class DealTaskStatus(StrEnum):
    OPEN = "open"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DealTaskType(StrEnum):
    VERIFY_AUTHORITY = "verify_authority"
    BUILD_HEIR_MAP = "build_heir_map"
    PULL_DEED_CHAIN = "pull_deed_chain"
    TAX_PAYOFF_CHECK = "tax_payoff_check"
    TITLE_COMPANY_CONSULT = "title_company_consult"
    ATTORNEY_CONSULT = "attorney_consult"
    MANUAL_CALL = "manual_call"
    OFFER_REVIEW = "offer_review"
    DOCUMENT_REVIEW = "document_review"
    PROVIDER_GATE_REVIEW = "provider_gate_review"
    CONFIRM_MORTGAGE_BALANCE = "confirm_mortgage_balance"
    CONFIRM_PITI = "confirm_piti"
    CONFIRM_OCCUPANCY = "confirm_occupancy"
    RUN_COMPS = "run_comps"


class DealDocumentRequirementStatus(StrEnum):
    MISSING = "missing"
    REQUESTED = "requested"
    RECEIVED = "received"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    WAIVED = "waived"


class DealRiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DealAuditEventType(StrEnum):
    DEAL_PROMOTED = "deal_promoted"
    STAGE_CHANGED = "stage_changed"
    TASK_CREATED = "task_created"
    DOCUMENT_REQUIREMENT_CREATED = "document_requirement_created"
    RISK_FLAG_CREATED = "risk_flag_created"
    PROVIDER_ACTION_BLOCKED = "provider_action_blocked"
    MANUAL_OVERRIDE = "manual_override"


class Deal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    source_lane: DealSourceLane
    strategy_lane: DealStrategyLane
    stage: DealStage = DealStage.QUALIFIED
    stage_status: str = "active"
    source_record_id: str | None = None
    source_lead_id: str | None = None
    crm_record_id: str | None = None
    probate_case_number: str | None = None
    property_address: str | None = None
    mailing_address: str | None = None
    county: str | None = None
    parcel_id: str | None = None
    primary_contact_id: str | None = None
    priority: str = "normal"
    deal_health: str = "needs_review"
    next_action: str | None = None
    blocking_reason: str | None = None
    expected_profit_low: float | None = None
    expected_profit_high: float | None = None
    expected_cashflow_monthly: float | None = None
    estimated_close_probability: float | None = None
    risk_level: DealRiskSeverity = DealRiskSeverity.MEDIUM
    deadline_next_at: datetime | None = None
    no_send: bool = True
    provider_sends_enabled: bool = False
    provider_gate_snapshot: dict[str, bool] = Field(default_factory=default_provider_gate_snapshot)
    source_evidence: list[dict[str, Any]] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_human_reviewed_at: datetime | None = None

    def identity_key(self) -> str:
        if self.source_record_id:
            return f"source:{self.source_lane.value}:{self.source_record_id}"
        if self.source_lead_id:
            return f"lead:{self.source_lane.value}:{self.source_lead_id}"
        if self.crm_record_id:
            return f"crm:{self.source_lane.value}:{self.crm_record_id}"
        if self.probate_case_number:
            return f"case:{self.source_lane.value}:{self.probate_case_number}"
        raise ValueError("Deal requires source_record_id, source_lead_id, crm_record_id, or probate_case_number")


class DealParty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    deal_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    role: DealPartyRole = DealPartyRole.UNKNOWN
    role_confidence: str = "low"
    authority_status: str = "unknown"
    authority_evidence: list[dict[str, Any]] = Field(default_factory=list)
    contact_status: str = "candidate"
    phone: str | None = None
    email: str | None = None
    mailing_address: str | None = None
    is_confirmed_seller: bool = False
    seller_authority_verified: bool = False
    skiptrace_status: str = "not_requested"
    outbound_allowed: bool = False
    source_evidence: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _contact_candidates_are_not_verified_sellers(self) -> DealParty:
        if self.role == DealPartyRole.CONTACT_CANDIDATE and (self.is_confirmed_seller or self.seller_authority_verified):
            raise ValueError("contact candidates cannot be confirmed sellers or verified seller-authority holders")
        return self

    def identity_key(self) -> str:
        return f"{self.deal_id}:{self.role.value}:{self.name.strip().casefold()}"


class DealTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    deal_id: str = Field(min_length=1)
    task_type: DealTaskType
    title: str = Field(min_length=1)
    description: str | None = None
    assignee_role: str = "operator"
    due_at: datetime | None = None
    sla_policy: str | None = None
    priority: str = "normal"
    status: DealTaskStatus = DealTaskStatus.OPEN
    blocking: bool = True
    depends_on: list[str] = Field(default_factory=list)
    proof_required: bool = False
    completion_evidence: dict[str, Any] = Field(default_factory=dict)
    created_from: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def identity_key(self) -> str:
        return f"{self.deal_id}:{self.task_type.value}:{self.title.strip().casefold()}"


class DealDocumentRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    deal_id: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    required_stage: DealStage
    status: DealDocumentRequirementStatus = DealDocumentRequirementStatus.MISSING
    blocker_severity: DealRiskSeverity = DealRiskSeverity.MEDIUM
    due_at: datetime | None = None
    satisfied_by_document_id: str | None = None
    review_required: bool = True
    approval_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def identity_key(self) -> str:
        return f"{self.deal_id}:{self.required_stage.value}:{self.document_type}"


class DealAuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    deal_id: str = Field(min_length=1)
    event_type: DealAuditEventType
    actor_id: str | None = None
    actor_type: str | None = None
    before_state: dict[str, Any] = Field(default_factory=dict)
    after_state: dict[str, Any] = Field(default_factory=dict)
    command_id: str | None = None
    approval_id: str | None = None
    provider_gate_snapshot: dict[str, Any] = Field(default_factory=dict)
    evidence_links: list[str] = Field(default_factory=list)
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class DealStageEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    deal_id: str = Field(min_length=1)
    from_stage: DealStage | None = None
    to_stage: DealStage
    actor_id: str | None = None
    actor_type: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class DealRiskFlag(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    deal_id: str = Field(min_length=1)
    code: str = Field(min_length=1)
    label: str = Field(min_length=1)
    severity: DealRiskSeverity = DealRiskSeverity.MEDIUM
    active: bool = True
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def identity_key(self) -> str:
        return f"{self.deal_id}:{self.code}"


class DealDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deal: Deal
    parties: list[DealParty] = Field(default_factory=list)
    tasks: list[DealTask] = Field(default_factory=list)
    document_requirements: list[DealDocumentRequirement] = Field(default_factory=list)
    risk_flags: list[DealRiskFlag] = Field(default_factory=list)
    stage_events: list[DealStageEvent] = Field(default_factory=list)
    audit_events: list[DealAuditEvent] = Field(default_factory=list)


class DealFireListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deal_id: str
    item_type: str = Field(min_length=1)
    severity: DealRiskSeverity = DealRiskSeverity.MEDIUM
    reason: str = Field(min_length=1)
    recommended_action: str = Field(min_length=1)
    due_at: datetime | None = None
    source_id: str | None = None
    action_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class DealPromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    lead_id: str = Field(min_length=1)
    source_lane: DealSourceLane
    strategy_lane: DealStrategyLane
    promotion_reason: str | None = None
    operator_notes: str | None = None
    no_send: bool = True


class DealStageTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_stage: DealStage
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    manual_override: bool = False


class DealListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deals: list[Deal]


class DealFireListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[DealFireListItem]
