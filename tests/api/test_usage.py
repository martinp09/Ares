from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_usage_api_aggregates_counts_by_kind_and_agent(client) -> None:
    reset_control_plane_state()

    first = client.post(
        "/usage",
        json={
            "kind": "run",
            "org_id": "org_limitless",
            "agent_id": "agt_1",
            "agent_revision_id": "rev_1",
            "count": 1,
        },
        headers=AUTH_HEADERS,
    )
    second = client.post(
        "/usage",
        json={
            "kind": "tool_call",
            "org_id": "org_limitless",
            "agent_id": "agt_1",
            "agent_revision_id": "rev_1",
            "count": 3,
            "source_kind": "trigger_dev",
        },
        headers=AUTH_HEADERS,
    )
    third = client.post(
        "/usage",
        json={
            "kind": "provider_call",
            "org_id": "org_limitless",
            "agent_id": "agt_1",
            "agent_revision_id": "rev_1",
            "count": 2,
            "source_kind": "anthropic",
        },
        headers=AUTH_HEADERS,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200

    listing = client.get("/usage?org_id=org_limitless&agent_id=agt_1", headers=AUTH_HEADERS)
    assert listing.status_code == 200
    body = listing.json()
    assert body["summary"]["total_count"] == 6
    assert body["summary"]["by_kind"] == {"provider_call": 2, "run": 1, "tool_call": 3}
    assert body["agent_id"] == "agt_1"
