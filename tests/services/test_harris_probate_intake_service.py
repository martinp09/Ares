from app.services.harris_probate_intake_service import HarrisProbateIntakeService


def test_keep_now_filter_accepts_only_target_types() -> None:
    service = HarrisProbateIntakeService()

    assert service.is_keep_now_case({"type": "PROBATE OF WILL (INDEPENDENT ADMINISTRATION)"}) is True
    assert service.is_keep_now_case({"type": "Dependent Administration"}) is False
    assert service.is_keep_now_case({"type": "Small Estate"}) is False


def test_normalize_case_collapses_fields_and_derives_decedent_name() -> None:
    service = HarrisProbateIntakeService()

    record = service.normalize_case(
        {
            "case_number": " 2026-12345 ",
            "file_date": "2026-04-16",
            "court": "  Court 4 ",
            "status": "  Open  ",
            "type": " app to determine heirship ",
            "estate_name": "Estate of   Jane Example, Deceased",
            "mail_to": " 123 Main St, Houston, TX 77002 ",
            "scraped_at": "2026-04-16T17:00:00Z",
        }
    )

    assert record.case_number == "2026-12345"
    assert str(record.file_date) == "2026-04-16"
    assert record.court_number == "Court 4"
    assert record.status == "Open"
    assert record.filing_type == "APP TO DETERMINE HEIRSHIP"
    assert record.decedent_name == "Jane Example"
    assert record.keep_now is True
    assert record.mailing_address == "123 Main St, Houston, TX 77002"
    assert record.last_seen_at is not None


def test_ingest_cases_keeps_only_keep_now_rows_by_default() -> None:
    service = HarrisProbateIntakeService()

    records = service.ingest_cases(
        [
            {"case_number": "1", "type": "Independent Administration"},
            {"case_number": "2", "type": "Guardianship"},
        ]
    )

    assert [record.case_number for record in records] == ["1"]
