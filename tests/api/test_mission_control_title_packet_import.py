from app.db.leads import LeadsRepository
from app.db.tasks import TasksRepository
from app.db.title_packets import TitlePacketsRepository
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def _payload(*, score: float = 95) -> dict:
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
                "external_key": "harris-hot18:0372510000004",
                "company_name": "LUKE DOROTHY ESTATE OF",
                "mailing_address": "PO BOX 14364 HOUSTON TX 77221-4364",
                "property_address": "3332 TUAM ST 77004",
                "probate_case_number": "336144",
                "score": score,
                "verification_status": "operator_packet_built",
                "enrichment_status": "hcad_tax_clerk_probate_enriched",
                "upload_method": "hermes_hot18_packet_import",
                "personalization": {
                    "operator_lane": "A — probate-first estate lead",
                    "why_now": "estate owner on tax roll; tax suit/litigation note",
                },
                "custom_variables": {
                    "hctax_account": "0372510000004",
                    "tax_due": 22909.44,
                    "delinquent_years": "2021,2022,2023,2024,2025",
                    "manual_pull_queue": "Probate case 336144: pull small estate affidavit",
                },
                "raw_payload": {"source_row": {"owner_tax": "LUKE DOROTHY ESTATE OF"}},
            }
        ],
    }


def test_lead_machine_imports_title_packet_payload_into_canonical_leads_packets_and_tasks(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/mission-control/lead-machine/title-packets/import",
        json=_payload(),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["imported_count"] == 1
    assert body["updated_count"] == 0
    assert len(body["lead_ids"]) == 1
    assert len(body["title_packet_ids"]) == 1
    assert len(body["task_ids"]) == 1

    lead = LeadsRepository().get_by_key(
        business_id="limitless",
        environment="dev",
        dedupe_key="external:harris-hot18:0372510000004",
    )
    assert lead is not None
    assert lead.company_name == "LUKE DOROTHY ESTATE OF"
    assert lead.probate_case_number == "336144"
    assert lead.custom_variables["tax_due"] == 22909.44
    packet = TitlePacketsRepository().get_by_key(
        business_id="limitless",
        environment="dev",
        dedupe_key="title-packet:harris-hot18:0372510000004",
    )
    assert packet is not None
    assert packet.lead_id == lead.id
    assert packet.hctax_account == "0372510000004"
    task_rows = TasksRepository().list(business_id="limitless", environment="dev", lead_id=lead.id)
    assert len(task_rows) == 1
    assert task_rows[0].details["title_packet_id"] == packet.id


def test_lead_machine_endpoint_surfaces_imported_title_packet_queue_and_tasks(client) -> None:
    reset_control_plane_state()
    import_response = client.post(
        "/mission-control/lead-machine/title-packets/import",
        json=_payload(),
        headers=AUTH_HEADERS,
    )
    assert import_response.status_code == 201

    response = client.get(
        "/mission-control/lead-machine?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["lead_count"] == 1
    assert body["summary"]["title_packet_count"] == 1
    assert body["summary"]["open_task_count"] == 1
    assert len(body["leads"]) == 1
    lead_row = body["leads"][0]
    assert lead_row["external_key"] == "harris-hot18:0372510000004"
    assert lead_row["lead_name"] == "LUKE DOROTHY ESTATE OF"
    assert lead_row["property_address"] == "3332 TUAM ST 77004"
    assert lead_row["probate_case_number"] == "336144"
    assert lead_row["operator_lane"] == "A — probate-first estate lead"
    assert lead_row["manual_pull_queue"] == "Probate case 336144: pull small estate affidavit"
    assert lead_row["title_packet_status"] == "needs_review"
    assert lead_row["title_packet_id"] is not None
    assert body["tasks"][0]["task_type"] == "manual_review"
    assert body["tasks"][0]["details"]["manual_pull_queue"] == "Probate case 336144: pull small estate affidavit"


def test_lead_machine_title_packet_import_is_idempotent(client) -> None:
    reset_control_plane_state()
    first = client.post("/mission-control/lead-machine/title-packets/import", json=_payload(score=95), headers=AUTH_HEADERS)
    second = client.post("/mission-control/lead-machine/title-packets/import", json=_payload(score=99), headers=AUTH_HEADERS)

    assert first.status_code == 201
    assert second.status_code == 201
    second_body = second.json()
    assert second_body["imported_count"] == 0
    assert second_body["updated_count"] == 1
    assert second_body["task_ids"] == first.json()["task_ids"]
    assert len(LeadsRepository().list(business_id="limitless", environment="dev")) == 1
    assert len(TitlePacketsRepository().list(business_id="limitless", environment="dev")) == 1
    assert len(TasksRepository().list(business_id="limitless", environment="dev")) == 1


def test_lead_machine_title_packet_import_rejects_bad_schema(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/mission-control/lead-machine/title-packets/import",
        json={"schema": "wrong", "records": []},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 400
    assert "ares.lead_import.v1" in response.json()["detail"]
