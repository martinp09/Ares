from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def agent_headers(org_id: str = "org_internal") -> dict[str, str]:
    return {**AUTH_HEADERS, "X-Ares-Org-Id": org_id}


def create_agent_revision(client, *, org_id: str, requires_secrets: list[str]) -> str:
    agent_response = client.post(
        "/agents",
        json={
            "name": f"{org_id} Secret Agent",
            "config": {"prompt": "Handle secrets"},
            "compatibility_metadata": {"requires_secrets": requires_secrets},
        },
        headers=agent_headers(org_id),
    )
    assert agent_response.status_code == 200
    return agent_response.json()["revisions"][0]["id"]



def test_secret_api_redacts_values_lists_revision_bindings_and_audits_reads(client) -> None:
    reset_control_plane_state()
    revision_id = create_agent_revision(client, org_id="org_internal", requires_secrets=["resend_api_key"])

    secret_response = client.post(
        "/secrets",
        json={
            "name": "resend_api_key",
            "description": "Outbound email credential",
            "secret_value": "resend-secret-value",
        },
        headers=AUTH_HEADERS,
    )
    assert secret_response.status_code == 200
    secret_body = secret_response.json()
    assert secret_body["name"] == "resend_api_key"
    assert secret_body["value_redacted"] == "[redacted]"
    assert "secret_value" not in secret_body

    binding_response = client.post(
        f"/secrets/{secret_body['id']}/bindings",
        json={"agent_revision_id": revision_id, "binding_name": "resend_api_key"},
        headers=AUTH_HEADERS,
    )
    assert binding_response.status_code == 200
    assert binding_response.json()["binding_name"] == "resend_api_key"

    list_response = client.get("/secrets", headers=AUTH_HEADERS)
    assert list_response.status_code == 200
    secrets = list_response.json()["secrets"]
    assert len(secrets) == 1
    assert secrets[0]["value_redacted"] == "[redacted]"
    assert secrets[0]["binding_count"] == 1
    assert "secret_value" not in secrets[0]

    revision_bindings = client.get(f"/secrets/revisions/{revision_id}", headers=AUTH_HEADERS)
    assert revision_bindings.status_code == 200
    assert revision_bindings.json()["bindings"][0]["binding_name"] == "resend_api_key"

    audit_response = client.get(
        f"/audit?event_type=secret_accessed&resource_id={secret_body['id']}",
        headers=AUTH_HEADERS,
    )
    assert audit_response.status_code == 200
    audit_events = audit_response.json()["events"]
    assert len(audit_events) == 2
    assert {event["metadata"]["access_path"] for event in audit_events} == {"list_secrets", "list_revision_bindings"}
    assert any(event["agent_revision_id"] == revision_id for event in audit_events)



def test_secret_binding_api_rejects_missing_and_undeclared_revision_refs(client) -> None:
    reset_control_plane_state()
    secret_response = client.post(
        "/secrets",
        json={"name": "resend_api_key", "secret_value": "resend-secret-value"},
        headers=AUTH_HEADERS,
    )
    assert secret_response.status_code == 200
    secret_id = secret_response.json()["id"]

    missing_revision_response = client.post(
        f"/secrets/{secret_id}/bindings",
        json={"agent_revision_id": "rev_missing", "binding_name": "resend_api_key"},
        headers=AUTH_HEADERS,
    )
    assert missing_revision_response.status_code == 404
    assert missing_revision_response.json()["detail"] == "Agent revision not found"

    undeclared_revision_id = create_agent_revision(
        client,
        org_id="org_internal",
        requires_secrets=["postmark_api_key"],
    )
    undeclared_binding_response = client.post(
        f"/secrets/{secret_id}/bindings",
        json={"agent_revision_id": undeclared_revision_id, "binding_name": "resend_api_key"},
        headers=AUTH_HEADERS,
    )
    assert undeclared_binding_response.status_code == 422
    assert "not declared" in undeclared_binding_response.json()["detail"]



def test_secret_binding_api_rejects_foreign_org_revision_and_missing_revision_list(client) -> None:
    reset_control_plane_state()
    secret_response = client.post(
        "/secrets",
        json={"org_id": "org_alpha", "name": "alpha_token", "secret_value": "alpha-secret-value"},
        headers=AUTH_HEADERS,
    )
    assert secret_response.status_code == 200

    foreign_revision_id = create_agent_revision(
        client,
        org_id="org_beta",
        requires_secrets=["alpha_token"],
    )
    binding_response = client.post(
        f"/secrets/{secret_response.json()['id']}/bindings",
        json={"agent_revision_id": foreign_revision_id, "binding_name": "alpha_token"},
        headers=AUTH_HEADERS,
    )
    assert binding_response.status_code == 404
    assert binding_response.json()["detail"] == "Agent revision not found"

    missing_revision_list = client.get("/secrets/revisions/rev_missing", headers=AUTH_HEADERS)
    assert missing_revision_list.status_code == 404
    assert missing_revision_list.json()["detail"] == "Agent revision not found"
