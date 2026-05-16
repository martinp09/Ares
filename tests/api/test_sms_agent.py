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


def test_sms_agent_textgrid_webhook_alias_accepts_form_payload(monkeypatch) -> None:
    class StubInboundSmsService:
        def __init__(self) -> None:
            self.calls = []

        def handle_textgrid_webhook(self, payload, *, signature, request_url=None):
            self.calls.append((payload, signature, request_url))
            return {
                "status": "processed",
                "event_type": "status",
                "action": "ignore",
                "notification": None,
            }

    from app.api import sms_agent as sms_agent_api

    stub = StubInboundSmsService()
    monkeypatch.setattr(sms_agent_api, "inbound_sms_service", stub)
    client = TestClient(app)

    response = client.post(
        "/sms-agent/webhooks/textgrid",
        data={"MessageSid": "SM123", "MessageStatus": "delivered"},
        headers={**AUTH_HEADERS, "content-type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "processed",
        "event_type": "status",
        "action": "ignore",
        "message_id": None,
        "task_id": None,
    }
    assert stub.calls[0][0] == {"MessageSid": "SM123", "MessageStatus": "delivered"}
    assert stub.calls[0][2] == "http://testserver/sms-agent/webhooks/textgrid"


def test_sms_agent_textgrid_webhook_preserves_slack_notification(monkeypatch) -> None:
    class StubInboundSmsService:
        def handle_textgrid_webhook(self, payload, *, signature, request_url=None):
            return {
                "status": "processed",
                "event_type": "inbound_message",
                "action": "qualify",
                "message_id": "msg_123",
                "task_id": None,
                "notification": {
                    "route": "sms_agent_inbound",
                    "status": "sent",
                    "deduped": False,
                    "channel_id": "C-SMS-AGENT",
                    "dedupe_key": "sms-agent:msg_123",
                    "slack_message_ts": "1715788800.000300",
                    "error_message": None,
                },
            }

    from app.api import sms_agent as sms_agent_api

    monkeypatch.setattr(sms_agent_api, "inbound_sms_service", StubInboundSmsService())
    client = TestClient(app)

    response = client.post(
        "/sms-agent/webhooks/textgrid",
        json={"From": "+15557654321", "To": "+15551234567", "Body": "Yes"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["notification"] == {
        "route": "sms_agent_inbound",
        "status": "sent",
        "deduped": False,
        "channel_id": "C-SMS-AGENT",
        "dedupe_key": "sms-agent:msg_123",
        "slack_message_ts": "1715788800.000300",
        "error_message": None,
    }
