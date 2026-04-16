from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.models.permissions import ToolPermissionMode


class OrgRoleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None


class OrgRoleRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class OrgRoleGrantCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: str | None = None
    tool_name: str = Field(min_length=1)
    mode: ToolPermissionMode


class OrgRoleGrantRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    role_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    mode: ToolPermissionMode
    created_at: datetime
    updated_at: datetime


class OrgRoleAssignmentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_revision_id: str = Field(min_length=1)
    role_id: str = Field(min_length=1)


class OrgRoleAssignmentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    agent_revision_id: str = Field(min_length=1)
    role_id: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime


class OrgPolicyUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    tool_name: str = Field(min_length=1)
    mode: ToolPermissionMode


class OrgPolicyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    tool_name: str = Field(min_length=1)
    mode: ToolPermissionMode
    created_at: datetime
    updated_at: datetime


class EffectivePermissionSourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    mode: ToolPermissionMode


class EffectivePermissionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_revision_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    mode: ToolPermissionMode
    source_modes: list[ToolPermissionMode] = Field(default_factory=list)
    sources: list[EffectivePermissionSourceRecord] = Field(default_factory=list)


class OrgRoleListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roles: list[OrgRoleRecord] = Field(default_factory=list)


class OrgRoleGrantListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grants: list[OrgRoleGrantRecord] = Field(default_factory=list)


class OrgRoleAssignmentListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignments: list[OrgRoleAssignmentRecord] = Field(default_factory=list)


class OrgPolicyListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policies: list[OrgPolicyRecord] = Field(default_factory=list)


class EffectivePermissionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1)
    mode: ToolPermissionMode
    source_modes: list[ToolPermissionMode] = Field(default_factory=list)
    sources: list[EffectivePermissionSourceRecord] = Field(default_factory=list)
