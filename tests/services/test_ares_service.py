from app.domains.ares import AresCounty, AresLeadRecord, AresSourceLane
from app.services.ares_service import AresLeadTier, AresMatchingService


def _probate(address: str, county: AresCounty = AresCounty.HARRIS) -> AresLeadRecord:
    return AresLeadRecord(
        county=county,
        source_lane=AresSourceLane.PROBATE,
        property_address=address,
        owner_name="Estate of Jane Doe",
    )


def _tax(
    address: str,
    *,
    county: AresCounty = AresCounty.HARRIS,
    owner_name: str = "Estate of Jane Doe",
) -> AresLeadRecord:
    return AresLeadRecord(
        county=county,
        source_lane=AresSourceLane.TAX_DELINQUENT,
        property_address=address,
        owner_name=owner_name,
    )


def test_probate_is_primary_and_tax_is_overlay() -> None:
    service = AresMatchingService()
    probate = _probate("123 Main St")
    unrelated_tax = _tax("999 Other St")

    ranked = service.rank_leads(probate_records=[probate], tax_records=[unrelated_tax])

    assert len(ranked) == 1
    assert ranked[0].lead == probate
    assert ranked[0].tier == AresLeadTier.PROBATE_ONLY
    assert ranked[0].tax_delinquent is False


def test_probate_and_verified_tax_overlap_is_highest_rank() -> None:
    service = AresMatchingService()
    matched_probate = _probate("123 Main St")
    unmatched_probate = _probate("456 Oak St")
    matched_tax = _tax("123 Main St")

    ranked = service.rank_leads(
        probate_records=[unmatched_probate, matched_probate],
        tax_records=[matched_tax],
    )

    assert ranked[0].lead == matched_probate
    assert ranked[0].tier == AresLeadTier.PROBATE_WITH_VERIFIED_TAX
    assert ranked[0].tax_delinquent is True


def test_tax_only_is_restricted_to_estate_of_and_confirmed_delinquent() -> None:
    service = AresMatchingService()
    estate_tax_only = _tax("100 Estate Ln")
    non_estate_tax_only = _tax("200 Non Estate Ln", owner_name="John Doe").model_copy(update={"estate_of": False})

    ranked = service.rank_leads(
        probate_records=[],
        tax_records=[estate_tax_only, non_estate_tax_only],
    )

    assert len(ranked) == 1
    assert ranked[0].lead == estate_tax_only
    assert ranked[0].tier == AresLeadTier.TAX_ONLY_ESTATE_VERIFIED
    assert ranked[0].tax_delinquent is True


def test_county_is_part_of_overlay_match_key() -> None:
    service = AresMatchingService()
    probate = _probate("123 Main St", county=AresCounty.HARRIS)
    tax_other_county = _tax("123 Main St", county=AresCounty.DALLAS)

    ranked = service.rank_leads(probate_records=[probate], tax_records=[tax_other_county])

    assert ranked[0].tier == AresLeadTier.PROBATE_ONLY
    assert ranked[0].tax_delinquent is False


def test_tax_lane_does_not_auto_mark_non_estate_owner_as_estate() -> None:
    record = _tax("200 Non Estate Ln", owner_name="John Doe")

    assert record.estate_of is False


def test_tax_only_non_estate_record_is_excluded_without_manual_estate_flag() -> None:
    service = AresMatchingService()
    non_estate_tax_only = _tax("200 Non Estate Ln", owner_name="John Doe")

    ranked = service.rank_leads(
        probate_records=[],
        tax_records=[non_estate_tax_only],
    )

    assert ranked == []


def test_tax_only_estate_leads_are_scoped_per_county_when_probate_exists_elsewhere() -> None:
    service = AresMatchingService()
    harris_probate = _probate("123 Main St", county=AresCounty.HARRIS)
    dallas_estate_tax_only = _tax("500 Dallas Ave", county=AresCounty.DALLAS, owner_name="Estate of Dallas Owner")

    ranked = service.rank_leads(
        probate_records=[harris_probate],
        tax_records=[dallas_estate_tax_only],
    )

    assert len(ranked) == 2
    assert ranked[0].lead == harris_probate
    assert ranked[0].tier == AresLeadTier.PROBATE_ONLY
    assert ranked[1].lead == dallas_estate_tax_only
    assert ranked[1].tier == AresLeadTier.TAX_ONLY_ESTATE_VERIFIED
