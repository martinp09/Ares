from app.models.leads import LeadInterestStatus, LeadLifecycleStatus, LeadRecord, LeadSource


def test_lead_record_supports_probate_and_provider_fields() -> None:
    record = LeadRecord(
        business_id="limitless",
        environment="dev",
        source=LeadSource.PROBATE_INTAKE,
        lifecycle_status=LeadLifecycleStatus.READY,
        provider_name="instantly",
        provider_lead_id="lead_123",
        external_key="probate:case-1",
        email="Owner@Example.com",
        phone="+1 832 555 0111",
        first_name="Ava",
        last_name="Stone",
        company_name="Stone Holdings",
        custom_variables={"county": "Harris"},
        score=87.5,
        lt_interest_status=LeadInterestStatus.INTERESTED,
    )

    assert record.identity_key() == "external:probate:case-1"
    assert record.provider_lead_id == "lead_123"
    assert record.custom_variables == {"county": "Harris"}
    assert record.lt_interest_status == LeadInterestStatus.INTERESTED


def test_lead_record_falls_back_to_normalized_email_or_phone_identity() -> None:
    email_record = LeadRecord(
        business_id="limitless",
        environment="dev",
        email="Owner@Example.com",
    )
    phone_record = LeadRecord(
        business_id="limitless",
        environment="dev",
        phone="+1 832 555 0111",
    )

    assert email_record.identity_key() == "email:owner@example.com"
    assert phone_record.identity_key() == "phone:+18325550111"
