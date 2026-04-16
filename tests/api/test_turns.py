from app.db.client import STORE
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def create_published_agent(client) -> tuple[str, str]:
    created = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Session Agent",
            "config": {"prompt": "Coordinate turns"},
        },
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    client.post(f"/agents/{agent_id}/revisions/{revision_id}/publish", headers=AUTH_HEADERS)
    return agent_id, revision_id


def test_session_turn_routes_start_resume_and_replay(client) -> None:
    reset_control_plane_state()
    _, revision_id = create_published_agent(client)

    session_response = client.post(
        "/sessions",
        json={
            "agent_revision_id": revision_id,
            "business_id": "limitless",
            "environment": "dev",
            "initial_message": "Start the turn loop",
        },
        headers=AUTH_HEADERS,
    )
    session_id = session_response.json()["id"]

    turn_response = client.post(
        f"/sessions/{session_id}/turns",
        json={
            "input_message": "Check title status",
            "tool_calls": [
                {"id": "call_1", "tool_name": "lookup_title", "arguments": {"property_id": "123"}}
            ],
        },
        headers=AUTH_HEADERS,
    )

    assert turn_response.status_code == 200
    turn_body = turn_response.json()
    turn_id = turn_body["id"]
    assert turn_body["status"] == "waiting_for_tool"

    events_response = client.get(f"/sessions/{session_id}/turns/{turn_id}/events", headers=AUTH_HEADERS)
    assert events_response.status_code == 200
    assert [event["event_type"] for event in events_response.json()] == [
        "turn_started",
        "tool_call_requested",
        "turn_waiting_for_tool",
    ]

    resume_response = client.post(
        f"/sessions/{session_id}/turns/{turn_id}/resume",
        json={
            "assistant_message": "Tool came back clean",
            "tool_results": [{"tool_call_id": "call_1", "output": {"status": "clear"}, "success": True}],
        },
        headers=AUTH_HEADERS,
    )
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "completed"
    assert resume_response.json()["assistant_message"] == "Tool came back clean"

    replayed = client.get(f"/sessions/{session_id}/turns/{turn_id}", headers=AUTH_HEADERS)
    assert replayed.status_code == 200
    assert replayed.json()["status"] == "completed"
    assert replayed.json()["turn_number"] == 1

    assert [entry["event_type"] for entry in client.get(f"/sessions/{session_id}", headers=AUTH_HEADERS).json()["timeline"]][-6:] == [
        "turn_started",
        "tool_call_requested",
        "turn_waiting_for_tool",
        "turn_resumed",
        "tool_result_recorded",
        "turn_completed",
    ]

    assert STORE.turns[turn_id].status.value == "completed"
