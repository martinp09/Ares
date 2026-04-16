from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DEFAULT_INTERNAL_ORG_ID


class SecretCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    secret_value: str = Field(min_length=1)


class SecretRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    secret_value: str = Field(min_length=1, exclude=True)
    created_at: datetime
    updated_at: datetime


class SecretBindingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_revision_id: str = Field(min_length=1)
    binding_name: str = Field(min_length=1)


class SecretBindingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    secret_id: str = Field(min_length=1)
    agent_revision_id: str = Field(min_length=1)
    binding_name: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime


class SecretSummaryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    value_redacted: str = Field(default="[redacted]", min_length=1)
    binding_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class SecretListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secrets: list[SecretSummaryRecord] = Field(default_factory=list)


class SecretBindingListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bindings: list[SecretBindingRecord] = Field(default_factory=list)


class SecretCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secret: SecretSummaryRecord


class SecretBindingCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding: SecretBindingRecord
