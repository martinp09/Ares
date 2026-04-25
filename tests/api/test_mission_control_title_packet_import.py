from app.db.leads import LeadsRepository
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_lead_machine_imports_title_packet_payload_into_canonical_leads(client) -> None:
    reset_control_plane_state()
    payload = {
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
                "score": 95,
                "verification_status": "operator_packet_built",
                "enrichment_status": "hcad_tax_clerk_probate_enriched",
                "upload_method": "hermes_hot18_packet_import",
                "personalization": {"operator_lane": "A — probate-first estate lead"},
                "custom_variables": {"hctax_account": "0372510000004", "tax_due": 22909.44},
                "raw_payload": {"source_row": {"owner_tax": "LUKE DOROTHY ESTATE OF"}},
            }
        ],
    }

    response = client.post(
        "/mission-control/lead-machine/title-packets/import",
        json=payload,
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["imported_count"] == 1
    assert body["updated_count"] == 0
    assert len(body["lead_ids"]) == 1

    lead = LeadsRepository().get_by_key(
        business_id="limitless",
        environment="dev",
        dedupe_key="external:harris-hot18:0372510000004",
    )
    assert lead is not None
    assert lead.company_name == "LUKE DOROTHY ESTATE OF"
    assert lead.probate_case_number == "336144"
    assert lead.custom_variables["tax_due"] == 22909.44


def test_lead_machine_title_packet_import_rejects_bad_schema(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/mission-control/lead-machine/title-packets/import",
        json={"schema": "wrong", "records": []},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 400
    assert "ares.lead_import.v1" in response.json()["detail"]
