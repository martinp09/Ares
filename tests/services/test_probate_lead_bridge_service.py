from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.leads import LeadsRepository
from app.models.leads import LeadLifecycleStatus, LeadSource
from app.models.probate_leads import ProbateContactConfidence, ProbateHCADMatchStatus, ProbateLeadRecord
from app.services.probate_lead_bridge_service import ProbateLeadBridgeService


def test_upsert_keep_now_lead_builds_canonical_probate_record() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repository = LeadsRepository(client)
    service = ProbateLeadBridgeService(repository)
    probate_lead = ProbateLeadRecord(
        id="prob_12345",
        case_number="2026-12345",
        filing_type="PROBATE OF WILL (INDEPENDENT ADMINISTRATION)",
        estate_name="Estate of Jane Example",
        decedent_name="Jane Example",
        keep_now=True,
        hcad_match_status=ProbateHCADMatchStatus.MATCHED,
        contact_confidence=ProbateContactConfidence.HIGH,
        hcad_acct="123400001",
        mailing_address="123 Main St, Houston, TX 77002",
        property_address="456 Oak St, Houston, TX 77008",
        lead_score=96.0,
    )

    record = service.upsert_keep_now_lead(
        business_id="limitless",
        environment="dev",
        probate_lead=probate_lead,
    )

    assert record.source == LeadSource.PROBATE_INTAKE
    assert record.lifecycle_status == LeadLifecycleStatus.READY
    assert record.external_key == probate_lead.identity_key()
    assert record.probate_case_number == "2026-12345"
    assert record.score == 96.0
    assert record.raw_payload["probate_lead_id"] == probate_lead.id
    assert record.raw_payload["probate_lead"]["case_number"] == "2026-12345"


def test_upsert_keep_now_lead_reuses_existing_canonical_record() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repository = LeadsRepository(client)
    service = ProbateLeadBridgeService(repository)
    probate_lead = ProbateLeadRecord(
        case_number="2026-12345",
        filing_type="INDEPENDENT ADMINISTRATION",
        decedent_name="Jane Example",
        keep_now=True,
        lead_score=72.0,
    )

    first = service.upsert_keep_now_lead(business_id="limitless", environment="dev", probate_lead=probate_lead)
    second = service.upsert_keep_now_lead(
        business_id="limitless",
        environment="dev",
        probate_lead=probate_lead.model_copy(update={"lead_score": 80.0}),
    )

    assert first.id == second.id
    assert second.score == 80.0
