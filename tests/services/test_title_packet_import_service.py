from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.leads import LeadsRepository
from app.services.title_packet_import_service import TitlePacketImportService


def _payload(*, score: float = 95.0) -> dict:
    return {
        "schema": "ares.lead_import.v1",
        "source": "hermes.harris_hot18_title_packet_run",
        "import_mode": "upsert_by_external_key",
        "records": [
            {
                "business_id": "limitless",
                "environment": "dev",
                "source": "manual",
                "lifecycle_status": "ready",
                "external_key": "harris-hot18:0611340530007",
                "company_name": "PLUMMER LETITIA W ESTATE OF",
                "mailing_address": "3324 S MACGREGOR WAY HOUSTON TX 77021-1107",
                "property_address": "3324 S MACGREGOR WAY 77021",
                "probate_case_number": "500741",
                "score": score,
                "verification_status": "operator_packet_built",
                "enrichment_status": "hcad_tax_clerk_probate_enriched",
                "upload_method": "hermes_hot18_packet_import",
                "personalization": {
                    "operator_lane": "A — probate-first estate lead",
                    "why_now": "estate owner on tax roll; 1 probate hit(s); low debt-to-value",
                },
                "custom_variables": {
                    "rank": 3,
                    "hctax_account": "0611340530007",
                    "tax_due": 63829.57,
                    "delinquent_years": "2022,2023,2024,2025",
                    "manual_pull_queue": "Probate case 500741: pull application/order docs",
                },
                "raw_payload": {"source_row": {"owner_tax": "PLUMMER LETITIA W ESTATE OF"}},
            }
        ],
    }


def test_import_payload_upserts_hot_title_packet_as_ready_lead() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repository = LeadsRepository(client)
    service = TitlePacketImportService(repository)

    result = service.import_payload(_payload())

    assert result.imported_count == 1
    assert result.updated_count == 0
    lead = repository.get_by_key(
        business_id="limitless",
        environment="dev",
        dedupe_key="external:harris-hot18:0611340530007",
    )
    assert lead is not None
    assert lead.lifecycle_status == "ready"
    assert lead.external_key == "harris-hot18:0611340530007"
    assert lead.company_name == "PLUMMER LETITIA W ESTATE OF"
    assert lead.probate_case_number == "500741"
    assert lead.custom_variables["hctax_account"] == "0611340530007"
    assert lead.personalization["operator_lane"] == "A — probate-first estate lead"
    assert lead.raw_payload["import_source"] == "hermes.harris_hot18_title_packet_run"


def test_import_payload_is_idempotent_by_external_key() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repository = LeadsRepository(client)
    service = TitlePacketImportService(repository)

    first = service.import_payload(_payload(score=93.0))
    second = service.import_payload(_payload(score=97.0))

    records = repository.list(business_id="limitless", environment="dev")
    assert first.imported_count == 1
    assert second.imported_count == 0
    assert second.updated_count == 1
    assert len(records) == 1
    assert records[0].score == 97.0


def test_import_payload_rejects_unknown_schema() -> None:
    service = TitlePacketImportService(LeadsRepository(InMemoryControlPlaneClient(InMemoryControlPlaneStore())))

    try:
        service.import_payload({"schema": "wrong", "records": []})
    except ValueError as exc:
        assert "ares.lead_import.v1" in str(exc)
    else:
        raise AssertionError("expected schema validation failure")
