from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.leads import LeadsRepository
from app.db.tasks import TasksRepository
from app.db.title_packets import TitlePacketsRepository
from app.models.tasks import TaskStatus, TaskType
from app.models.title_packets import TitlePacketStatus
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
                    "market_value": 955088,
                    "debt_to_value_pct": 6.68,
                },
                "raw_payload": {
                    "packet_source_files": ["/root/.hermes/output/harris_tax_verify/HOT_18_title_packet_report.md"],
                    "source_row": {"owner_tax": "PLUMMER LETITIA W ESTATE OF"},
                },
            }
        ],
    }


def _service(store: InMemoryControlPlaneStore) -> tuple[TitlePacketImportService, LeadsRepository, TitlePacketsRepository, TasksRepository]:
    client = InMemoryControlPlaneClient(store)
    leads = LeadsRepository(client)
    packets = TitlePacketsRepository(client)
    tasks = TasksRepository(client)
    return TitlePacketImportService(leads, packets, tasks), leads, packets, tasks


def test_import_payload_upserts_hot_title_packet_as_ready_lead() -> None:
    service, repository, packets, tasks = _service(InMemoryControlPlaneStore())

    result = service.import_payload(_payload())

    assert result.imported_count == 1
    assert result.updated_count == 0
    assert len(result.title_packet_ids) == 1
    assert len(result.task_ids) == 1
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

    packet = packets.get_by_key(
        business_id="limitless",
        environment="dev",
        dedupe_key="title-packet:harris-hot18:0611340530007",
    )
    assert packet is not None
    assert packet.lead_id == lead.id
    assert packet.status == TitlePacketStatus.NEEDS_REVIEW
    assert packet.hctax_account == "0611340530007"
    assert packet.facts["tax_due"] == 63829.57
    assert packet.artifact_refs == ["/root/.hermes/output/harris_tax_verify/HOT_18_title_packet_report.md"]

    task_rows = tasks.list(business_id="limitless", environment="dev", lead_id=lead.id)
    assert len(task_rows) == 1
    assert task_rows[0].task_type == TaskType.MANUAL_REVIEW
    assert task_rows[0].status == TaskStatus.OPEN
    assert task_rows[0].priority == "high"
    assert task_rows[0].details["title_packet_id"] == packet.id
    assert task_rows[0].details["manual_pull_queue"] == "Probate case 500741: pull application/order docs"


def test_import_payload_is_idempotent_by_external_key_packet_and_task() -> None:
    service, repository, packets, tasks = _service(InMemoryControlPlaneStore())

    first = service.import_payload(_payload(score=93.0))
    second = service.import_payload(_payload(score=97.0))

    records = repository.list(business_id="limitless", environment="dev")
    packet_records = packets.list(business_id="limitless", environment="dev")
    task_records = tasks.list(business_id="limitless", environment="dev")
    assert first.imported_count == 1
    assert second.imported_count == 0
    assert second.updated_count == 1
    assert len(records) == 1
    assert records[0].score == 97.0
    assert len(packet_records) == 1
    assert packet_records[0].facts["score"] == 97.0
    assert len(task_records) == 1
    assert task_records[0].id in first.task_ids
    assert second.task_ids == [task_records[0].id]


def test_import_payload_rejects_unknown_schema() -> None:
    service, _, _, _ = _service(InMemoryControlPlaneStore())

    try:
        service.import_payload({"schema": "wrong", "records": []})
    except ValueError as exc:
        assert "ares.lead_import.v1" in str(exc)
    else:
        raise AssertionError("expected schema validation failure")
