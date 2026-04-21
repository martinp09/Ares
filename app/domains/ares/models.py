from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ESTATE_OF_PATTERN = re.compile(r"\bestate\s+of\b", re.IGNORECASE)


class AresCounty(StrEnum):
    HARRIS = "harris"
    TARRANT = "tarrant"
    MONTGOMERY = "montgomery"
    DALLAS = "dallas"
    TRAVIS = "travis"


class AresSourceLane(StrEnum):
    PROBATE = "probate"
    TAX_DELINQUENT = "tax_delinquent"


class AresPlannerActionType(StrEnum):
    READ_ONLY = "read_only"
    SIDE_EFFECTING = "side_effecting"


class AresExecutionDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class AresPlannerCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class AresPlannerStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    source_lane: AresSourceLane
    action_type: AresPlannerActionType = AresPlannerActionType.READ_ONLY
    requires_approval: bool = False

    @model_validator(mode="after")
    def enforce_approval_for_side_effects(self) -> "AresPlannerStep":
        if self.action_type == AresPlannerActionType.SIDE_EFFECTING and not self.requires_approval:
            raise ValueError("requires_approval must be true for side-effecting planner steps")
        return self


class AresPlannerPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1)
    counties: list[AresCounty] = Field(default_factory=list)
    source_lanes: list[AresSourceLane] = Field(min_length=1)
    checks: list[AresPlannerCheck] = Field(default_factory=list)
    steps: list[AresPlannerStep] = Field(min_length=1)
    rationale: str = Field(min_length=1)

    @field_validator("goal")
    @classmethod
    def normalize_goal(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("String should have at least 1 character")
        return normalized


class AresRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    counties: list[AresCounty] = Field(default_factory=list)
    include_briefs: bool = True
    include_drafts: bool = True


class AresExecutionRunSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    business_id: str | None = None
    environment: str | None = None
    market: str = Field(min_length=1)
    counties: list[AresCounty] = Field(min_length=1, max_length=2)
    action_budget: int = Field(ge=1, le=20)
    retry_limit: int = Field(ge=0, le=3)
    approved_tools: tuple[str, ...] = Field(min_length=1)


class AresExecutionActionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    raw_input: dict[str, object] = Field(default_factory=dict)
    requested_effects: tuple[str, ...] = Field(default_factory=tuple)
    attempt: int = Field(ge=0)
    hard_approval_id: str | None = None


class AresExecutionGuardrailResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: AresExecutionDecision
    reason: str


class AresLeadRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    county: AresCounty
    source_lane: AresSourceLane
    property_address: str = Field(min_length=1)
    owner_name: str | None = None
    estate_of: bool = False

    @model_validator(mode="after")
    def infer_estate_of(self) -> "AresLeadRecord":
        if self.estate_of:
            return self
        if self.owner_name and ESTATE_OF_PATTERN.search(self.owner_name):
            self.estate_of = True
        return self
