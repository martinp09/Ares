from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_upserting_permissions_persists_explicit_tool_policy(client) -> None:
    reset_control_plane_state()

    agent = client.post(
        "/agents",
        json={"name": "Permission Agent", "config": {"prompt": "Be careful"}},
        headers=AUTH_HEADERS,
    ).json()
    revision_id = agent["revisions"][0]["id"]

    first = client.post(
        "/permissions",
        json={
            "agent_revision_id": revision_id,
            "tool_name": "run_market_research",
            "mode": "always_ask",
        },
        headers=AUTH_HEADERS,
    )
    second = client.post(
        "/permissions",
        json={
            "agent_revision_id": revision_id,
            "tool_name": "run_market_research",
            "mode": "forbidden",
        },
        headers=AUTH_HEADERS,
    )
    listed = client.get(f"/permissions/{revision_id}", headers=AUTH_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["mode"] == "forbidden"
    permissions = listed.json()["permissions"]
    assert len(permissions) == 1
    assert permissions[0]["tool_name"] == "run_market_research"
    assert permissions[0]["mode"] == "forbidden"
