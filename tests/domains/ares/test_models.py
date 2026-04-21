from app.domains.ares import AresCounty, AresLeadRecord, AresRunRequest, AresSourceLane


def test_counties_cover_the_five_target_markets() -> None:
    assert [county.value for county in AresCounty] == [
        "harris",
        "tarrant",
        "montgomery",
        "dallas",
        "travis",
    ]


def test_run_request_coerces_counties_and_defaults_to_briefs_and_drafts() -> None:
    request = AresRunRequest(counties=["harris", "travis"])

    assert request.counties == [AresCounty.HARRIS, AresCounty.TRAVIS]
    assert request.include_briefs is True
    assert request.include_drafts is True


def test_estate_of_detection_requires_explicit_estate_evidence() -> None:
    owner_name_estate_lead = AresLeadRecord(
        county=AresCounty.HARRIS,
        source_lane=AresSourceLane.PROBATE,
        property_address="123 Main St, Houston, TX",
        owner_name="Estate of Jane Doe",
    )
    tax_only_non_estate_lead = AresLeadRecord(
        county=AresCounty.DALLAS,
        source_lane=AresSourceLane.TAX_DELINQUENT,
        property_address="200 Elm St, Dallas, TX",
        owner_name="John Doe",
    )

    assert owner_name_estate_lead.estate_of is True
    assert tax_only_non_estate_lead.estate_of is False
