from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/marketing", tags=["marketing"])


class MarketingStageRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    business_id: str | int | None = None
    environment: str | None = None
    command_id: str | None = None
    run_id: str | None = None
    campaignId: str = Field(min_length=1)
    market: str | None = None
    objective: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    marketResearch: Any | None = None
    campaignBrief: Any | None = None
    campaignAssets: Any | None = None


@router.post("/market-research/run")
def run_market_research(request: MarketingStageRequest) -> dict[str, Any]:
    return {
        "artifact_type": "market_research",
        "status": "ready",
        "campaign_id": request.campaignId,
        "market": request.market,
        "objective": request.objective,
        "context": request.context,
    }


@router.post("/campaign-brief/create")
def create_campaign_brief(request: MarketingStageRequest) -> dict[str, Any]:
    return {
        "artifact_type": "campaign_brief",
        "status": "ready",
        "campaign_id": request.campaignId,
        "market_research": request.marketResearch,
    }


@router.post("/campaign-assets/draft")
def draft_campaign_assets(request: MarketingStageRequest) -> dict[str, Any]:
    return {
        "artifact_type": "campaign_assets",
        "status": "draft",
        "campaign_id": request.campaignId,
        "campaign_brief": request.campaignBrief,
    }


@router.post("/launch-proposal/assemble")
def assemble_launch_proposal(request: MarketingStageRequest) -> dict[str, Any]:
    return {
        "artifact_type": "launch_proposal",
        "status": "approval_required",
        "campaign_id": request.campaignId,
        "campaign_assets": request.campaignAssets,
    }
