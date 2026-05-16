from fastapi.testclient import TestClient

from app.main import app
from app.models.sms_agent import SmsAgentSendResponse

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_sms_agent_send_requires_runtime_auth() -> None:
    client = TestClient(app)

    response = client.post(
        "/sms-agent/messages",
        json={"business_id": "limitless", "environment": "dev", "to": "5551234567", "body": "hi"},
    )

    assert response.status_code == 401


def test_sms_agent_process_pending_requires_runtime_auth() -> None:
    client = TestClient(app)

    response = client.post("/sms-agent/internal/process-pending", json={"limit": 10})

    assert response.status_code == 401


def test_sms_agent_process_pending_accepts_empty_body_with_runtime_auth() -> None:
    class StubSmsAgentService:
        def __init__(self) -> None:
            self.calls = []

        def process_pending(self, *, limit=None):
            self.calls.append(limit)
            return {
                "processed_count": 0,
                "sent_count": 0,
                "blocked_count": 0,
                "failed_count": 0,
            }

    from app.api import sms_agent as sms_agent_api

    stub = StubSmsAgentService()
    app.dependency_overrides[sms_agent_api.sms_agent_service_dependency] = lambda: stub
    client = TestClient(app)

    try:
        response = client.post("/sms-agent/internal/process-pending", headers=AUTH_HEADERS)
    finally:
        app.dependency_overrides.pop(sms_agent_api.sms_agent_service_dependency, None)

    assert response.status_code == 200
    assert response.json() == {
        "processed_count": 0,
        "sent_count": 0,
        "blocked_count": 0,
        "failed_count": 0,
    }
    assert stub.calls == [None]


def test_sms_agent_send_routes_to_service() -> None:
    class StubSmsAgentService:
        def __init__(self) -> None:
            self.calls = []

        def send_message(self, request):
            self.calls.append(request)
            return SmsAgentSendResponse(
                status="skipped",
                to="+15551234567",
                dry_run=True,
                log_status="skipped_dry_run",
            )

    from app.api import sms_agent as sms_agent_api

    stub = StubSmsAgentService()
    app.dependency_overrides[sms_agent_api.sms_agent_service_dependency] = lambda: stub
    client = TestClient(app)

    try:
        response = client.post(
            "/sms-agent/messages",
            json={
                "business_id": "limitless",
                "environment": "dev",
                "to": "5551234567",
                "body": "Ares SMS agent dry run",
            },
            headers=AUTH_HEADERS,
        )
    finally:
        app.dependency_overrides.pop(sms_agent_api.sms_agent_service_dependency, None)

    assert response.status_code == 201
    assert response.json() == {
        "channel": "sms",
        "provider": "textgrid",
        "status": "skipped",
        "to": "+15551234567",
        "from_identity": None,
        "message_id": None,
        "conversation_id": None,
        "provider_message_id": None,
        "dry_run": True,
        "log_status": "skipped_dry_run",
        "error_message": None,
    }
    assert stub.calls[0].body == "Ares SMS agent dry run"


def test_sms_agent_textgrid_webhook_accepts_signed_form_without_runtime_auth(monkeypatch) -> None:
    class StubInboundSmsService:
        def __init__(self) -> None:
            self.calls = []

        def handle_textgrid_webhook(self, payload, *, signature, request_url=None):
            self.calls.append((payload, signature, request_url))
            return {"status": "processed", "event_type": "message", "action": "queued"}

    from app.api import sms_agent as sms_agent_api

    stub = StubInboundSmsService()
    monkeypatch.setattr(sms_agent_api, "inbound_sms_service", stub)
    client = TestClient(app)

    response = client.post(
        "/sms-agent/webhooks/textgrid",
        data={"MessageSid": "SM123", "From": "+15551234567", "To": "+15557654321", "Body": "Hello"},
        headers={
            "X-Twilio-Signature": "twilio-signature",
            "content-type": "application/x-www-form-urlencoded",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"
    assert response.text == "<Response></Response>"
    assert stub.calls == [
        (
            {"MessageSid": "SM123", "From": "+15551234567", "To": "+15557654321", "Body": "Hello"},
            "twilio-signature",
            "http://testserver/sms-agent/webhooks/textgrid",
        )
    ]


def test_sms_agent_textgrid_webhook_alias_accepts_form_payload(monkeypatch) -> None:
    class StubInboundSmsService:
        def __init__(self) -> None:
            self.calls = []

        def handle_textgrid_webhook(self, payload, *, signature, request_url=None):
            self.calls.append((payload, signature, request_url))
            return {"status": "processed", "event_type": "status", "action": "ignore"}

    from app.api import sms_agent as sms_agent_api

    stub = StubInboundSmsService()
    monkeypatch.setattr(sms_agent_api, "inbound_sms_service", stub)
    client = TestClient(app)

    response = client.post(
        "/sms-agent/webhooks/textgrid",
        data={"MessageSid": "SM123", "MessageStatus": "delivered"},
        headers={
            **AUTH_HEADERS,
            "X-TextGrid-Signature": "textgrid-signature",
            "X-Twilio-Signature": "twilio-signature",
            "content-type": "application/x-www-form-urlencoded",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"
    assert response.headers["x-ares-sms-agent-status"] == "processed"
    assert response.text == "<Response></Response>"
    assert stub.calls[0][0] == {"MessageSid": "SM123", "MessageStatus": "delivered"}
    assert stub.calls[0][1] == "textgrid-signature"
    assert stub.calls[0][2] == "http://testserver/sms-agent/webhooks/textgrid"
