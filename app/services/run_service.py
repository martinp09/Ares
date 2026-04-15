from __future__ import annotations

from app.db.client import STORE, reset_control_plane_store, utc_now
from app.db.commands import CommandsRepository
from app.db.runs import RunsRepository
from app.models.commands import CommandRecord, CommandStatus
from app.models.runs import RunDetailResponse, RunRecord, RunStatus


def reset_control_plane_state() -> None:
    reset_control_plane_store(STORE)


class RunService:
    def __init__(
        self,
        runs_repository: RunsRepository | None = None,
        commands_repository: CommandsRepository | None = None,
    ) -> None:
        self.runs_repository = runs_repository or RunsRepository()
        self.commands_repository = commands_repository or CommandsRepository()

    def create_run(
        self,
        command: CommandRecord,
        *,
        parent_run_id: str | None = None,
        replay_reason: str | None = None,
    ) -> RunRecord:
        now = utc_now()
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
        run.events.append({"type": "run_created", "created_at": now.isoformat(), "parent_run_id": parent_run_id})
        command.run_id = run.id
        command.status = CommandStatus.QUEUED
        return run

    def get_run(self, run_id: str) -> RunRecord | None:
        return self.runs_repository.get(run_id)

    def get_run_detail(self, run_id: str) -> RunDetailResponse | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        return RunDetailResponse(**run.model_dump())


run_service = RunService()
