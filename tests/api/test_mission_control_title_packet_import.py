from app.services.run_service import reset_control_plane_state


AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_mission_control_imports_title_packet_payload(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/mission-control/lead-machine/title-packets/import",
        headers=AUTH_HEADERS,
        json={
            "schema": "ares.lead_import.v1",
            "source": "hermes.harris_hot18_title_packet_run",
            "records": [
                {
                    "business_id": "limitless",
                    "environment": "dev",
                    "source": "manual",
                    "lifecycle_status": "ready",
                    "external_key": "harris-hot18:0611340530007",
                    "company_name": "PLUMMER LETITIA W ESTATE OF",
                    "property_address": "3324 S MACGREGOR WAY 77021",
                    "probate_case_number": "500741",
                    "score": 93,
                    "personalization": {
                        "operator_lane": "A - probate-first estate lead",
                        "why_now": "estate owner on tax roll",
                    },
                    "custom_variables": {
                        "hctax_account": "0611340530007",
                        "manual_pull_queue": "Probate case 500741: pull application/order docs",
                    },
                    "raw_payload": {
                        "packet_source_files": ["HOT_18_title_packet_report.md"],
                        "source_row": {"owner_tax": "PLUMMER LETITIA W ESTATE OF"},
                    },
                }
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["imported_count"] == 1
    assert body["updated_count"] == 0
    assert len(body["lead_ids"]) == 1
    assert body["lead_ids"][0].startswith("lead_")
    assert len(body["title_packet_ids"]) == 1
    assert body["title_packet_ids"][0].startswith("tpkt_")
    assert len(body["task_ids"]) == 1
    assert body["task_ids"][0].startswith("tsk_")

    lead_machine = client.get(
        "/mission-control/lead-machine?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert lead_machine.status_code == 200
    assert lead_machine.json()["tasks"]["items"][0]["title"] == "Review title packet: 3324 S MACGREGOR WAY 77021"
