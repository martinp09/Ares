from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import utc_now


class ProviderLinkStatus(StrEnum):
    ACTIVE = "active"
    STALE = "stale"
    CONFLICT = "conflict"
    ARCHIVED = "archived"


class ProviderSyncDirection(StrEnum):
    ARES_TO_PROVIDER = "ares_to_provider"
    PROVIDER_TO_ARES = "provider_to_ares"
    BIDIRECTIONAL = "bidirectional"
    DRY_RUN = "dry_run"


class ProviderSyncRunStatus(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProviderObjectLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    provider_object_type: str = Field(min_length=1)
    provider_object_id: str = Field(min_length=1)
    ares_object_type: str = Field(min_length=1)
    ares_object_id: str = Field(min_length=1)
    link_status: ProviderLinkStatus = ProviderLinkStatus.ACTIVE
    sync_hash: str | None = None
    last_synced_at: datetime | None = None
    last_seen_at: datetime | None = None
    conflict_reason: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def provider_identity_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.business_id,
            self.environment,
            self.provider.casefold(),
            self.provider_object_type.casefold(),
            self.provider_object_id,
        )

    def ares_identity_key(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.business_id,
            self.environment,
            self.provider.casefold(),
            self.ares_object_type.casefold(),
            self.ares_object_id,
            self.provider_object_type.casefold(),
        )


class ProviderSyncCursor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    sync_name: str = Field(min_length=1)
    cursor_value: str | None = None
    cursor_payload: dict[str, Any] = Field(default_factory=dict)
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def identity_key(self) -> tuple[str, str, str, str]:
        return (self.business_id, self.environment, self.provider.casefold(), self.sync_name)


class ProviderSyncRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    sync_name: str = Field(min_length=1)
    direction: ProviderSyncDirection = ProviderSyncDirection.ARES_TO_PROVIDER
    status: ProviderSyncRunStatus = ProviderSyncRunStatus.QUEUED
    idempotency_key: str = Field(min_length=1)
    cursor_before: str | None = None
    cursor_after: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    scanned_count: int = Field(default=0, ge=0)
    created_count: int = Field(default=0, ge=0)
    updated_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
    conflict_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    command_id: str | None = None
    run_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def identity_key(self) -> tuple[str, str, str, str, str]:
        return (self.business_id, self.environment, self.provider.casefold(), self.sync_name, self.idempotency_key)
