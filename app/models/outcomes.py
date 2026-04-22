from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OutcomeStatus(StrEnum):
    SATISFIED = "satisfied"
    FAILED = "failed"


class ReleaseDecisionAction(StrEnum):
    PROMOTION = "promotion"
    ROLLBACK = "rollback"


class ReleaseDecisionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    action: ReleaseDecisionAction
    notes: str | None = None
    require_passing_evaluation: bool = False
    rollback_reason: str | None = None


class OutcomeEvaluationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome_name: str = Field(min_length=1)
    artifact_type: str = Field(min_length=1)
    artifact_payload: dict[str, Any] = Field(default_factory=dict)
    rubric_criteria: list[str] = Field(default_factory=list)
    evaluator_result: str = Field(min_length=1)
    passed: bool
    failure_details: list[str] = Field(default_factory=list)


class ReleaseDecisionEvaluationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome_id: str = Field(min_length=1)
    outcome_name: str = Field(min_length=1)
    status: OutcomeStatus
    satisfied: bool
    evaluator_result: str
    failure_details: list[str] = Field(default_factory=list)
    rubric_criteria: list[str] = Field(default_factory=list)
    require_passing_evaluation: bool = False
    blocked_promotion: bool = False
    rollback_reason: str | None = None


class OutcomeEvaluateRequest(OutcomeEvaluationPayload):
    run_id: str | None = None
    release_decision: ReleaseDecisionContext | None = None


class OutcomeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    outcome_name: str
    artifact_type: str
    artifact_payload: dict[str, Any] = Field(default_factory=dict)
    rubric_criteria: list[str] = Field(default_factory=list)
    evaluator_result: str
    status: OutcomeStatus
    satisfied: bool
    failure_details: list[str] = Field(default_factory=list)
    run_id: str | None = None
    release_decision: ReleaseDecisionContext | None = None
    created_at: datetime
