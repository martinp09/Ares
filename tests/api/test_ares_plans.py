from app.core.config import Settings
from app.db.client import SupabaseControlPlaneClient
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_ares_plans_route_returns_planner_contract(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/ares/plans",
        json={
            "goal": "Find probate plus tax delinquent leads in Harris and Travis counties.",
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()

    assert body["business_id"] == "limitless"
    assert body["environment"] == "dev"
    assert body["goal"] == "Find probate plus tax delinquent leads in Harris and Travis counties."
    assert "Approval required before any side-effecting step" in body["explanation"]
    assert body["plan"]["source_lanes"] == ["probate", "tax_delinquent"]
    assert body["plan"]["counties"] == ["harris", "travis"]
    assert body["plan"]["steps"][-1]["action_type"] == "side_effecting"
    assert body["plan"]["steps"][-1]["requires_approval"] is True
    assert body["generated_at"]


def test_mission_control_autonomy_visibility_surfaces_latest_planner_output(client) -> None:
    reset_control_plane_state()

    plan_response = client.post(
        "/ares/plans",
        json={
            "goal": "Plan probate outreach in Dallas county.",
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=AUTH_HEADERS,
    )
    assert plan_response.status_code == 200

    visibility = client.get(
        "/mission-control/autonomy-visibility?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )
    assert visibility.status_code == 200
    body = visibility.json()

    assert body["planner_review"]["goal"] == "Plan probate outreach in Dallas county."
    assert body["planner_review"]["business_id"] == "limitless"
    assert body["planner_review"]["environment"] == "dev"
    assert body["planner_review"]["plan"]["counties"] == ["dallas"]
    assert body["planner_review"]["plan"]["source_lanes"] == ["probate"]


def test_ares_plans_route_rejects_whitespace_only_goal(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/ares/plans",
        json={
            "goal": "   ",
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422


def test_autonomy_visibility_planner_snapshot_survives_supabase_transaction_boundary(client, monkeypatch) -> None:
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

    plan_response = client.post(
        "/ares/plans",
        json={
            "goal": "Plan probate outreach in Dallas county.",
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=AUTH_HEADERS,
    )
    assert plan_response.status_code == 200

    visibility = client.get(
        "/mission-control/autonomy-visibility?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )
    assert visibility.status_code == 200
    body = visibility.json()

    assert body["planner_review"] is not None
    assert body["planner_review"]["goal"] == "Plan probate outreach in Dallas county."
