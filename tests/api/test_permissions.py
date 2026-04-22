from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, org_id: str, actor_id: str, actor_type: str = "user") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


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


def test_permissions_are_scoped_to_actor_org_even_with_same_business_environment(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")

    alpha_agent = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Alpha Permission Agent",
            "config": {"prompt": "Guard alpha tools"},
        },
        headers=alpha_headers,
    )
    beta_agent = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Beta Permission Agent",
            "config": {"prompt": "Guard beta tools"},
        },
        headers=beta_headers,
    )

    assert alpha_agent.status_code == 200
    assert beta_agent.status_code == 200
    alpha_revision_id = alpha_agent.json()["revisions"][0]["id"]
    beta_revision_id = beta_agent.json()["revisions"][0]["id"]

    alpha_upsert = client.post(
        "/permissions",
        json={
            "agent_revision_id": alpha_revision_id,
            "tool_name": "lookup_title",
            "mode": "always_ask",
        },
        headers=alpha_headers,
    )
    beta_upsert = client.post(
        "/permissions",
        json={
            "agent_revision_id": beta_revision_id,
            "tool_name": "lookup_title",
            "mode": "forbidden",
        },
        headers=beta_headers,
    )

    leaked_list = client.get(f"/permissions/{alpha_revision_id}", headers=beta_headers)
    leaked_write = client.post(
        "/permissions",
        json={
            "agent_revision_id": alpha_revision_id,
            "tool_name": "lookup_title",
            "mode": "forbidden",
        },
        headers=beta_headers,
    )

    assert alpha_upsert.status_code == 200
    assert beta_upsert.status_code == 200
    assert leaked_list.status_code == 404
    assert leaked_write.status_code == 404
    assert client.get(f"/permissions/{alpha_revision_id}", headers=alpha_headers).json()["permissions"] == [alpha_upsert.json()]
    assert client.get(f"/permissions/{beta_revision_id}", headers=beta_headers).json()["permissions"] == [beta_upsert.json()]
