import pytest

from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.opportunities import OpportunitiesRepository
from app.models.opportunities import OpportunityPipelineConfig, OpportunityPipelineStageConfig, OpportunityStage
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


def test_advance_stage_allows_forward_transition() -> None:
    service = build_service()
    created = service.create_for_contact(
        business_id="limitless",
        environment="dev",
        contact_id="contact_1",
        source_lane="lease_option_inbound",
    )

    moved = service.advance_stage(created.id or "", OpportunityStage.OFFER_PATH_SELECTED)

    assert moved.stage == OpportunityStage.OFFER_PATH_SELECTED


def test_summarize_by_lane_and_stage_keeps_lane_and_stage_separate() -> None:
    service = build_service()
    service.create_for_lead(
        business_id="limitless",
        environment="dev",
        lead_id="lead_1",
        source_lane="probate",
    )
    service.create_for_contact(
        business_id="limitless",
        environment="dev",
        contact_id="contact_1",
        source_lane="lease_option_inbound",
    )

    summary = service.summarize_by_lane_and_stage(business_id="limitless", environment="dev")

    assert [item.model_dump(mode="json") for item in summary] == [
        {"source_lane": "lease_option_inbound", "stage": "qualified_opportunity", "count": 1},
        {"source_lane": "probate", "stage": "qualified_opportunity", "count": 1},
    ]


def test_custom_pipeline_config_controls_stage_order_and_history() -> None:
    service = build_service()
    service.upsert_pipeline_config(
        OpportunityPipelineConfig(
            business_id="limitless",
            environment="dev",
            source_lane="probate",
            name="Probate custom pipeline",
            stages=[
                OpportunityPipelineStageConfig(stage=OpportunityStage.QUALIFIED_OPPORTUNITY, label="Qualified", order=0),
                OpportunityPipelineStageConfig(stage=OpportunityStage.TITLE_OPEN, label="Title Open", order=1),
                OpportunityPipelineStageConfig(stage=OpportunityStage.CLOSED, label="Closed", order=2, terminal=True),
            ],
        )
    )
    created = service.create_for_lead(
        business_id="limitless",
        environment="dev",
        lead_id="lead_2",
        source_lane="probate",
    )

    moved = service.advance_stage(
        created.id or "",
        OpportunityStage.TITLE_OPEN,
        actor_id="operator_1",
        actor_type="user",
        reason="title company opened file",
    )

    assert moved.stage == OpportunityStage.TITLE_OPEN
    history = service.list_stage_history(created.id or "")
    assert [event.model_dump(mode="json", exclude={"id", "created_at"}) for event in history] == [
        {
            "business_id": "limitless",
            "environment": "dev",
            "opportunity_id": created.id,
            "from_stage": "qualified_opportunity",
            "to_stage": "title_open",
            "actor_id": "operator_1",
            "actor_type": "user",
            "reason": "title company opened file",
            "metadata": {},
        }
    ]


def test_custom_pipeline_rejects_unconfigured_stage() -> None:
    service = build_service()
    service.upsert_pipeline_config(
        OpportunityPipelineConfig(
            business_id="limitless",
            environment="dev",
            source_lane="probate",
            name="Probate custom pipeline",
            stages=[
                OpportunityPipelineStageConfig(stage=OpportunityStage.QUALIFIED_OPPORTUNITY, label="Qualified", order=0),
                OpportunityPipelineStageConfig(stage=OpportunityStage.TITLE_OPEN, label="Title Open", order=1),
            ],
        )
    )
    created = service.create_for_lead(
        business_id="limitless",
        environment="dev",
        lead_id="lead_3",
        source_lane="probate",
    )

    with pytest.raises(KeyError):
        service.advance_stage(created.id or "", OpportunityStage.CONTRACT_SENT)
