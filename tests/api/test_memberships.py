from app.core.config import DEFAULT_INTERNAL_ACTOR_ID, DEFAULT_INTERNAL_ORG_ID, Settings
from app.db.client import SupabaseControlPlaneClient
from app.db.memberships import MembershipsRepository
from app.db.organizations import OrganizationsRepository
from app.services.access_service import access_service
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


def test_memberships_api_persists_across_supabase_transaction_boundary(client, monkeypatch) -> None:
    reset_control_plane_state()
    supabase_client = _build_supabase_client(monkeypatch)
    monkeypatch.setattr(
        organization_service,
        "organizations_repository",
        OrganizationsRepository(client=supabase_client),
    )
    monkeypatch.setattr(
        access_service,
        "organizations_repository",
        OrganizationsRepository(client=supabase_client),
    )
    monkeypatch.setattr(
        access_service,
        "memberships_repository",
        MembershipsRepository(client=supabase_client),
    )

    alpha_headers = org_actor_headers(org_id="org_alpha", actor_id="actor_alpha")
    create_org(client, headers=alpha_headers, org_id="org_alpha", name="Alpha Org")

    created = client.post(
        "/memberships",
        json={
            "org_id": "org_alpha",
            "actor_id": "actor_alice",
            "actor_type": "user",
            "member_id": "member_alice",
            "name": "Alice",
            "role_name": "viewer",
            "metadata": {"source": "invite"},
        },
        headers=alpha_headers,
    )
    assert created.status_code == 200
    membership_id = created.json()["id"]

    updated = client.post(
        "/memberships",
        json={
            "org_id": "org_alpha",
            "actor_id": "actor_alice",
            "actor_type": "user",
            "member_id": "member_alice",
            "name": "Alice",
            "role_name": "admin",
            "metadata": {"source": "sso"},
        },
        headers=alpha_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == membership_id
    assert updated.json()["role_name"] == "admin"

    listed = client.get("/memberships", headers=alpha_headers)
    assert listed.status_code == 200
    assert [membership["id"] for membership in listed.json()["memberships"]] == [membership_id]

    detail = client.get(f"/memberships/{membership_id}", headers=alpha_headers)
    assert detail.status_code == 200
    assert detail.json()["role_name"] == "admin"
    assert detail.json()["metadata"] == {"source": "sso"}
