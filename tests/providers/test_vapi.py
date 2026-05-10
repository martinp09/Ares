import httpx

from app.core.config import Settings
from app.services.providers.vapi import VapiProviderClient


def test_vapi_provider_client_sends_authenticated_assistant_create() -> None:
    calls = []

    def fake_sender(method, url, *, headers, json, timeout):
        calls.append({"method": method, "url": url, "headers": headers, "json": json, "timeout": timeout})
        return httpx.Response(201, json={"id": "asst_123"}, request=httpx.Request(method, url))

    client = VapiProviderClient(
        settings=Settings(
            _env_file=None,
            vapi_api_key="vapi_test_key",
            vapi_base_url="https://api.vapi.ai",
            provider_request_timeout_seconds=7,
        ),
        http_sender=fake_sender,
    )

    response = client.create_assistant({"name": "Ares Voice Agent"})

    assert response == {"id": "asst_123"}
    assert calls == [
        {
            "method": "POST",
            "url": "https://api.vapi.ai/assistant",
            "headers": {
                "Authorization": "Bearer vapi_test_key",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            "json": {"name": "Ares Voice Agent"},
            "timeout": 7.0,
        }
    ]


def test_vapi_provider_client_requires_api_key() -> None:
    client = VapiProviderClient(settings=Settings(_env_file=None, vapi_api_key=None))

    try:
        client.create_call({"customer": {"number": "+15551234567"}})
    except RuntimeError as exc:
        assert str(exc) == "VAPI_API_KEY is required"
    else:
        raise AssertionError("Expected missing Vapi API key to raise")
