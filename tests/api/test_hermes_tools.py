from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def create_agent_revision(client) -> str:
    created = client.post(
        "/agents",
        json={"name": "Tool Agent", "config": {"prompt": "Use tools carefully"}},
        headers=AUTH_HEADERS,
    ).json()
    return created["revisions"][0]["id"]


def test_list_hermes_tools_exposes_marketing_commands(client) -> None:
    reset_control_plane_state()

    response = client.get("/hermes/tools", headers=AUTH_HEADERS)
    assert response.status_code == 200
    tools = response.json()["tools"]
    tool_names = {tool["name"] for tool in tools}
    assert "run_market_research" in tool_names
    assert "publish_campaign" in tool_names


def test_invoke_hermes_tool_reuses_command_service_when_allowed(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/hermes/tools/run_market_research/invoke",
        json={
            "business_id": 101,
            "environment": "dev",
            "idempotency_key": "cmd-040",
            "payload": {"topic": "austin landlords"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["command_type"] == "run_market_research"
    assert body["policy"] == "safe_autonomous"
    assert body["run_id"] is not None


def test_always_ask_permission_returns_approval_path_instead_of_direct_execution(client) -> None:
    reset_control_plane_state()
    revision_id = create_agent_revision(client)

    client.post(
        "/permissions",
        json={
            "agent_revision_id": revision_id,
            "tool_name": "run_market_research",
            "mode": "always_ask",
        },
        headers=AUTH_HEADERS,
    )

    listed = client.get(f"/hermes/tools?agent_revision_id={revision_id}", headers=AUTH_HEADERS)
    listed_tool = next(tool for tool in listed.json()["tools"] if tool["name"] == "run_market_research")
    response = client.post(
        "/hermes/tools/run_market_research/invoke",
        json={
            "agent_revision_id": revision_id,
            "business_id": 101,
            "environment": "dev",
            "idempotency_key": "cmd-041",
            "payload": {"topic": "dallas absentee owners"},
        },
        headers=AUTH_HEADERS,
    )

    assert listed.status_code == 200
    assert listed_tool["permission_mode"] == "always_ask"
    assert listed_tool["approval_mode"] == "approval_required"
    assert response.status_code == 201
    body = response.json()
    assert body["policy"] == "approval_required"
    assert body["approval_id"] is not None
    assert body["run_id"] is None


def test_forbidden_permission_rejects_tool_invocation(client) -> None:
    reset_control_plane_state()
    revision_id = create_agent_revision(client)

    client.post(
        "/permissions",
        json={
            "agent_revision_id": revision_id,
            "tool_name": "run_market_research",
            "mode": "forbidden",
        },
        headers=AUTH_HEADERS,
    )

    response = client.post(
        "/hermes/tools/run_market_research/invoke",
        json={
            "agent_revision_id": revision_id,
            "business_id": 101,
            "environment": "dev",
            "idempotency_key": "cmd-042",
            "payload": {"topic": "houston multifamily"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"]
