import pytest

from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, org_id: str, actor_id: str, actor_type: str = "user") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def create_published_agent(
    client,
    *,
    headers: dict[str, str] = AUTH_HEADERS,
    name: str = "Usage Agent",
    business_id: str = "limitless",
    environment: str = "dev",
) -> tuple[str, str]:
    created = client.post(
        "/agents",
        json={
            "business_id": business_id,
            "environment": environment,
            "name": name,
            "config": {"prompt": "Track usage"},
        },
        headers=headers,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    client.post(f"/agents/{agent_id}/revisions/{revision_id}/publish", headers=headers)
    return agent_id, revision_id


def test_usage_api_aggregates_counts_by_kind_and_agent(client) -> None:
    reset_control_plane_state()

    headers = org_actor_headers(org_id="org_limitless", actor_id="actor_limitless")
    agent_id, revision_id = create_published_agent(client, headers=headers, name="Limitless Usage Agent")

    first = client.post(
        "/usage",
        json={
            "kind": "run",
            "org_id": "org_limitless",
            "agent_id": agent_id,
            "agent_revision_id": revision_id,
            "count": 1,
        },
        headers=headers,
    )
    second = client.post(
        "/usage",
        json={
            "kind": "tool_call",
            "org_id": "org_limitless",
            "agent_id": agent_id,
            "agent_revision_id": revision_id,
            "count": 3,
            "source_kind": "trigger_dev",
        },
        headers=headers,
    )
    third = client.post(
        "/usage",
        json={
            "kind": "provider_call",
            "org_id": "org_limitless",
            "agent_id": agent_id,
            "agent_revision_id": revision_id,
            "count": 2,
            "source_kind": "anthropic",
        },
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200

    listing = client.get(f"/usage?org_id=org_limitless&agent_id={agent_id}", headers=headers)
    assert listing.status_code == 200
    body = listing.json()
    assert body["summary"]["total_count"] == 6
    assert body["summary"]["by_kind"] == {"provider_call": 2, "run": 1, "tool_call": 3}
    assert body["agent_id"] == agent_id


def test_usage_api_derives_actor_org_scopes_reads_and_scrubs_metadata_with_correlation_fields(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")
    alpha_agent_id, alpha_revision_id = create_published_agent(client, headers=alpha_headers, name="Alpha Usage Agent")
    _, beta_revision_id = create_published_agent(client, headers=beta_headers, name="Beta Usage Agent")

    alpha_session = client.post(
        "/sessions",
        json={
            "agent_revision_id": alpha_revision_id,
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=alpha_headers,
    )
    beta_session = client.post(
        "/sessions",
        json={
            "agent_revision_id": beta_revision_id,
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=beta_headers,
    )
    assert alpha_session.status_code == 200
    assert beta_session.status_code == 200

    alpha_response = client.post(
        "/usage",
        json={
            "kind": "tool_call",
            "session_id": alpha_session.json()["id"],
            "run_id": "run_alpha",
            "count": 3,
            "metadata": {
                "api_key": "super-secret",
                "nested": {"access_token": "token-value"},
                "safe": "kept",
            },
        },
        headers=alpha_headers,
    )
    beta_response = client.post(
        "/usage",
        json={
            "kind": "tool_call",
            "session_id": beta_session.json()["id"],
            "run_id": "run_beta",
            "count": 7,
        },
        headers=beta_headers,
    )

    assert alpha_response.status_code == 200
    assert beta_response.status_code == 200
    alpha_body = alpha_response.json()
    assert alpha_body["org_id"] == "org_alpha"
    assert alpha_body["agent_id"] == alpha_agent_id
    assert alpha_body["agent_revision_id"] == alpha_revision_id
    assert alpha_body["session_id"] == alpha_session.json()["id"]
    assert alpha_body["run_id"] == "run_alpha"
    assert alpha_body["metadata"] == {
        "api_key": "[redacted]",
        "nested": {"access_token": "[redacted]"},
        "safe": "kept",
    }

    listing = client.get(
        f"/usage?session_id={alpha_session.json()['id']}&run_id=run_alpha",
        headers=alpha_headers,
    )
    assert listing.status_code == 200
    body = listing.json()
    assert body["org_id"] == "org_alpha"
    assert body["summary"]["total_count"] == 3
    assert [event["org_id"] for event in body["events"]] == ["org_alpha"]
    assert [event["session_id"] for event in body["events"]] == [alpha_session.json()["id"]]
    assert [event["run_id"] for event in body["events"]] == ["run_alpha"]
    assert body["events"][0]["metadata"] == alpha_body["metadata"]

    mismatched_listing = client.get("/usage?org_id=org_beta", headers=alpha_headers)
    assert mismatched_listing.status_code == 422
    assert mismatched_listing.json()["detail"] == "Org id must match actor context"


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        ({"org_id": "org_beta"}, "Org id must match actor context"),
        ({"agent_revision_id": "rev_missing"}, "Agent revision not found"),
        ({"session_id": "ses_missing"}, "Session not found"),
    ],
)
def test_usage_api_rejects_invalid_actor_org_and_missing_links(client, payload: dict[str, str], detail: str) -> None:
    reset_control_plane_state()

    response = client.post(
        "/usage",
        json={"kind": "run", **payload},
        headers=org_actor_headers(org_id="org_alpha", actor_id="actor_alpha"),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == detail


def test_usage_api_rejects_conflicting_revision_and_session_identity(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    alpha_agent_id, alpha_revision_id = create_published_agent(client, headers=alpha_headers, name="Alpha Usage Agent")
    other_agent_id, other_revision_id = create_published_agent(client, headers=alpha_headers, name="Other Usage Agent")
    alpha_session = client.post(
        "/sessions",
        json={
            "agent_revision_id": alpha_revision_id,
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=alpha_headers,
    )
    assert alpha_session.status_code == 200

    mismatched_agent = client.post(
        "/usage",
        json={
            "kind": "run",
            "agent_revision_id": alpha_revision_id,
            "agent_id": other_agent_id,
        },
        headers=alpha_headers,
    )
    mismatched_session_revision = client.post(
        "/usage",
        json={
            "kind": "run",
            "session_id": alpha_session.json()["id"],
            "agent_revision_id": other_revision_id,
        },
        headers=alpha_headers,
    )

    assert alpha_agent_id != other_agent_id
    assert mismatched_agent.status_code == 422
    assert mismatched_agent.json()["detail"] == "Agent id must match agent revision"
    assert mismatched_session_revision.status_code == 422
    assert mismatched_session_revision.json()["detail"] == "Agent revision id must match session"
