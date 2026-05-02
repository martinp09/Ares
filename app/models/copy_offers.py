from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domains.ares import AresSourceLane


class CopySegment(StrEnum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    ALL = "all"


class CopyAssetStatus(StrEnum):
    DRAFT = "draft"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    RETIRED = "retired"


class OfferAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    source_lane: AresSourceLane
    segment: CopySegment = CopySegment.ALL
    audience: str = Field(min_length=1)
    pain_points: list[str] = Field(min_length=1)
    dream_outcome: str = Field(min_length=1)
    likelihood_boosters: list[str] = Field(min_length=1)
    time_delay_reducers: list[str] = Field(min_length=1)
    effort_reducers: list[str] = Field(min_length=1)
    risk_reversal: str | None = None
    unique_mechanism: str = Field(min_length=1)
    proof_points: list[str] = Field(default_factory=list)
    value_stack: list[str] = Field(min_length=1)
    offer_code_insights: list[str] = Field(default_factory=list)
    infusion_directives: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    truth_risk_notes: list[str] = Field(min_length=1)
    status: CopyAssetStatus = CopyAssetStatus.REVIEW_REQUIRED
    auto_send: bool = False

    @model_validator(mode="after")
    def enforce_review_gate(self) -> "OfferAsset":
        if self.auto_send:
            raise ValueError("offer assets cannot auto-send")
        if self.status == CopyAssetStatus.APPROVED and not self.truth_risk_notes:
            raise ValueError("approved offers require truth/risk notes")
        return self

    def hormozi_value_equation_summary(self) -> dict[str, object]:
        return {
            "dream_outcome": self.dream_outcome,
            "perceived_likelihood": list(self.likelihood_boosters),
            "time_delay": list(self.time_delay_reducers),
            "effort_and_sacrifice": list(self.effort_reducers),
        }
