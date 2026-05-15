import json

from app.core.config import get_settings

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_instantly_enrollment_preview_endpoint_requires_no_token_and_no_provider_call(client) -> None:
    response = client.post(
        "/mission-control/providers/instantly/enrollments/preview",
        json={
            "instantly_campaign_id": "inst_camp_1",
            "records": [
                {"id": "crm_1", "email": "jane@example.com", "display_name": "Jane", "verification_status": "valid"},
                {"id": "crm_2", "email": "bad@example.com", "display_name": "Bad", "verification_status": "invalid"},
            ],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "instantly"
    assert body["dry_run"] is True
    assert body["would_call_provider"] is False
    assert body["eligible_count"] == 1
    assert body["excluded_count"] == 1
    assert body["results"][0]["action"] == "enroll"
    assert body["results"][1]["action"] == "exclude"


def test_instantly_enrollment_apply_endpoint_rejects_missing_operator_approval(client) -> None:
    response = client.post(
        "/mission-control/providers/instantly/enrollments/apply",
        json={
            "business_id": "biz",
            "environment": "dev",
            "instantly_campaign_id": "inst_camp_1",
            "records": [{"id": "crm_1", "email": "jane@example.com", "verification_status": "valid"}],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "operator approval" in response.json()["detail"]


def test_instantly_enrollment_apply_endpoint_rejects_global_gate(client, monkeypatch) -> None:
    monkeypatch.setenv("INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED", "true")
    monkeypatch.setenv("INSTANTLY_API_KEY", "test-key")
    get_settings.cache_clear()

    response = client.post(
        "/mission-control/providers/instantly/enrollments/apply",
        json={
            "operator_approval": True,
            "business_id": "biz",
            "environment": "dev",
            "instantly_campaign_id": "inst_camp_1",
            "records": [],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "Provider live sends are disabled" in response.json()["detail"]


def test_instantly_enrollment_apply_endpoint_rejects_instantly_gate(client, monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_LIVE_SENDS_ENABLED", "true")
    monkeypatch.setenv("INSTANTLY_API_KEY", "test-key")
    get_settings.cache_clear()

    response = client.post(
        "/mission-control/providers/instantly/enrollments/apply",
        json={
            "operator_approval": True,
            "business_id": "biz",
            "environment": "dev",
            "instantly_campaign_id": "inst_camp_1",
            "records": [],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "Instantly live enrollment is disabled" in response.json()["detail"]


def test_instantly_enrollment_apply_endpoint_rejects_missing_api_key(client, monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_LIVE_SENDS_ENABLED", "true")
    monkeypatch.setenv("INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED", "true")
    monkeypatch.setenv("INSTANTLY_API_KEY", "")
    get_settings.cache_clear()

    response = client.post(
        "/mission-control/providers/instantly/enrollments/apply",
        json={
            "operator_approval": True,
            "business_id": "biz",
            "environment": "dev",
            "instantly_campaign_id": "inst_camp_1",
            "records": [],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "API key is required" in response.json()["detail"]


def test_instantly_enrollment_apply_endpoint_shape_with_fake_service_and_no_secret_text(client, monkeypatch) -> None:
    def fake_apply(self, *, business_id, environment, records, operator_approval=False, **kwargs):
        assert business_id == "biz"
        assert environment == "dev"
        assert operator_approval is True
        assert kwargs["instantly_campaign_id"] == "inst_camp_1"
        assert kwargs["campaign_id"] == "internal_campaign"
        assert records[0]["id"] == "crm_1"
        return {
            "provider": "instantly",
            "dry_run": False,
            "live_applied": True,
            "would_call_provider": True,
            "live_enrollment_enabled": True,
            "eligible_count": 1,
            "submitted_count": 1,
            "enrolled_count": 1,
            "skipped_count": 0,
            "excluded_count": 0,
            "error_count": 0,
            "target": {
                "instantly_campaign_id": "inst_camp_1",
                "instantly_list_id": None,
                "campaign_id": "internal_campaign",
            },
            "results": [
                {
                    "record_id": "crm_1",
                    "email": "jane@example.com",
                    "action": "enroll",
                    "reason": "eligible",
                    "provider_object_id": "lead_1",
                    "provider_link_id": "plink_1",
                    "sync_hash": "hash_1",
                }
            ],
            "warnings": [],
            "provider_batch_result": {
                "type": "list",
                "top_level_count_fields": {},
                "top_level_collection_lengths": {"items": 1},
                "per_lead_id_count": 1,
                "omitted_raw_payload": True,
            },
        }

    monkeypatch.setattr("app.api.mission_control.InstantlyEnrollmentService.apply_enrollment", fake_apply)

    response = client.post(
        "/mission-control/providers/instantly/enrollments/apply",
        json={
            "operator_approval": True,
            "business_id": "biz",
            "environment": "dev",
            "instantly_campaign_id": "inst_camp_1",
            "campaign_id": "internal_campaign",
            "records": [
                {
                    "id": "crm_1",
                    "email": "jane@example.com",
                    "display_name": "Jane Seller",
                    "verification_status": "valid",
                    "sync_hash": "hash_1",
                }
            ],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "instantly"
    assert body["results"][0]["provider_object_id"] == "lead_1"
    serialized_body = json.dumps(body, sort_keys=True).lower()
    assert "token" not in serialized_body
    assert "secret" not in serialized_body


def test_instantly_enrollment_apply_endpoint_rejects_missing_or_conflicting_provider_target(client) -> None:
    base_payload = {
        "operator_approval": True,
        "business_id": "biz",
        "environment": "dev",
        "records": [{"id": "crm_1", "email": "jane@example.com", "verification_status": "valid"}],
    }

    missing_response = client.post(
        "/mission-control/providers/instantly/enrollments/apply",
        json=base_payload,
        headers=AUTH_HEADERS,
    )
    both_response = client.post(
        "/mission-control/providers/instantly/enrollments/apply",
        json={**base_payload, "instantly_campaign_id": "inst_camp_1", "instantly_list_id": "inst_list_1"},
        headers=AUTH_HEADERS,
    )

    assert missing_response.status_code == 422
    assert both_response.status_code == 422


def test_instantly_enrollment_request_forbids_unknown_fields(client) -> None:
    response = client.post(
        "/mission-control/providers/instantly/enrollments/preview",
        json={"unexpected": True, "records": []},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
