import httpx

from app.core.config import Settings
from app.services.providers.hubspot import HubSpotProviderClient


def test_hubspot_provider_client_sends_authenticated_property_create() -> None:
    calls = []

    def fake_sender(method, url, *, headers, json, timeout):
        calls.append({"method": method, "url": url, "headers": headers, "json": json, "timeout": timeout})
        return httpx.Response(201, json={"name": "ares_source_lane"}, request=httpx.Request(method, url))

    client = HubSpotProviderClient(
        settings=Settings(
            _env_file=None,
            hubspot_access_token="hubspot_test_token",
            hubspot_base_url="https://api.hubapi.com",
            provider_request_timeout_seconds=7,
        ),
        http_sender=fake_sender,
    )

    response = client.create_property("deals", {"name": "ares_source_lane", "label": "Ares source lane"})

    assert response == {"name": "ares_source_lane"}
    assert calls == [
        {
            "method": "POST",
            "url": "https://api.hubapi.com/crm/v3/properties/deals",
            "headers": {
                "Authorization": "Bearer hubspot_test_token",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            "json": {"name": "ares_source_lane", "label": "Ares source lane"},
            "timeout": 7.0,
        }
    ]


def test_hubspot_provider_client_upserts_existing_property_with_patch() -> None:
    calls = []

    def fake_sender(method, url, *, headers, json, timeout):
        calls.append({"method": method, "url": url, "json": json})
        request = httpx.Request(method, url)
        if method == "POST":
            return httpx.Response(409, json={"message": "Property already exists"}, request=request)
        return httpx.Response(200, json={"name": "ares_source_lane", "updated": True}, request=request)

    client = HubSpotProviderClient(
        settings=Settings(_env_file=None, hubspot_access_token="hubspot_test_token"),
        http_sender=fake_sender,
    )

    response = client.upsert_property("deals", "ares_source_lane", {"name": "ares_source_lane", "label": "Ares source lane"})

    assert response == {"status": "updated", "property": {"name": "ares_source_lane", "updated": True}}
    assert calls == [
        {
            "method": "POST",
            "url": "https://api.hubapi.com/crm/v3/properties/deals",
            "json": {"name": "ares_source_lane", "label": "Ares source lane"},
        },
        {
            "method": "PATCH",
            "url": "https://api.hubapi.com/crm/v3/properties/deals/ares_source_lane",
            "json": {"label": "Ares source lane"},
        },
    ]


def test_hubspot_provider_client_upserts_existing_pipeline_by_label_without_duplicate_create() -> None:
    calls = []

    def fake_sender(method, url, **kwargs):
        calls.append({"method": method, "url": url, "json": kwargs.get("json")})
        request = httpx.Request(method, url)
        return httpx.Response(
            200,
            json={"results": [{"id": "pipeline_ares", "label": "Ares Acquisition Pipeline"}]},
            request=request,
        )

    client = HubSpotProviderClient(
        settings=Settings(_env_file=None, hubspot_access_token="hubspot_test_token"),
        http_sender=fake_sender,
    )

    response = client.upsert_pipeline_by_label("deals", {"label": "Ares Acquisition Pipeline", "stages": []})

    assert response == {"status": "exists", "pipeline": {"id": "pipeline_ares", "label": "Ares Acquisition Pipeline"}}
    assert calls == [
        {
            "method": "GET",
            "url": "https://api.hubapi.com/crm/v3/pipelines/deals",
            "json": None,
        }
    ]


def test_hubspot_provider_client_requires_token() -> None:
    client = HubSpotProviderClient(settings=Settings(_env_file=None, hubspot_access_token=None))

    try:
        client.create_object("contacts", {"email": "seller@example.com"})
    except RuntimeError as exc:
        assert str(exc) == "HUBSPOT_ACCESS_TOKEN or HUBSPOT_PERSONAL_KEY is required"
    else:
        raise AssertionError("Expected missing HubSpot token to raise")
