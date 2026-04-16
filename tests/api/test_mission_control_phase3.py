from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_mission_control_surfaces_secret_health_audit_and_usage(client) -> None:
    reset_control_plane_state()

    agent_response = client.post(
        "/agents",
        json={"name": "Mission Control Agent", "config": {"prompt": "Observe governance"}},
        headers=AUTH_HEADERS,
    )
    assert agent_response.status_code == 200
    revision_id = agent_response.json()["revisions"][0]["id"]

    secret_response = client.post(
        "/secrets",
        json={"name": "textgrid_auth_token", "secret_value": "tok-12345"},
        headers=AUTH_HEADERS,
    )
    assert secret_response.status_code == 200
    secret_id = secret_response.json()["id"]
    binding_response = client.post(
        f"/secrets/{secret_id}/bindings",
        json={"agent_revision_id": revision_id, "binding_name": "textgrid_auth_token"},
        headers=AUTH_HEADERS,
    )
    assert binding_response.status_code == 200

    audit_response = client.post(
        "/audit",
        json={
            "event_type": "secret_accessed",
            "summary": "Accessed secret metadata",
            "org_id": "org_internal",
            "resource_type": "secret",
            "resource_id": secret_id,
        },
        headers=AUTH_HEADERS,
    )
    assert audit_response.status_code == 200

    usage_response = client.post(
        "/usage",
        json={
            "kind": "tool_call",
            "org_id": "org_internal",
            "agent_id": agent_response.json()["agent"]["id"],
            "agent_revision_id": revision_id,
            "count": 2,
        },
        headers=AUTH_HEADERS,
    )
    assert usage_response.status_code == 200

    secrets_listing = client.get("/mission-control/settings/secrets", headers=AUTH_HEADERS)
    assert secrets_listing.status_code == 200
    secrets_body = secrets_listing.json()
    assert secrets_body["secrets"][0]["value_redacted"] == "[redacted]"
    assert secrets_body["secrets"][0]["binding_count"] == 1

    audit_listing = client.get("/mission-control/audit?org_id=org_internal", headers=AUTH_HEADERS)
    assert audit_listing.status_code == 200
    assert audit_listing.json()["events"][0]["event_type"] == "secret_accessed"

    usage_listing = client.get("/mission-control/usage?org_id=org_internal", headers=AUTH_HEADERS)
    assert usage_listing.status_code == 200
    assert usage_listing.json()["summary"]["total_count"] == 2
