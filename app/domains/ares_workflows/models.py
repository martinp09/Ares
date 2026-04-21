from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domains.ares import AresCounty


class AresWorkflowStepStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AresWorkflowScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    counties: list[AresCounty] = Field(default_factory=list)
    market: str | None = None

    @model_validator(mode="after")
    def require_market_or_county_slice(self) -> "AresWorkflowScope":
        if not self.counties and not self.market:
            raise ValueError("workflow scope must include counties or market")
        return self


class AresWorkflowStepState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1)
    status: AresWorkflowStepStatus = AresWorkflowStepStatus.PENDING
    detail: str | None = None


class AresWorkflowHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class AresWorkflowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(min_length=1)
    scope: AresWorkflowScope
    steps: list[AresWorkflowStepState] = Field(min_length=1)
    next_best_action: str = Field(min_length=1)
    history: list[AresWorkflowHistoryEntry] = Field(default_factory=list)

    def record_history(self, entry: AresWorkflowHistoryEntry) -> None:
        self.history.append(entry)
