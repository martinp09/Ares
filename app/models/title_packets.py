from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import utc_now


class TitlePacketStatus(StrEnum):
    IMPORTED = "imported"
    NEEDS_REVIEW = "needs_review"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TitlePacketPriority(StrEnum):
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TitlePacketRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    external_key: str = Field(min_length=1)
    lead_id: str | None = None
    status: TitlePacketStatus = TitlePacketStatus.IMPORTED
    priority: TitlePacketPriority = TitlePacketPriority.NORMAL
    owner_name: str | None = None
    estate_name: str | None = None
    property_address: str | None = None
    mailing_address: str | None = None
    probate_case_number: str | None = None
    hctax_account: str | None = None
    packet_source: str | None = None
    operator_lane: str | None = None
    assigned_to: str | None = None
    artifact_refs: list[str] = Field(default_factory=list)
    review_notes: str | None = None
    facts: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def identity_key(self) -> str:
        return f"title-packet:{self.external_key.strip().casefold()}"
