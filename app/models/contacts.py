from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConsentState = Literal["unknown", "opted_in", "opted_out"]


class ContactRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    contact_key: str = Field(min_length=1)
    email: str | None = None
    phone: str | None = None
    consent_state: ConsentState = "unknown"
