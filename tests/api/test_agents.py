from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_create_agent_creates_stable_id_and_initial_draft_revision(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/agents",
        json={
            "name": "Research Agent",
            "description": "Scaffold agent",
            "config": {"prompt": "Find seller opportunities"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent"]["id"].startswith("agt_")
    assert body["agent"]["active_revision_id"] is None
    assert len(body["revisions"]) == 1
    assert body["revisions"][0]["state"] == "draft"
    assert body["revisions"][0]["revision_number"] == 1


def test_create_agent_persists_provider_selection_and_capabilities(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/agents",
        json={
            "name": "Provider Agent",
            "config": {"prompt": "Choose the right model"},
            "provider_kind": "openai_compat",
            "provider_config": {"base_url": "https://example.com/v1"},
            "provider_capabilities": ["streaming", "json_schema"],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    revision = body["revisions"][0]
    assert revision["provider_kind"] == "openai_compat"
    assert revision["provider_config"] == {"base_url": "https://example.com/v1"}
    assert revision["provider_capabilities"] == ["streaming", "json_schema"]


def test_publish_draft_revision_marks_it_active_production_revision(client) -> None:
    reset_control_plane_state()

    created = client.post(
        "/agents",
        json={"name": "Research Agent", "config": {"prompt": "Find seller opportunities"}},
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]

    response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent"]["active_revision_id"] == revision_id
    revisions = {revision["id"]: revision for revision in body["revisions"]}
    assert revisions[revision_id]["state"] == "published"
    assert revisions[revision_id]["published_at"] is not None


def test_cloning_published_revision_creates_new_draft_with_copied_config(client) -> None:
    reset_control_plane_state()

    created = client.post(
        "/agents",
        json={"name": "Research Agent", "config": {"prompt": "Find seller opportunities", "tools": ["run_market_research"]}},
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    published_revision_id = created["revisions"][0]["id"]
    client.post(f"/agents/{agent_id}/revisions/{published_revision_id}/publish", headers=AUTH_HEADERS)

    response = client.post(
        f"/agents/{agent_id}/revisions/{published_revision_id}/clone",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["revisions"]) == 2
    cloned_revision = max(body["revisions"], key=lambda revision: revision["revision_number"])
    assert cloned_revision["state"] == "draft"
    assert cloned_revision["config"] == {"prompt": "Find seller opportunities", "tools": ["run_market_research"]}
    assert cloned_revision["cloned_from_revision_id"] == published_revision_id


def test_archived_revisions_remain_queryable_but_cannot_be_published_again(client) -> None:
    reset_control_plane_state()

    created = client.post(
        "/agents",
        json={"name": "Ops Agent", "config": {"prompt": "Handle launches"}},
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]

    client.post(f"/agents/{agent_id}/revisions/{revision_id}/publish", headers=AUTH_HEADERS)
    archive_response = client.post(f"/agents/{agent_id}/revisions/{revision_id}/archive", headers=AUTH_HEADERS)
    assert archive_response.status_code == 200

    get_response = client.get(f"/agents/{agent_id}", headers=AUTH_HEADERS)
    assert get_response.status_code == 200
    revisions = {revision["id"]: revision for revision in get_response.json()["revisions"]}
    assert revisions[revision_id]["state"] == "archived"

    republish_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert republish_response.status_code == 409
