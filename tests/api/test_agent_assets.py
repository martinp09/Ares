from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def create_agent(client) -> tuple[str, str, dict]:
    response = client.post(
        "/agents",
        json={"name": "Asset Agent", "config": {"prompt": "Operate the inbox"}},
        headers=AUTH_HEADERS,
    )
    body = response.json()
    return body["agent"]["id"], body["revisions"][0]["id"], body


def test_creating_unbound_asset_stores_connect_later_true(client) -> None:
    reset_control_plane_state()
    agent_id, _, _ = create_agent(client)

    response = client.post(
        "/agent-assets",
        json={
            "agent_id": agent_id,
            "asset_type": "calendar",
            "label": "Primary Booking Calendar",
            "metadata": {"provider": "cal.com"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["connect_later"] is True
    assert body["status"] == "unbound"


def test_binding_connect_later_asset_updates_only_asset_record_not_agent_revision(client) -> None:
    reset_control_plane_state()
    agent_id, revision_id, agent_body = create_agent(client)

    asset = client.post(
        "/agent-assets",
        json={
            "agent_id": agent_id,
            "asset_type": "inbox",
            "label": "Leads Inbox",
            "metadata": {"provider": "gmail"},
        },
        headers=AUTH_HEADERS,
    ).json()

    bind_response = client.post(
        f"/agent-assets/{asset['id']}/bind",
        json={"binding_reference": "inbox_123", "metadata": {"address": "ops@example.com"}},
        headers=AUTH_HEADERS,
    )
    agent_after = client.get(f"/agents/{agent_id}", headers=AUTH_HEADERS).json()
    revision_before = next(revision for revision in agent_body["revisions"] if revision["id"] == revision_id)
    revision_after = next(revision for revision in agent_after["revisions"] if revision["id"] == revision_id)

    assert bind_response.status_code == 200
    assert bind_response.json()["connect_later"] is False
    assert bind_response.json()["binding_reference"] == "inbox_123"
    assert revision_after["config"] == revision_before["config"]


def test_asset_types_outside_operational_scope_are_rejected(client) -> None:
    reset_control_plane_state()
    agent_id, _, _ = create_agent(client)

    response = client.post(
        "/agent-assets",
        json={
            "agent_id": agent_id,
            "asset_type": "landing_page",
            "label": "Out of Scope",
            "metadata": {},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
