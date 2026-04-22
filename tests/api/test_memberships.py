from app.core.config import DEFAULT_INTERNAL_ACTOR_ID, DEFAULT_INTERNAL_ORG_ID
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, org_id: str, actor_id: str, actor_type: str = "user") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def create_org(client, *, headers: dict[str, str], org_id: str, name: str) -> None:
    response = client.post(
        "/organizations",
        json={"id": org_id, "name": name},
        headers=headers,
    )
    assert response.status_code == 200


def test_memberships_api_keeps_internal_runtime_api_key_scope_sane(client) -> None:
    reset_control_plane_state()

    seeded = client.get("/memberships", headers=AUTH_HEADERS)
    assert seeded.status_code == 200
    seeded_memberships = seeded.json()["memberships"]
    assert len(seeded_memberships) == 1
    assert seeded_memberships[0]["actor_id"] == DEFAULT_INTERNAL_ACTOR_ID
    assert seeded_memberships[0]["org_id"] == DEFAULT_INTERNAL_ORG_ID

    created = client.post(
        "/memberships",
        json={
            "actor_id": "actor_jane",
            "actor_type": "user",
            "member_id": "member_jane",
            "name": "Jane Doe",
            "role_name": "viewer",
            "metadata": {"source": "invite"},
        },
        headers=AUTH_HEADERS,
    )
    assert created.status_code == 200
    membership_id = created.json()["id"]
    assert created.json()["org_id"] == DEFAULT_INTERNAL_ORG_ID

    updated = client.post(
        "/memberships",
        json={
            "org_id": DEFAULT_INTERNAL_ORG_ID,
            "actor_id": "actor_jane",
            "actor_type": "user",
            "member_id": "member_jane",
            "name": "Jane Doe",
            "role_name": "admin",
            "metadata": {"source": "sso"},
        },
        headers=AUTH_HEADERS,
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == membership_id
    assert updated.json()["role_name"] == "admin"

    listed = client.get("/memberships", headers=AUTH_HEADERS)
    assert listed.status_code == 200
    memberships = listed.json()["memberships"]
    assert len(memberships) == 2
    assert sorted(membership["actor_id"] for membership in memberships) == ["actor_jane", DEFAULT_INTERNAL_ACTOR_ID]

    detail = client.get(f"/memberships/{membership_id}", headers=AUTH_HEADERS)
    assert detail.status_code == 200
    assert detail.json()["member_id"] == "member_jane"
    assert detail.json()["metadata"] == {"source": "sso"}


def test_memberships_api_rejects_unknown_org(client) -> None:
    reset_control_plane_state()

    missing_org_headers = org_actor_headers(org_id="org_missing", actor_id="actor_jane")
    response = client.post(
        "/memberships",
        json={
            "org_id": "org_missing",
            "actor_id": "actor_jane",
            "actor_type": "user",
        },
        headers=missing_org_headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Organization not found"


def test_memberships_api_is_scoped_to_actor_org_headers(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")

    create_org(client, headers=alpha_headers, org_id="org_alpha", name="Alpha Org")
    create_org(client, headers=beta_headers, org_id="org_beta", name="Beta Org")

    alpha_created = client.post(
        "/memberships",
        json={
            "org_id": "org_alpha",
            "actor_id": "actor_alice",
            "actor_type": "user",
            "member_id": "member_alice",
            "name": "Alice",
            "role_name": "admin",
        },
        headers=alpha_headers,
    )
    beta_created = client.post(
        "/memberships",
        json={
            "org_id": "org_beta",
            "actor_id": "actor_bob",
            "actor_type": "user",
            "member_id": "member_bob",
            "name": "Bob",
            "role_name": "viewer",
        },
        headers=beta_headers,
    )

    assert alpha_created.status_code == 200
    assert beta_created.status_code == 200
    alpha_membership_id = alpha_created.json()["id"]
    beta_membership_id = beta_created.json()["id"]

    alpha_list = client.get("/memberships", headers=alpha_headers)
    beta_list = client.get("/memberships", headers=beta_headers)
    leaked_list = client.get("/memberships?org_id=org_beta", headers=alpha_headers)
    leaked_detail = client.get(f"/memberships/{beta_membership_id}", headers=alpha_headers)
    leaked_write = client.post(
        "/memberships",
        json={
            "org_id": "org_beta",
            "actor_id": "actor_intruder",
            "actor_type": "user",
            "member_id": "member_intruder",
        },
        headers=alpha_headers,
    )

    assert alpha_list.status_code == 200
    assert beta_list.status_code == 200
    assert [membership["id"] for membership in alpha_list.json()["memberships"]] == [alpha_membership_id]
    assert [membership["id"] for membership in beta_list.json()["memberships"]] == [beta_membership_id]
    assert client.get(f"/memberships/{alpha_membership_id}", headers=alpha_headers).status_code == 200
    assert client.get(f"/memberships/{beta_membership_id}", headers=beta_headers).status_code == 200
    assert leaked_list.status_code == 422
    assert leaked_detail.status_code == 404
    assert leaked_write.status_code == 422
