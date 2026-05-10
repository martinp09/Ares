from app.core.config import Settings
from app.models.voice_agents import VoiceAssistantCreateRequest, VoiceOutboundCallRequest
from app.services.voice_agent_service import VoiceAgentService


class FakeVapiClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def create_assistant(self, payload: dict) -> dict:
        self.calls.append(("create_assistant", payload))
        return {"id": "asst_123"}

    def create_phone_number(self, payload: dict) -> dict:
        self.calls.append(("create_phone_number", payload))
        return {"id": "pn_123"}

    def create_call(self, payload: dict) -> dict:
        self.calls.append(("create_call", payload))
        return {"id": "call_123"}


def test_voice_assistant_dry_run_returns_vapi_payload_without_provider_call() -> None:
    fake = FakeVapiClient()
    service = VoiceAgentService(
        settings=Settings(_env_file=None, provider_live_sends_enabled=False, vapi_webhook_url="https://runtime.example.com/voice/vapi/webhook"),
        vapi_client=fake,
    )

    response = service.create_assistant(
        VoiceAssistantCreateRequest(
            name="Ares Seller Intake Voice Agent",
            first_message="Hi, this is Ares calling about your property.",
            system_prompt="Qualify the seller and hand off to Martin.",
        )
    )

    assert response.dry_run is True
    assert response.status == "skipped"
    assert response.request_payload["name"] == "Ares Seller Intake Voice Agent"
    assert response.request_payload["server"] == {"url": "https://runtime.example.com/voice/vapi/webhook"}
    assert response.request_payload["model"]["messages"][0]["content"] == "Qualify the seller and hand off to Martin."
    assert fake.calls == []


def test_voice_outbound_call_live_gate_calls_vapi_with_saved_assistant_and_number() -> None:
    fake = FakeVapiClient()
    service = VoiceAgentService(
        settings=Settings(
            _env_file=None,
            provider_live_sends_enabled=True,
            vapi_provider_live_sends_enabled=True,
            vapi_api_key="vapi_test_key",
            vapi_default_assistant_id="asst_saved",
            vapi_default_phone_number_id="pn_saved",
        ),
        vapi_client=fake,
    )

    response = service.create_outbound_call(
        VoiceOutboundCallRequest(to="555-123-4567", metadata={"lead_id": "lead_123"})
    )

    assert response.dry_run is False
    assert response.status == "queued"
    assert response.provider_id == "call_123"
    assert fake.calls == [
        (
            "create_call",
            {
                "customer": {"number": "+15551234567"},
                "metadata": {"ares_voice_agent": True, "lead_id": "lead_123"},
                "assistantId": "asst_saved",
                "phoneNumberId": "pn_saved",
            },
        )
    ]


def test_voice_webhook_assistant_request_returns_configured_assistant_id() -> None:
    service = VoiceAgentService(settings=Settings(_env_file=None, vapi_default_assistant_id="asst_saved"))

    response = service.handle_webhook({"message": {"type": "assistant-request", "call": {}}})

    assert response.assistantId == "asst_saved"


def test_voice_webhook_tool_calls_returns_vapi_results_shape() -> None:
    service = VoiceAgentService(settings=Settings(_env_file=None))

    response = service.handle_webhook(
        {
            "message": {
                "type": "tool-calls",
                "toolCallList": [{"id": "tool_1", "name": "lookupLead", "parameters": {"phone": "+15551234567"}}],
            }
        }
    )

    assert response.results == [
        {
            "name": "lookupLead",
            "toolCallId": "tool_1",
            "result": '{"status": "unsupported", "message": "Tool not wired in Ares yet"}',
        }
    ]
