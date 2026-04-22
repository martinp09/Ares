from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.models.actors import ActorType
from app.models.commands import utc_now


class OrganizationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(default=None, min_length=1)
    name: str = Field(min_length=1)
    slug: str | None = Field(default=None, min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)
    is_internal: bool = False


class OrganizationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    name: str = Field(min_length=1)
    slug: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    is_internal: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class OrganizationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organizations: list[OrganizationRecord] = Field(default_factory=list)


class MembershipCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    actor_id: str = Field(min_length=1)
    actor_type: ActorType = ActorType.USER
    member_id: str | None = Field(default=None, min_length=1)
    name: str | None = Field(default=None, min_length=1)
    role_name: str | None = Field(default=None, min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)


class MembershipRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    actor_id: str = Field(min_length=1)
    actor_type: ActorType = ActorType.USER
    member_id: str = Field(min_length=1)
    name: str | None = None
    role_name: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class MembershipListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memberships: list[MembershipRecord] = Field(default_factory=list)
