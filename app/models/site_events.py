from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class SiteEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: int
    environment: str = Field(min_length=1)
    event_name: str = Field(min_length=1)
    visitor_id: str = Field(min_length=1)
    session_id: str | None = None
    occurred_at: datetime | None = None
    idempotency_key: str = Field(min_length=1)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("payload", "properties"),
    )
