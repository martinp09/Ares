from app.core.config import get_settings
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, org_id: str, actor_id: str, actor_type: str = "user") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def create_agent(client, *, headers: dict[str, str], name: str, compatibility_metadata: dict | None = None) -> tuple[str, str]:
    payload = {
        "name": name,
        "description": f"{name} description",
        "visibility": "private_catalog",
        "config": {"prompt": f"{name} prompt"},
        "release_channel": "dogfood",
    }
    if compatibility_metadata is not None:
        payload["compatibility_metadata"] = compatibility_metadata
    response = client.post("/agents", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    return body["agent"]["id"], body["revisions"][0]["id"]


def test_catalog_api_creates_entry_from_agent_revision_and_scopes_to_actor_org(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")
    agent_id, revision_id = create_agent(
        client,
        headers=alpha_headers,
        name="Seller Ops Agent",
        compatibility_metadata={"requires_secrets": ["resend_api_key"]},
    )

    create_response = client.post(
        "/catalog",
        json={
            "agent_id": agent_id,
            "agent_revision_id": revision_id,
            "slug": "seller-ops",
            "name": "Seller Ops",
            "summary": "Internal seller ops package",
            "description": "Installable seller ops agent",
        },
        headers=alpha_headers,
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["org_id"] == "org_alpha"
    assert created["agent_id"] == agent_id
    assert created["agent_revision_id"] == revision_id
    assert created["slug"] == "seller-ops"
    assert created["host_adapter_kind"] == "trigger_dev"
    assert created["provider_kind"] == "anthropic"
    assert created["visibility"] == "private_catalog"
    assert created["marketplace_publication_enabled"] is False
    assert created["release_channel"] == "dogfood"
    assert created["required_skill_ids"] == []
    assert created["required_secret_names"] == ["resend_api_key"]

    alpha_list = client.get("/catalog", headers=alpha_headers)
    beta_list = client.get("/catalog", headers=beta_headers)
    assert alpha_list.status_code == 200
    assert beta_list.status_code == 200
    assert [entry["id"] for entry in alpha_list.json()["entries"]] == [created["id"]]
    assert beta_list.json()["entries"] == []
    assert client.get(f"/catalog/{created['id']}", headers=beta_headers).status_code == 404


def test_catalog_api_exposes_marketplace_candidate_visibility_without_enabling_public_launch(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    agent_id, revision_id = create_agent(client, headers=alpha_headers, name="Candidate Agent")

    update_visibility = client.post(
        "/agents",
        json={
            "name": "Candidate Agent",
            "slug": "candidate-agent",
            "description": "Marketplace candidate metadata only",
            "visibility": "marketplace_candidate",
            "config": {"prompt": "Candidate prompt"},
            "release_channel": "dogfood",
        },
        headers=alpha_headers,
    )
    assert update_visibility.status_code == 200
    candidate_agent_id = update_visibility.json()["agent"]["id"]
    candidate_revision_id = update_visibility.json()["revisions"][0]["id"]

    create_response = client.post(
        "/catalog",
        json={
            "agent_id": candidate_agent_id,
            "agent_revision_id": candidate_revision_id,
            "slug": "candidate-agent",
            "name": "Candidate Agent",
            "summary": "Candidate visibility only",
        },
        headers=alpha_headers,
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["visibility"] == "marketplace_candidate"
    assert created["marketplace_publication_enabled"] is False


def test_catalog_api_reports_marketplace_published_visibility_without_claiming_public_launch_when_flag_is_disabled(client, monkeypatch) -> None:
    reset_control_plane_state()
    monkeypatch.setenv("MARKETPLACE_PUBLISH_ENABLED", "true")
    get_settings.cache_clear()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    agent_response = client.post(
        "/agents",
        json={
            "name": "Marketplace Published Agent",
            "slug": "marketplace-published-agent",
            "description": "Published metadata only",
            "visibility": "marketplace_published",
            "config": {"prompt": "Published prompt"},
            "release_channel": "dogfood",
        },
        headers=alpha_headers,
    )
    assert agent_response.status_code == 200
    body = agent_response.json()
    agent_id = body["agent"]["id"]
    revision_id = body["revisions"][0]["id"]

    create_response = client.post(
        "/catalog",
        json={
            "agent_id": agent_id,
            "agent_revision_id": revision_id,
            "slug": "marketplace-published-agent",
            "name": "Marketplace Published Agent",
            "summary": "Published metadata only",
        },
        headers=alpha_headers,
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["visibility"] == "marketplace_published"
    assert created["marketplace_publication_enabled"] is True

    monkeypatch.setenv("MARKETPLACE_PUBLISH_ENABLED", "false")
    get_settings.cache_clear()

    fetched = client.get(f"/catalog/{created['id']}", headers=alpha_headers)
    assert fetched.status_code == 200
    fetched_body = fetched.json()
    assert fetched_body["visibility"] == "marketplace_published"
    assert fetched_body["marketplace_publication_enabled"] is False


def test_catalog_api_rejects_cross_org_agent_revisions(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")
    agent_id, revision_id = create_agent(client, headers=alpha_headers, name="Alpha Agent")

    response = client.post(
        "/catalog",
        json={
            "agent_id": agent_id,
            "agent_revision_id": revision_id,
            "slug": "alpha-agent",
            "name": "Alpha Agent",
            "summary": "Should not leak across orgs",
        },
        headers=beta_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent revision not found"
