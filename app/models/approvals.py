from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ApprovalStatus = Literal["pending", "approved", "rejected", "cancelled"]


class ApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: str = Field(min_length=1)
    approved_by: str | None = None
    approval_surface: str = Field(min_length=1)
    status: ApprovalStatus = "pending"
