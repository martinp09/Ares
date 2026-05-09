from datetime import date

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.crm_records import CrmRecordsRepository
from app.db.leads import LeadsRepository
from app.db.probate_leads import ProbateLeadsRepository
from app.models.crm_records import CrmRecordStatus
from app.services.harris_daily_lead_machine_service import HarrisDailyLeadMachineService
from app.services.harris_probate_intake_service import HarrisProbateIntakeService
from app.services.probate_hcad_match_service import ProbateHCADMatchService
from app.services.probate_lead_bridge_service import ProbateLeadBridgeService
from app.services.probate_lead_score_service import ProbateLeadScoreService
from app.services.probate_write_path_service import ProbateWritePathService


def _build_service(
    settings: Settings | None = None,
) -> tuple[HarrisDailyLeadMachineService, ProbateLeadsRepository, LeadsRepository, CrmRecordsRepository]:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    settings = settings or Settings(_env_file=None)
    probate_repository = ProbateLeadsRepository(client=client, settings=settings)
    leads_repository = LeadsRepository(client=client, settings=settings)
    crm_repository = CrmRecordsRepository(client=client, settings=settings, force_memory=True)
    write_path = ProbateWritePathService(
        settings=settings,
        intake_service=HarrisProbateIntakeService(),
        hcad_match_service=ProbateHCADMatchService(),
        score_service=ProbateLeadScoreService(),
        probate_leads_repository=probate_repository,
        lead_bridge_service=ProbateLeadBridgeService(leads_repository),
    )
    service = HarrisDailyLeadMachineService(
        settings=settings,
        probate_write_path=write_path,
        crm_records_repository=crm_repository,
        probate_intake_service=HarrisProbateIntakeService(),
        hcad_match_service=ProbateHCADMatchService(),
        score_service=ProbateLeadScoreService(),
    )
    return service, probate_repository, leads_repository, crm_repository


def test_harris_daily_import_dry_run_scores_and_warns_without_persistence() -> None:
    service, probate_repository, leads_repository, crm_repository = _build_service()

    result = service.run_daily_import(
        business_id="limitless",
        environment="dev",
        run_date=date(2026, 5, 9),
        dry_run=True,
        probate_records=[
            {
                "case_number": "2026-10001",
                "type": "INDEPENDENT ADMINISTRATION",
                "estate_name": "Estate of Jane Example",
                "decedent_name": "Jane Example",
                "hcad_candidates": [
                    {
                        "acct": "00011122",
                        "owner_name": "Jane Example",
                        "mailing_address": "123 Main St, Houston, TX 77002",
                        "property_address": "456 Oak St, Houston, TX 77008",
                    }
                ],
                "tax_delinquent": True,
                "estate_of": True,
                "pain_stack": {"tax_delinquent": True, "estate_of": True, "amount_owed": 8200},
            }
        ],
        hcad_estate_of_records=[
            {
                "hcad_account": "1234567890123",
                "owner_name": "Estate Of Maria Ramos",
                "property_address": "789 Pine St, Houston, TX 77009",
                "tax_delinquent": True,
                "amount_owed": "$9,250.15",
                "selected_contacts": [
                    {"name": "Alex Ramos", "relationship": "applicant"},
                    {"name": "Bea Ramos", "relationship": "heir"},
                    {"name": "Chris Ramos", "relationship": "heir"},
                ],
            },
            {
                "hcad_account": "9999999999999",
                "owner_name": "JMDH Real Estate Of Houston LLC",
                "property_address": "111 Entity Way, Houston, TX",
            },
        ],
    )

    assert result["dry_run"] is True
    assert result["counts"]["provider_send_count"] == 0
    assert result["probate"]["records"][0]["hcad_match_status"] == "matched"
    assert result["probate"]["records"][0]["lead_score"] == 100.0
    assert result["estate_of"]["candidate_count"] == 1
    assert result["estate_of"]["excluded_count"] == 1
    assert result["estate_of"]["records"][0]["selected_contact_count"] == 2
    assert result["estate_of"]["records"][0]["additional_contacts_hidden"] is True
    assert result["notifications"][0]["status"] == "skipped_missing_token"
    assert {warning["code"] for warning in result["qc_warnings"]} == {
        "estate_of_contact_cap_applied",
        "estate_of_false_positive_excluded",
    }
    assert probate_repository.list(business_id="limitless", environment="dev") == []
    assert leads_repository.list(business_id="limitless", environment="dev") == []
    assert crm_repository.list_records(business_id="limitless", environment="dev") == []


def test_harris_daily_import_persists_probate_and_estate_of_records_without_provider_send() -> None:
    service, probate_repository, leads_repository, crm_repository = _build_service()

    result = service.run_daily_import(
        business_id="limitless",
        environment="dev",
        run_date=date(2026, 5, 9),
        dry_run=False,
        probate_records=[
            {
                "case_number": "2026-10002",
                "type": "INDEPENDENT ADMINISTRATION",
                "estate_name": "Estate of Morgan Deed",
                "decedent_name": "Morgan Deed",
                "hcad_candidates": [
                    {
                        "acct": "00033344",
                        "owner_name": "Morgan Deed",
                        "mailing_address": "10 Main St, Houston, TX 77002",
                        "property_address": "20 Oak St, Houston, TX 77008",
                    }
                ],
                "tax_delinquent": True,
                "estate_of": True,
                "pain_stack": {"tax_delinquent": True, "estate_of": True},
            }
        ],
        hcad_estate_of_records=[
            {
                "hcad_account": "1234567890123",
                "owner_name": "Estate Of Maria Ramos",
                "property_address": "789 Pine St, Houston, TX 77009",
                "mailing_address": "PO Box 10, Houston, TX",
                "tax_delinquent": True,
                "amount_owed": 9250.15,
                "selected_contacts": [{"name": "Alex Ramos", "relationship": "applicant"}],
            }
        ],
    )

    assert result["dry_run"] is False
    assert result["counts"] == {
        "probate_received": 1,
        "probate_keep_now": 1,
        "probate_bridged": 1,
        "estate_of_received": 1,
        "estate_of_candidates": 1,
        "estate_of_imported": 1,
        "qc_warning_count": 0,
        "provider_send_count": 0,
    }
    assert len(probate_repository.list(business_id="limitless", environment="dev")) == 1
    leads = leads_repository.list(business_id="limitless", environment="dev")
    assert len(leads) == 1
    assert leads[0].custom_variables["hcad_acct"] == "33344"
    assert leads[0].custom_variables["tax_delinquent"] is True
    crm_records = crm_repository.list_records(business_id="limitless", environment="dev")
    assert len(crm_records) == 1
    record = crm_records[0]
    assert record.identity_key == "hcad_estate_of:1234567890123"
    assert record.status == CrmRecordStatus.CLEAN
    assert record.facts["source_lane"] == "hcad_estate_of"
    assert record.facts["selected_contact_count"] == 1
    assert record.facts["delinquent_amount"] == 9250.15
    assert result["estate_of"]["records"][0]["record_id"] == record.id


def test_harris_daily_import_with_slack_config_reports_ready_not_sent() -> None:
    settings = Settings(
        _env_file=None,
        **{
            "slack_bot_token": "configured-test-value",
            "slack_channel_leads": "C123LEADS",
        },
    )
    service, probate_repository, leads_repository, crm_repository = _build_service(settings=settings)

    result = service.run_daily_import(
        business_id="limitless",
        environment="dev",
        run_date=date(2026, 5, 9),
        dry_run=True,
        hcad_estate_of_records=[
            {
                "hcad_account": "2222222222222",
                "owner_name": "Estate Of Test Owner",
                "property_address": "200 No Post St, Houston, TX",
                "tax_delinquent": True,
                "amount_owed": "not-a-number",
                "extracted_at": "not-a-date",
            }
        ],
    )

    assert result["counts"]["provider_send_count"] == 0
    assert result["notifications"] == [
        {
            "type": "daily_digest",
            "status": "ready_not_sent",
            "reason": "Slack token is configured, but this endpoint records import readiness only and does not post live Slack messages.",
            "channel_id": "C123LEADS",
            "counts": result["counts"],
        }
    ]
    assert result["estate_of"]["records"][0]["status"] == "needs_skip_trace"
    assert probate_repository.list(business_id="limitless", environment="dev") == []
    assert leads_repository.list(business_id="limitless", environment="dev") == []
    assert crm_repository.list_records(business_id="limitless", environment="dev") == []
