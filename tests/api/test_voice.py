import json

from app.core.config import get_settings

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def outbound_payload(**overrides):
    payload = {
        "business_id": "biz",
        "environment": "dev",
        "crm_record_id": "crm_1",
        "to_number": "+17135550100",
        "assistant_id": "asst_1",
        "phone_number_id": "pn_1",
        "customer_name": "Jane Seller",
    }
    payload.update(overrides)
    return payload


def test_voice_routes_exist_and_list_previews_make_no_provider_call(client) -> None:
    assistants = client.get("/voice/assistants", headers=AUTH_HEADERS)
    phone_numbers = client.get("/voice/phone-numbers", headers=AUTH_HEADERS)

    assert assistants.status_code == 200
    assert phone_numbers.status_code == 200
    assert assistants.json()["provider"] == "vapi"
    assert assistants.json()["would_call_provider"] is False
    assert phone_numbers.json()["resource"] == "phone_numbers"


def test_outbound_preview_dry_run_requires_no_token(client) -> None:
    response = client.post("/voice/calls/outbound", json=outbound_payload(), headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "vapi"
    assert body["dry_run"] is True
    assert body["would_call_provider"] is False
    assert body["action"] == "preview"
    assert body["payload"]["assistantId"] == "asst_1"


def test_outbound_live_gate_failure(client, monkeypatch) -> None:
    monkeypatch.setenv("VAPI_PROVIDER_LIVE_SENDS_ENABLED", "true")
    monkeypatch.setenv("VAPI_API_KEY", "test-key")
    monkeypatch.setenv("VAPI_DEFAULT_ASSISTANT_ID", "asst_default")
    monkeypatch.setenv("VAPI_DEFAULT_PHONE_NUMBER_ID", "pn_default")
    get_settings.cache_clear()

    response = client.post(
        "/voice/calls/outbound",
        json=outbound_payload(dry_run=False, operator_approval=True),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "Provider live sends are disabled" in response.json()["detail"]


def test_fake_dispatch_response_shape_has_no_token_or_secret_text(client, monkeypatch) -> None:
    def fake_dispatch(self, payload):
        return {
            "provider": "vapi",
            "dry_run": False,
            "would_call_provider": True,
            "live_applied": True,
            "action": "dispatched",
            "call_id": "call_123",
            "provider_call_id": "call_123",
            "provider_link_id": "plink_123",
            "payload": {"redacted": True, "customer_number_present": bool(payload.to_number)},
            "warnings": [],
            "error_message": None,
        }

    monkeypatch.setattr("app.api.voice.VapiCallService.dispatch_outbound_call", fake_dispatch)

    response = client.post(
        "/voice/calls/outbound",
        json=outbound_payload(dry_run=False, operator_approval=True),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider_call_id"] == "call_123"
    serialized = json.dumps(body, sort_keys=True).lower()
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "+171****0100" not in serialized
    assert "jane seller" not in serialized


def test_outbound_error_api_response_redacts_request_values(client, monkeypatch) -> None:
    from app.core.config import Settings
    from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
    from app.db.provider_links import ProviderLinksRepository
    from app.models.providers import ProviderTransportError
    from app.services.vapi_call_service import VapiCallService

    class FakeClient:
        def create_outbound_call(self, payload):
            raise ProviderTransportError(
                "provider echoed +171****0100 +171****0199 Jane Seller asst_1 pn_1 vip-lane crm_1",
                status_code=502,
            )

    svc_settings = Settings(
        provider_live_sends_enabled=True,
        vapi_provider_live_sends_enabled=True,
        vapi_api_key="test-key",
        control_plane_backend="memory",
        lead_machine_backend="memory",
    )
    service = VapiCallService(
        settings=svc_settings,
        client=FakeClient(),
        provider_links=ProviderLinksRepository(
            client=InMemoryControlPlaneClient(InMemoryControlPlaneStore()),
            settings=svc_settings,
            force_memory=True,
        ),
    )
    monkeypatch.setattr("app.api.voice.VapiCallService", lambda: service)

    response = client.post(
        "/voice/calls/outbound",
        json=outbound_payload(
            dry_run=False,
            operator_approval=True,
            from_number="+171****0199",
            metadata={"lane": "vip-lane"},
        ),
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    serialized = json.dumps(response.json(), sort_keys=True)
    assert response.json()["error_message"] == "Vapi provider dispatch failed."
    for raw_value in ("+171****0100", "+171****0199", "Jane Seller", "asst_1", "pn_1", "vip-lane", "crm_1"):
        assert raw_value not in serialized


def test_webhook_secret_required_behavior(client, monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_WEBHOOK_SIGNATURES_REQUIRED", "true")
    monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "expected")
    get_settings.cache_clear()

    rejected = client.post("/voice/vapi/webhook", json={"type": "call-ended"}, headers=AUTH_HEADERS)
    accepted = client.post(
        "/voice/vapi/webhook",
        json={"type": "call-ended", "call": {"id": "call_123", "status": "ended"}},
        headers={**AUTH_HEADERS, "X-Vapi-Secret": "expected"},
    )

    assert rejected.status_code == 200
    assert rejected.json()["accepted"] is False
    assert rejected.json()["trust_status"] == "rejected_bad_secret"
    assert accepted.status_code == 200
    assert accepted.json()["accepted"] is True
    assert accepted.json()["trust_status"] == "verified_secret"
    assert accepted.json()["provider_call_id"] == "call_123"
