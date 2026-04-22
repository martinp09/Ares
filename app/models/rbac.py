from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.models.permissions import ToolPermissionMode


class CanonicalOrgRoleName(StrEnum):
    PLATFORM_ADMIN = "platform_admin"
    ORG_ADMIN = "org_admin"
    AGENT_BUILDER = "agent_builder"
    OPERATOR = "operator"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"


CANONICAL_ORG_ROLE_NAMES: tuple[str, ...] = tuple(role.value for role in CanonicalOrgRoleName)
_CANONICAL_ORG_ROLE_INDEX = {name: index for index, name in enumerate(CANONICAL_ORG_ROLE_NAMES)}


def normalize_stored_org_role_name(name: str) -> str:
    return name.strip().lower()


def normalize_org_role_name(name: str) -> str:
    normalized = normalize_stored_org_role_name(name)
    if normalized not in _CANONICAL_ORG_ROLE_INDEX:
        raise ValueError(f"Unsupported role name: {name.strip() or name}")
    return normalized


def org_role_sort_key(name: str) -> tuple[int, str]:
    normalized = normalize_stored_org_role_name(name)
    return _CANONICAL_ORG_ROLE_INDEX.get(normalized, 10_000), normalized


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
