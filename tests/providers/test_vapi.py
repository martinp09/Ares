import pytest

from app.models.providers import ProviderTransportError
from app.providers.vapi import (
    VapiClient,
    build_vapi_request,
    normalize_vapi_webhook_payload,
    verify_vapi_webhook_secret,
)


def test_build_request_uses_bearer_auth_and_json_headers() -> None:
    request = build_vapi_request(api_key="vapi_key_123", method="POST", path="/call", payload={"assistantId": "asst_1"})

    assert request["headers"]["Authorization"] == "Bearer vapi_key_123"
    assert request["headers"]["Accept"] == "application/json"
    assert request["headers"]["Content-Type"] == "application/json"
    assert request["headers"]["User-Agent"] == "Mozilla/5.0 Ares/1.0 VapiClient"
    assert request["endpoint"] == "https://api.vapi.ai/call"
    assert request["payload"] == {"assistantId": "asst_1"}


def test_client_create_call_uses_fake_sender_and_expected_endpoint() -> None:
    captured: list[dict] = []

    def sender(outbound_request: dict) -> dict:
        captured.append(outbound_request)
        return {"id": "call_123"}

    client = VapiClient(api_key="vapi_key_123", request_sender=sender)

    assert client.create_outbound_call({"assistantId": "asst_1"}) == {"id": "call_123"}
    assert captured[-1]["method"] == "POST"
    assert captured[-1]["endpoint"] == "https://api.vapi.ai/call"
    assert captured[-1]["payload"] == {"assistantId": "asst_1"}


def test_client_repr_redacts_key() -> None:
    rendered = repr(VapiClient(api_key="vapi-super-secret-token"))

    assert "super-secret" not in rendered
    assert "***" in rendered


def test_transport_error_sanitizes_secret_text_and_headers() -> None:
    configured_vapi_key = "vapi_configured_api_key_123"
    configured_private_key = "vapi_configured_private_key_456"

    def sender(_: dict) -> dict:
        raise ProviderTransportError(
            f"Authorization: Bearer {configured_vapi_key} body secret=abc private_key={configured_private_key}",
            status_code=503,
            headers={"Retry-After": "2", "Authorization": f"Bearer {configured_vapi_key}", "X-Vapi-Key": configured_private_key},
        )

    client = VapiClient(api_key=configured_vapi_key, request_sender=sender)

    with pytest.raises(ProviderTransportError) as excinfo:
        client.list_assistants()

    message = str(excinfo.value).lower()
    assert "vapi-secret-token" not in message
    assert "secret=abc" not in message
    assert configured_vapi_key not in str(excinfo.value)
    assert configured_private_key not in str(excinfo.value)
    assert configured_vapi_key not in str(excinfo.value.headers)
    assert configured_private_key not in str(excinfo.value.headers)
    assert excinfo.value.headers == {"Retry-After": "2"}


def test_verify_vapi_webhook_secret_constant_time_helper() -> None:
    assert verify_vapi_webhook_secret("expected", "expected") is True
    assert verify_vapi_webhook_secret("expected", "wrong") is False
    assert verify_vapi_webhook_secret("expected", None) is False


def test_normalize_webhook_payload_maps_call_event_summary() -> None:
    normalized = normalize_vapi_webhook_payload(
        {
            "type": "call-ended",
            "timestamp": "2026-05-14T01:00:00Z",
            "call": {"id": "call_123", "status": "ended", "recordingUrl": "https://example.test/r.mp3"},
            "artifact": {"transcript": "hello"},
            "analysis": {"summary": "seller wants callback"},
        }
    )

    assert normalized["event_type"] == "call-ended"
    assert normalized["provider_call_id"] == "call_123"
    assert normalized["status"] == "ended"
    assert normalized["transcript"] == "hello"
    assert normalized["summary"] == "seller wants callback"
    assert normalized["recording_url"] == "https://example.test/r.mp3"
    assert normalized["raw_payload"]["call_id_present"] is True
