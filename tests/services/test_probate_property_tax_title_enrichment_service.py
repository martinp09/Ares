from app.domains.ares.models import AresCounty
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
        assert "live CAD/tax/land-record calls are not enabled" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected live execution rejection")


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
