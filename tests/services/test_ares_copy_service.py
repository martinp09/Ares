from app.domains.ares import AresCounty, AresLeadRecord, AresSourceLane
from app.services.ares_copy_service import AresCopyService
from app.services.ares_service import AresLeadTier, RankedAresLead


def _ranked_lead() -> RankedAresLead:
    lead = AresLeadRecord(
        county=AresCounty.HARRIS,
        source_lane=AresSourceLane.PROBATE,
        property_address="123 Main St",
        owner_name="Estate of Jane Doe",
    )
    return RankedAresLead(
        lead=lead,
        tier=AresLeadTier.PROBATE_WITH_VERIFIED_TAX,
        rank=1,
        tax_delinquent=True,
    )


def test_generate_lead_briefs_returns_concise_brief_per_ranked_opportunity() -> None:
    service = AresCopyService()

    briefs = service.generate_lead_briefs([_ranked_lead()])

    assert len(briefs) == 1
    brief = briefs[0]
    assert brief.rank == 1
    assert brief.county == AresCounty.HARRIS
    assert brief.source_lane == AresSourceLane.PROBATE
    assert brief.rationale == "Probate lead with verified tax delinquency overlay."
    assert "123 Main St" in brief.brief
    assert "Rank #1" in brief.brief


def test_generate_outreach_drafts_keeps_human_review_gate_and_context() -> None:
    service = AresCopyService()

    drafts = service.generate_outreach_drafts([_ranked_lead()])

    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.rank == 1
    assert draft.county == AresCounty.HARRIS
    assert draft.source_lane == AresSourceLane.PROBATE
    assert draft.rationale == "Probate lead with verified tax delinquency overlay."
    assert draft.approval_status == "pending_human_approval"
    assert draft.auto_send is False
    assert "123 Main St" in draft.subject
    assert "Rank #1" in draft.body
