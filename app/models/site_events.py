from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SiteEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    event_name: str = Field(min_length=1)
    visitor_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    properties: dict[str, Any] = Field(default_factory=dict)
