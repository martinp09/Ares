from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_audit_api_appends_events_and_returns_newest_first(client) -> None:
    reset_control_plane_state()

    first = client.post(
        "/audit",
        json={
            "event_type": "secret_created",
            "summary": "Created secret",
            "org_id": "org_limitless",
            "resource_type": "secret",
            "resource_id": "sec_1",
        },
        headers=AUTH_HEADERS,
    )
    second = client.post(
        "/audit",
        json={
            "event_type": "secret_accessed",
            "summary": "Read secret metadata",
            "org_id": "org_limitless",
            "resource_type": "secret",
            "resource_id": "sec_1",
        },
        headers=AUTH_HEADERS,
    )

    assert first.status_code == 200
    assert second.status_code == 200

    listing = client.get("/audit?org_id=org_limitless", headers=AUTH_HEADERS)
    assert listing.status_code == 200
    events = listing.json()["events"]
    assert [event["event_type"] for event in events] == ["secret_accessed", "secret_created"]
