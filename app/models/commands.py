from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class CommandPolicy(StrEnum):
    SAFE_AUTONOMOUS = "safe_autonomous"
    APPROVAL_REQUIRED = "approval_required"
    FORBIDDEN = "forbidden"


class CommandStatus(StrEnum):
    ACCEPTED = "accepted"
    AWAITING_APPROVAL = "awaiting_approval"
    QUEUED = "queued"
    REJECTED = "rejected"


class CommandCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: int
    environment: str = Field(min_length=1)
    command_type: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class CommandRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("cmd"))
    business_id: int
    environment: str = Field(min_length=1)
    command_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1)
    policy: CommandPolicy
    status: CommandStatus
    approval_id: str | None = None
    run_id: str | None = None
    deduped: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class CommandIngestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    business_id: int
    environment: str
    command_type: str
    idempotency_key: str
    payload: dict[str, Any] = Field(default_factory=dict)
    policy: CommandPolicy
    status: CommandStatus
    approval_id: str | None = None
    run_id: str | None = None
    deduped: bool
    created_at: datetime
