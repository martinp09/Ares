from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConversationStatus = Literal["open", "waiting", "closed"]


class ConversationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    contact_id: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    provider_thread_id: str = Field(min_length=1)
    status: ConversationStatus = "open"
