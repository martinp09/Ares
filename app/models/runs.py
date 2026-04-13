from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RunStatus = Literal["queued", "in_progress", "succeeded", "failed", "cancelled"]


class RunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: str = Field(min_length=1)
    trigger_run_id: str | None = None
    status: RunStatus = "queued"
    parent_run_id: str | None = None
