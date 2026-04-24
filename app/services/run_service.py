from __future__ import annotations
from app.db.client import STORE, reset_control_plane_store, utc_now
from app.db.commands import CommandsRepository
from app.db.events import EventsRepository
from app.db.runs import RunsRepository
from app.models.commands import CommandRecord, CommandStatus
from app.models.runs import RunDetailResponse, RunRecord, RunStatus
from app.services.agent_execution_service import agent_execution_service as default_agent_execution_service
from app.services.runtime_observability_service import runtime_observability_service
import shutil
from pathlib import Path


def reset_control_plane_state() -> None:
    reset_control_plane_store(STORE)
    runtime_root = Path("/tmp/ares-runtime")
    if runtime_root.exists():
        shutil.rmtree(runtime_root)


class RunService:
    def __init__(
        self,
        runs_repository: RunsRepository | None = None,
        commands_repository: CommandsRepository | None = None,
        events_repository: EventsRepository | None = None,
        agent_execution_service=default_agent_execution_service,
    ) -> None:
        self.runs_repository = runs_repository or RunsRepository()
        self.commands_repository = commands_repository or CommandsRepository()
        self.events_repository = events_repository or EventsRepository()
        self.agent_execution_service = agent_execution_service

    def create_run(
        self,
        command: CommandRecord,
        *,
        agent_revision_id: str | None = None,
        parent_run_id: str | None = None,
        replay_reason: str | None = None,
        skip_dispatch_validation: bool = False,
        observability_agent_revision_id: str | None = None,
    ) -> RunRecord:
        if agent_revision_id is not None and not skip_dispatch_validation:
            self.agent_execution_service.validate_dispatchable(agent_revision_id)
        now = utc_now()
        prior_command = self.commands_repository.get(command.id)
        run = self.runs_repository.create(
            command_id=command.id,
            business_id=command.business_id,
            environment=command.environment,
            command_type=command.command_type,
            command_policy=command.policy,
            status=RunStatus.QUEUED,
            parent_run_id=parent_run_id,
            replay_reason=replay_reason,
            created_at=now,
        )
        self.events_repository.append(
            run.id,
            event_type="run_created",
            payload={"parent_run_id": parent_run_id},
            created_at=now,
        )
        run.events.append({"type": "run_created", "created_at": now.isoformat(), "parent_run_id": parent_run_id})
        self.commands_repository.attach_run(command.id, run_id=run.id)
        command.run_id = run.id
        command.status = CommandStatus.QUEUED
        if agent_revision_id is not None:
            try:
                self.agent_execution_service.dispatch_revision(
                    agent_revision_id,
                    payload=command.payload,
                    run_id=run.id,
                )
            except Exception:
                self._rollback_failed_run_creation(run.id, previous_command=prior_command)
                raise
        runtime_observability_service.nonfatal(
            runtime_observability_service.record_run_created,
            run,
            agent_revision_id=observability_agent_revision_id or agent_revision_id,
        )
        return run

    def _rollback_failed_run_creation(self, run_id: str, *, previous_command: CommandRecord | None) -> None:
        with self.runs_repository.client.transaction() as store:
            store.runs.pop(run_id, None)
            if previous_command is not None:
                store.commands[previous_command.id] = previous_command

    def get_run(self, run_id: str) -> RunRecord | None:
        return self.runs_repository.get(run_id)

    def get_run_detail(self, run_id: str) -> RunDetailResponse | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        return RunDetailResponse(**run.model_dump())


run_service = RunService()
