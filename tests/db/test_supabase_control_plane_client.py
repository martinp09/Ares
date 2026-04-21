from app.core.config import Settings
from app.db.client import SupabaseControlPlaneClient
from app.models.agents import AgentRecord, AgentRevisionRecord, AgentRevisionState
from app.models.sessions import SessionRecord, SessionStatus
from app.models.session_journal import SessionCompactionState
from app.models.mission_control import MissionControlContactRecord, MissionControlThreadRecord
from app.models.turns import TurnRecord, TurnStatus


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )


def test_supabase_control_plane_client_hydrates_and_persists_text_runtime_tables(monkeypatch) -> None:
    settings = build_settings()
    inserted = []
    patched = []

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        if table == "commands":
            return []
        if table == "approvals":
            return []
        if table == "runs":
            return []
        if table == "events":
            return []
        if table == "artifacts":
            return []
        return []

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        inserted.append((table, rows[0]))
        return [{"id": rows[0]["id"]}]

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        patched.append((table, params, row))
        return [{"id": row["id"]}]

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", fake_patch_rows)

    client = SupabaseControlPlaneClient(settings)
    with client.transaction() as store:
        store.agents["agt_1"] = AgentRecord(
            id="agt_1",
            org_id="org_internal",
            business_id="limitless",
            environment="dev",
            name="Runtime Agent",
            description=None,
            active_revision_id="rev_1",
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-20T00:00:00Z",
        )
        store.agent_revisions["rev_1"] = AgentRevisionRecord(
            id="rev_1",
            agent_id="agt_1",
            revision_number=1,
            state=AgentRevisionState.PUBLISHED,
            config={"prompt": "Work"},
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-20T00:00:00Z",
        )
        store.sessions["ses_1"] = SessionRecord(
            id="ses_1",
            agent_id="agt_1",
            agent_revision_id="rev_1",
            org_id="org_internal",
            business_id="limitless",
            environment="dev",
            status=SessionStatus.ACTIVE,
            timeline=[],
            compaction=SessionCompactionState(),
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-20T00:00:00Z",
        )
        store.turns["trn_1"] = TurnRecord(
            id="trn_1",
            session_id="ses_1",
            agent_id="agt_1",
            agent_revision_id="rev_1",
            org_id="org_internal",
            turn_number=1,
            status=TurnStatus.COMPLETED,
            input_message="Start",
            assistant_message="Done",
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-20T00:00:00Z",
        )
        store.mission_control_threads["mc_1"] = MissionControlThreadRecord(
            id="mc_1",
            business_id="limitless",
            environment="dev",
            channel="sms",
            contact=MissionControlContactRecord(display_name="Taylor"),
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-20T00:00:00Z",
        )

    inserted_tables = {table for table, _ in inserted}
    assert "agents_runtime" in inserted_tables
    assert "agent_revisions_runtime" in inserted_tables
    assert "sessions_runtime" in inserted_tables
    assert "turns_runtime" in inserted_tables
    assert "mission_control_threads_runtime" in inserted_tables


def test_supabase_control_plane_client_rehydrates_core_runs_for_store_reads(monkeypatch) -> None:
    settings = build_settings()

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        if table == "commands":
            return [
                {
                    "id": 101,
                    "business_id": 7,
                    "environment": "dev",
                    "command_type": "run_market_research",
                    "payload": {"topic": "houston"},
                    "idempotency_key": "cmd-1",
                    "policy_result": "safe_autonomous",
                    "status": "queued",
                    "created_at": "2026-04-20T00:00:00Z",
                }
            ]
        if table == "approvals":
            return []
        if table == "runs":
            return [
                {
                    "id": 201,
                    "business_id": 7,
                    "environment": "dev",
                    "command_id": 101,
                    "parent_run_id": None,
                    "replay_reason": None,
                    "trigger_run_id": None,
                    "status": "running",
                    "started_at": None,
                    "completed_at": None,
                    "error_classification": None,
                    "error_message": None,
                    "created_at": "2026-04-20T00:00:00Z",
                    "updated_at": "2026-04-20T00:00:00Z",
                }
            ]
        if table in {"events", "artifacts"}:
            return []
        return []

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", lambda *args, **kwargs: [{"id": "noop"}])
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", lambda *args, **kwargs: [{"id": "noop"}])

    client = SupabaseControlPlaneClient(settings)
    with client.transaction() as store:
        run = store.runs["run_201"]
        assert run.command_id == "cmd_101"
        assert run.command_type == "run_market_research"
        assert run.status == "in_progress"
