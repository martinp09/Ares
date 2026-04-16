from app.models.probate_leads import ProbateContactConfidence, ProbateHCADMatchStatus, ProbateLeadRecord
from app.services.probate_hcad_match_service import ProbateHCADMatchService


def test_match_lead_fills_hcad_fields_from_single_best_candidate() -> None:
    service = ProbateHCADMatchService()
    lead = ProbateLeadRecord(
        case_number="2026-12345",
        filing_type="INDEPENDENT ADMINISTRATION",
        estate_name="Estate of John Example",
        decedent_name="John Example",
        keep_now=True,
    )

    matched = service.match_lead(
        lead,
        [
            {
                "acct": "0000123400001",
                "owner_name": "Example John",
                "mailing_address": "123 Main St, Houston, TX 77002",
                "property_address": "456 Oak St, Houston, TX 77008",
            }
        ],
    )

    assert matched.hcad_match_status == ProbateHCADMatchStatus.MATCHED
    assert matched.hcad_acct == "123400001"
    assert matched.owner_name == "Example John"
    assert matched.mailing_address == "123 Main St, Houston, TX 77002"
    assert matched.property_address == "456 Oak St, Houston, TX 77008"
    assert matched.contact_confidence == ProbateContactConfidence.MEDIUM


def test_match_lead_marks_multiple_when_best_candidates_tie() -> None:
    service = ProbateHCADMatchService()
    lead = ProbateLeadRecord(
        case_number="2026-12345",
        filing_type="APP TO DETERMINE HEIRSHIP",
        decedent_name="John Example",
        keep_now=True,
    )

    matched = service.match_lead(
        lead,
        [
            {"acct": "0001", "owner_name": "Example John", "property_address": "111 Oak St"},
            {"acct": "0002", "owner_name": "John Example", "property_address": "222 Oak St"},
        ],
    )

    assert matched.hcad_match_status == ProbateHCADMatchStatus.MULTIPLE
    assert matched.hcad_acct is None
    assert matched.matched_candidate_count == 2
    assert matched.contact_confidence == ProbateContactConfidence.LOW


def test_match_lead_leaves_unmatched_records_without_inventing_data() -> None:
    service = ProbateHCADMatchService()
    lead = ProbateLeadRecord(
        case_number="2026-99999",
        filing_type="INDEPENDENT ADMINISTRATION",
        decedent_name="Jane Example",
        keep_now=True,
        mailing_address="500 Pine St, Houston, TX 77003",
    )

    matched = service.match_lead(lead, [{"acct": "123", "owner_name": "Someone Else", "mailing_address": "1 Other St"}])

    assert matched.hcad_match_status == ProbateHCADMatchStatus.UNMATCHED
    assert matched.hcad_acct is None
    assert matched.property_address is None
    assert matched.mailing_address == "500 Pine St, Houston, TX 77003"
    assert matched.contact_confidence == ProbateContactConfidence.NONE
