from datetime import UTC, datetime

from app.db.artifacts import ArtifactsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.events import EventsRepository
from app.db.runs import RunsRepository
from app.models.commands import CommandPolicy
from app.models.runs import RunStatus


def build_repositories() -> tuple[RunsRepository, EventsRepository, ArtifactsRepository]:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return RunsRepository(client), EventsRepository(client), ArtifactsRepository(client)


def test_creating_run_stores_command_business_environment_and_status() -> None:
    runs_repository, _, _ = build_repositories()

    run = runs_repository.create(
        command_id="cmd_123",
        business_id="limitless",
        environment="dev",
        command_type="run_market_research",
        command_policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=RunStatus.QUEUED,
    )

    assert run.command_id == "cmd_123"
    assert run.business_id == "limitless"
    assert run.environment == "dev"
    assert run.status == "queued"


def test_creating_replay_child_run_stores_parent_run_id_and_reason() -> None:
    runs_repository, _, _ = build_repositories()

    run = runs_repository.create(
        command_id="cmd_123",
        business_id="limitless",
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
        business_id="limitless",
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
        business_id="limitless",
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
