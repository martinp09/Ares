import json

import pytest

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.provider_links import ProviderLinksRepository
from app.models.calls import VoiceOutboundCallRequest
from app.models.providers import ProviderTransportError
from app.services.vapi_call_service import VapiCallService


class ExplodingClient:
    def create_outbound_call(self, *args, **kwargs):  # pragma: no cover - should never be called
        raise AssertionError("provider call was not allowed")


class ExplodingLinks:
    def get_by_ares_object(self, *args, **kwargs):  # pragma: no cover - should never be called
        raise AssertionError("provider link read was not allowed")

    def upsert_link(self, *args, **kwargs):  # pragma: no cover - should never be called
        raise AssertionError("provider link write was not allowed")


class FakeVapiClient:
    def __init__(self, response=None, exc=None):
        self.response = response if response is not None else {"id": "call_1"}
        self.exc = exc
        self.calls = []

    def create_outbound_call(self, payload):
        self.calls.append(payload)
        if self.exc:
            raise self.exc
        return self.response


def settings(**overrides):
    defaults = {
        "provider_live_sends_enabled": False,
        "vapi_provider_live_sends_enabled": False,
        "vapi_api_key": "",
        "vapi_private_key": "",
        "vapi_default_assistant_id": "",
        "vapi_default_phone_number_id": "",
        "provider_webhook_signatures_required": False,
        "vapi_webhook_secret": "",
        "control_plane_backend": "memory",
        "lead_machine_backend": "memory",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def live_settings(**overrides):
    defaults = {
        "provider_live_sends_enabled": True,
        "vapi_provider_live_sends_enabled": True,
        "vapi_api_key": "test-key",
        "vapi_default_assistant_id": "asst_default",
        "vapi_default_phone_number_id": "pn_default",
    }
    defaults.update(overrides)
    return settings(**defaults)


def request(**overrides) -> VoiceOutboundCallRequest:
    data = {
        "business_id": "biz",
        "environment": "dev",
        "crm_record_id": "crm_1",
        "to_number": "+171****0100",
        "customer_name": "Jane Seller",
        "metadata": {"source_lane": "probate", "custom_sensitive": "do-not-echo"},
        "sync_hash": "hash_1",
    }
    data.update(overrides)
    return VoiceOutboundCallRequest(**data)


def memory_links():
    return ProviderLinksRepository(client=InMemoryControlPlaneClient(InMemoryControlPlaneStore()), settings=live_settings(), force_memory=True)


def test_preview_builds_payload_without_provider_or_link_calls_or_token() -> None:
    service = VapiCallService(settings=settings(), client=ExplodingClient(), provider_links=ExplodingLinks())

    result = service.preview_outbound_call(request(assistant_id="asst_1", phone_number_id="pn_1"))

    assert result["dry_run"] is True
    assert result["would_call_provider"] is False
    assert result["action"] == "preview"
    assert result["payload"]["assistantId"] == "asst_1"
    assert result["payload"]["phoneNumberId"] == "pn_1"
    assert result["payload"]["customer"] == {"number": "+171****0100", "name": "Jane Seller"}
    assert result["payload"]["metadata"]["crm_record_id"] == "crm_1"
    assert result["payload"]["metadata"]["custom_sensitive"] == "do-not-echo"


def assert_live_response_payload_is_redacted(result: dict) -> None:
    serialized = json.dumps(result, sort_keys=True)
    assert result["dry_run"] is False
    assert result["payload"]["redacted"] is True
    assert result["payload"]["customer_number_present"] is True
    assert result["payload"]["customer_name_present"] is True
    assert "+171****0100" not in serialized
    assert "Jane Seller" not in serialized
    assert "probate" not in serialized
    assert "do-not-echo" not in serialized
    assert "asst_default" not in serialized
    assert "pn_default" not in serialized


@pytest.mark.parametrize(
    ("svc_settings", "approval", "req_overrides", "message"),
    [
        (live_settings(), False, {}, "operator approval"),
        (settings(vapi_provider_live_sends_enabled=True, vapi_api_key="test-key"), True, {}, "Provider live sends are disabled"),
        (settings(provider_live_sends_enabled=True, vapi_api_key="test-key"), True, {}, "Vapi live sends are disabled"),
        (settings(provider_live_sends_enabled=True, vapi_provider_live_sends_enabled=True), True, {}, "API key/private key is required"),
        (
            settings(provider_live_sends_enabled=True, vapi_provider_live_sends_enabled=True, vapi_api_key="test-key"),
            True,
            {},
            "assistant ID is required",
        ),
        (
            settings(
                provider_live_sends_enabled=True,
                vapi_provider_live_sends_enabled=True,
                vapi_api_key="test-key",
                vapi_default_assistant_id="asst_1",
            ),
            True,
            {},
            "phone number ID is required",
        ),
        (live_settings(), True, {"to_number": ""}, "to_number"),
    ],
)
def test_dispatch_preflight_gates_before_provider_or_link_calls(svc_settings, approval, req_overrides, message) -> None:
    service = VapiCallService(settings=svc_settings, client=ExplodingClient(), provider_links=ExplodingLinks())

    with pytest.raises(RuntimeError) as excinfo:
        service.dispatch_outbound_call(request(operator_approval=approval, **req_overrides))

    assert message in str(excinfo.value)


def test_dispatch_fake_success_writes_provider_link() -> None:
    links = memory_links()
    fake_client = FakeVapiClient(response={"id": "call_123"})
    service = VapiCallService(settings=live_settings(), client=fake_client, provider_links=links)

    result = service.dispatch_outbound_call(request(operator_approval=True))

    assert len(fake_client.calls) == 1
    assert fake_client.calls[0]["assistantId"] == "asst_default"
    assert fake_client.calls[0]["phoneNumberId"] == "pn_default"
    assert result["action"] == "dispatched"
    assert result["provider_call_id"] == "call_123"
    assert result["provider_link_id"]
    assert_live_response_payload_is_redacted(result)
    link = links.get_by_ares_object(
        business_id="biz",
        environment="dev",
        provider="vapi",
        ares_object_type="crm_record",
        ares_object_id="crm_1",
        provider_object_type="call",
    )
    assert link is not None
    assert link.provider_object_id == "call_123"
    assert link.sync_hash == "hash_1"


def test_dispatch_no_provider_id_submitted_unlinked() -> None:
    fake_client = FakeVapiClient(response={"status": "queued"})
    service = VapiCallService(settings=live_settings(), client=fake_client, provider_links=memory_links())

    result = service.dispatch_outbound_call(request(operator_approval=True))

    assert result["action"] == "submitted_unlinked"
    assert result["provider_link_id"] is None
    assert any("provider link was not written" in warning for warning in result["warnings"])
    assert_live_response_payload_is_redacted(result)


def test_dispatch_existing_link_skip_payload_is_redacted() -> None:
    links = memory_links()
    service = VapiCallService(settings=live_settings(), client=FakeVapiClient(response={"id": "call_existing"}), provider_links=links)

    first = service.dispatch_outbound_call(request(operator_approval=True))
    skipped = service.dispatch_outbound_call(request(operator_approval=True))

    assert first["action"] == "dispatched"
    assert skipped["action"] == "skip"
    assert skipped["provider_call_id"] == "call_existing"
    assert skipped["provider_link_id"]
    assert_live_response_payload_is_redacted(skipped)


def test_dispatch_provider_error_returns_generic_message_without_secret_text() -> None:
    svc_settings = live_settings(vapi_api_key="actual-vapi-api-key", vapi_private_key="actual-vapi-private-key")
    fake_client = FakeVapiClient(
        exc=ProviderTransportError(
            "Authorization: Bearer *** raw actual-vapi-private-key api_key=abc",
            status_code=500,
        )
    )
    service = VapiCallService(settings=svc_settings, client=fake_client, provider_links=memory_links())

    result = service.dispatch_outbound_call(request(operator_approval=True))

    serialized = json.dumps(result, sort_keys=True).lower()
    assert result["action"] == "error"
    assert result["error_message"] == "Vapi provider dispatch failed."
    assert "actual-vapi-api-key" not in serialized
    assert "actual-vapi-private-key" not in serialized
    assert "api_key=abc" not in serialized
    assert_live_response_payload_is_redacted(result)


@pytest.mark.parametrize(
    "exc",
    [
        ProviderTransportError(
            "provider rejected call for +171****0100 / +171****0199 Jane Seller "
            "asst_req pn_req vip-lane crm_sensitive opp_sensitive task_sensitive",
            status_code=502,
        ),
        RuntimeError(
            "dispatch failed: +171****0100 +171****0199 Jane Seller asst_req pn_req "
            "vip-lane crm_sensitive nested-sensitive opp_sensitive task_sensitive"
        ),
    ],
)
def test_dispatch_error_returns_generic_message_without_current_request_values(exc) -> None:
    fake_client = FakeVapiClient(exc=exc)
    service = VapiCallService(settings=live_settings(), client=fake_client, provider_links=memory_links())

    result = service.dispatch_outbound_call(
        request(
            operator_approval=True,
            to_number="+171****0100",
            from_number="+171****0199",
            customer_name="Jane Seller",
            assistant_id="asst_req",
            phone_number_id="pn_req",
            metadata={"lane": "vip-lane", "nested": {"secret": "nested-sensitive"}},
            crm_record_id="crm_sensitive",
            opportunity_id="opp_sensitive",
            task_id="task_sensitive",
        )
    )

    serialized = json.dumps(result, sort_keys=True)
    assert result["action"] == "error"
    assert result["error_message"] == "Vapi provider dispatch failed."
    for raw_value in (
        "+171****0100",
        "+171****0199",
        "Jane Seller",
        "asst_req",
        "pn_req",
        "vip-lane",
        "nested-sensitive",
        "crm_sensitive",
        "opp_sensitive",
        "task_sensitive",
    ):
        assert raw_value not in result["error_message"]
        assert raw_value not in serialized
    assert result["payload"]["redacted"] is True


def test_dispatch_transport_error_truncated_prefixes_do_not_leak_request_values() -> None:
    assistant_id = "asst_" + "A" * 80
    phone_number_id = "pn_" + "P" * 80
    to_number = "+17135550123"
    request_prefix = assistant_id[:60]
    fake_client = FakeVapiClient(
        exc=ProviderTransportError(
            f"provider rejected assistant={request_prefix} customer={to_number[:8]} phone={phone_number_id[:50]}",
            status_code=502,
        )
    )
    service = VapiCallService(settings=live_settings(), client=fake_client, provider_links=memory_links())

    result = service.dispatch_outbound_call(
        request(
            operator_approval=True,
            to_number=to_number,
            assistant_id=assistant_id,
            phone_number_id=phone_number_id,
            metadata={"long_value": "metadata-" + "M" * 80},
        )
    )

    serialized = json.dumps(result, sort_keys=True)
    assert result["action"] == "error"
    assert result["error_message"] == "Vapi provider dispatch failed."
    for leaked_fragment in (request_prefix, to_number[:8], phone_number_id[:50], "metadata-" + "M" * 20):
        assert leaked_fragment not in serialized
    assert result["payload"]["redacted"] is True


def test_webhook_accepts_when_signatures_not_required() -> None:
    result = VapiCallService(settings=settings()).handle_webhook(
        {"type": "call-ended", "call": {"id": "call_123", "status": "ended"}},
        {},
    )

    assert result["accepted"] is True
    assert result["trust_status"] == "unverified_accepted"
    assert result["provider_call_id"] == "call_123"


def test_webhook_rejects_missing_or_wrong_secret_when_required() -> None:
    service = VapiCallService(settings=settings(provider_webhook_signatures_required=True, vapi_webhook_secret="expected"))

    missing = service.handle_webhook({"type": "call-ended"}, {})
    wrong = service.handle_webhook({"type": "call-ended"}, {"X-Vapi-Secret": "wrong"})
    good = service.handle_webhook({"type": "call-ended", "call": {"id": "call_123"}}, {"X-Vapi-Secret": "expected"})

    assert missing["accepted"] is False
    assert wrong["accepted"] is False
    assert good["accepted"] is True
    assert good["trust_status"] == "verified_secret"
