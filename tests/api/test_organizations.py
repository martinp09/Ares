from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, org_id: str, actor_id: str, actor_type: str = "user") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def test_organizations_api_keeps_internal_runtime_api_key_scope_sane(client) -> None:
    reset_control_plane_state()

    seeded = client.get("/organizations", headers=AUTH_HEADERS)
    assert seeded.status_code == 200
    assert [organization["id"] for organization in seeded.json()["organizations"]] == [DEFAULT_INTERNAL_ORG_ID]

    updated = client.post(
        "/organizations",
        json={
            "name": "Internal Ops",
            "metadata": {"tier": "dogfood"},
            "is_internal": True,
        },
        headers=AUTH_HEADERS,
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == DEFAULT_INTERNAL_ORG_ID

    detail = client.get(f"/organizations/{DEFAULT_INTERNAL_ORG_ID}", headers=AUTH_HEADERS)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Internal Ops"
    assert detail.json()["metadata"] == {"tier": "dogfood"}

    listed = client.get("/organizations", headers=AUTH_HEADERS)
    assert listed.status_code == 200
    assert [organization["id"] for organization in listed.json()["organizations"]] == [DEFAULT_INTERNAL_ORG_ID]


def test_organizations_api_is_scoped_to_actor_org_headers(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")

    alpha_created = client.post(
        "/organizations",
        json={"id": "org_alpha", "name": "Alpha Org", "slug": "alpha-org"},
        headers=alpha_headers,
    )
    beta_created = client.post(
        "/organizations",
        json={"id": "org_beta", "name": "Beta Org", "slug": "beta-org"},
        headers=beta_headers,
    )

    assert alpha_created.status_code == 200
    assert beta_created.status_code == 200

    alpha_list = client.get("/organizations", headers=alpha_headers)
    beta_list = client.get("/organizations", headers=beta_headers)
    leaked_detail = client.get("/organizations/org_beta", headers=alpha_headers)
    leaked_write = client.post(
        "/organizations",
        json={"id": "org_beta", "name": "Wrong Org"},
        headers=alpha_headers,
    )
    slug_collision = client.post(
        "/organizations",
        json={"id": "org_alpha", "name": "Alpha Org Renamed", "slug": "beta-org"},
        headers=alpha_headers,
    )
    slug_rename = client.post(
        "/organizations",
        json={"id": "org_alpha", "name": "Alpha Org Renamed", "slug": "alpha-renamed"},
        headers=alpha_headers,
    )
    slug_reuse = client.post(
        "/organizations",
        json={"id": "org_gamma", "name": "Gamma Org", "slug": "alpha-org"},
        headers=org_actor_headers(org_id="org_gamma", actor_id="actor_gamma"),
    )

    assert alpha_list.status_code == 200
    assert beta_list.status_code == 200
    assert [organization["id"] for organization in alpha_list.json()["organizations"]] == ["org_alpha"]
    assert [organization["id"] for organization in beta_list.json()["organizations"]] == ["org_beta"]
    assert client.get("/organizations/org_alpha", headers=alpha_headers).status_code == 200
    assert client.get("/organizations/org_beta", headers=beta_headers).status_code == 200
    assert leaked_detail.status_code == 404
    assert leaked_write.status_code == 422
    assert slug_collision.status_code == 422
    assert "slug already exists" in slug_collision.json()["detail"].lower()
    assert slug_rename.status_code == 200
    assert slug_rename.json()["slug"] == "alpha-renamed"
    assert slug_reuse.status_code == 200
    assert slug_reuse.json()["id"] == "org_gamma"
    assert client.get("/organizations/org_beta", headers=beta_headers).json()["name"] == "Beta Org"
