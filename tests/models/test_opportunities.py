import pytest

from app.models.opportunities import OpportunityRecord


def test_opportunity_record_requires_exactly_one_identity_reference() -> None:
    with pytest.raises(ValueError):
        OpportunityRecord(
            business_id="limitless",
            environment="dev",
            source_lane="probate",
            lead_id="lead_1",
            contact_id="ctc_1",
        )

    with pytest.raises(ValueError):
        OpportunityRecord(
            business_id="limitless",
            environment="dev",
            source_lane="probate",
        )


def test_opportunity_record_accepts_lead_or_contact_identity() -> None:
    lead_record = OpportunityRecord(
        business_id="limitless",
        environment="dev",
        source_lane="probate",
        lead_id="lead_1",
    )
    contact_record = OpportunityRecord(
        business_id="limitless",
        environment="dev",
        source_lane="lease_option_inbound",
        contact_id="ctc_1",
    )

    assert lead_record.lead_id == "lead_1"
    assert lead_record.contact_id is None
    assert contact_record.contact_id == "ctc_1"
    assert contact_record.lead_id is None
