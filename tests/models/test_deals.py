from pydantic import ValidationError

from app.models.deals import (
    Deal,
    DealDocumentRequirement,
    DealDocumentRequirementStatus,
    DealParty,
    DealPartyRole,
    DealSourceLane,
    DealStage,
    DealStrategyLane,
)


def test_deal_keeps_source_strategy_and_stage_separate_with_no_send_defaults() -> None:
    deal = Deal(
        business_id="limitless",
        environment="dev",
        source_lane=DealSourceLane.HARRIS_PROBATE,
        strategy_lane=DealStrategyLane.CURATIVE_TITLE,
        stage=DealStage.QUALIFIED,
        source_record_id="lead_341",
        property_address="123 Main St",
    )

    assert deal.source_lane == DealSourceLane.HARRIS_PROBATE
    assert deal.strategy_lane == DealStrategyLane.CURATIVE_TITLE
    assert deal.stage == DealStage.QUALIFIED
    assert deal.no_send is True
    assert deal.provider_sends_enabled is False
    assert deal.provider_gate_snapshot["instantly_enrollment_enabled"] is False
    assert deal.provider_gate_snapshot["sms_sends_enabled"] is False
    assert deal.provider_gate_snapshot["hubspot_batch_writes_enabled"] is False


def test_deal_party_contact_candidate_is_not_verified_seller_by_default() -> None:
    party = DealParty(
        business_id="limitless",
        environment="dev",
        deal_id="deal_001",
        name="Jane Applicant",
        role=DealPartyRole.CONTACT_CANDIDATE,
        source_evidence=[{"source": "case_detail", "role": "applicant"}],
    )

    assert party.role == DealPartyRole.CONTACT_CANDIDATE
    assert party.is_confirmed_seller is False
    assert party.seller_authority_verified is False
    assert party.outbound_allowed is False
    assert party.skiptrace_status == "not_requested"


def test_deal_party_cannot_claim_authority_for_contact_candidate_without_verification() -> None:
    try:
        DealParty(
            business_id="limitless",
            environment="dev",
            deal_id="deal_001",
            name="Jane Applicant",
            role=DealPartyRole.CONTACT_CANDIDATE,
            is_confirmed_seller=True,
            seller_authority_verified=True,
        )
    except ValidationError as exc:
        assert "contact candidates cannot be confirmed sellers" in str(exc)
    else:  # pragma: no cover - defensive assertion for TDD red/green clarity
        raise AssertionError("contact candidate was allowed to become a verified seller")


def test_document_requirement_identity_key_is_deterministic() -> None:
    requirement = DealDocumentRequirement(
        business_id="limitless",
        environment="dev",
        deal_id="deal_001",
        document_type="affidavit_of_heirship",
        required_stage=DealStage.UNDER_CONTRACT,
        status=DealDocumentRequirementStatus.MISSING,
    )

    assert requirement.identity_key() == "deal_001:under_contract:affidavit_of_heirship"
