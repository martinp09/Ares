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


def test_voice_assistant_dry_run_uses_default_ares_prompt_and_tools() -> None:
    fake = FakeVapiClient()
    service = VoiceAgentService(
        settings=Settings(_env_file=None, provider_live_sends_enabled=False),
        vapi_client=fake,
    )

    response = service.create_assistant(VoiceAssistantCreateRequest())

    assert response.dry_run is True
    assert "Mission Control" in response.request_payload["model"]["messages"][0]["content"]
    assert "lease-option inbound" in response.request_payload["model"]["messages"][0]["content"]
    assert response.request_payload["model"]["tools"][0]["function"]["name"] == "search_ares_leads"
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


def test_voice_webhook_tool_call_validation_error_returns_vapi_result() -> None:
    service = VoiceAgentService(settings=Settings(_env_file=None))

    response = service.handle_webhook(
        {
            "message": {
                "type": "tool-calls",
                "toolCallList": [{"id": "tool_1", "name": "update_ares_record", "parameters": {"action": "status"}}],
            }
        }
    )

    result = __import__("json").loads(response.results[0]["result"])
    assert result == {
        "status": "error",
        "message": "recordId is required",
        "tool": "update_ares_record",
    }


def test_voice_assistant_payload_includes_ares_real_estate_tools() -> None:
    service = VoiceAgentService(settings=Settings(_env_file=None, vapi_webhook_url="https://runtime.example.com/voice/vapi/webhook"))

    payload = service.build_assistant_payload()

    tool_names = [tool["function"]["name"] for tool in payload["model"]["tools"]]
    assert tool_names == [
        "search_ares_leads",
        "get_ares_record_detail",
        "get_ares_call_script",
        "update_ares_record",
        "move_ares_opportunity_stage",
        "complete_ares_task",
        "qualify_real_estate_lead",
        "create_operator_task",
        "prepare_follow_up_summary",
        "request_human_handoff",
    ]
    assert "probate outbound" in payload["model"]["messages"][0]["content"]
    assert "lease-option inbound" in payload["model"]["messages"][0]["content"]
    assert payload["server"] == {"url": "https://runtime.example.com/voice/vapi/webhook"}


def test_voice_webhook_search_ares_leads_pulls_mission_control_records() -> None:
    class StubMissionControlService:
        def __init__(self) -> None:
            self.record_calls = []

        def get_records(self, **kwargs):
            self.record_calls.append(kwargs)
            return {
                "records": [
                    {
                        "id": "record_1",
                        "display_name": "Maria Lopez",
                        "property_address": "123 Main St",
                        "phone": "+17135550123",
                        "email": None,
                        "source": "probate_intake",
                        "record_status": "new",
                        "promotion_status": "not_promoted",
                        "source_lead_id": "lead_1",
                    },
                    {
                        "id": "record_2",
                        "display_name": "Other Owner",
                        "property_address": "500 Oak",
                        "phone": "+18175559999",
                        "email": None,
                        "source": "manual",
                        "record_status": "new",
                        "promotion_status": "not_promoted",
                    },
                ]
            }

        def get_lead_machine(self, **kwargs):
            return {"queue": {"total_lead_count": 2}, "updated_at": "2026-05-13T00:00:00Z"}

    stub = StubMissionControlService()
    service = VoiceAgentService(settings=Settings(_env_file=None), mission_control_service=stub)

    response = service.handle_webhook(
        {
            "message": {
                "type": "tool-calls",
                "toolCallList": [{"id": "tool_1", "name": "search_ares_leads", "parameters": {"phone": "713-555-0123"}}],
            }
        }
    )

    assert stub.record_calls == [{"org_id": "org_internal", "business_id": "1", "environment": "prod"}]
    result = response.results[0]
    assert result["name"] == "search_ares_leads"
    assert result["toolCallId"] == "tool_1"
    payload = __import__("json").loads(result["result"])
    assert payload["status"] == "found"
    assert payload["matches"][0]["id"] == "record_1"
    assert payload["lead_machine"]["queue"]["total_lead_count"] == 2


def test_voice_webhook_update_ares_record_calls_mission_control_status_update() -> None:
    class StubMissionControlService:
        def __init__(self) -> None:
            self.status_calls = []

        def update_record_status(self, record_id, payload, **kwargs):
            self.status_calls.append((record_id, payload, kwargs))
            return {"record": {"id": record_id, "record_status": payload.status, "display_name": "Maria Lopez"}}

    stub = StubMissionControlService()
    service = VoiceAgentService(settings=Settings(_env_file=None), mission_control_service=stub)

    response = service.handle_webhook(
        {
            "message": {
                "type": "tool-calls",
                "toolCallList": [
                    {
                        "id": "tool_1",
                        "name": "update_ares_record",
                        "parameters": {
                            "recordId": "record_1",
                            "action": "status",
                            "status": "marketable",
                            "reason": "Caller confirmed follow-up permission.",
                        },
                    }
                ],
            }
        }
    )

    record_id, request, kwargs = stub.status_calls[0]
    assert record_id == "record_1"
    assert request.status == "marketable"
    assert request.reason == "Caller confirmed follow-up permission."
    assert kwargs == {"actor_id": "vapi_voice_agent", "actor_type": "voice_agent"}
    payload = __import__("json").loads(response.results[0]["result"])
    assert payload["status"] == "updated"
    assert payload["result"]["record"]["id"] == "record_1"
