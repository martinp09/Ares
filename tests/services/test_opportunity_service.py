import pytest

from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.opportunities import OpportunitiesRepository
from app.models.opportunities import OpportunityStage
from app.services.opportunity_service import OpportunityService


def build_service() -> OpportunityService:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repository = OpportunitiesRepository(client)
    return OpportunityService(opportunities_repository=repository)


def test_create_from_lead_creates_qualified_opportunity() -> None:
    service = build_service()

    created = service.create_for_lead(
        business_id="limitless",
        environment="dev",
        lead_id="lead_1",
        source_lane="probate",
    )

    assert created.lead_id == "lead_1"
    assert created.stage == OpportunityStage.QUALIFIED_OPPORTUNITY


def test_advance_stage_rejects_backward_transition() -> None:
    service = build_service()
    created = service.create_for_lead(
        business_id="limitless",
        environment="dev",
        lead_id="lead_1",
        source_lane="probate",
    )
    moved = service.advance_stage(created.id or "", OpportunityStage.CONTRACT_SENT)

    with pytest.raises(ValueError):
        service.advance_stage(moved.id or "", OpportunityStage.QUALIFIED_OPPORTUNITY)
