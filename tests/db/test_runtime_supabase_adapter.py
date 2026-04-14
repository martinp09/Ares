from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.db.approvals import ApprovalsRepository
from app.db.artifacts import ArtifactsRepository
from app.db.commands import CommandsRepository
from app.db.events import EventsRepository
from app.db.runs import RunsRepository
from app.models.approvals import ApprovalStatus
from app.models.commands import CommandPolicy, CommandStatus
from app.models.run_events import RunStartedCallbackRequest
from app.models.runs import ReplayRequest
from app.models.runs import RunStatus
from app.services.replay_service import ReplayService
from app.services.run_lifecycle_service import RunLifecycleService
from app.services.run_service import RunService


def _matches(row: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    for key, value in filters.items():
        if row.get(key) != value:
            return False
    return True


@dataclass
class FakeSupabaseClient:
    backend: str = "supabase"
    commands: list[dict[str, Any]] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    runs: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    _counters: dict[str, int] = field(
        default_factory=lambda: {
            "commands": 0,
            "approvals": 0,
            "runs": 0,
            "events": 0,
            "artifacts": 0,
        }
    )

    def _table(self, name: str) -> list[dict[str, Any]]:
        return getattr(self, name)

    def select(
        self,
        table: str,
        *,
        columns: str,
        filters: dict[str, Any] | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        del columns
        rows = [dict(row) for row in self._table(table) if _matches(row, filters)]
        if order:
            key, _, direction = order.partition(".")
            rows.sort(key=lambda item: item.get(key))
            if direction == "desc":
                rows.reverse()
        if limit is not None:
            rows = rows[:limit]
        return rows

    def insert(
        self,
        table: str,
        *,
        rows: list[dict[str, Any]],
        columns: str,
        on_conflict: str | None = None,
        ignore_duplicates: bool = False,
    ) -> list[dict[str, Any]]:
        del columns, on_conflict
        inserted: list[dict[str, Any]] = []
        for row in rows:
            if ignore_duplicates and table == "commands":
                duplicate = next(
                    (
                        existing
                        for existing in self.commands
                        if existing["business_id"] == row["business_id"]
                        and existing["environment"] == row["environment"]
                        and existing["command_type"] == row["command_type"]
                        and existing["idempotency_key"] == row["idempotency_key"]
                    ),
                    None,
                )
                if duplicate is not None:
                    continue

            self._counters[table] += 1
            enriched = dict(row)
            enriched["id"] = self._counters[table]
            now = datetime.now(UTC).isoformat()
            enriched.setdefault("created_at", now)
            enriched.setdefault("updated_at", now)
            self._table(table).append(enriched)
            inserted.append(dict(enriched))
        return inserted

    def update(
        self,
        table: str,
        *,
        values: dict[str, Any],
        filters: dict[str, Any],
        columns: str,
    ) -> list[dict[str, Any]]:
        del columns
        rows = self._table(table)
        updated: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            if not _matches(row, filters):
                continue
            next_row = dict(row)
            next_row.update(values)
            next_row["updated_at"] = datetime.now(UTC).isoformat()
            rows[index] = next_row
            updated.append(dict(next_row))
        return updated


def _build_runtime_repositories(client: FakeSupabaseClient) -> tuple[
    CommandsRepository,
    ApprovalsRepository,
    RunsRepository,
    EventsRepository,
    ArtifactsRepository,
]:
    return (
        CommandsRepository(client),
        ApprovalsRepository(client),
        RunsRepository(client),
        EventsRepository(client),
        ArtifactsRepository(client),
    )


def test_supabase_command_dedupe_and_run_link_are_runtime_shaped() -> None:
    client = FakeSupabaseClient()
    commands_repository, _, runs_repository, _, _ = _build_runtime_repositories(client)

    first = commands_repository.create(
        business_id=101,
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-supabase-001",
        payload={"topic": "north dallas"},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )
    run = runs_repository.create(
        command_id=first.id,
        business_id=first.business_id,
        environment=first.environment,
        command_type=first.command_type,
        command_policy=first.policy,
        status=RunStatus.QUEUED,
    )
    first.run_id = run.id
    first.status = CommandStatus.QUEUED
    commands_repository.save(first)

    duplicate = commands_repository.create(
        business_id=101,
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-supabase-001",
        payload={"topic": "north dallas"},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )

    assert duplicate.id == first.id
    assert duplicate.deduped is True
    assert duplicate.run_id == run.id
    assert duplicate.status == CommandStatus.QUEUED


def test_supabase_approvals_create_approve_and_list() -> None:
    client = FakeSupabaseClient()
    commands_repository, approvals_repository, _, _, _ = _build_runtime_repositories(client)
    command = commands_repository.create(
        business_id=101,
        environment="dev",
        command_type="publish_campaign",
        idempotency_key="cmd-supabase-002",
        payload={"campaign_id": "camp-42"},
        policy=CommandPolicy.APPROVAL_REQUIRED,
        status=CommandStatus.ACCEPTED,
    )

    approval = approvals_repository.create(
        command_id=command.id,
        business_id=command.business_id,
        environment=command.environment,
        command_type=command.command_type,
        payload_snapshot=command.payload,
    )
    approved = approvals_repository.approve(approval.id, actor_id="ops-2")
    pending = approvals_repository.list(
        business_id=101,
        environment="dev",
        status=ApprovalStatus.PENDING,
    )
    done = approvals_repository.list(
        business_id=101,
        environment="dev",
        status=ApprovalStatus.APPROVED,
    )

    assert approved is not None
    assert approved.actor_id == "ops-2"
    assert pending == []
    assert len(done) == 1
    assert done[0].id == approval.id


def test_supabase_run_get_hydrates_events_and_artifacts() -> None:
    client = FakeSupabaseClient()
    commands_repository, _, runs_repository, events_repository, artifacts_repository = _build_runtime_repositories(client)
    command = commands_repository.create(
        business_id=101,
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-supabase-003",
        payload={"topic": "austin absentee owners"},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )

    run = runs_repository.create(
        command_id=command.id,
        business_id=command.business_id,
        environment=command.environment,
        command_type=command.command_type,
        command_policy=command.policy,
        status=RunStatus.QUEUED,
    )
    events_repository.append(run.id, event_type="run_started", payload={"trigger_run_id": "trg-001"})
    artifacts_repository.append(
        run.id,
        artifact_type="market_research_report",
        payload={"summary": "high equity zip clusters"},
    )

    hydrated = runs_repository.get(run.id)

    assert hydrated is not None
    assert hydrated.id == run.id
    assert hydrated.command_type == "run_market_research"
    assert [event["event_type"] for event in hydrated.events] == ["run_started"]
    assert [artifact["artifact_type"] for artifact in hydrated.artifacts] == ["market_research_report"]


def test_supabase_run_service_persists_command_link_via_repository_save() -> None:
    client = FakeSupabaseClient()
    commands_repository, _, runs_repository, events_repository, _ = _build_runtime_repositories(client)
    command = commands_repository.create(
        business_id=101,
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-supabase-004",
        payload={"topic": "south austin"},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )

    service = RunService(
        runs_repository=runs_repository,
        commands_repository=commands_repository,
        events_repository=events_repository,
    )
    run = service.create_run(command)
    persisted_command = commands_repository.get(command.id)
    persisted_run = runs_repository.get(run.id)

    assert persisted_command is not None
    assert persisted_command.run_id == run.id
    assert persisted_command.status == CommandStatus.QUEUED
    assert persisted_run is not None
    assert any(event["event_type"] == "run_created" for event in persisted_run.events)


def test_supabase_run_lifecycle_service_persists_run_status_transition() -> None:
    client = FakeSupabaseClient()
    commands_repository, _, runs_repository, events_repository, artifacts_repository = _build_runtime_repositories(client)
    command = commands_repository.create(
        business_id=101,
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-supabase-005",
        payload={"topic": "east dallas"},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )
    run = runs_repository.create(
        command_id=command.id,
        business_id=command.business_id,
        environment=command.environment,
        command_type=command.command_type,
        command_policy=command.policy,
        status=RunStatus.QUEUED,
    )

    service = RunLifecycleService(
        runs_repository=runs_repository,
        events_repository=events_repository,
        artifacts_repository=artifacts_repository,
        commands_repository=commands_repository,
    )
    response = service.mark_run_started(
        run.id,
        RunStartedCallbackRequest(trigger_run_id="trg-supabase-001"),
    )
    persisted = runs_repository.get(run.id)

    assert response is not None
    assert response.status == RunStatus.IN_PROGRESS
    assert persisted is not None
    assert persisted.status == RunStatus.IN_PROGRESS
    assert persisted.trigger_run_id == "trg-supabase-001"


def test_supabase_replay_service_records_replay_requested_event() -> None:
    client = FakeSupabaseClient()
    commands_repository, approvals_repository, runs_repository, events_repository, _ = _build_runtime_repositories(client)
    command = commands_repository.create(
        business_id=101,
        environment="dev",
        command_type="publish_campaign",
        idempotency_key="cmd-supabase-006",
        payload={"campaign_id": "camp-55"},
        policy=CommandPolicy.APPROVAL_REQUIRED,
        status=CommandStatus.ACCEPTED,
    )
    run = runs_repository.create(
        command_id=command.id,
        business_id=command.business_id,
        environment=command.environment,
        command_type=command.command_type,
        command_policy=command.policy,
        status=RunStatus.QUEUED,
    )
    service = ReplayService(
        commands_repository=commands_repository,
        runs_repository=runs_repository,
        approvals_repository=approvals_repository,
        events_repository=events_repository,
    )

    replay, status_code = service.replay_run(run.id, ReplayRequest(reason="retry with operator review")) or (None, None)
    events = events_repository.list_for_run(run.id)

    assert replay is not None
    assert status_code == 409
    assert replay.requires_approval is True
    replay_events = [event for event in events if event["event_type"] == "replay_requested"]
    assert len(replay_events) == 1
    assert replay_events[0]["payload"]["requires_approval"] is True
