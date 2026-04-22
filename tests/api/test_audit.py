import pytest

from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def audit_headers(*, org_id: str = "org_internal", actor_id: str = "ares-runtime", actor_type: str = "service") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def test_audit_api_derives_actor_context_scopes_reads_and_scrubs_metadata(client) -> None:
    reset_control_plane_state()

    alpha_headers = audit_headers(org_id="org_alpha", actor_id="actor_alpha", actor_type="user")
    beta_headers = audit_headers(org_id="org_beta", actor_id="actor_beta", actor_type="service")

    alpha_response = client.post(
        "/audit",
        json={
            "event_type": "secret_created",
            "summary": "Created secret",
            "resource_type": "secret",
            "resource_id": "sec_alpha",
            "metadata": {
                "secret_value": "super-secret",
                "nested": {"access_token": "nested-secret"},
                "safe": "kept",
            },
        },
        headers=alpha_headers,
    )
    beta_response = client.post(
        "/audit",
        json={
            "event_type": "secret_accessed",
            "summary": "Read secret metadata",
            "resource_type": "secret",
            "resource_id": "sec_beta",
            "metadata": {"safe": "visible"},
        },
        headers=beta_headers,
    )

    assert alpha_response.status_code == 200
    assert beta_response.status_code == 200
    alpha_body = alpha_response.json()
    assert alpha_body["org_id"] == "org_alpha"
    assert alpha_body["actor_id"] == "actor_alpha"
    assert alpha_body["actor_type"] == "user"
    assert alpha_body["metadata"] == {
        "secret_value": "[redacted]",
        "nested": {"access_token": "[redacted]"},
        "safe": "kept",
    }

    listing = client.get("/audit", headers=alpha_headers)
    assert listing.status_code == 200
    events = listing.json()["events"]
    assert [event["org_id"] for event in events] == ["org_alpha"]
    assert [event["actor_id"] for event in events] == ["actor_alpha"]
    assert events[0]["metadata"] == alpha_body["metadata"]

    mismatched_listing = client.get("/audit?org_id=org_beta", headers=alpha_headers)
    assert mismatched_listing.status_code == 422
    assert mismatched_listing.json()["detail"] == "Org id must match actor context"


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        ({"org_id": "org_beta"}, "Org id must match actor context"),
        ({"actor_id": "actor_beta"}, "Actor id must match actor context"),
        ({"actor_type": "service"}, "Actor type must match actor context"),
    ],
)
def test_audit_api_rejects_conflicting_actor_context_fields(client, payload: dict[str, str], detail: str) -> None:
    reset_control_plane_state()

    response = client.post(
        "/audit",
        json={
            "event_type": "secret_created",
            "summary": "Created secret",
            **payload,
        },
        headers=audit_headers(org_id="org_alpha", actor_id="actor_alpha", actor_type="user"),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == detail
