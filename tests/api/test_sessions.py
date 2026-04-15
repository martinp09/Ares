from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def create_published_agent(client) -> tuple[str, str]:
    created = client.post(
        "/agents",
        json={"name": "Session Agent", "config": {"prompt": "Coordinate outreach"}},
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    client.post(f"/agents/{agent_id}/revisions/{revision_id}/publish", headers=AUTH_HEADERS)
    return agent_id, revision_id


def test_creating_two_sessions_from_same_revision_keeps_threads_isolated(client) -> None:
    reset_control_plane_state()
    _, revision_id = create_published_agent(client)

    first = client.post(
        "/sessions",
        json={
            "agent_revision_id": revision_id,
            "business_id": "limitless",
            "environment": "dev",
            "initial_message": "Handle landlords in Austin",
        },
        headers=AUTH_HEADERS,
    )
    second = client.post(
        "/sessions",
        json={
            "agent_revision_id": revision_id,
            "business_id": "limitless",
            "environment": "dev",
            "initial_message": "Handle wholesalers in Dallas",
        },
        headers=AUTH_HEADERS,
    )

    first_id = first.json()["id"]
    second_id = second.json()["id"]
    client.post(
        f"/sessions/{first_id}/events",
        json={"event_type": "assistant_note", "payload": {"message": "draft ready"}},
        headers=AUTH_HEADERS,
    )

    first_detail = client.get(f"/sessions/{first_id}", headers=AUTH_HEADERS).json()
    second_detail = client.get(f"/sessions/{second_id}", headers=AUTH_HEADERS).json()

    assert first_id != second_id
    assert len(first_detail["timeline"]) == 3
    assert len(second_detail["timeline"]) == 2
    assert first_detail["timeline"][-1]["payload"]["message"] == "draft ready"
    assert second_detail["timeline"][-1]["payload"]["message"] == "Handle wholesalers in Dallas"


def test_session_cannot_be_created_from_archived_revision(client) -> None:
    reset_control_plane_state()

    created = client.post(
        "/agents",
        json={"name": "Session Agent", "config": {"prompt": "Coordinate outreach"}},
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    client.post(f"/agents/{agent_id}/revisions/{revision_id}/archive", headers=AUTH_HEADERS)

    response = client.post(
        "/sessions",
        json={
            "agent_revision_id": revision_id,
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "archived revision" in response.json()["detail"]


def test_session_stays_pinned_to_original_revision_after_new_publish(client) -> None:
    reset_control_plane_state()
    agent_id, first_revision_id = create_published_agent(client)

    session_response = client.post(
        "/sessions",
        json={
            "agent_revision_id": first_revision_id,
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=AUTH_HEADERS,
    )
    session_id = session_response.json()["id"]

    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{first_revision_id}/clone",
        headers=AUTH_HEADERS,
    )
    second_revision_id = max(
        clone_response.json()["revisions"],
        key=lambda revision: revision["revision_number"],
    )["id"]
    client.post(f"/agents/{agent_id}/revisions/{second_revision_id}/publish", headers=AUTH_HEADERS)

    session_detail = client.get(f"/sessions/{session_id}", headers=AUTH_HEADERS)
    agent_detail = client.get(f"/agents/{agent_id}", headers=AUTH_HEADERS)

    assert session_detail.status_code == 200
    assert session_detail.json()["agent_revision_id"] == first_revision_id
    assert agent_detail.json()["agent"]["active_revision_id"] == second_revision_id
