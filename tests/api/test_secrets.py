from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_secret_api_redacts_values_and_lists_revision_bindings(client) -> None:
    reset_control_plane_state()

    agent_response = client.post(
        "/agents",
        json={"name": "Secret Agent", "config": {"prompt": "Handle secrets"}},
        headers=AUTH_HEADERS,
    )
    assert agent_response.status_code == 200
    revision_id = agent_response.json()["revisions"][0]["id"]

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

    revision_bindings = client.get(f"/secrets/revisions/{revision_id}", headers=AUTH_HEADERS)
    assert revision_bindings.status_code == 200
    assert revision_bindings.json()["bindings"][0]["binding_name"] == "resend_api_key"
