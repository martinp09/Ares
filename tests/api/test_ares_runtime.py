from app.core.config import Settings
from app.db.client import SupabaseControlPlaneClient
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_ares_run_executes_phase1_runtime_path(client) -> None:
    response = client.post(
        "/ares/run",
        json={
            "run": {
                "counties": ["harris", "travis"],
                "include_briefs": True,
                "include_drafts": True,
            },
            "probate_records": [
                {
                    "county": "harris",
                    "source_lane": "probate",
                    "property_address": "123 Main St, Houston, TX",
                    "owner_name": "Estate of Jane Doe",
                },
                {
                    "county": "travis",
                    "source_lane": "probate",
                    "property_address": "88 River Rd, Austin, TX",
                    "owner_name": "Alex Rivers",
                },
            ],
            "tax_records": [
                {
                    "county": "harris",
                    "source_lane": "tax_delinquent",
                    "property_address": "123 Main St, Houston, TX",
                    "owner_name": "Estate of Jane Doe",
                },
                {
                    "county": "dallas",
                    "source_lane": "tax_delinquent",
                    "property_address": "999 Elm St, Dallas, TX",
                    "owner_name": "Estate of Filtered Out",
                },
            ],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counties"] == ["harris", "travis"]
    assert body["lead_count"] == 2
    assert body["include_briefs"] is True
    assert body["include_drafts"] is True

    ranked = body["ranked_leads"]
    assert ranked[0]["rank"] == 1
    assert ranked[0]["tier"] == "PROBATE_WITH_VERIFIED_TAX"
    assert ranked[0]["lead"]["county"] == "harris"
    assert ranked[0]["tax_delinquent"] is True
    assert ranked[0]["brief"]["rank"] == 1
    assert ranked[0]["draft"]["approval_status"] == "pending_human_approval"

    assert ranked[1]["rank"] == 2
    assert ranked[1]["tier"] == "PROBATE_ONLY"
    assert ranked[1]["lead"]["county"] == "travis"
    assert ranked[1]["tax_delinquent"] is False


def test_ares_run_honors_copy_flags(client) -> None:
    response = client.post(
        "/ares/run",
        json={
            "run": {
                "counties": ["harris"],
                "include_briefs": False,
                "include_drafts": False,
            },
            "probate_records": [
                {
                    "county": "harris",
                    "source_lane": "probate",
                    "property_address": "123 Main St, Houston, TX",
                }
            ],
            "tax_records": [],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lead_count"] == 1
    assert body["include_briefs"] is False
    assert body["include_drafts"] is False
    assert body["ranked_leads"][0]["brief"] is None
    assert body["ranked_leads"][0]["draft"] is None


def test_ares_execution_run_triggers_bounded_execution_path(client) -> None:
    response = client.post(
        "/ares/execution/run",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "market": "texas",
            "counties": ["harris", "travis"],
            "action_budget": 6,
            "retry_limit": 1,
            "approved_tools": ["county_fetch"],
            "county_payloads": {
                "harris": {
                    "probate": [
                        {
                            "property_address": "123 Main St, Houston, TX",
                            "owner_name": "Estate of Jane Doe",
                        }
                    ],
                    "tax": [
                        {
                            "property_address": "123 Main St, Houston, TX",
                            "owner_name": "Estate of Jane Doe",
                        }
                    ],
                },
                "travis": {
                    "probate": [
                        {
                            "property_address": "88 River Rd, Austin, TX",
                            "owner_name": "Alex Rivers",
                        }
                    ],
                    "tax": [],
                },
            },
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["business_id"] == "limitless"
    assert body["environment"] == "dev"
    assert body["state"] == "completed"
    assert body["lead_count"] == 2
    assert body["interrupted"] is False
    assert body["failures"] == []
    assert body["ranked_leads"][0]["tier"] == "PROBATE_WITH_VERIFIED_TAX"
    assert body["ranked_leads"][0]["tax_delinquent"] is True
    assert body["ranked_leads"][1]["tier"] == "PROBATE_ONLY"


def test_ares_execution_run_excludes_tax_only_non_estate_records(client) -> None:
    response = client.post(
        "/ares/execution/run",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "market": "texas",
            "counties": ["harris"],
            "action_budget": 6,
            "retry_limit": 1,
            "approved_tools": ["county_fetch"],
            "county_payloads": {
                "harris": {
                    "probate": [],
                    "tax": [
                        {
                            "property_address": "999 Main St, Houston, TX",
                            "owner_name": "John Doe",
                        }
                    ],
                }
            },
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lead_count"] == 0
    assert body["ranked_leads"] == []


def test_autonomy_visibility_execution_snapshot_survives_supabase_transaction_boundary(client, monkeypatch) -> None:
    reset_control_plane_state()
    settings = Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    rows_by_table: dict[str, dict[str, dict]] = {}

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        table_rows = list(rows_by_table.get(table, {}).values())
        filtered = []
        for row in table_rows:
            matches = True
            for key, value in params.items():
                if key in {"select", "order", "limit", "offset"}:
                    continue
                if isinstance(value, str) and value.startswith("eq.") and str(row.get(key)) != value[3:]:
                    matches = False
                    break
            if matches:
                filtered.append(row)
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
        if row_id.startswith("eq."):
            existing_id = row_id[3:]
        else:
            existing_id = str(row.get("id", len(table_rows) + 1))
        payload = dict(table_rows.get(existing_id, {}))
        payload.update(row)
        payload["id"] = existing_id
        table_rows[existing_id] = payload
        return [payload]

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", fake_patch_rows)

    supabase_client = SupabaseControlPlaneClient(settings)
    monkeypatch.setattr("app.api.ares._control_plane_client", supabase_client)
    monkeypatch.setattr("app.services.mission_control_service.mission_control_service.client", supabase_client)

    execute = client.post(
        "/ares/execution/run",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "market": "texas",
            "counties": ["harris"],
            "action_budget": 5,
            "retry_limit": 1,
            "approved_tools": ["county_fetch"],
            "county_payloads": {
                "harris": {
                    "probate": [
                        {
                            "property_address": "123 Main St, Houston, TX",
                            "owner_name": "Estate of Jane Doe",
                        }
                    ],
                    "tax": [
                        {
                            "property_address": "123 Main St, Houston, TX",
                            "owner_name": "Estate of Jane Doe",
                        }
                    ],
                }
            },
        },
        headers=AUTH_HEADERS,
    )
    assert execute.status_code == 200
    run_id = execute.json()["run_id"]

    visibility = client.get(
        "/mission-control/autonomy-visibility?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )
    assert visibility.status_code == 200
    body = visibility.json()

    assert body["execution_review"] is not None
    assert body["execution_review"]["run_id"] == run_id
