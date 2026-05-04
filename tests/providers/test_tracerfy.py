from app.providers.tracerfy import TracerfyClient, build_tracerfy_request, primary_email_from_trace, primary_phone_from_trace


def test_build_tracerfy_request_uses_bearer_auth_and_v1_base_url() -> None:
    outbound = build_tracerfy_request(
        api_key="tracerfy-secret",
        method="POST",
        path="/trace/lookup/",
        payload={"address": "123 Main St", "city": "Houston", "state": "TX", "find_owner": True},
    )

    assert outbound["endpoint"] == "https://tracerfy.com/v1/api/trace/lookup/"
    assert outbound["headers"]["Authorization"] == "Bearer tracerfy-secret"
    assert outbound["headers"]["Accept"] == "application/json"
    assert outbound["headers"]["Content-Type"] == "application/json"
    assert outbound["headers"]["User-Agent"] == "Mozilla/5.0 Ares/1.0 TracerfyClient"


def test_client_builds_instant_address_lookup_payload() -> None:
    captured: list[dict] = []

    def sender(outbound_request: dict) -> dict:
        captured.append(outbound_request)
        return {"hit": False, "persons_count": 0, "credits_deducted": 0, "persons": []}

    client = TracerfyClient(api_key="trace_123", request_sender=sender)
    response = client.instant_address_lookup(
        address="123 Main St",
        city="Houston",
        state="TX",
        zip_code="77002",
        find_owner=True,
    )

    assert response["hit"] is False
    assert captured[-1]["method"] == "POST"
    assert captured[-1]["endpoint"] == "https://tracerfy.com/v1/api/trace/lookup/"
    assert captured[-1]["payload"] == {
        "address": "123 Main St",
        "city": "Houston",
        "state": "TX",
        "zip": "77002",
        "find_owner": True,
    }


def test_client_builds_apn_and_dnc_requests() -> None:
    captured: list[dict] = []

    def sender(outbound_request: dict) -> dict:
        captured.append(outbound_request)
        return {"ok": True}

    client = TracerfyClient(api_key="trace_123", request_sender=sender)

    client.instant_apn_lookup(parcel_id="1234567890123", county="Harris", state="TX")
    assert captured[-1]["endpoint"] == "https://tracerfy.com/v1/api/trace/parcel/lookup/"
    assert captured[-1]["payload"] == {"parcel_id": "1234567890123", "county": "Harris", "state": "TX"}

    client.dnc_lookup(phone="7135550100")
    assert captured[-1]["endpoint"] == "https://tracerfy.com/v1/api/dnc/lookup/"
    assert captured[-1]["payload"] == {"phone": "7135550100"}


def test_primary_contact_helpers_prefer_non_dnc_living_person_contacts() -> None:
    response = {
        "persons": [
            {"deceased": True, "phones": [{"number": "7135550000", "rank": 1}], "emails": [{"email": "dead@example.com", "rank": 1}]},
            {
                "deceased": False,
                "phones": [
                    {"number": "7135550001", "rank": 1, "dnc": True},
                    {"number": "7135550002", "rank": 2, "dnc": False},
                ],
                "emails": [{"email": "living@example.com", "rank": 1}],
            },
        ]
    }

    assert primary_phone_from_trace(response) == "7135550002"
    assert primary_email_from_trace(response) == "living@example.com"
