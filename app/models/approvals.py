from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    command_id: str
    business_id: int
    environment: str
    command_type: str
    status: ApprovalStatus
    payload_snapshot: dict
    created_at: datetime
    approved_at: datetime | None = None
    actor_id: str | None = None


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: str


class ApprovalDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval: ApprovalRecord
    run_id: str | None = None
