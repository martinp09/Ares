import base64
import hashlib
import hmac

from app.providers.textgrid import (
    build_outbound_sms_request,
    normalize_incoming_webhook,
    verify_webhook_signature,
)


def _twilio_style_signature(secret: str, url: str, payload: dict[str, str]) -> str:
    data = url + "".join(str(payload[key]) for key in sorted(payload))
    digest = hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def test_textgrid_outbound_request_shape_and_auth() -> None:
    request = build_outbound_sms_request(
        account_sid="AC123",
        auth_token="token-123",
        from_number="+15551231234",
        to_number="+15557654321",
        body="Hello from Hermes",
        base_url="https://api.textgrid.com/",
        status_callback_url="https://runtime.example.com/webhooks/textgrid/status",
    )

    assert request["endpoint"] == "https://api.textgrid.com/2010-04-01/Accounts/AC123/Messages.json"
    assert request["payload"] == {
        "Body": "Hello from Hermes",
        "From": "+15551231234",
        "StatusCallback": "https://runtime.example.com/webhooks/textgrid/status",
        "To": "+15557654321",
    }

    expected = base64.b64encode(b"AC123:token-123").decode("utf-8")
    assert request["headers"]["Authorization"] == f"Basic {expected}"
    assert request["headers"]["Content-Type"] == "application/x-www-form-urlencoded"


def test_textgrid_webhook_signature_validation() -> None:
    url = "https://runtime.example.com/marketing/webhooks/textgrid"
    payload = {"Body": "Yes", "From": "+15551231234", "MessageSid": "SM123"}
    signature = _twilio_style_signature("whsec_123", url, payload)

    assert verify_webhook_signature(
        secret="whsec_123",
        signature=signature,
        request_url=url,
        payload=payload,
    )
    assert not verify_webhook_signature(
        secret="whsec_123",
        signature="invalid",
        request_url=url,
        payload=payload,
    )


def test_textgrid_webhook_payload_normalization() -> None:
    inbound = normalize_incoming_webhook(
        {"Body": "Still interested", "From": "+15551231234", "MessageSid": "SM100", "To": "+15550990000"}
    )
    assert inbound == {
        "content": "Still interested",
        "external_id": "SM100",
        "from": "+15551231234",
        "metadata": {"provider": "textgrid"},
        "status": "read",
        "to": "+15550990000",
        "type": "message.inbound",
    }

    status = normalize_incoming_webhook({"MessageSid": "SM100", "MessageStatus": "undelivered"})
    assert status["type"] == "message.status"
    assert status["status"] == "failed"
