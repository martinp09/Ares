from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, org_id: str, actor_id: str, actor_type: str = "user") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def create_agent_revision(client, *, headers: dict[str, str], name: str) -> str:
    response = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": name,
            "config": {"prompt": "Follow policy"},
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["revisions"][0]["id"]


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


def test_rbac_api_rejects_unsupported_role_names(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/rbac/roles",
        json={"name": "supervisor", "description": "Not part of the canonical set"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "Unsupported role name" in response.json()["detail"]


def test_rbac_api_resolves_forbidden_effective_mode_with_deterministic_source_order(client) -> None:
    reset_control_plane_state()

    headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    revision_id = create_agent_revision(client, headers=headers, name="Alpha RBAC Agent")

    operator_role = client.post(
        "/rbac/roles",
        json={"name": "operator", "description": "Operator access"},
        headers=headers,
    )
    org_admin_role = client.post(
        "/rbac/roles",
        json={"name": " Org_Admin ", "description": "Admin access"},
        headers=headers,
    )

    assert operator_role.status_code == 200
    assert org_admin_role.status_code == 200
    assert operator_role.json()["name"] == "operator"
    assert org_admin_role.json()["name"] == "org_admin"

    operator_role_id = operator_role.json()["id"]
    org_admin_role_id = org_admin_role.json()["id"]

    operator_grant = client.post(
        f"/rbac/roles/{operator_role_id}/grants",
        json={"tool_name": "publish_campaign", "mode": "always_allow"},
        headers=headers,
    )
    org_admin_grant = client.post(
        f"/rbac/roles/{org_admin_role_id}/grants",
        json={"tool_name": "publish_campaign", "mode": "forbidden"},
        headers=headers,
    )
    operator_assignment = client.post(
        "/rbac/assignments",
        json={"agent_revision_id": revision_id, "role_id": operator_role_id},
        headers=headers,
    )
    org_admin_assignment = client.post(
        "/rbac/assignments",
        json={"agent_revision_id": revision_id, "role_id": org_admin_role_id},
        headers=headers,
    )
    org_policy = client.post(
        "/rbac/policies",
        json={"tool_name": "publish_campaign", "mode": "always_ask"},
        headers=headers,
    )

    assert operator_grant.status_code == 200
    assert org_admin_grant.status_code == 200
    assert operator_assignment.status_code == 200
    assert org_admin_assignment.status_code == 200
    assert org_policy.status_code == 200

    effective_response = client.get(
        f"/rbac/revisions/{revision_id}/effective?tool_name=publish_campaign",
        headers=headers,
    )

    assert effective_response.status_code == 200
    assert effective_response.json() == {
        "tool_name": "publish_campaign",
        "mode": "forbidden",
        "source_modes": ["forbidden", "always_allow", "always_ask"],
        "sources": [
            {"source": "role:org_admin", "mode": "forbidden"},
            {"source": "role:operator", "mode": "always_allow"},
            {"source": "org:org_alpha", "mode": "always_ask"},
        ],
    }


def test_rbac_api_is_scoped_to_actor_org_with_same_business_environment(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")

    alpha_revision_id = create_agent_revision(client, headers=alpha_headers, name="Alpha RBAC Agent")
    beta_revision_id = create_agent_revision(client, headers=beta_headers, name="Beta RBAC Agent")

    alpha_role = client.post(
        "/rbac/roles",
        json={"name": "operator", "description": "Alpha approvals"},
        headers=alpha_headers,
    )
    beta_role = client.post(
        "/rbac/roles",
        json={"name": "operator", "description": "Beta approvals"},
        headers=beta_headers,
    )

    assert alpha_role.status_code == 200
    assert beta_role.status_code == 200
    alpha_role_id = alpha_role.json()["id"]
    beta_role_id = beta_role.json()["id"]
    assert alpha_role_id != beta_role_id

    alpha_grant = client.post(
        f"/rbac/roles/{alpha_role_id}/grants",
        json={"tool_name": "publish_campaign", "mode": "always_ask"},
        headers=alpha_headers,
    )
    alpha_assignment = client.post(
        "/rbac/assignments",
        json={"agent_revision_id": alpha_revision_id, "role_id": alpha_role_id},
        headers=alpha_headers,
    )

    assert alpha_grant.status_code == 200
    assert alpha_assignment.status_code == 200
    assert [role["id"] for role in client.get("/rbac/roles", headers=alpha_headers).json()["roles"]] == [alpha_role_id]
    assert [role["id"] for role in client.get("/rbac/roles", headers=beta_headers).json()["roles"]] == [beta_role_id]

    leaked_grant = client.post(
        f"/rbac/roles/{alpha_role_id}/grants",
        json={"tool_name": "publish_campaign", "mode": "forbidden"},
        headers=beta_headers,
    )
    leaked_assignment = client.post(
        "/rbac/assignments",
        json={"agent_revision_id": beta_revision_id, "role_id": alpha_role_id},
        headers=beta_headers,
    )
    leaked_effective = client.get(
        f"/rbac/revisions/{alpha_revision_id}/effective?tool_name=publish_campaign",
        headers=beta_headers,
    )
    mismatched_role_create = client.post(
        "/rbac/roles",
        json={"org_id": "org_beta", "name": "auditor", "description": "wrong org"},
        headers=alpha_headers,
    )
    mismatched_role_list = client.get("/rbac/roles?org_id=org_beta", headers=alpha_headers)
    mismatched_policy = client.post(
        "/rbac/policies",
        json={"org_id": "org_beta", "tool_name": "publish_campaign", "mode": "forbidden"},
        headers=alpha_headers,
    )

    assert leaked_grant.status_code == 404
    assert leaked_assignment.status_code == 404
    assert leaked_effective.status_code == 404
    assert mismatched_role_create.status_code == 422
    assert mismatched_role_list.status_code == 422
    assert mismatched_policy.status_code == 422
