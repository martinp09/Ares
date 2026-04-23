from app.core.config import DEFAULT_INTERNAL_ORG_ID, Settings
from app.db.client import SupabaseControlPlaneClient
from app.db.organizations import OrganizationsRepository
from app.services.organization_service import organization_service
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, org_id: str, actor_id: str, actor_type: str = "user") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def _build_supabase_client(monkeypatch) -> SupabaseControlPlaneClient:
    settings = Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    rows_by_table: dict[str, dict[str, dict]] = {}

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        table_rows = list(rows_by_table.get(table, {}).values())
        filtered: list[dict] = []
        for row in table_rows:
            matches = True
            for key, value in params.items():
                if key in {"select", "order", "limit", "offset"}:
                    continue
                if isinstance(value, str) and value.startswith("eq.") and str(row.get(key)) != value[3:]:
                    matches = False
                    break
            if matches:
                filtered.append(dict(row))
        order = params.get("order")
        if isinstance(order, str) and order.endswith(".asc"):
            sort_key = order[:-4]
            filtered.sort(key=lambda row: str(row.get(sort_key) or ""))
        return filtered

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        table_rows = rows_by_table.setdefault(table, {})
        inserted = []
        for row in rows:
            payload = dict(row)
            row_id = str(payload.get("id", len(table_rows) + 1))
            payload["id"] = row_id
            table_rows[row_id] = payload
            inserted.append(payload)
        return inserted

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        table_rows = rows_by_table.setdefault(table, {})
        row_id = params.get("id", "")
        existing_id = row_id[3:] if row_id.startswith("eq.") else str(row.get("id", len(table_rows) + 1))
        payload = dict(table_rows.get(existing_id, {}))
        payload.update(row)
        payload["id"] = existing_id
        table_rows[existing_id] = payload
        return [payload]

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", fake_patch_rows)
    return SupabaseControlPlaneClient(settings)


def test_organizations_api_keeps_internal_runtime_api_key_scope_sane(client) -> None:
    reset_control_plane_state()

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    beta_headers = org_actor_headers(org_id="org_beta", actor_id="actor_beta")

    seeded = client.get("/organizations", headers=AUTH_HEADERS)
    assert seeded.status_code == 200
    assert [organization["id"] for organization in seeded.json()["organizations"]] == [DEFAULT_INTERNAL_ORG_ID]

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
    assert [organization["id"] for organization in listed.json()["organizations"]] == [
        DEFAULT_INTERNAL_ORG_ID,
        "org_alpha",
        "org_beta",
    ]


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


def test_organizations_api_persists_across_supabase_transaction_boundary(client, monkeypatch) -> None:
    reset_control_plane_state()
    supabase_client = _build_supabase_client(monkeypatch)
    monkeypatch.setattr(
        organization_service,
        "organizations_repository",
        OrganizationsRepository(client=supabase_client),
    )

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    create_response = client.post(
        "/organizations",
        json={"id": "org_alpha", "name": "Alpha Org", "slug": "alpha-org"},
        headers=alpha_headers,
    )
    assert create_response.status_code == 200
    assert create_response.json()["id"] == "org_alpha"

    listed = client.get("/organizations", headers=AUTH_HEADERS)
    assert listed.status_code == 200
    assert [organization["id"] for organization in listed.json()["organizations"]] == [
        DEFAULT_INTERNAL_ORG_ID,
        "org_alpha",
    ]

    detail = client.get("/organizations/org_alpha", headers=alpha_headers)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Alpha Org"
