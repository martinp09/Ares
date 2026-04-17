from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.commands import utc_now


class OpportunitySourceLane(StrEnum):
    PROBATE = "probate"
    LEASE_OPTION_INBOUND = "lease_option_inbound"


class OpportunityStage(StrEnum):
    QUALIFIED_OPPORTUNITY = "qualified_opportunity"
    OFFER_PATH_SELECTED = "offer_path_selected"
    UNDER_NEGOTIATION = "under_negotiation"
    CONTRACT_SENT = "contract_sent"
    CONTRACT_SIGNED = "contract_signed"
    TITLE_OPEN = "title_open"
    CURATIVE_REVIEW = "curative_review"
    DISPO_READY = "dispo_ready"
    CLOSED = "closed"
    DEAD = "dead"


class OpportunityTitleStatus(StrEnum):
    NOT_OPEN = "not_open"
    OPEN = "open"
    CURATIVE_REVIEW = "curative_review"
    CLEARED = "cleared"
    BLOCKED = "blocked"


class OpportunityTCStatus(StrEnum):
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    WAITING = "waiting"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class OpportunityDispoStatus(StrEnum):
    NOT_READY = "not_ready"
    READY = "ready"
    MARKETING = "marketing"
    ASSIGNED = "assigned"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class OpportunityRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    source_lane: OpportunitySourceLane
    strategy_lane: str | None = None
    stage: OpportunityStage = OpportunityStage.QUALIFIED_OPPORTUNITY
    lead_id: str | None = None
    contact_id: str | None = None
    title_status: OpportunityTitleStatus = OpportunityTitleStatus.NOT_OPEN
    tc_status: OpportunityTCStatus = OpportunityTCStatus.NOT_STARTED
    dispo_status: OpportunityDispoStatus = OpportunityDispoStatus.NOT_READY
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate_identity(self) -> OpportunityRecord:
        if (self.lead_id is None) == (self.contact_id is None):
            raise ValueError("OpportunityRecord requires exactly one of lead_id or contact_id")
        return self

    def identity_key(self) -> str:
        if self.lead_id:
            return f"lead:{self.lead_id}"
        return f"contact:{self.contact_id}"


class OpportunityLaneStageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_lane: OpportunitySourceLane
    stage: OpportunityStage
    count: int = Field(ge=0)
