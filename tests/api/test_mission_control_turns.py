from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def _create_published_agent(client, *, business_id: str, environment: str, name: str) -> tuple[str, str]:
    created = client.post(
        "/agents",
        json={
            "business_id": business_id,
            "environment": environment,
            "name": name,
            "config": {"prompt": "Coordinate execution"},
        },
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    publish_response = client.post(f"/agents/{agent_id}/revisions/{revision_id}/publish", headers=AUTH_HEADERS)
    assert publish_response.status_code == 200
    return agent_id, revision_id


def test_mission_control_turns_endpoint_returns_scoped_turn_state_and_retry_count(client) -> None:
    reset_control_plane_state()

    agent_id, revision_id = _create_published_agent(
        client,
        business_id="limitless",
        environment="dev",
        name="Mission Control Turn Agent",
    )
    session_response = client.post(
        "/sessions",
        json={
            "agent_revision_id": revision_id,
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=AUTH_HEADERS,
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["id"]

    turn_response = client.post(
        f"/sessions/{session_id}/turns",
        json={
            "input_message": "Check the title chain",
            "assistant_message": "Title chain reviewed and ready.",
            "metadata": {"retry_count": 2},
        },
        headers=AUTH_HEADERS,
    )
    assert turn_response.status_code == 200

    other_agent_id, other_revision_id = _create_published_agent(
        client,
        business_id="otherco",
        environment="prod",
        name="Out of Scope Turn Agent",
    )
    other_session_response = client.post(
        "/sessions",
        json={
            "agent_revision_id": other_revision_id,
            "business_id": "otherco",
            "environment": "prod",
        },
        headers=AUTH_HEADERS,
    )
    assert other_session_response.status_code == 200
    other_session_id = other_session_response.json()["id"]

    other_turn_response = client.post(
        f"/sessions/{other_session_id}/turns",
        json={
            "input_message": "Ignore this turn",
            "assistant_message": "Out of scope.",
            "metadata": {"retry_count": 5},
        },
        headers=AUTH_HEADERS,
    )
    assert other_turn_response.status_code == 200

    response = client.get(
        "/mission-control/turns?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["turns"]) == 1
    turn = body["turns"][0]
    assert turn["id"] == turn_response.json()["id"]
    assert turn["session_id"] == session_id
    assert turn["business_id"] == "limitless"
    assert turn["environment"] == "dev"
    assert turn["agent_id"] == agent_id
    assert turn["agent_revision_id"] == revision_id
    assert turn["turn_number"] == 1
    assert turn["state"] == "completed"
    assert turn["retry_count"] == 2
    assert turn["resumed_from_turn_id"] is None
    assert "updated_at" in turn

    turn_ids = {item["id"] for item in body["turns"]}
    assert other_turn_response.json()["id"] not in turn_ids
