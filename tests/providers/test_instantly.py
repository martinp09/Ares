from app.models.providers import ProviderTransportError
from app.providers.instantly import (
    InstantlyClient,
    build_instantly_request,
    normalize_webhook_payload,
)


def test_build_request_uses_bearer_auth() -> None:
    request = build_instantly_request(
        api_key="inst_1234567890",
        method="POST",
        path="/api/v2/leads",
        payload={"email": "lead@example.com"},
    )

    assert request["headers"]["Authorization"] == "Bearer inst_1234567890"
    assert request["endpoint"] == "https://api.instantly.ai/api/v2/leads"
    assert request["payload"] == {"email": "lead@example.com"}


def test_client_repr_redacts_api_key() -> None:
    client = InstantlyClient(api_key="instantly-super-secret-token")

    rendered = repr(client)

    assert "super-secret" not in rendered
    assert "***" in rendered


def test_normalize_webhook_payload_maps_to_canonical_event() -> None:
    normalized = normalize_webhook_payload(
        {
            "event_type": "reply_received",
            "timestamp": "2026-04-16T17:00:00Z",
            "campaign_id": "cmp_123",
            "campaign_name": "Probate Wave 1",
            "lead_email": "lead@example.com",
            "email_id": "msg_123",
            "step": 2,
        }
    )

    assert normalized["canonical_event_type"] == "lead.reply.received"
    assert normalized["lead_email"] == "lead@example.com"
    assert normalized["metadata"]["step"] == 2
    assert normalized["provider_email_id"] == "msg_123"


def test_client_retries_transport_errors_before_failing() -> None:
    attempts: list[int] = []

    def sender(_: dict) -> dict:
        attempts.append(1)
        raise ProviderTransportError("busy", status_code=503)

    client = InstantlyClient(api_key="inst_123", request_sender=sender, sleep_fn=lambda _: None)

    try:
        client.get_campaign("cmp_123")
    except ProviderTransportError as exc:
        assert exc.status_code == 503
    else:
        raise AssertionError("expected ProviderTransportError")

    assert len(attempts) == 3
