from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_rbac_api_creates_roles_grants_and_assignments_and_resolves_effective_mode(client) -> None:
    reset_control_plane_state()

    agent_response = client.post(
        "/agents",
        json={"name": "RBAC Agent", "config": {"prompt": "Follow policy"}},
        headers=AUTH_HEADERS,
    )
    assert agent_response.status_code == 200
    revision_id = agent_response.json()["revisions"][0]["id"]

    role_response = client.post(
        "/rbac/roles",
        json={"name": "operator", "description": "Approves risky actions"},
        headers=AUTH_HEADERS,
    )
    assert role_response.status_code == 200
    role_id = role_response.json()["id"]

    grant_response = client.post(
        f"/rbac/roles/{role_id}/grants",
        json={"tool_name": "publish_campaign", "mode": "always_ask"},
        headers=AUTH_HEADERS,
    )
    assert grant_response.status_code == 200
    assert grant_response.json()["mode"] == "always_ask"

    assignment_response = client.post(
        "/rbac/assignments",
        json={"agent_revision_id": revision_id, "role_id": role_id},
        headers=AUTH_HEADERS,
    )
    assert assignment_response.status_code == 200

    effective_response = client.get(
        f"/rbac/revisions/{revision_id}/effective?tool_name=publish_campaign",
        headers=AUTH_HEADERS,
    )
    assert effective_response.status_code == 200
    body = effective_response.json()
    assert body["tool_name"] == "publish_campaign"
    assert body["mode"] == "always_ask"
    assert body["source_modes"] == ["always_ask"]
