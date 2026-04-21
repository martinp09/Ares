from app.core.config import Settings
from app.db.approvals import ApprovalsRepository
from app.db.artifacts import ArtifactsRepository
from app.db.commands import CommandsRepository
from app.db.events import EventsRepository
from app.db.runs import RunsRepository
from app.models.approvals import ApprovalStatus
from app.models.commands import CommandPolicy, CommandStatus
from app.models.runs import RunRecord, RunStatus


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )


def test_commands_repository_translates_through_supabase(monkeypatch) -> None:
    settings = build_settings()
    captured = {}

    monkeypatch.setattr(
        "app.db.commands.resolve_tenant",
        lambda business_id, environment, settings=None: type(
            "Tenant",
            (),
            {"business_pk": 7, "environment": environment},
        )(),
    )

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        if table == "commands" and params.get("idempotency_key") == "eq.cmd-001":
            return []
        if table == "approvals":
            return []
        if table == "runs":
            return []
        return []

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        captured["table"] = table
        captured["row"] = rows[0]
        return [
            {
                "id": 101,
                "business_id": 7,
                "environment": "dev",
                "command_type": "run_market_research",
                "payload": {"topic": "houston"},
                "idempotency_key": "cmd-001",
                "policy_result": "safe_autonomous",
                "status": "queued",
                "created_at": "2026-04-20T00:00:00Z",
            }
        ]

    monkeypatch.setattr("app.db.commands.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.commands.insert_rows", fake_insert_rows)

    repo = CommandsRepository(settings=settings)
    command = repo.create(
        business_id="limitless",
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-001",
        payload={"topic": "houston"},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )

    assert captured["table"] == "commands"
    assert captured["row"]["business_id"] == 7
    assert captured["row"]["status"] == "queued"
    assert command.id == "cmd_101"
    assert command.status == CommandStatus.QUEUED


def test_runs_repository_save_translates_in_progress_status_for_supabase(monkeypatch) -> None:
    settings = build_settings()
    captured = {}

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        captured["table"] = table
        captured["row"] = row
        return [
            {
                "id": 22,
                "business_id": 7,
                "environment": "dev",
                "command_id": 101,
                "parent_run_id": None,
                "replay_reason": None,
                "trigger_run_id": "trg-123",
                "status": "running",
                "started_at": "2026-04-20T00:00:00Z",
                "completed_at": None,
                "error_classification": None,
                "error_message": None,
                "created_at": "2026-04-20T00:00:00Z",
                "updated_at": "2026-04-20T00:00:00Z",
            }
        ]

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        if table == "commands":
            return [{"command_type": "run_market_research", "policy_result": "safe_autonomous"}]
        return []

    monkeypatch.setattr("app.db.runs.patch_rows", fake_patch_rows)
    monkeypatch.setattr("app.db.runs.fetch_rows", fake_fetch_rows)

    repo = RunsRepository(settings=settings)
    run = repo.save(
        RunRecord(
            id="run_22",
            command_id="cmd_101",
            business_id="7",
            environment="dev",
            command_type="run_market_research",
            command_policy=CommandPolicy.SAFE_AUTONOMOUS,
            status=RunStatus.IN_PROGRESS,
            created_at="2026-04-20T00:00:00Z",
            updated_at="2026-04-20T00:00:00Z",
            trigger_run_id="trg-123",
            artifacts=[],
            events=[],
        )
    )

    assert captured["table"] == "runs"
    assert captured["row"]["status"] == "running"
    assert run.status == RunStatus.IN_PROGRESS


def test_approvals_repository_approve_persists_actor_and_timestamp(monkeypatch) -> None:
    settings = build_settings()
    captured = {}

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        captured["table"] = table
        captured["row"] = row
        return [
            {
                "id": 31,
                "business_id": 7,
                "environment": "dev",
                "command_id": 101,
                "approved_payload": {"campaign_id": "camp-1"},
                "status": "approved",
                "approved_by": "operator-1",
                "decided_at": "2026-04-20T00:00:00Z",
                "created_at": "2026-04-20T00:00:00Z",
            }
        ]

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        if table == "commands":
            return [{"command_type": "publish_campaign"}]
        return []

    monkeypatch.setattr("app.db.approvals.patch_rows", fake_patch_rows)
    monkeypatch.setattr("app.db.approvals.fetch_rows", fake_fetch_rows)

    repo = ApprovalsRepository(settings=settings)
    approval = repo.approve("apr_31", actor_id="operator-1")

    assert captured["table"] == "approvals"
    assert captured["row"]["status"] == ApprovalStatus.APPROVED.value
    assert captured["row"]["approved_by"] == "operator-1"
    assert approval is not None
    assert approval.status == ApprovalStatus.APPROVED
    assert approval.actor_id == "operator-1"


def test_event_and_artifact_repositories_translate_supabase_rows(monkeypatch) -> None:
    settings = build_settings()
    inserted = []

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        if table == "runs":
            return [{"business_id": 7, "environment": "dev"}]
        return []

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        inserted.append((table, rows[0]))
        if table == "events":
            return [{"id": 41, "run_id": 22, "event_type": "run_started", "payload": {"ok": True}, "created_at": "2026-04-20T00:00:00Z"}]
        if table == "artifacts":
            return [{"id": 42, "run_id": 22, "artifact_type": "report", "data": {"ok": True}, "created_at": "2026-04-20T00:00:00Z"}]
        raise AssertionError(table)

    monkeypatch.setattr("app.db.events.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.events.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.artifacts.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.artifacts.insert_rows", fake_insert_rows)

    event = EventsRepository(settings=settings).append("run_22", event_type="run_started", payload={"ok": True})
    artifact = ArtifactsRepository(settings=settings).append("run_22", artifact_type="report", payload={"ok": True})

    assert inserted[0][0] == "events"
    assert inserted[1][0] == "artifacts"
    assert event is not None and event["id"] == "evt_41"
    assert artifact is not None and artifact["id"] == "art_42"
