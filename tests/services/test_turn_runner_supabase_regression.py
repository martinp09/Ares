from app.core.config import Settings
from app.db.client import SupabaseControlPlaneClient
from app.db.control_plane_store_supabase import hydrate_control_plane_store, persist_control_plane_store
from app.db.sessions import SessionsRepository
from app.db.turn_events import TurnEventsRepository
from app.models.session_journal import SessionCompactionState
from app.models.sessions import SessionRecord, SessionStatus
from app.models.turns import TurnStartRequest
from app.services.turn_runner_service import TurnRunnerService


def test_turn_runner_preserves_session_timeline_under_supabase_backend(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    tables: dict[str, dict[str, dict]] = {
        "sessions_runtime": {
            "ses_1": {
                "id": "ses_1",
                "org_id": "org_internal",
                "business_id": "limitless",
                "environment": "dev",
                "agent_id": "agt_1",
                "agent_revision_id": "rev_1",
                "status": "active",
                "payload_json": {
                    "id": "ses_1",
                    "agent_id": "agt_1",
                    "agent_revision_id": "rev_1",
                    "org_id": "org_internal",
                    "business_id": "limitless",
                    "environment": "dev",
                    "status": "active",
                    "timeline": [],
                    "compaction": SessionCompactionState().model_dump(mode="json"),
                    "created_at": "2026-04-20T00:00:00Z",
                    "updated_at": "2026-04-20T00:00:00Z",
                },
                "created_at": "2026-04-20T00:00:00Z",
                "updated_at": "2026-04-20T00:00:00Z",
            }
        },
        "turns_runtime": {},
        "turn_events_runtime": {},
    }

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        if table in {"commands", "approvals", "runs", "events", "artifacts"}:
            return []
        rows = list(tables.get(table, {}).values())
        if "id" in params and params["id"].startswith("eq."):
            key = params["id"][3:]
            rows = [row for row in rows if row["id"] == key]
        if "session_id" in params and params["session_id"].startswith("eq."):
            key = params["session_id"][3:]
            rows = [row for row in rows if row.get("session_id") == key]
        if "turn_id" in params and params["turn_id"].startswith("eq."):
            key = params["turn_id"][3:]
            rows = [row for row in rows if row.get("turn_id") == key]
        if params.get("order") == "updated_at.asc":
            rows.sort(key=lambda row: row.get("updated_at") or "")
        elif params.get("order") == "created_at.asc":
            rows.sort(key=lambda row: row.get("created_at") or "")
        elif params.get("order") == "id.asc":
            rows.sort(key=lambda row: row["id"])
        return rows

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        for row in rows:
            tables.setdefault(table, {})[row["id"]] = dict(row)
        return [{"id": rows[0]["id"]}]

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        key = params["id"][3:]
        tables.setdefault(table, {})[key] = dict(row)
        return [{"id": key}]

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", fake_patch_rows)

    client = SupabaseControlPlaneClient(settings)
    sessions_repository = SessionsRepository(client)
    turn_events_repository = TurnEventsRepository(client)
    turn_runner = TurnRunnerService(
        sessions_repository=sessions_repository,
        turn_events_repository=turn_events_repository,
    )

    turn_runner.start_turn(
        "ses_1",
        TurnStartRequest(
            input_message="Check title chain",
            assistant_message="Title chain checked.",
        ),
        org_id="org_internal",
    )

    session = sessions_repository.get("ses_1")
    assert session is not None
    assert [entry.event_type for entry in session.timeline] == ["turn_started", "turn_completed"]
    assert len(tables["turns_runtime"]) == 1
    assert len(tables["turn_events_runtime"]) == 2


def test_control_plane_store_does_not_mutate_append_only_events(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    tables: dict[str, dict[str, dict]] = {
        "businesses": {
            "1": {"business_id": "1", "slug": "limitless", "environment": "dev"},
        },
        "commands": {},
        "approvals": {},
        "runs": {},
        "events": {
            "1": {
                "id": "1",
                "business_id": "1",
                "environment": "dev",
                "command_id": None,
                "run_id": None,
                "event_type": "run_created",
                "payload": {},
                "created_at": "2026-04-20T00:00:00Z",
            }
        },
        "artifacts": {},
    }
    patched: list[str] = []
    deleted: list[str] = []

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        return list(tables.get(table, {}).values())

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        for row in rows:
            tables.setdefault(table, {})[str(row["id"])] = dict(row)
        return rows

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        patched.append(table)
        return [{"id": params["id"][3:]}]

    def fake_delete_rows(table: str, *, params: dict[str, str], settings=None):
        deleted.append(table)
        return []

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", fake_patch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.delete_rows", fake_delete_rows)

    store = hydrate_control_plane_store(settings)
    persist_control_plane_store(store, settings)

    assert "events" not in patched
    assert "events" not in deleted
