from app.core.config import Settings
from app.db.client import SupabaseControlPlaneClient
from app.models.actors import ActorType
from app.models.agent_installs import AgentInstallRecord
from app.models.agents import AgentRecord, AgentRevisionRecord, AgentRevisionState
from app.models.catalog import CatalogEntryRecord
from app.models.host_adapters import HostAdapterKind
from app.models.sessions import SessionRecord, SessionStatus
from app.models.session_journal import SessionCompactionState
from app.models.mission_control import MissionControlContactRecord, MissionControlThreadRecord
from app.models.organizations import MembershipRecord, OrganizationRecord
from app.models.providers import ProviderKind
from app.models.release_management import ReleaseEventRecord, ReleaseEventType
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


def test_supabase_control_plane_client_persists_core_runtime_deletions(monkeypatch) -> None:
    settings = build_settings()
    rows_by_table = {
        "commands": {
            "101": {
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
        },
        "approvals": {},
        "runs": {
            "201": {
                "id": 201,
                "business_id": 7,
                "environment": "dev",
                "command_id": 101,
                "parent_run_id": None,
                "replay_reason": None,
                "trigger_run_id": None,
                "status": "queued",
                "started_at": None,
                "completed_at": None,
                "error_classification": None,
                "error_message": None,
                "created_at": "2026-04-20T00:00:00Z",
                "updated_at": "2026-04-20T00:00:00Z",
            }
        },
        "events": {
            "301": {
                "id": 301,
                "business_id": 7,
                "environment": "dev",
                "command_id": 101,
                "run_id": 201,
                "event_type": "run_started",
                "payload": {},
                "created_at": "2026-04-20T00:00:00Z",
            }
        },
        "artifacts": {
            "401": {
                "id": 401,
                "business_id": 7,
                "environment": "dev",
                "run_id": 201,
                "artifact_type": "report",
                "data": {},
                "created_at": "2026-04-20T00:00:00Z",
            }
        },
    }
    deleted: list[tuple[str, dict[str, str]]] = []

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        table_rows = list(rows_by_table.get(table, {}).values())
        if params.get("id", "").startswith("eq."):
            row_id = params["id"][3:]
            return [row for row in table_rows if str(row.get("id")) == row_id]
        return table_rows

    def fake_delete_rows(table: str, *, params: dict[str, str], settings=None):
        deleted.append((table, dict(params)))
        row_id = params["id"][3:]
        rows_by_table[table].pop(row_id, None)
        return []

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", lambda *args, **kwargs: [{"id": "noop"}])
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", lambda *args, **kwargs: [{"id": "noop"}])
    monkeypatch.setattr("app.db.control_plane_store_supabase.delete_rows", fake_delete_rows)

    client = SupabaseControlPlaneClient(settings)
    with client.transaction() as store:
        del store.commands["cmd_101"]
        del store.runs["run_201"]

    assert deleted == [
        ("artifacts", {"id": "eq.401"}),
        ("events", {"id": "eq.301"}),
        ("runs", {"id": "eq.201"}),
        ("commands", {"id": "eq.101"}),
    ]


def test_supabase_control_plane_client_restores_core_deletions_when_later_flush_fails(monkeypatch) -> None:
    settings = build_settings()
    command_row = {
        "id": 101,
        "business_id": 7,
        "environment": "dev",
        "command_type": "run_market_research",
        "payload": {"topic": "houston"},
        "idempotency_key": "cmd-1",
        "policy_result": "safe_autonomous",
        "approval_required": False,
        "status": "queued",
        "created_at": "2026-04-20T00:00:00Z",
    }
    run_row = {
        "id": 201,
        "business_id": 7,
        "environment": "dev",
        "command_id": 101,
        "parent_run_id": None,
        "replay_source_run_id": None,
        "replay_reason": None,
        "trigger_run_id": None,
        "status": "queued",
        "started_at": None,
        "completed_at": None,
        "error_classification": None,
        "error_message": None,
        "created_at": "2026-04-20T00:00:00Z",
        "updated_at": "2026-04-20T00:00:00Z",
    }
    event_row = {
        "id": 301,
        "business_id": 7,
        "environment": "dev",
        "command_id": 101,
        "run_id": 201,
        "event_type": "run_started",
        "payload": {},
        "created_at": "2026-04-20T00:00:00Z",
    }
    artifact_row = {
        "id": 401,
        "business_id": 7,
        "environment": "dev",
        "run_id": 201,
        "artifact_type": "report",
        "data": {},
        "created_at": "2026-04-20T00:00:00Z",
    }
    rows_by_table = {
        "commands": {"101": dict(command_row)},
        "approvals": {},
        "runs": {"201": dict(run_row)},
        "events": {"301": dict(event_row)},
        "artifacts": {"401": dict(artifact_row)},
    }

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        table_rows = list(rows_by_table.get(table, {}).values())
        if params.get("id", "").startswith("eq."):
            row_id = params["id"][3:]
            return [row for row in table_rows if str(row.get("id")) == row_id]
        return table_rows

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        if table == "agents_runtime":
            raise RuntimeError("agents flush failed")
        table_rows = rows_by_table.setdefault(table, {})
        inserted = []
        for row in rows:
            payload = dict(row)
            row_id = str(payload["id"])
            if table == "runs" and str(payload["command_id"]) not in rows_by_table["commands"]:
                raise AssertionError("runs restored before commands")
            if table == "events" and str(payload["run_id"]) not in rows_by_table["runs"]:
                raise AssertionError("events restored before runs")
            if table == "artifacts" and str(payload["run_id"]) not in rows_by_table["runs"]:
                raise AssertionError("artifacts restored before runs")
            table_rows[row_id] = payload
            inserted.append(payload)
        return inserted

    def fake_delete_rows(table: str, *, params: dict[str, str], settings=None):
        row_id = params["id"][3:]
        rows_by_table[table].pop(row_id, None)
        return []

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", lambda *args, **kwargs: [{"id": "noop"}])
    monkeypatch.setattr("app.db.control_plane_store_supabase.delete_rows", fake_delete_rows)

    client = SupabaseControlPlaneClient(settings)
    try:
        with client.transaction() as store:
            del store.commands["cmd_101"]
            del store.runs["run_201"]
            store.agents["agt_rollback"] = AgentRecord(
                id="agt_rollback",
                org_id="org_internal",
                business_id="limitless",
                environment="dev",
                name="Rollback Agent",
                description=None,
                active_revision_id=None,
                created_at="2026-04-20T00:00:00Z",
                updated_at="2026-04-20T00:00:00Z",
            )
    except RuntimeError as exc:
        assert str(exc) == "agents flush failed"
    else:
        raise AssertionError("expected flush failure")

    assert rows_by_table["commands"]["101"] == command_row
    assert rows_by_table["runs"]["201"] == run_row
    assert rows_by_table["events"]["301"] == event_row
    assert rows_by_table["artifacts"]["401"] == artifact_row


def test_supabase_control_plane_client_restores_core_updates_when_later_flush_fails(monkeypatch) -> None:
    settings = build_settings()
    command_row = {
        "id": 101,
        "business_id": 7,
        "environment": "dev",
        "command_type": "run_market_research",
        "payload": {"topic": "houston"},
        "idempotency_key": "cmd-1",
        "policy_result": "safe_autonomous",
        "approval_required": False,
        "status": "queued",
        "created_at": "2026-04-20T00:00:00Z",
    }
    run_row = {
        "id": 201,
        "business_id": 7,
        "environment": "dev",
        "command_id": 101,
        "parent_run_id": None,
        "replay_source_run_id": None,
        "replay_reason": None,
        "trigger_run_id": None,
        "status": "queued",
        "started_at": None,
        "completed_at": None,
        "error_classification": None,
        "error_message": None,
        "created_at": "2026-04-20T00:00:00Z",
        "updated_at": "2026-04-20T00:00:00Z",
    }
    rows_by_table = {
        "commands": {"101": dict(command_row)},
        "approvals": {},
        "runs": {"201": dict(run_row)},
        "events": {},
        "artifacts": {},
    }

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        return list(rows_by_table.get(table, {}).values())

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        row_id = params["id"][3:]
        payload = dict(rows_by_table[table][row_id])
        payload.update(row)
        rows_by_table[table][row_id] = payload
        return [payload]

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        if table == "agents_runtime":
            raise RuntimeError("agents flush failed")
        return rows

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", fake_patch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.delete_rows", lambda *args, **kwargs: [])

    client = SupabaseControlPlaneClient(settings)
    try:
        with client.transaction() as store:
            run = store.runs["run_201"]
            run.status = "in_progress"
            store.runs["run_201"] = run
            store.agents["agt_rollback"] = AgentRecord(
                id="agt_rollback",
                org_id="org_internal",
                business_id="limitless",
                environment="dev",
                name="Rollback Agent",
                description=None,
                active_revision_id=None,
                created_at="2026-04-20T00:00:00Z",
                updated_at="2026-04-20T00:00:00Z",
            )
    except RuntimeError as exc:
        assert str(exc) == "agents flush failed"
    else:
        raise AssertionError("expected flush failure")

    assert rows_by_table["commands"]["101"] == command_row
    assert rows_by_table["runs"]["201"] == run_row


def test_supabase_control_plane_client_restores_parent_runs_before_child_runs(monkeypatch) -> None:
    settings = build_settings()
    rows_by_table = {
        "commands": {
            "101": {
                "id": 101,
                "business_id": 7,
                "environment": "dev",
                "command_type": "run_market_research",
                "payload": {},
                "idempotency_key": "cmd-1",
                "policy_result": "safe_autonomous",
                "status": "queued",
                "created_at": "2026-04-20T00:00:00Z",
            },
            "102": {
                "id": 102,
                "business_id": 7,
                "environment": "dev",
                "command_type": "run_market_research",
                "payload": {},
                "idempotency_key": "cmd-2",
                "policy_result": "safe_autonomous",
                "status": "queued",
                "created_at": "2026-04-20T00:00:00Z",
            },
        },
        "approvals": {},
        "runs": {
            "201": {
                "id": 201,
                "business_id": 7,
                "environment": "dev",
                "command_id": 101,
                "parent_run_id": None,
                "replay_reason": None,
                "trigger_run_id": None,
                "status": "queued",
                "started_at": None,
                "completed_at": None,
                "error_classification": None,
                "error_message": None,
                "created_at": "2026-04-20T00:00:00Z",
                "updated_at": "2026-04-20T00:00:00Z",
            },
            "202": {
                "id": 202,
                "business_id": 7,
                "environment": "dev",
                "command_id": 102,
                "parent_run_id": 201,
                "replay_reason": "retry",
                "trigger_run_id": None,
                "status": "queued",
                "started_at": None,
                "completed_at": None,
                "error_classification": None,
                "error_message": None,
                "created_at": "2026-04-20T00:01:00Z",
                "updated_at": "2026-04-20T00:01:00Z",
            },
        },
        "events": {},
        "artifacts": {},
    }
    restored_runs: list[str] = []

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        return list(rows_by_table.get(table, {}).values())

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        if table == "agents_runtime":
            raise RuntimeError("agents flush failed")
        for row in rows:
            row_id = str(row["id"])
            if table == "runs":
                parent_id = row.get("parent_run_id")
                if parent_id is not None and str(parent_id) not in rows_by_table["runs"]:
                    raise AssertionError("child run restored before parent run")
                restored_runs.append(row_id)
            rows_by_table.setdefault(table, {})[row_id] = dict(row)
        return rows

    def fake_delete_rows(table: str, *, params: dict[str, str], settings=None):
        rows_by_table[table].pop(params["id"][3:], None)
        return []

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", lambda *args, **kwargs: [{"id": "noop"}])
    monkeypatch.setattr("app.db.control_plane_store_supabase.delete_rows", fake_delete_rows)

    client = SupabaseControlPlaneClient(settings)
    try:
        with client.transaction() as store:
            store.runs.clear()
            store.commands.clear()
            store.agents["agt_rollback"] = AgentRecord(
                id="agt_rollback",
                org_id="org_internal",
                business_id="limitless",
                environment="dev",
                name="Rollback Agent",
                description=None,
                active_revision_id=None,
                created_at="2026-04-20T00:00:00Z",
                updated_at="2026-04-20T00:00:00Z",
            )
    except RuntimeError as exc:
        assert str(exc) == "agents flush failed"
    else:
        raise AssertionError("expected flush failure")

    assert restored_runs == ["201", "202"]


def test_supabase_control_plane_client_persists_enterprise_tables(monkeypatch) -> None:
    settings = build_settings()
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

    client = SupabaseControlPlaneClient(settings)
    with client.transaction() as store:
        store.organizations["org_alpha"] = OrganizationRecord(
            id="org_alpha",
            name="Alpha Org",
            slug="alpha-org",
            metadata={"segment": "enterprise"},
            is_internal=False,
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-20T00:00:00Z",
        )
        store.memberships["mbr_alpha_actor"] = MembershipRecord(
            id="mbr_alpha_actor",
            org_id="org_alpha",
            actor_id="actor_alpha",
            actor_type=ActorType.USER,
            member_id="actor_alpha",
            name="Alpha Operator",
            role_name="owner",
            metadata={},
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-20T00:00:00Z",
        )
        store.catalog_entries["cat_alpha"] = CatalogEntryRecord(
            id="cat_alpha",
            org_id="org_alpha",
            agent_id="agt_1",
            agent_revision_id="rev_1",
            slug="alpha-runtime",
            name="Alpha Runtime",
            summary="Enterprise runtime package",
            description=None,
            host_adapter_kind=HostAdapterKind.TRIGGER_DEV,
            provider_kind=ProviderKind.ANTHROPIC,
            metadata={},
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-20T00:00:00Z",
        )
        store.agent_installs["ins_alpha"] = AgentInstallRecord(
            id="ins_alpha",
            org_id="org_alpha",
            catalog_entry_id="cat_alpha",
            source_agent_id="agt_1",
            source_agent_revision_id="rev_1",
            installed_agent_id="agt_2",
            installed_agent_revision_id="rev_2",
            business_id="limitless",
            environment="dev",
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-20T00:00:00Z",
        )
        store.release_events["rel_alpha"] = ReleaseEventRecord(
            id="rel_alpha",
            org_id="org_alpha",
            agent_id="agt_1",
            event_type=ReleaseEventType.PUBLISH,
            actor_id="actor_alpha",
            actor_type=ActorType.USER,
            target_revision_id="rev_1",
            resulting_active_revision_id="rev_1",
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-20T00:00:00Z",
        )

    organization_row = rows_by_table["organizations_runtime"]["org_alpha"]
    assert organization_row["name"] == "Alpha Org"
    assert organization_row["slug"] == "alpha-org"
    assert organization_row["is_internal"] is False

    membership_row = rows_by_table["memberships_runtime"]["mbr_alpha_actor"]
    assert membership_row["org_id"] == "org_alpha"
    assert membership_row["actor_id"] == "actor_alpha"

    catalog_row = rows_by_table["catalog_entries_runtime"]["cat_alpha"]
    assert catalog_row["org_id"] == "org_alpha"
    assert catalog_row["slug"] == "alpha-runtime"

    install_row = rows_by_table["agent_installs_runtime"]["ins_alpha"]
    assert install_row["catalog_entry_id"] == "cat_alpha"
    assert install_row["installed_agent_id"] == "agt_2"

    with client.transaction() as reloaded_store:
        org = reloaded_store.organizations.get("org_alpha")
        assert org is not None
        assert org.slug == "alpha-org"
        assert org.name == "Alpha Org"

        membership = reloaded_store.memberships.get("mbr_alpha_actor")
        assert membership is not None
        assert membership.actor_id == "actor_alpha"
        assert membership.role_name == "owner"

        catalog = reloaded_store.catalog_entries.get("cat_alpha")
        assert catalog is not None
        assert catalog.slug == "alpha-runtime"
        assert catalog.provider_kind == ProviderKind.ANTHROPIC

        install = reloaded_store.agent_installs.get("ins_alpha")
        assert install is not None
        assert install.business_id == "limitless"
        assert install.environment == "dev"

        release_event = reloaded_store.release_events.get("rel_alpha")
        assert release_event is not None
        assert release_event.event_type == ReleaseEventType.PUBLISH
        assert release_event.target_revision_id == "rev_1"


def test_supabase_control_plane_client_persists_ares_snapshots(monkeypatch) -> None:
    settings = build_settings()
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

    client = SupabaseControlPlaneClient(settings)
    with client.transaction() as store:
        store.ares_plans_by_scope[("limitless", "dev")] = {
            "business_id": "limitless",
            "environment": "dev",
            "goal": "Plan probate outreach in Harris county.",
            "generated_at": "2026-04-20T00:00:00Z",
        }
        store.ares_execution_runs_by_scope[("limitless", "dev")] = {
            "run_id": "ares_exec_001",
            "business_id": "limitless",
            "environment": "dev",
            "lead_count": 1,
            "failure_count": 0,
            "generated_at": "2026-04-20T00:00:00Z",
        }
        store.ares_operator_runs_by_scope[("limitless", "dev")] = {
            "run_id": "ares_operator_001",
            "objective_id": "obj_001",
            "business_id": "limitless",
            "environment": "dev",
            "generated_at": "2026-04-20T00:00:00Z",
        }

    with client.transaction() as reloaded_store:
        scope = ("limitless", "dev")
        plan_snapshot = reloaded_store.ares_plans_by_scope.get(scope)
        assert plan_snapshot is not None
        assert plan_snapshot["goal"] == "Plan probate outreach in Harris county."
        assert plan_snapshot["business_id"] == "limitless"

        execution_snapshot = reloaded_store.ares_execution_runs_by_scope.get(scope)
        assert execution_snapshot is not None
        assert execution_snapshot["run_id"] == "ares_exec_001"
        assert execution_snapshot["lead_count"] == 1

        operator_snapshot = reloaded_store.ares_operator_runs_by_scope.get(scope)
        assert operator_snapshot is not None
        assert operator_snapshot["run_id"] == "ares_operator_001"
        assert operator_snapshot["objective_id"] == "obj_001"
