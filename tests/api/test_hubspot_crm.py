from app.models.crm_records import CrmRecordStatus, CrmRecordType

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_hubspot_customization_endpoint_returns_dry_run_schema(client) -> None:
    response = client.post(
        "/crm/hubspot/customization",
        json={"business_id": "limitless", "environment": "prod"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["action"] == "configure_hubspot_crm"
    assert body["status"] == "skipped"
    assert body["dry_run"] is True
    property_names = {definition["name"] for definition in body["request_payload"]["properties"]}
    assert "ares_hctax_account" in property_names
    assert "ares_skiptrace_status" in property_names
    assert body["request_payload"]["deal_pipeline"]["label"] == "Ares Acquisition Pipeline"


def test_hubspot_record_sync_endpoint_maps_record_without_live_write(client) -> None:
    response = client.post(
        "/crm/hubspot/records/sync",
        json={
            "record": {
                "business_id": "limitless",
                "environment": "prod",
                "record_type": CrmRecordType.CONTACT.value,
                "status": CrmRecordStatus.NEEDS_SKIP_TRACE.value,
                "identity_key": "harris-hot18:0123456789012",
                "display_name": "Maria Lopez",
                "owner_name": "Maria Lopez",
                "property_address": "123 Main St, Houston, TX",
                "phone": "713-555-0101",
                "facts": {
                    "source_lane": "curative_title",
                    "hctax_account": "0123456789012",
                    "probate_case_number": "PR-123456",
                },
            },
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["action"] == "sync_hubspot_record"
    assert body["status"] == "skipped"
    assert body["dry_run"] is True
    assert body["request_payload"]["contact"]["properties"]["phone"] == "+17135550101"
    assert body["request_payload"]["deal"]["properties"]["ares_hctax_account"] == "0123456789012"
