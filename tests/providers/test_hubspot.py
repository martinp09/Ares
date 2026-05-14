from io import BytesIO
from urllib import error

import pytest

from app.core.config import Settings
from app.models.providers import ProviderTransportError
from app.providers.hubspot import HubSpotClient, build_hubspot_request
from app.services.provider_retry_service import ProviderRetryService


def test_build_hubspot_request_uses_bearer_auth_and_json_headers() -> None:
    outbound = build_hubspot_request(
        access_token="hubspot-secret",
        method="POST",
        path="/crm/v3/objects/contacts",
        payload={"properties": {"email": "seller@example.com"}},
        query={"archived": False},
    )

    assert outbound["method"] == "POST"
    assert outbound["endpoint"] == "https://api.hubapi.com/crm/v3/objects/contacts?archived=False"
    assert outbound["headers"]["Authorization"] == "Bearer hubspot-secret"
    assert outbound["headers"]["Accept"] == "application/json"
    assert outbound["headers"]["Content-Type"] == "application/json"
    assert outbound["headers"]["User-Agent"] == "Mozilla/5.0 Ares/1.0 HubSpotClient"
    assert outbound["payload"] == {"properties": {"email": "seller@example.com"}}


def test_hubspot_client_builds_read_and_write_requests_with_injected_sender() -> None:
    captured: list[dict] = []

    def sender(outbound_request: dict) -> dict:
        captured.append(outbound_request)
        return {"ok": True}

    client = HubSpotClient(access_token="hub_123", request_sender=sender)

    assert client.list_owners(limit=10) == {"ok": True}
    assert captured[-1]["method"] == "GET"
    assert captured[-1]["endpoint"] == "https://api.hubapi.com/crm/v3/owners?limit=10"

    client.create_object("contacts", {"properties": {"email": "seller@example.com"}})
    assert captured[-1]["method"] == "POST"
    assert captured[-1]["endpoint"] == "https://api.hubapi.com/crm/v3/objects/contacts"
    assert captured[-1]["payload"] == {"properties": {"email": "seller@example.com"}}

    client.update_object("contacts", "123", {"properties": {"phone": "7135550100"}})
    assert captured[-1]["method"] == "PATCH"
    assert captured[-1]["endpoint"] == "https://api.hubapi.com/crm/v3/objects/contacts/123"
    assert captured[-1]["payload"] == {"properties": {"phone": "7135550100"}}

    client.list_property_groups("deals")
    assert captured[-1]["method"] == "GET"
    assert captured[-1]["endpoint"] == "https://api.hubapi.com/crm/v3/properties/deals/groups"

    client.create_pipeline_stage("deals", "pipeline_123", {"label": "New Lead"})
    assert captured[-1]["method"] == "POST"
    assert captured[-1]["endpoint"] == "https://api.hubapi.com/crm/v3/pipelines/deals/pipeline_123/stages"
    assert captured[-1]["payload"] == {"label": "New Lead"}


def test_hubspot_client_retries_sanitized_transport_errors_without_response_body_kwarg() -> None:
    calls = 0

    def sender(_: dict) -> dict:
        nonlocal calls
        calls += 1
        raise ValueError("boom")

    client = HubSpotClient(access_token="hub_123", request_sender=sender)

    with pytest.raises(ProviderTransportError, match="HubSpot transport failed"):
        client.list_pipelines()

    assert calls == 3


def test_hubspot_client_sanitizes_unexpected_sender_exception_message() -> None:
    access_token = "pat-na1-secret-token"

    def sender(outbound_request: dict) -> dict:
        raise ValueError(
            "boom "
            + access_token
            + " "
            + outbound_request["headers"]["Authorization"]
            + " raw provider body"
        )

    client = HubSpotClient(
        access_token=access_token,
        request_sender=sender,
        retry_service=ProviderRetryService(Settings(provider_request_max_retries=0)),
    )

    with pytest.raises(ProviderTransportError) as exc_info:
        client.create_object("contacts", {"properties": {"email": "seller@example.com"}})

    message = str(exc_info.value)
    assert "HubSpot transport failed for POST /crm/v3/objects/contacts" in message
    assert "ValueError" in message
    assert access_token not in message
    assert "Authorization" not in message
    assert "Bearer" not in message
    assert "raw provider body" not in message
    assert exc_info.value.headers == {}


def test_default_request_sender_sanitizes_http_error_body_and_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    raw_body = b'{"message":"invalid token pat-na1-secret-token","category":"VALIDATION_ERROR"}'

    def raise_http_error(*_: object, **__: object) -> None:
        raise error.HTTPError(
            url="https://api.hubapi.com/crm/v3/objects/contacts",
            code=400,
            msg="Bad Request",
            hdrs={
                "Authorization": "Bearer pat-na1-secret-token",
                "Content-Type": "application/json",
                "Set-Cookie": "session=pat-na1-secret-token",
                "Retry-After": "2",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Token": "pat-na1-secret-token",
            },
            fp=BytesIO(raw_body),
        )

    monkeypatch.setattr("app.providers.hubspot.request.urlopen", raise_http_error)
    client = HubSpotClient(
        access_token="pat-na1-secret-token",
        retry_service=ProviderRetryService(Settings(provider_request_max_retries=0)),
    )

    with pytest.raises(ProviderTransportError) as exc_info:
        client.create_object("contacts", {"properties": {"email": "seller@example.com"}})

    message = str(exc_info.value)
    assert message == "HubSpot transport failed for POST /crm/v3/objects/contacts; status=400 Bad Request"
    assert "pat-na1-secret-token" not in message
    assert "Authorization" not in message
    assert "Bearer" not in message
    assert "invalid token" not in message
    assert "VALIDATION_ERROR" not in message
    assert exc_info.value.headers == {"Retry-After": "2", "X-RateLimit-Remaining": "0"}
    assert "Authorization" not in exc_info.value.headers
    assert "Content-Type" not in exc_info.value.headers
    assert "Set-Cookie" not in exc_info.value.headers
    assert "X-RateLimit-Token" not in exc_info.value.headers


def test_hubspot_client_sanitizes_injected_provider_transport_error_headers_and_message() -> None:
    def sender(_: dict) -> dict:
        raise ProviderTransportError(
            "raw bearer leaked Bearer pat-na1-secret-token provider body",
            status_code=429,
            headers={
                "Authorization": "Bearer pat-na1-secret-token",
                "Set-Cookie": "session=secret-token",
                "Retry-After": "0",
                "X-RateLimit-Max": "100",
                "X-RateLimit-Token": "secret-token",
            },
        )

    client = HubSpotClient(
        access_token="pat-na1-secret-token",
        request_sender=sender,
        retry_service=ProviderRetryService(Settings(provider_request_max_retries=0)),
    )

    with pytest.raises(ProviderTransportError) as exc_info:
        client.list_owners()

    message = str(exc_info.value)
    assert message == "HubSpot transport failed for GET /crm/v3/owners; status=429 Too Many Requests"
    assert "pat-na1-secret-token" not in message
    assert "Bearer" not in message
    assert "provider body" not in message
    assert exc_info.value.headers == {"Retry-After": "0", "X-RateLimit-Max": "100"}
    assert "Authorization" not in exc_info.value.headers
    assert "Set-Cookie" not in exc_info.value.headers
    assert "X-RateLimit-Token" not in exc_info.value.headers


def test_hubspot_client_still_retries_with_sanitized_retry_after_header() -> None:
    calls = 0
    sleeps: list[float] = []

    def sender(_: dict) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ProviderTransportError(
                "rate limited with Bearer pat-na1-secret-token",
                status_code=429,
                headers={"Retry-After": "0", "Authorization": "Bearer pat-na1-secret-token"},
            )
        return {"ok": True}

    client = HubSpotClient(
        access_token="pat-na1-secret-token",
        request_sender=sender,
        retry_service=ProviderRetryService(Settings(provider_request_max_retries=1), sleep_fn=sleeps.append),
    )

    assert client.list_owners() == {"ok": True}
    assert calls == 2
    assert sleeps == []


def test_hubspot_client_honors_lowercase_retry_after_header_for_delay() -> None:
    calls = 0
    sleeps: list[float] = []

    def sender(_: dict) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ProviderTransportError(
                "rate limited",
                status_code=429,
                headers={"retry-after": "1.5", "Authorization": "Bearer pat-na1-secret-token"},
            )
        return {"ok": True}

    client = HubSpotClient(
        access_token="pat-na1-secret-token",
        request_sender=sender,
        retry_service=ProviderRetryService(Settings(provider_request_max_retries=1), sleep_fn=sleeps.append),
    )

    assert client.list_owners() == {"ok": True}
    assert calls == 2
    assert sleeps == [1.5]
