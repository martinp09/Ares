from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import utc_now


class CrmRecordType(StrEnum):
    PROPERTY = "property_record"
    OWNER = "owner_record"
    CONTACT = "contact_record"
    PROBATE_CASE = "probate_case_record"
    TAX_DELINQUENCY = "tax_delinquency_record"


class CrmRecordStatus(StrEnum):
    NEW = "new"
    INCOMPLETE = "incomplete"
    CLEAN = "clean"
    NEEDS_SKIP_TRACE = "needs_skip_trace"
    MARKETABLE = "marketable"
    SUPPRESSED = "suppressed"
    PROMOTED = "promoted"
    ARCHIVED = "archived"


class CrmSourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    source_key: str = Field(min_length=1)
    source_type: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    extracted_at: datetime | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def identity_key(self) -> str:
        return f"source:{self.source_system.strip().casefold()}:{self.source_key.strip().casefold()}"


class CrmRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    record_type: CrmRecordType
    status: CrmRecordStatus = CrmRecordStatus.NEW
    identity_key: str | None = None
    display_name: str = Field(min_length=1)
    owner_name: str | None = None
    property_address: str | None = None
    mailing_address: str | None = None
    phone: str | None = None
    email: str | None = None
    assigned_to: str | None = None
    tags: list[str] = Field(default_factory=list)
    data_quality_score: int = Field(default=0, ge=0, le=100)
    source_record_ids: list[str] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_activity_at: datetime | None = None

    def resolved_identity_key(self) -> str:
        if self.identity_key:
            return self.identity_key
        anchors = [
            self.record_type.value,
            self.owner_name,
            self.property_address,
            self.mailing_address,
            self.email,
            self.phone,
            self.display_name,
        ]
        normalized = ":".join(str(value).strip().casefold() for value in anchors if value)
        if not normalized:
            raise ValueError("CrmRecord requires a deterministic identity anchor")
        return f"record:{normalized}"


class CrmRecordSourceMembership(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    record_id: str = Field(min_length=1)
    source_record_id: str | None = None
    source_system: str = Field(min_length=1)
    source_key: str = Field(min_length=1)
    list_name: str | None = None
    campaign_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    def identity_key(self) -> str:
        return ":".join(
            [
                "membership",
                self.record_id.strip().casefold(),
                self.source_system.strip().casefold(),
                self.source_key.strip().casefold(),
            ]
        )


class CrmRecordStatusHistory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    record_id: str = Field(min_length=1)
    from_status: CrmRecordStatus | None = None
    to_status: CrmRecordStatus
    actor_id: str | None = None
    actor_type: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class CrmRecordPromotion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    record_id: str = Field(min_length=1)
    opportunity_id: str = Field(min_length=1)
    actor_id: str | None = None
    actor_type: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class CrmRecordSavedView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    name: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    filters: dict[str, Any] = Field(default_factory=dict)
    sort: str = Field(default="last_activity_desc", min_length=1)
    is_default: bool = False
    created_by: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def identity_key(self) -> str:
        return f"saved_view:{self.slug.strip().casefold()}"
