from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, org_id: str, actor_id: str, actor_type: str = "user") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def create_published_agent(client, *, headers: dict[str, str], name: str) -> tuple[str, str]:
    created = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": name,
            "config": {"prompt": "Coordinate turns"},
        },
        headers=headers,
    )
    assert created.status_code == 200
    created_body = created.json()
    assert created_body["agent"]["org_id"] == headers["X-Ares-Org-Id"]
    agent_id = created_body["agent"]["id"]
    revision_id = created_body["revisions"][0]["id"]
    publish_response = client.post(f"/agents/{agent_id}/revisions/{revision_id}/publish", headers=headers)
    assert publish_response.status_code == 200
    assert publish_response.json()["agent"]["org_id"] == headers["X-Ares-Org-Id"]
    return agent_id, revision_id


def test_turn_loop_contract_is_org_scoped_and_visible_in_mission_control(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    _, alpha_revision_id = create_published_agent(
        client,
        headers=alpha_headers,
        name="Alpha Turn Agent",
    )
    alpha_session_response = client.post(
        "/sessions",
        json={
            "agent_revision_id": alpha_revision_id,
            "business_id": "limitless",
            "environment": "dev",
            "initial_message": "Start the org scoped turn loop",
        },
        headers=alpha_headers,
    )
    assert alpha_session_response.status_code == 200
    alpha_session = alpha_session_response.json()
    alpha_session_id = alpha_session["id"]
    assert alpha_session["org_id"] == "org_alpha"

    alpha_turn_response = client.post(
        f"/sessions/{alpha_session_id}/turns",
        json={
            "input_message": "Check title status",
            "tool_calls": [
                {"id": "call_alpha_1", "tool_name": "lookup_title", "arguments": {"property_id": "123"}}
            ],
            "metadata": {"retry_count": 1},
        },
        headers=alpha_headers,
    )
    assert alpha_turn_response.status_code == 200
    alpha_turn = alpha_turn_response.json()
    assert alpha_turn["status"] == "waiting_for_tool"

    alpha_resume_response = client.post(
        f"/sessions/{alpha_session_id}/turns/{alpha_turn['id']}/resume",
        json={
            "assistant_message": "Title came back clean",
            "tool_results": [
                {"tool_call_id": "call_alpha_1", "output": {"status": "clear"}, "success": True}
            ],
        },
        headers=alpha_headers,
    )
    assert alpha_resume_response.status_code == 200
    assert alpha_resume_response.json()["status"] == "completed"

    alpha_session_detail = client.get(f"/sessions/{alpha_session_id}", headers=alpha_headers)
    assert alpha_session_detail.status_code == 200
    alpha_session_body = alpha_session_detail.json()
    assert alpha_session_body["org_id"] == "org_alpha"
    assert alpha_session_body["compaction"]["compacted_turn_count"] == 1
    assert alpha_session_body["compaction"]["compacted_through_turn_id"] == alpha_turn["id"]

    alpha_journal_response = client.get(f"/sessions/{alpha_session_id}/journal", headers=alpha_headers)
    assert alpha_journal_response.status_code == 200
    alpha_journal = alpha_journal_response.json()
    assert alpha_journal["org_id"] == "org_alpha"
    assert alpha_journal["turn_count"] == 1
    assert alpha_journal["memory_summary"]["compacted_through_turn_id"] == alpha_turn["id"]
    assert alpha_journal["memory_summary"]["turns"][0]["tool_interactions"][0]["result"]["output"] == {"status": "clear"}

    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")
    _, beta_revision_id = create_published_agent(
        client,
        headers=beta_headers,
        name="Beta Turn Agent",
    )
    beta_session_response = client.post(
        "/sessions",
        json={
            "agent_revision_id": beta_revision_id,
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=beta_headers,
    )
    assert beta_session_response.status_code == 200
    beta_session_id = beta_session_response.json()["id"]

    beta_turn_response = client.post(
        f"/sessions/{beta_session_id}/turns",
        json={
            "input_message": "Ignore this out of org turn",
            "assistant_message": "Out of org turn complete",
            "metadata": {"retry_count": 4},
        },
        headers=beta_headers,
    )
    assert beta_turn_response.status_code == 200

    turns_response = client.get("/mission-control/turns", headers=alpha_headers)
    assert turns_response.status_code == 200
    turns_body = turns_response.json()
    assert len(turns_body["turns"]) == 1
    mission_control_turn = turns_body["turns"][0]
    assert mission_control_turn["id"] == alpha_turn["id"]
    assert mission_control_turn["org_id"] == "org_alpha"
    assert mission_control_turn["business_id"] == "limitless"
    assert mission_control_turn["environment"] == "dev"
    assert mission_control_turn["state"] == "completed"
    assert mission_control_turn["retry_count"] == 1

    turn_ids = {turn["id"] for turn in turns_body["turns"]}
    assert beta_turn_response.json()["id"] not in turn_ids
