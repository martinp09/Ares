from fastapi.testclient import TestClient

from app.main import app
from app.models.voice_agents import VapiWebhookResponse, VoiceProviderActionResponse

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_voice_outbound_requires_runtime_auth() -> None:
    client = TestClient(app)

    response = client.post("/voice/calls/outbound", json={"to": "5551234567"})

    assert response.status_code == 401


def test_voice_outbound_routes_to_service() -> None:
    class StubVoiceAgentService:
        def __init__(self) -> None:
            self.calls = []

        def create_outbound_call(self, request):
            self.calls.append(request)
            return VoiceProviderActionResponse(
                action="create_outbound_call",
                status="skipped",
                dry_run=True,
                request_payload={"customer": {"number": "+15551234567"}},
            )

    from app.api import voice_agents as voice_api

    stub = StubVoiceAgentService()
    app.dependency_overrides[voice_api.voice_agent_service_dependency] = lambda: stub
    client = TestClient(app)

    try:
        response = client.post("/voice/calls/outbound", json={"to": "5551234567"}, headers=AUTH_HEADERS)
    finally:
        app.dependency_overrides.pop(voice_api.voice_agent_service_dependency, None)

    assert response.status_code == 201
    assert response.json()["action"] == "create_outbound_call"
    assert response.json()["dry_run"] is True
    assert stub.calls[0].to == "5551234567"


def test_vapi_webhook_routes_to_service() -> None:
    class StubVoiceAgentService:
        def __init__(self) -> None:
            self.calls = []

        def handle_webhook(self, payload):
            self.calls.append(payload)
            return VapiWebhookResponse(status="accepted", event_type="status-update")

    from app.api import voice_agents as voice_api

    stub = StubVoiceAgentService()
    app.dependency_overrides[voice_api.voice_agent_service_dependency] = lambda: stub
    client = TestClient(app)

    try:
        response = client.post(
            "/voice/vapi/webhook",
            json={"message": {"type": "status-update", "status": "ended"}},
            headers=AUTH_HEADERS,
        )
    finally:
        app.dependency_overrides.pop(voice_api.voice_agent_service_dependency, None)

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert stub.calls == [{"message": {"type": "status-update", "status": "ended"}}]


def test_vapi_webhook_requires_secret_when_provider_signatures_required(monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_WEBHOOK_SIGNATURES_REQUIRED", "true")
    monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "vapi_whsec_1")

    from app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    try:
        response = client.post(
            "/voice/vapi/webhook",
            json={"message": {"type": "status-update", "status": "ended"}},
            headers=AUTH_HEADERS,
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid Vapi webhook secret"


def test_vapi_webhook_accepts_configured_secret_when_required(monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_WEBHOOK_SIGNATURES_REQUIRED", "true")
    monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "vapi_whsec_1")

    from app.core.config import get_settings

    get_settings.cache_clear()
    client = TestClient(app)

    try:
        response = client.post(
            "/voice/vapi/webhook",
            json={"message": {"type": "status-update", "status": "ended"}},
            headers={**AUTH_HEADERS, "x-vapi-secret": "vapi_whsec_1"},
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["event_type"] == "status-update"
