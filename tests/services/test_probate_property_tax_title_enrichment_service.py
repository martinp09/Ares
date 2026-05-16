from app.core.config import Settings
from app.domains.ares.models import AresCounty
from app.models.probate_leads import ProbateLeadRecord
from app.services import probate_live_enrichment_clients
from app.services.probate_live_enrichment_clients import MontgomeryPublicSearchLandRecordClient
from app.services.probate_property_tax_title_enrichment_service import ProbatePropertyTaxTitleEnrichmentService
from app.services.tax_overlay_service import TaxOverlayResult, TaxOverlayStatus


def test_property_tax_title_enrichment_runs_from_local_artifacts_without_live_calls() -> None:
    service = ProbatePropertyTaxTitleEnrichmentService()
    result = service.run_enrichment(
        business_id="limitless",
        environment="test",
        keep_now_rows=[
            {
                "case_number": "2026-10001",
                "filing_type": "APP TO DETERMINE HEIRSHIP",
                "estate_name": "Estate of Jane Example",
                "decedent_name": "Jane Example",
                "keep_now": True,
            }
        ],
        hcad_candidates_by_case={
            "2026-10001": [
                {
                    "acct": "000123400001",
                    "owner_name": "Example Jane",
                    "mailing_address": "123 MAIN ST, HOUSTON, TX 77002",
                    "property_address": "456 OAK ST, HOUSTON, TX 77008",
                }
            ]
        },
        tax_overlays_by_account={
            "123400001": TaxOverlayResult(
                county=AresCounty.HARRIS,
                account="123400001",
                owner_name="EXAMPLE JANE",
                property_address="456 OAK ST",
                status=TaxOverlayStatus.VERIFIED_DELINQUENT,
                is_delinquent=True,
                amount_owed=5250.75,
                prior_years_owed=4000.25,
                current_year_owed=1250.50,
                estimated_years_delinquent=3,
                tax_value=220000,
                taxes_under_suit=True,
                search_method="local_harris_tax_statement_snapshot",
                confidence="high",
            )
        },
        land_record_rows_by_case={
            "2026-10001": [
                {
                    "instrument_number": "RP-2026-1",
                    "instrument_type": "Affidavit of Heirship",
                    "grantor": "Example Jane",
                    "grantee": "Example Family",
                },
                {"instrument_number": "RP-2025-2", "instrument_type": "Tax Lien", "grantor": "Harris County"},
            ]
        },
    )

    assert result["no_send"] is True
    assert result["provider_sends_enabled"] is False
    assert result["outbound_allowed"] is False
    assert result["live_cad_calls_attempted"] is False
    assert result["live_tax_calls_attempted"] is False
    assert result["live_land_record_calls_attempted"] is False
    assert result["enriched_count"] == 1
    assert result["property_match_completed_count"] == 1
    assert result["tax_overlay_completed_count"] == 1
    assert result["title_friction_completed_count"] == 1
    assert result["title_friction_review_count"] == 1
    assert result["hubspot_mirror_blocked_until_approval_count"] == 1
    assert result["outbound_blocked_until_explicit_approval_count"] == 1

    record = result["records"][0]
    assert record["hcad_match_status"] == "matched"
    assert record["hcad_acct"] == "123400001"
    assert record["tax_delinquent"] is True
    assert record["estate_of"] is True
    assert record["lead_score"] is not None
    assert record["pain_stack"]["tax_overlay"]["status"] == "tax_overlay_verified_delinquent"
    assert record["pain_stack"]["tax_overlay"]["live_calls_attempted"] is False
    assert record["pain_stack"]["title_friction"]["friction_flags"]["affidavit_of_heirship"] is True
    assert record["pain_stack"]["title_friction"]["friction_flags"]["lien_or_tax_suit"] is True
    assert record["pain_stack"]["title_friction"]["next_action"] == "needs_document_image_review"


def test_property_tax_title_enrichment_rejects_live_execution_flags_before_work() -> None:
    service = ProbatePropertyTaxTitleEnrichmentService()

    try:
        service.run_enrichment(
            business_id="limitless",
            environment="test",
            keep_now_rows=[],
            live_tax_calls=True,
        )
    except RuntimeError as exc:
        assert "enrichment_approval.approved=true" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected live execution rejection")


def test_property_tax_title_enrichment_rejects_live_execution_without_explicit_no_send_approval() -> None:
    service = ProbatePropertyTaxTitleEnrichmentService(
        settings=Settings(_env_file=None, lead_machine_live_tax_calls_enabled=True),
        tax_client=FakeTaxClient(),
    )

    try:
        service.run_enrichment(
            business_id="limitless",
            environment="test",
            keep_now_rows=[],
            live_tax_calls=True,
            enrichment_approval={"approved": True, "approved_by": "operator"},
        )
    except RuntimeError as exc:
        assert "enrichment_approval.no_send=true" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected no-send live approval rejection")


def test_property_tax_title_enrichment_keeps_unmatched_and_unchecked_as_blocked_review_state() -> None:
    service = ProbatePropertyTaxTitleEnrichmentService()
    result = service.run_enrichment(
        business_id="limitless",
        environment="test",
        keep_now_rows=[
            {
                "case_number": "2026-10002",
                "filing_type": "INDEPENDENT ADMINISTRATION",
                "estate_name": "Estate of No Match",
                "keep_now": True,
            }
        ],
    )

    record = result["records"][0]
    assert result["property_match_unmatched_count"] == 1
    assert result["tax_overlay_completed_count"] == 0
    assert result["title_friction_review_count"] == 1
    assert record["tax_delinquent"] is False
    assert record["pain_stack"]["tax_overlay"]["status"] == "tax_overlay_not_checked"
    assert record["pain_stack"]["title_friction"]["status"] == "not_checked"
    assert result["hubspot_mirror_blocked_until_approval_count"] == 1
    assert result["outbound_blocked_until_explicit_approval_count"] == 1


class FakeCadClient:
    def __init__(self) -> None:
        self.calls = []

    def fetch_candidates(self, *, record, source_row):
        self.calls.append((record.case_number, source_row["case_number"]))
        return [
            {
                "acct": "000999000001",
                "owner_name": record.decedent_name,
                "mailing_address": "100 LIVE MAIL ST, HOUSTON, TX",
                "property_address": "200 LIVE PROPERTY ST, HOUSTON, TX",
            }
        ]


class FakeTaxClient:
    def __init__(self) -> None:
        self.calls = []

    def fetch_tax_overlay(self, *, record, source_row):
        self.calls.append((record.case_number, record.hcad_acct, source_row["case_number"]))
        return {
            "status": TaxOverlayStatus.VERIFIED_DELINQUENT,
            "is_delinquent": True,
            "amount_owed": 1800.0,
            "account": record.hcad_acct,
            "confidence": "high",
            "search_method": "fake_public_tax_client",
        }


class FakeLandRecordClient:
    def __init__(self) -> None:
        self.calls = []

    def fetch_land_records(self, *, record, source_row):
        self.calls.append((record.case_number, source_row["case_number"]))
        return [
            {
                "instrument_number": "RP-LIVE-1",
                "instrument_type": "Affidavit of Heirship",
                "grantor": record.decedent_name,
                "grantee": "Example Heirs",
            }
        ]


def test_property_tax_title_enrichment_uses_registered_live_clients_with_explicit_no_send_approval() -> None:
    cad_client = FakeCadClient()
    tax_client = FakeTaxClient()
    land_record_client = FakeLandRecordClient()
    service = ProbatePropertyTaxTitleEnrichmentService(
        settings=Settings(
            _env_file=None,
            lead_machine_live_cad_calls_enabled=True,
            lead_machine_live_tax_calls_enabled=True,
            lead_machine_live_land_record_calls_enabled=True,
        ),
        cad_client=cad_client,
        tax_client=tax_client,
        land_record_client=land_record_client,
    )

    result = service.run_enrichment(
        business_id="limitless",
        environment="test",
        keep_now_rows=[
            {
                "case_number": "2026-LIVE-1",
                "filing_type": "APP TO DETERMINE HEIRSHIP",
                "estate_name": "Estate of Live Example",
                "decedent_name": "Live Example",
                "keep_now": True,
            }
        ],
        live_cad_calls=True,
        live_tax_calls=True,
        live_land_record_calls=True,
        enrichment_approval={"approved": True, "approved_by": "operator", "no_send": True, "provider_sends_enabled": False},
    )

    assert cad_client.calls == [("2026-LIVE-1", "2026-LIVE-1")]
    assert tax_client.calls == [("2026-LIVE-1", "999000001", "2026-LIVE-1")]
    assert land_record_client.calls == [("2026-LIVE-1", "2026-LIVE-1")]
    assert result["no_send"] is True
    assert result["provider_sends_enabled"] is False
    assert result["outbound_allowed"] is False
    assert result["live_cad_calls_attempted"] is True
    assert result["live_tax_calls_attempted"] is True
    assert result["live_land_record_calls_attempted"] is True
    record = result["records"][0]
    assert record["hcad_acct"] == "999000001"
    assert record["tax_delinquent"] is True
    assert record["pain_stack"]["property_match"]["live_calls_attempted"] is True
    assert record["pain_stack"]["tax_overlay"]["live_calls_attempted"] is True
    assert record["pain_stack"]["title_friction"]["live_calls_attempted"] is True
    assert record["pain_stack"]["title_friction"]["friction_flags"]["affidavit_of_heirship"] is True


def test_property_tax_title_enrichment_uses_default_registered_public_clients(monkeypatch) -> None:
    calls = []

    def fake_cad(*, record, source_row):
        calls.append(("cad", record.case_number, source_row["case_number"]))
        return [
            {
                "acct": "000777000001",
                "owner_name": record.decedent_name,
                "property_address": "777 PUBLIC PROPERTY ST, HOUSTON, TX",
            }
        ]

    def fake_tax(*, record, source_row):
        calls.append(("tax", record.case_number, record.hcad_acct, source_row["case_number"]))
        return {
            "status": TaxOverlayStatus.VERIFIED_DELINQUENT,
            "is_delinquent": True,
            "amount_owed": 777.0,
            "account": record.hcad_acct,
            "confidence": "high",
            "search_method": "patched_default_public_tax_client",
        }

    def fake_land(*, record, source_row):
        calls.append(("land", record.case_number, source_row["case_number"]))
        return [
            {
                "instrument_number": "RP-PUBLIC-1",
                "instrument_type": "Certified Copy of Probate",
                "grantor": record.decedent_name,
            }
        ]

    monkeypatch.setattr(probate_live_enrichment_clients.public_probate_live_cad_client, "fetch_candidates", fake_cad)
    monkeypatch.setattr(probate_live_enrichment_clients.public_probate_live_tax_client, "fetch_tax_overlay", fake_tax)
    monkeypatch.setattr(
        probate_live_enrichment_clients.public_probate_live_land_record_client,
        "fetch_land_records",
        fake_land,
    )

    service = ProbatePropertyTaxTitleEnrichmentService(
        settings=Settings(
            _env_file=None,
            lead_machine_live_cad_calls_enabled=True,
            lead_machine_live_tax_calls_enabled=True,
            lead_machine_live_land_record_calls_enabled=True,
        )
    )

    result = service.run_enrichment(
        business_id="limitless",
        environment="test",
        keep_now_rows=[
            {
                "county": "harris",
                "case_number": "2026-PUBLIC-1",
                "filing_type": "APP TO DETERMINE HEIRSHIP",
                "estate_name": "Estate of Public Client",
                "decedent_name": "Public Client",
                "keep_now": True,
            }
        ],
        live_cad_calls=True,
        live_tax_calls=True,
        live_land_record_calls=True,
        enrichment_approval={"approved": True, "approved_by": "operator", "no_send": True, "provider_sends_enabled": False},
    )

    assert calls == [
        ("cad", "2026-PUBLIC-1", "2026-PUBLIC-1"),
        ("tax", "2026-PUBLIC-1", "777000001", "2026-PUBLIC-1"),
        ("land", "2026-PUBLIC-1", "2026-PUBLIC-1"),
    ]
    assert result["live_cad_calls_attempted"] is True
    assert result["live_tax_calls_attempted"] is True
    assert result["live_land_record_calls_attempted"] is True
    assert result["records"][0]["tax_delinquent"] is True


def test_montgomery_publicsearch_land_record_date_range_uses_current_day(monkeypatch) -> None:
    requested_urls = []

    class FixedDate:
        @classmethod
        def today(cls):
            from datetime import date

            return date(2026, 5, 16)

    def fake_request_text(opener, url, **kwargs):
        requested_urls.append(url)
        return "<html></html>"

    monkeypatch.setattr(probate_live_enrichment_clients, "date", FixedDate)
    monkeypatch.setattr(probate_live_enrichment_clients, "_request_text", fake_request_text)

    record = ProbateLeadRecord(
        case_number="2026-10001",
        filing_type="APP TO DETERMINE HEIRSHIP",
        decedent_name="Jane Example",
        estate_name="Estate of Jane Example",
    )

    rows = MontgomeryPublicSearchLandRecordClient().fetch_land_records(
        record=record,
        source_row={"county": "montgomery", "case_number": "2026-10001", "decedent_name": "Jane Example"},
    )

    assert rows[0]["live_calls_attempted"] is True
    assert requested_urls
    assert "recordedDateRange=16000101%2C20260516" in requested_urls[0]
