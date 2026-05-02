from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domains.ares import AresSourceLane
from app.models.copy_offers import CopyAssetStatus, CopySegment


class CopyAssetType(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    DIRECT_MAIL = "direct_mail"
    CALL_SCRIPT = "call_script"
    LANDING_PAGE = "landing_page"
    VOICEMAIL = "voicemail"


class CopyChannel(StrEnum):
    INSTANTLY = "instantly"
    TEXTGRID = "textgrid"
    DIRECT_MAIL = "direct_mail"
    MANUAL_CALL = "manual_call"
    WEB = "web"


class CopyFramework(StrEnum):
    HORMOZI_OFFER = "hormozi_offer"
    SULTANIC_PAIN_FIRST = "sultanic_pain_first"
    HYBRID = "hybrid"


class AwarenessLevel(StrEnum):
    UNAWARE = "unaware"
    PROBLEM_AWARE = "problem_aware"
    SOLUTION_AWARE = "solution_aware"
    PRODUCT_AWARE = "product_aware"
    MOST_AWARE = "most_aware"


class CopyAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    offer_id: str = Field(min_length=1)
    asset_type: CopyAssetType
    channel: CopyChannel
    source_lane: AresSourceLane
    segment: CopySegment
    framework: CopyFramework = CopyFramework.HYBRID
    awareness_level: AwarenessLevel = AwarenessLevel.PROBLEM_AWARE
    copy_hinge: str | None = None
    headline_or_subject: str | None = None
    body: str = Field(min_length=1)
    hook_variants: list[str] = Field(default_factory=list)
    critique_notes: list[str] = Field(default_factory=list)
    truth_risk_notes: list[str] = Field(min_length=1)
    template_variables: list[str] = Field(default_factory=list)
    status: CopyAssetStatus = CopyAssetStatus.REVIEW_REQUIRED
    auto_send: bool = False

    @model_validator(mode="after")
    def enforce_review_gate_and_truth_notes(self) -> "CopyAsset":
        if self.auto_send:
            raise ValueError("copy assets cannot auto-send")
        if not self.truth_risk_notes:
            raise ValueError("copy assets require truth/risk notes")
        return self
