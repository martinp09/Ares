from app.core.config import get_settings

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_hubspot_customization_preview_endpoint_defaults_to_dry_run_and_requires_no_token(client) -> None:
    response = client.post(
        "/mission-control/providers/hubspot/customization/preview",
        json={},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "hubspot"
    assert body["dry_run"] is True
    assert body["would_call_provider"] is False
    assert body["live_write_enabled"] is False
    assert body["payloads"]["property_groups"]["deals"][0]["name"] == "ares_information"
    assert body["payloads"]["pipelines"]["deals"][0]["label"] == "Ares Acquisitions"


def test_hubspot_record_preview_endpoint_builds_payloads_without_provider_token(client) -> None:
    response = client.post(
        "/mission-control/providers/hubspot/records/preview-sync",
        json={
            "records": [
                {
                    "id": "crm_1",
                    "record_type": "contact_record",
                    "display_name": "Jane Seller",
                    "property_address": "123 Main St",
                    "mailing_address": "PO Box 123",
                    "source": "harris_probate",
                    "record_status": "active",
                    "email": "jane@example.com",
                    "phone": "7135550100",
                    "opportunity_id": "opp_1",
                    "lead_score": 91,
                    "probate_case_number": "543678",
                    "best_contact_name": "Jane Applicant",
                    "best_contact_role": "Applicant",
                    "heir_candidate_count": 5,
                    "heir_candidates_summary": "Jane Applicant (Applicant); John Heir (Respondent)",
                }
            ]
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "hubspot"
    assert body["dry_run"] is True
    assert body["would_call_provider"] is False
    assert body["payloads"]["contacts"][0]["properties"]["email"] == "jane@example.com"
    assert body["payloads"]["contacts"][0]["properties"]["ares_mailing_address"] == "PO Box 123"
    assert body["payloads"]["deals"][0]["properties"]["ares_opportunity_id"] == "opp_1"
    assert body["payloads"]["deals"][0]["properties"]["ares_probate_case_number"] == "543678"
    assert body["payloads"]["deals"][0]["properties"]["ares_heir_candidates_summary"] == "Jane Applicant (Applicant); John Heir (Respondent)"
    assert body["payloads"]["companies"] == []


def test_hubspot_record_preview_rejects_live_without_gate_before_provider_call(client, monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_LIVE_SENDS_ENABLED", "true")
    get_settings.cache_clear()

    response = client.post(
        "/mission-control/providers/hubspot/records/preview-sync",
        json={"dry_run": False, "records": []},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "live writes are disabled" in response.json()["detail"]


def test_hubspot_record_preview_rejects_live_apply_after_gate_without_provider_call(client, monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_LIVE_SENDS_ENABLED", "true")
    monkeypatch.setenv("HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED", "true")
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "token")
    get_settings.cache_clear()

    response = client.post(
        "/mission-control/providers/hubspot/records/preview-sync",
        json={"dry_run": False, "records": []},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "apply-sync" in response.json()["detail"]


def test_hubspot_customization_apply_rejects_missing_operator_approval_before_provider_call(client) -> None:
    response = client.post(
        "/mission-control/providers/hubspot/customization/apply",
        json={},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "operator approval" in response.json()["detail"]


def test_hubspot_customization_apply_rejects_global_gate_before_provider_call(client, monkeypatch) -> None:
    monkeypatch.setenv("HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED", "true")
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "token")
    get_settings.cache_clear()

    response = client.post(
        "/mission-control/providers/hubspot/customization/apply",
        json={"operator_approval": True},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "Provider live sends are disabled" in response.json()["detail"]


def test_hubspot_customization_apply_rejects_hubspot_gate_before_provider_call(client, monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_LIVE_SENDS_ENABLED", "true")
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "token")
    get_settings.cache_clear()

    response = client.post(
        "/mission-control/providers/hubspot/customization/apply",
        json={"operator_approval": True},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "HubSpot live writes are disabled" in response.json()["detail"]


def test_hubspot_customization_apply_rejects_missing_token_before_provider_call(client, monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_LIVE_SENDS_ENABLED", "true")
    monkeypatch.setenv("HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED", "true")
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "")
    get_settings.cache_clear()

    response = client.post(
        "/mission-control/providers/hubspot/customization/apply",
        json={"operator_approval": True},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "access token is required" in response.json()["detail"]


def test_hubspot_preview_request_forbids_unknown_fields(client) -> None:
    response = client.post(
        "/mission-control/providers/hubspot/customization/preview",
        json={"dry_run": True, "unexpected": True},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422


def test_hubspot_record_apply_sync_endpoint_rejects_missing_operator_approval(client) -> None:
    response = client.post(
        "/mission-control/providers/hubspot/records/apply-sync",
        json={"business_id": "biz", "environment": "dev", "records": []},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "operator approval" in response.json()["detail"]


def test_hubspot_record_apply_sync_endpoint_shape_with_fake_service(client, monkeypatch) -> None:
    def fake_apply_record_sync(self, *, business_id, environment, records, operator_approval=False):
        assert business_id == "biz"
        assert environment == "dev"
        assert operator_approval is True
        assert records[0]["id"] == "crm_1"
        return {
            "provider": "hubspot",
            "live_applied": True,
            "created_count": 1,
            "updated_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "error_count": 0,
            "results": [
                {
                    "record_id": "crm_1",
                    "object_type": "contact",
                    "ares_object_type": "crm_record",
                    "ares_object_id": "crm_1",
                    "action": "create",
                    "provider_object_id": "hs_1",
                    "provider_link_id": "plink_1",
                    "sync_hash": "hash_1",
                }
            ],
            "warnings": [],
        }

    monkeypatch.setattr("app.api.mission_control.HubSpotMirrorService.apply_record_sync", fake_apply_record_sync)

    response = client.post(
        "/mission-control/providers/hubspot/records/apply-sync",
        json={
            "operator_approval": True,
            "business_id": "biz",
            "environment": "dev",
            "records": [{"id": "crm_1", "display_name": "Jane Seller", "email": "jane@example.com", "sync_hash": "hash_1"}],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "hubspot"
    assert body["live_applied"] is True
    assert body["created_count"] == 1
    assert body["results"][0]["provider_object_id"] == "hs_1"
    import json

    serialized_body = json.dumps(body, sort_keys=True)
    assert "token" not in serialized_body.lower()
