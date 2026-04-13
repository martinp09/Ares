from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PolicyResult = Literal["safe_autonomous", "approval_required", "forbidden"]


class CommandRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    command_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1)
    policy_result: PolicyResult
