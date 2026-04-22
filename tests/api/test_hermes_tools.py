from app.db.client import STORE
from app.db.host_adapter_dispatches import HostAdapterDispatchesRepository
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def create_agent_revision(client) -> str:
    created = client.post(
        "/agents",
        json={"name": "Tool Agent", "config": {"prompt": "Use tools carefully"}},
        headers=AUTH_HEADERS,
    ).json()
    return created["revisions"][0]["id"]


def create_published_agent(client) -> tuple[str, str]:
    created = client.post(
        "/agents",
        json={
            "name": "Published Tool Agent",
            "config": {"prompt": "Use tools carefully"},
            "host_adapter_kind": "trigger_dev",
            "host_adapter_config": {"queue": "priority"},
        },
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200
    return agent_id, revision_id


def create_published_agent_revision(client) -> str:
    _, revision_id = create_published_agent(client)
    return revision_id


def create_published_disabled_agent_revision(client) -> str:
    created = client.post(
        "/agents",
        json={
            "name": "Disabled Tool Agent",
            "config": {"prompt": "Use tools carefully"},
            "host_adapter_kind": "codex",
        },
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200
    return revision_id


def create_skill(client, *, name: str, required_tools: list[str]) -> str:
    response = client.post(
        "/skills",
        json={"name": name, "required_tools": required_tools},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_agent_with_skills(client, *, name: str, skill_ids: list[str], published: bool = False) -> tuple[str, str]:
    created = client.post(
        "/agents",
        json={
            "name": name,
            "config": {"prompt": "Use tools carefully"},
            "skill_ids": skill_ids,
        },
        headers=AUTH_HEADERS,
    )
    assert created.status_code == 200
    body = created.json()
    agent_id = body["agent"]["id"]
    revision_id = body["revisions"][0]["id"]
    if published:
        publish_response = client.post(
            f"/agents/{agent_id}/revisions/{revision_id}/publish",
            headers=AUTH_HEADERS,
        )
        assert publish_response.status_code == 200
    return agent_id, revision_id


def test_list_hermes_tools_exposes_marketing_commands(client) -> None:
    reset_control_plane_state()

    response = client.get("/hermes/tools", headers=AUTH_HEADERS)
    assert response.status_code == 200
    tools = response.json()["tools"]
    tool_names = {tool["name"] for tool in tools}
    assert "run_market_research" in tool_names
    assert "publish_campaign" in tool_names


def test_list_hermes_tools_with_command_backed_bound_skills_only_exposes_supported_intersection(client) -> None:
    reset_control_plane_state()
    research_skill_id = create_skill(
        client,
        name="research_skill",
        required_tools=["run_market_research", "lookup_title"],
    )
    launch_skill_id = create_skill(
        client,
        name="launch_skill",
        required_tools=["publish_campaign"],
    )
    _, revision_id = create_agent_with_skills(
        client,
        name="Bound Tool Agent",
        skill_ids=[research_skill_id, launch_skill_id],
    )

    response = client.get(f"/hermes/tools?agent_revision_id={revision_id}", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert [tool["name"] for tool in response.json()["tools"]] == [
        "publish_campaign",
        "run_market_research",
    ]


def test_list_hermes_tools_with_non_command_skill_requirements_falls_back_to_full_surface(client) -> None:
    reset_control_plane_state()
    skill_id = create_skill(
        client,
        name="non_command_skill",
        required_tools=["lookup_title", "route_lead"],
    )
    _, revision_id = create_agent_with_skills(
        client,
        name="Fallback Tool Agent",
        skill_ids=[skill_id],
    )

    response = client.get(f"/hermes/tools?agent_revision_id={revision_id}", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert {tool["name"] for tool in response.json()["tools"]} == {
        "create_campaign_brief",
        "draft_campaign_assets",
        "propose_launch",
        "publish_campaign",
        "run_market_research",
    }


def test_invoke_hermes_tool_rejects_command_outside_bound_skill_surface(client) -> None:
    reset_control_plane_state()
    skill_id = create_skill(
        client,
        name="approval_only_skill",
        required_tools=["publish_campaign"],
    )
    _, revision_id = create_agent_with_skills(
        client,
        name="Restricted Tool Agent",
        skill_ids=[skill_id],
        published=True,
    )

    response = client.post(
        "/hermes/tools/run_market_research/invoke",
        json={
            "agent_revision_id": revision_id,
            "business_id": "limitless",
            "environment": "dev",
            "idempotency_key": "cmd-040-skill-surface",
            "payload": {"topic": "austin landlords"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 403
    assert "not allowed for this agent skill surface" in response.json()["detail"]
    assert STORE.commands == {}
    assert STORE.runs == {}
    assert HostAdapterDispatchesRepository().list() == []


def test_invoke_hermes_tool_reuses_command_service_when_allowed(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/hermes/tools/run_market_research/invoke",
        json={
            "business_id": "limitless",
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
    assert HostAdapterDispatchesRepository().list() == []


def test_invoke_hermes_tool_with_published_agent_revision_dispatches_through_adapter_seam(client) -> None:
    reset_control_plane_state()
    revision_id = create_published_agent_revision(client)

    response = client.post(
        "/hermes/tools/run_market_research/invoke",
        json={
            "agent_revision_id": revision_id,
            "business_id": "limitless",
            "environment": "dev",
            "idempotency_key": "cmd-040-agent",
            "payload": {"topic": "austin landlords"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["command_type"] == "run_market_research"
    assert body["policy"] == "safe_autonomous"
    assert body["run_id"] is not None

    dispatches = HostAdapterDispatchesRepository().list()
    assert len(dispatches) == 1
    dispatch = dispatches[0]
    assert dispatch.agent_revision_id == revision_id
    assert dispatch.run_id == body["run_id"]
    assert dispatch.external_reference == body["run_id"]
    assert dispatch.host_adapter_config == {"queue": "priority"}


def test_invoke_hermes_tool_retry_dedupes_after_revision_is_archived(client) -> None:
    reset_control_plane_state()
    agent_id, revision_id = create_published_agent(client)
    payload = {
        "agent_revision_id": revision_id,
        "business_id": "limitless",
        "environment": "dev",
        "idempotency_key": "cmd-040-agent-archived-retry",
        "payload": {"topic": "austin landlords"},
    }

    first = client.post(
        "/hermes/tools/run_market_research/invoke",
        json=payload,
        headers=AUTH_HEADERS,
    )
    archive_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/archive",
        headers=AUTH_HEADERS,
    )
    second = client.post(
        "/hermes/tools/run_market_research/invoke",
        json=payload,
        headers=AUTH_HEADERS,
    )

    assert first.status_code == 201
    assert archive_response.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert second_body["deduped"] is True
    assert second_body["id"] == first_body["id"]
    assert second_body["run_id"] == first_body["run_id"]
    assert len(STORE.commands) == 1
    assert len(STORE.runs) == 1
    assert len(HostAdapterDispatchesRepository().list()) == 1


def test_invoke_hermes_tool_with_draft_agent_revision_fails_closed_before_persisting_queue_records(client) -> None:
    reset_control_plane_state()
    revision_id = create_agent_revision(client)

    response = client.post(
        "/hermes/tools/run_market_research/invoke",
        json={
            "agent_revision_id": revision_id,
            "business_id": "limitless",
            "environment": "dev",
            "idempotency_key": "cmd-040-draft-agent",
            "payload": {"topic": "austin landlords"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Only published revisions can be dispatched"
    assert STORE.commands == {}
    assert STORE.runs == {}
    assert HostAdapterDispatchesRepository().list() == []


def test_invoke_hermes_tool_with_archived_agent_revision_fails_closed_before_persisting_queue_records(client) -> None:
    reset_control_plane_state()
    created = client.post(
        "/agents",
        json={
            "name": "Archived Tool Agent",
            "config": {"prompt": "Use tools carefully"},
        },
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    archive_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/archive",
        headers=AUTH_HEADERS,
    )
    assert archive_response.status_code == 200

    response = client.post(
        "/hermes/tools/run_market_research/invoke",
        json={
            "agent_revision_id": revision_id,
            "business_id": "limitless",
            "environment": "dev",
            "idempotency_key": "cmd-040-archived-agent",
            "payload": {"topic": "austin landlords"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Archived revisions cannot be dispatched"
    assert STORE.commands == {}
    assert STORE.runs == {}
    assert HostAdapterDispatchesRepository().list() == []


def test_invoke_hermes_tool_with_disabled_adapter_revision_fails_closed_before_persisting_queue_records(client) -> None:
    reset_control_plane_state()
    revision_id = create_published_disabled_agent_revision(client)

    response = client.post(
        "/hermes/tools/run_market_research/invoke",
        json={
            "agent_revision_id": revision_id,
            "business_id": "limitless",
            "environment": "dev",
            "idempotency_key": "cmd-040-disabled-agent",
            "payload": {"topic": "austin landlords"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "codex adapter is disabled in this environment"
    assert STORE.commands == {}
    assert STORE.runs == {}
    assert HostAdapterDispatchesRepository().list() == []


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
            "business_id": "limitless",
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
            "business_id": "limitless",
            "environment": "dev",
            "idempotency_key": "cmd-042",
            "payload": {"topic": "houston multifamily"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"]
