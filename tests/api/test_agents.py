from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, org_id: str, actor_id: str, actor_type: str = "user") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


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
    assert body["agent"]["slug"] == "research-agent"
    assert body["agent"]["visibility"] == "internal"
    assert body["agent"]["lifecycle_status"] == "draft"
    assert body["agent"]["packaging_metadata"] == {}
    assert len(body["revisions"]) == 1
    assert body["revisions"][0]["state"] == "draft"
    assert body["revisions"][0]["revision_number"] == 1


def test_create_agent_rejects_non_draft_lifecycle_status(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/agents",
        json={
            "name": "Broken Lifecycle Agent",
            "lifecycle_status": "active",
            "config": {"prompt": "Should not bypass publish"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("lifecycle_status='draft'" in item["msg"] for item in detail)


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


def test_create_agent_persists_host_adapter_kind_and_skill_binding(client) -> None:
    reset_control_plane_state()

    skill_response = client.post(
        "/skills",
        json={
            "name": "lead_triage",
            "description": "Score inbound leads",
            "required_tools": ["run_market_research"],
        },
        headers=AUTH_HEADERS,
    )
    skill_id = skill_response.json()["id"]

    response = client.post(
        "/agents",
        json={
            "name": "Adapter Agent",
            "config": {"prompt": "Dispatch using codex seam"},
            "host_adapter_kind": "codex",
            "host_adapter_config": {"queue": "priority"},
            "skill_ids": [skill_id],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    revision = body["revisions"][0]
    assert revision["host_adapter_kind"] == "codex"
    assert revision["host_adapter_config"] == {"queue": "priority"}
    assert revision["skill_ids"] == [skill_id]


def test_create_agent_rejects_unknown_skill_ids(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/agents",
        json={
            "name": "Broken Agent",
            "config": {"prompt": "Do not bind missing skills"},
            "skill_ids": ["skl_missing"],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "Unknown skill ids" in response.json()["detail"]


def test_agent_product_metadata_round_trips_through_create_get_publish_and_clone(client) -> None:
    reset_control_plane_state()

    create_response = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "prod",
            "name": "Seller Ops Agent",
            "slug": "seller-ops-agent",
            "description": "Operator-facing managed agent",
            "visibility": "private_catalog",
            "lifecycle_status": "draft",
            "packaging_metadata": {
                "category": "operations",
                "channels": ["email", "sms"],
            },
            "config": {"prompt": "Handle seller ops workflows"},
            "input_schema": {
                "type": "object",
                "properties": {"lead_id": {"type": "string"}},
                "required": ["lead_id"],
            },
            "output_schema": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
            "release_notes": "Initial seller-ops packaging.",
            "compatibility_metadata": {
                "host_adapters": ["trigger_dev"],
                "requires_secrets": ["resend_api_key"],
            },
        },
        headers=AUTH_HEADERS,
    )

    assert create_response.status_code == 200
    created = create_response.json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]

    assert created["agent"] == {
        "id": agent_id,
        "org_id": "org_internal",
        "business_id": "limitless",
        "environment": "prod",
        "name": "Seller Ops Agent",
        "slug": "seller-ops-agent",
        "description": "Operator-facing managed agent",
        "visibility": "private_catalog",
        "lifecycle_status": "draft",
        "packaging_metadata": {
            "category": "operations",
            "channels": ["email", "sms"],
        },
        "active_revision_id": None,
        "created_at": created["agent"]["created_at"],
        "updated_at": created["agent"]["updated_at"],
    }
    assert created["revisions"][0]["input_schema"] == {
        "type": "object",
        "properties": {"lead_id": {"type": "string"}},
        "required": ["lead_id"],
    }
    assert created["revisions"][0]["output_schema"] == {
        "type": "object",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
    }
    assert created["revisions"][0]["release_notes"] == "Initial seller-ops packaging."
    assert created["revisions"][0]["compatibility_metadata"] == {
        "host_adapters": ["trigger_dev"],
        "requires_secrets": ["resend_api_key"],
    }

    get_response = client.get(f"/agents/{agent_id}", headers=AUTH_HEADERS)
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["agent"]["slug"] == "seller-ops-agent"
    assert fetched["agent"]["visibility"] == "private_catalog"
    assert fetched["agent"]["lifecycle_status"] == "draft"
    assert fetched["agent"]["packaging_metadata"] == {
        "category": "operations",
        "channels": ["email", "sms"],
    }
    assert fetched["revisions"][0]["input_schema"] == created["revisions"][0]["input_schema"]
    assert fetched["revisions"][0]["output_schema"] == created["revisions"][0]["output_schema"]
    assert fetched["revisions"][0]["release_notes"] == "Initial seller-ops packaging."
    assert fetched["revisions"][0]["compatibility_metadata"] == {
        "host_adapters": ["trigger_dev"],
        "requires_secrets": ["resend_api_key"],
    }

    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200
    published = publish_response.json()
    assert published["agent"]["slug"] == "seller-ops-agent"
    assert published["agent"]["visibility"] == "private_catalog"
    assert published["agent"]["lifecycle_status"] == "active"
    published_revision = next(revision for revision in published["revisions"] if revision["id"] == revision_id)
    assert published_revision["input_schema"] == created["revisions"][0]["input_schema"]
    assert published_revision["output_schema"] == created["revisions"][0]["output_schema"]
    assert published_revision["release_notes"] == "Initial seller-ops packaging."
    assert published_revision["compatibility_metadata"] == {
        "host_adapters": ["trigger_dev"],
        "requires_secrets": ["resend_api_key"],
    }

    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/clone",
        headers=AUTH_HEADERS,
    )
    assert clone_response.status_code == 200
    cloned = clone_response.json()
    cloned_revision = max(cloned["revisions"], key=lambda revision: revision["revision_number"])
    assert cloned_revision["state"] == "draft"
    assert cloned_revision["input_schema"] == created["revisions"][0]["input_schema"]
    assert cloned_revision["output_schema"] == created["revisions"][0]["output_schema"]
    assert cloned_revision["release_notes"] == "Initial seller-ops packaging."
    assert cloned_revision["compatibility_metadata"] == {
        "host_adapters": ["trigger_dev"],
        "requires_secrets": ["resend_api_key"],
    }
    assert cloned_revision["cloned_from_revision_id"] == revision_id


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
    assert body["agent"]["lifecycle_status"] == "active"
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
    assert cloned_revision["input_schema"] == {}
    assert cloned_revision["output_schema"] == {}
    assert cloned_revision["release_notes"] is None
    assert cloned_revision["compatibility_metadata"] == {}
    assert cloned_revision["cloned_from_revision_id"] == published_revision_id


def test_archiving_only_draft_revision_updates_agent_lifecycle(client) -> None:
    reset_control_plane_state()

    created = client.post(
        "/agents",
        json={"name": "Draft Only Agent", "config": {"prompt": "Archive me cleanly"}},
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    original_updated_at = created["agent"]["updated_at"]

    archive_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/archive",
        headers=AUTH_HEADERS,
    )

    assert archive_response.status_code == 200
    body = archive_response.json()
    revisions = {revision["id"]: revision for revision in body["revisions"]}
    assert body["agent"]["active_revision_id"] is None
    assert body["agent"]["lifecycle_status"] == "archived"
    assert body["agent"]["updated_at"] != original_updated_at
    assert revisions[revision_id]["state"] == "archived"


def test_cloning_archived_revision_reopens_agent_in_draft_state(client) -> None:
    reset_control_plane_state()

    created = client.post(
        "/agents",
        json={"name": "Archived Clone Agent", "config": {"prompt": "Let me reopen"}},
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]

    client.post(f"/agents/{agent_id}/revisions/{revision_id}/archive", headers=AUTH_HEADERS)
    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/clone",
        headers=AUTH_HEADERS,
    )

    assert clone_response.status_code == 200
    body = clone_response.json()
    cloned_revision = max(body["revisions"], key=lambda revision: revision["revision_number"])
    assert body["agent"]["lifecycle_status"] == "draft"
    assert cloned_revision["state"] == "draft"
    assert cloned_revision["cloned_from_revision_id"] == revision_id


def test_archiving_active_revision_with_remaining_draft_keeps_agent_in_draft_state(client) -> None:
    reset_control_plane_state()

    created = client.post(
        "/agents",
        json={"name": "Draft Recovery Agent", "config": {"prompt": "Keep the draft alive"}},
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]

    client.post(f"/agents/{agent_id}/revisions/{revision_id}/publish", headers=AUTH_HEADERS)
    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/clone",
        headers=AUTH_HEADERS,
    )
    cloned_revision = max(clone_response.json()["revisions"], key=lambda revision: revision["revision_number"])

    archive_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/archive",
        headers=AUTH_HEADERS,
    )

    assert archive_response.status_code == 200
    body = archive_response.json()
    revisions = {revision["id"]: revision for revision in body["revisions"]}
    assert body["agent"]["active_revision_id"] is None
    assert body["agent"]["lifecycle_status"] == "draft"
    assert revisions[revision_id]["state"] == "archived"
    assert revisions[cloned_revision["id"]]["state"] == "draft"


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
    body = get_response.json()
    revisions = {revision["id"]: revision for revision in body["revisions"]}
    assert body["agent"]["lifecycle_status"] == "archived"
    assert revisions[revision_id]["state"] == "archived"

    republish_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert republish_response.status_code == 409


def test_agents_with_same_business_environment_do_not_leak_across_orgs(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")

    alpha_response = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Alpha Agent",
            "config": {"prompt": "Protect alpha scope"},
        },
        headers=alpha_headers,
    )
    beta_response = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Beta Agent",
            "config": {"prompt": "Protect beta scope"},
        },
        headers=beta_headers,
    )

    assert alpha_response.status_code == 200
    assert beta_response.status_code == 200

    alpha_id = alpha_response.json()["agent"]["id"]
    beta_id = beta_response.json()["agent"]["id"]

    assert alpha_response.json()["agent"]["org_id"] == "org_alpha"
    assert beta_response.json()["agent"]["org_id"] == "org_beta"
    assert client.get(f"/agents/{alpha_id}", headers=alpha_headers).status_code == 200
    assert client.get(f"/agents/{beta_id}", headers=beta_headers).status_code == 200
    assert client.get(f"/agents/{alpha_id}", headers=beta_headers).status_code == 404
    assert client.get(f"/agents/{beta_id}", headers=alpha_headers).status_code == 404
