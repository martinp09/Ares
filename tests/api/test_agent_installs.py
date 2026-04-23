from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, org_id: str, actor_id: str, actor_type: str = "user") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def create_agent(client, *, headers: dict[str, str], name: str) -> tuple[str, str]:
    response = client.post(
        "/agents",
        json={
            "name": name,
            "description": f"{name} description",
            "visibility": "private_catalog",
            "packaging_metadata": {"category": "operations"},
            "config": {"prompt": f"{name} prompt"},
            "release_channel": "dogfood",
            "compatibility_metadata": {"requires_secrets": ["resend_api_key"]},
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    return body["agent"]["id"], body["revisions"][0]["id"]


def create_catalog_entry(client, *, headers: dict[str, str], agent_id: str, revision_id: str) -> str:
    response = client.post(
        "/catalog",
        json={
            "agent_id": agent_id,
            "agent_revision_id": revision_id,
            "slug": "seller-ops",
            "name": "Seller Ops",
            "summary": "Internal seller ops package",
            "description": "Installable seller ops agent",
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_agent_installs_api_creates_install_and_preserves_lineage(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")
    source_agent_id, source_revision_id = create_agent(client, headers=alpha_headers, name="Seller Ops Agent")
    catalog_entry_id = create_catalog_entry(
        client,
        headers=alpha_headers,
        agent_id=source_agent_id,
        revision_id=source_revision_id,
    )

    response = client.post(
        "/agent-installs",
        json={
            "catalog_entry_id": catalog_entry_id,
            "business_id": "limitless",
            "environment": "prod",
            "name": "Installed Seller Ops",
        },
        headers=alpha_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["install"]["org_id"] == "org_alpha"
    assert body["install"]["catalog_entry_id"] == catalog_entry_id
    assert body["install"]["source_agent_id"] == source_agent_id
    assert body["install"]["source_agent_revision_id"] == source_revision_id
    assert body["install"]["installed_agent_id"] != source_agent_id
    assert body["install"]["installed_agent_revision_id"] != source_revision_id
    assert body["agent"]["org_id"] == "org_alpha"
    assert body["agent"]["business_id"] == "limitless"
    assert body["agent"]["environment"] == "prod"
    assert body["agent"]["name"] == "Installed Seller Ops"
    assert body["agent"]["visibility"] == "private_catalog"
    assert body["agent"]["packaging_metadata"]["catalog_entry_id"] == catalog_entry_id
    assert body["agent"]["packaging_metadata"]["source_agent_id"] == source_agent_id
    assert body["agent"]["packaging_metadata"]["source_agent_revision_id"] == source_revision_id
    assert body["revisions"][0]["config"] == {"prompt": "Seller Ops Agent prompt"}
    assert body["revisions"][0]["release_channel"] == "dogfood"
    assert body["revisions"][0]["compatibility_metadata"] == {"requires_secrets": ["resend_api_key"]}

    alpha_list = client.get("/agent-installs", headers=alpha_headers)
    beta_list = client.get("/agent-installs", headers=beta_headers)
    assert alpha_list.status_code == 200
    assert beta_list.status_code == 200
    assert [install["id"] for install in alpha_list.json()["installs"]] == [body["install"]["id"]]
    assert beta_list.json()["installs"] == []
    assert client.get(f"/agent-installs/{body['install']['id']}", headers=beta_headers).status_code == 404


def test_agent_installs_preserve_marketplace_candidate_visibility_as_internal_metadata_only(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    source_response = client.post(
        "/agents",
        json={
            "name": "Candidate Source Agent",
            "description": "Candidate metadata only",
            "visibility": "marketplace_candidate",
            "packaging_metadata": {"category": "operations"},
            "config": {"prompt": "Candidate prompt"},
            "release_channel": "dogfood",
            "compatibility_metadata": {"requires_secrets": ["resend_api_key"]},
        },
        headers=alpha_headers,
    )
    assert source_response.status_code == 200
    source_body = source_response.json()
    source_agent_id = source_body["agent"]["id"]
    source_revision_id = source_body["revisions"][0]["id"]

    catalog_entry_id = create_catalog_entry(
        client,
        headers=alpha_headers,
        agent_id=source_agent_id,
        revision_id=source_revision_id,
    )

    install_response = client.post(
        "/agent-installs",
        json={
            "catalog_entry_id": catalog_entry_id,
            "business_id": "limitless",
            "environment": "prod",
            "name": "Installed Candidate Agent",
        },
        headers=alpha_headers,
    )

    assert install_response.status_code == 200
    body = install_response.json()
    assert body["agent"]["visibility"] == "marketplace_candidate"


def test_agent_installs_api_rejects_missing_catalog_entries(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    response = client.post(
        "/agent-installs",
        json={
            "catalog_entry_id": "cat_missing",
            "business_id": "limitless",
            "environment": "prod",
        },
        headers=alpha_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalog entry not found"
