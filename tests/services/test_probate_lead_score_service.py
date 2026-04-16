from app.models.probate_leads import ProbateContactConfidence, ProbateHCADMatchStatus, ProbateLeadRecord
from app.services.probate_lead_score_service import ProbateLeadScoreService, score_probate_lead


def test_independent_admin_with_hcad_match_scores_highest() -> None:
    lead = ProbateLeadRecord(
        case_number="2026-12345",
        filing_type="PROBATE OF WILL (INDEPENDENT ADMINISTRATION)",
        keep_now=True,
        hcad_match_status=ProbateHCADMatchStatus.MATCHED,
        contact_confidence=ProbateContactConfidence.HIGH,
        mailing_address="123 Main St, Houston, TX 77002",
        property_address="456 Oak St, Houston, TX 77008",
        matched_candidate_count=1,
        decedent_name="Jane Example",
    )

    assert score_probate_lead(lead) >= 90


def test_unmatched_lead_without_mailing_address_scores_lower() -> None:
    service = ProbateLeadScoreService()
    lead = ProbateLeadRecord(
        case_number="2026-12345",
        filing_type="INDEPENDENT ADMINISTRATION",
        keep_now=True,
        hcad_match_status=ProbateHCADMatchStatus.UNMATCHED,
        contact_confidence=ProbateContactConfidence.NONE,
    )

    assert service.score(lead) < 50


def test_score_lead_returns_updated_record() -> None:
    service = ProbateLeadScoreService()
    lead = ProbateLeadRecord(
        case_number="2026-12345",
        filing_type="APP TO DETERMINE HEIRSHIP",
        keep_now=True,
        hcad_match_status=ProbateHCADMatchStatus.MATCHED,
        contact_confidence=ProbateContactConfidence.MEDIUM,
        mailing_address="123 Main St, Houston, TX 77002",
        decedent_name="Jane Example",
    )

    scored = service.score_lead(lead)

    assert scored.lead_score is not None
    assert scored.lead_score == service.score(lead)
