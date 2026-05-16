from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.deals import DealsRepository
from app.db.leads import LeadsRepository
from app.models.deals import (
    DealSourceLane,
    DealStage,
    DealStrategyLane,
    DealTaskType,
)
from app.models.leads import LeadRecord, LeadSource
from app.services.deal_promotion_service import DealPromotionService


def _service() -> tuple[DealPromotionService, DealsRepository, LeadsRepository]:
    store = InMemoryControlPlaneStore()
    client = InMemoryControlPlaneClient(store)
    deals = DealsRepository(client=client)
    leads = LeadsRepository(client=client)
    return DealPromotionService(deals_repository=deals, leads_repository=leads), deals, leads


def _seed_probate_lead(leads: LeadsRepository) -> LeadRecord:
    return leads.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.PROBATE_INTAKE,
            external_key="harris-probate-543678",
            first_name="Jane",
            last_name="Applicant",
            phone="7135550101",
            mailing_address="PO Box 1, Houston, TX",
            property_address="123 Main St, Houston, TX",
            probate_case_number="543678",
            raw_payload={
                "county": "harris",
                "case_detail_url": "https://www.cclerk.hctx.net/Applications/WebSearch/CaseDetail.aspx?Case=543678",
                "contact_candidates": [
                    {"name": "Jane Applicant", "role": "applicant", "source": "case_detail"},
                ],
            },
        )
    )


def test_promote_existing_probate_lead_creates_canonical_curative_deal_with_tasks_docs_and_audit() -> None:
    service, _deals, leads = _service()
    lead = _seed_probate_lead(leads)
    assert lead.id is not None

    detail = service.promote_lead_to_deal(
        lead.id,
        business_id="limitless",
        environment="dev",
        source_lane=DealSourceLane.HARRIS_PROBATE,
        strategy_lane=DealStrategyLane.CURATIVE_TITLE,
        actor_id="martin",
        actor_type="user",
        promotion_reason="keep-now probate lead with title friction",
    )

    assert detail.deal.source_record_id == lead.id
    assert detail.deal.source_lane == DealSourceLane.HARRIS_PROBATE
    assert detail.deal.strategy_lane == DealStrategyLane.CURATIVE_TITLE
    assert detail.deal.stage == DealStage.QUALIFIED
    assert detail.deal.no_send is True
    assert detail.deal.provider_sends_enabled is False
    assert {task.task_type for task in detail.tasks} >= {
        DealTaskType.VERIFY_AUTHORITY,
        DealTaskType.BUILD_HEIR_MAP,
        DealTaskType.PULL_DEED_CHAIN,
        DealTaskType.TAX_PAYOFF_CHECK,
    }
    assert {requirement.document_type for requirement in detail.document_requirements} >= {
        "letters_testamentary_or_administration",
        "affidavit_of_heirship",
        "deed_chain",
    }
    assert detail.parties[0].is_confirmed_seller is False
    assert detail.parties[0].seller_authority_verified is False
    assert detail.audit_events[0].event_type == "deal_promoted"
    assert detail.stage_events[0].to_stage == DealStage.QUALIFIED


def test_promotion_is_idempotent_for_same_source_record_and_does_not_duplicate_children() -> None:
    service, _deals, leads = _service()
    lead = _seed_probate_lead(leads)
    assert lead.id is not None

    first = service.promote_lead_to_deal(
        lead.id,
        business_id="limitless",
        environment="dev",
        source_lane=DealSourceLane.HARRIS_PROBATE,
        strategy_lane=DealStrategyLane.CURATIVE_TITLE,
    )
    second = service.promote_lead_to_deal(
        lead.id,
        business_id="limitless",
        environment="dev",
        source_lane=DealSourceLane.HARRIS_PROBATE,
        strategy_lane=DealStrategyLane.CURATIVE_TITLE,
    )

    assert first.deal.id == second.deal.id
    assert len(second.tasks) == len(first.tasks)
    assert len(second.document_requirements) == len(first.document_requirements)
    assert len(second.audit_events) == 1
    assert second.deal.provider_gate_snapshot["paid_skiptrace_enabled"] is False


def test_promote_lease_option_lead_generates_lease_option_checklist_without_probate_tasks() -> None:
    service, _deals, leads = _service()
    lead = leads.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.MANUAL,
            external_key="lease-option-inbound-1",
            first_name="Sam",
            last_name="Seller",
            phone="2145550101",
            property_address="500 Oak St, Tomball, TX",
            custom_variables={"seller_desired_price": "525000", "mortgage_balance": "410000"},
        )
    )
    assert lead.id is not None

    detail = service.promote_lead_to_deal(
        lead.id,
        business_id="limitless",
        environment="dev",
        source_lane=DealSourceLane.LEASE_OPTION_INBOUND,
        strategy_lane=DealStrategyLane.LEASE_OPTION,
    )

    assert detail.deal.strategy_lane == DealStrategyLane.LEASE_OPTION
    assert DealTaskType.BUILD_HEIR_MAP not in {task.task_type for task in detail.tasks}
    assert {task.task_type for task in detail.tasks} >= {
        DealTaskType.CONFIRM_MORTGAGE_BALANCE,
        DealTaskType.CONFIRM_PITI,
        DealTaskType.OFFER_REVIEW,
    }
    assert {requirement.document_type for requirement in detail.document_requirements} >= {
        "mortgage_statement",
        "lease_option_terms",
        "texas_lease_option_compliance_checklist",
    }
