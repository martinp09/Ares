from datetime import UTC, datetime

from app.db.artifacts import ArtifactsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.events import EventsRepository
from app.db.runs import RunsRepository
from app.db.artifacts import artifact_row_from_record
from app.db.events import event_row_from_record
from app.db.runs import run_record_from_row, run_status_from_sql_status, run_status_to_sql_status
from app.models.commands import CommandPolicy
from app.models.runs import RunStatus


def build_repositories() -> tuple[RunsRepository, EventsRepository, ArtifactsRepository]:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return RunsRepository(client), EventsRepository(client), ArtifactsRepository(client)


def test_creating_run_stores_command_business_environment_and_status() -> None:
    runs_repository, _, _ = build_repositories()

    run = runs_repository.create(
        command_id="cmd_123",
        business_id=1,
        environment="dev",
        command_type="run_market_research",
        command_policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=RunStatus.QUEUED,
    )

    assert run.command_id == "cmd_123"
    assert run.business_id == 1
    assert run.environment == "dev"
    assert run.status == "queued"


def test_creating_replay_child_run_stores_parent_run_id_and_reason() -> None:
    runs_repository, _, _ = build_repositories()

    run = runs_repository.create(
        command_id="cmd_123",
        business_id=1,
        environment="dev",
        command_type="run_market_research",
        command_policy=CommandPolicy.SAFE_AUTONOMOUS,
        parent_run_id="run_parent",
        replay_reason="new market context",
    )

    assert run.parent_run_id == "run_parent"
    assert run.replay_reason == "new market context"


def test_appending_two_run_events_preserves_order_by_created_at() -> None:
    runs_repository, events_repository, _ = build_repositories()
    run = runs_repository.create(
        command_id="cmd_123",
        business_id=1,
        environment="dev",
        command_type="run_market_research",
        command_policy=CommandPolicy.SAFE_AUTONOMOUS,
    )
    later = datetime(2026, 4, 13, 18, 0, 5, tzinfo=UTC)
    earlier = datetime(2026, 4, 13, 18, 0, 1, tzinfo=UTC)

    events_repository.append(run.id, event_type="run_completed", created_at=later)
    events_repository.append(run.id, event_type="run_started", created_at=earlier)
    events = events_repository.list_for_run(run.id)

    assert [event["event_type"] for event in events] == ["run_started", "run_completed"]
    assert [event["created_at"] for event in events] == [
        earlier.isoformat(),
        later.isoformat(),
    ]


def test_appending_artifact_stores_artifact_type_and_payload() -> None:
    runs_repository, _, artifacts_repository = build_repositories()
    run = runs_repository.create(
        command_id="cmd_123",
        business_id=1,
        environment="dev",
        command_type="run_market_research",
        command_policy=CommandPolicy.SAFE_AUTONOMOUS,
    )

    artifact = artifacts_repository.append(
        run.id,
        artifact_type="market_research_report",
        payload={"summary": "top neighborhoods"},
    )

    assert artifact is not None
    assert artifact["artifact_type"] == "market_research_report"
    assert artifact["payload"] == {"summary": "top neighborhoods"}


def test_run_repository_registers_runtime_to_sql_identity_mapping() -> None:
    store = InMemoryControlPlaneStore()
    runs_repository = RunsRepository(InMemoryControlPlaneClient(store))

    run = runs_repository.create(
        command_id="cmd_123",
        business_id=1,
        environment="dev",
        command_type="run_market_research",
        command_policy=CommandPolicy.SAFE_AUTONOMOUS,
    )

    assert store.run_runtime_to_sql_id[run.id] == 1


def test_run_sql_compatibility_mapping_bridges_running_and_in_progress() -> None:
    assert run_status_to_sql_status(RunStatus.IN_PROGRESS) == "running"
    assert run_status_from_sql_status("running") == RunStatus.IN_PROGRESS


def test_run_row_mapping_prefers_runtime_compatibility_columns() -> None:
    row = {
        "id": 22,
        "runtime_id": "run_runtime_22",
        "command_runtime_id": "cmd_runtime_9",
        "business_id": 1,
        "environment": "dev",
        "command_type": "run_market_research",
        "runtime_policy": "safe_autonomous",
        "runtime_status": "in_progress",
        "parent_runtime_id": "run_runtime_parent",
        "replay_reason": "new context",
        "created_at": "2026-04-13T18:00:00+00:00",
        "updated_at": "2026-04-13T18:02:00+00:00",
        "started_at": "2026-04-13T18:01:00+00:00",
        "completed_at": None,
    }

    run = run_record_from_row(row)

    assert run.id == "run_runtime_22"
    assert run.command_id == "cmd_runtime_9"
    assert run.status == RunStatus.IN_PROGRESS
    assert run.parent_run_id == "run_runtime_parent"


def test_run_row_mapping_preserves_distinct_replay_source_runtime_id() -> None:
    row = {
        "id": 23,
        "runtime_id": "run_runtime_23",
        "command_runtime_id": "cmd_runtime_10",
        "business_id": 1,
        "environment": "dev",
        "command_type": "run_market_research",
        "runtime_policy": "safe_autonomous",
        "runtime_status": "in_progress",
        "parent_runtime_id": "run_runtime_parent",
        "replay_source_runtime_id": "run_runtime_origin",
        "created_at": "2026-04-13T18:00:00+00:00",
        "updated_at": "2026-04-13T18:02:00+00:00",
    }

    run = run_record_from_row(row)

    assert run.parent_run_id == "run_runtime_parent"
    assert run.replay_source_run_id == "run_runtime_origin"


def test_event_and_artifact_rows_include_runtime_compatibility_ids() -> None:
    event = event_row_from_record(
        {
            "id": "evt_runtime_1",
            "run_id": "run_runtime_1",
            "event_type": "run_started",
            "payload": {},
            "created_at": "2026-04-13T18:00:00+00:00",
        },
        business_id=1,
        environment="dev",
    )
    artifact = artifact_row_from_record(
        {
            "id": "art_runtime_1",
            "run_id": "run_runtime_1",
            "artifact_type": "market_research_report",
            "payload": {"summary": "top neighborhoods"},
            "created_at": "2026-04-13T18:03:00+00:00",
        },
        business_id=1,
        environment="dev",
    )

    assert event["runtime_id"] == "evt_runtime_1"
    assert event["run_runtime_id"] == "run_runtime_1"
    assert artifact["runtime_id"] == "art_runtime_1"
    assert artifact["run_runtime_id"] == "run_runtime_1"
    assert artifact["data"] == {"summary": "top neighborhoods"}
