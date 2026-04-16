from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import DEFAULT_INTERNAL_ACTOR_ID, DEFAULT_INTERNAL_ACTOR_TYPE, DEFAULT_INTERNAL_ORG_ID


class ActorType(StrEnum):
    USER = "user"
    SERVICE = "service"
    SYSTEM = "system"


class ActorContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str = Field(default=DEFAULT_INTERNAL_ORG_ID, min_length=1)
    actor_id: str = Field(default=DEFAULT_INTERNAL_ACTOR_ID, min_length=1)
    actor_type: ActorType = DEFAULT_INTERNAL_ACTOR_TYPE
