from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.models.approvals import ApprovalRecord
from app.models.commands import CommandRecord, CommandStatus, generate_id
from app.models.runs import RunDetailResponse, RunRecord, RunStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class InMemoryControlPlaneStore:
    commands: dict[str, CommandRecord] = field(default_factory=dict)
    command_keys: dict[tuple[str, str, str, str], str] = field(default_factory=dict)
    approvals: dict[str, ApprovalRecord] = field(default_factory=dict)
    runs: dict[str, RunRecord] = field(default_factory=dict)


STORE = InMemoryControlPlaneStore()


def reset_control_plane_state() -> None:
    STORE.commands.clear()
    STORE.command_keys.clear()
    STORE.approvals.clear()
    STORE.runs.clear()


class RunService:
    def create_run(
        self,
        command: CommandRecord,
        *,
        parent_run_id: str | None = None,
        replay_reason: str | None = None,
    ) -> RunRecord:
        now = utc_now()
        run = RunRecord(
            id=generate_id("run"),
            command_id=command.id,
            business_id=command.business_id,
            environment=command.environment,
            command_type=command.command_type,
            command_policy=command.policy,
            status=RunStatus.QUEUED,
            created_at=now,
            updated_at=now,
            parent_run_id=parent_run_id,
            replay_reason=replay_reason,
            artifacts=[],
            events=[],
        )
        run.events.append(
            {"type": "run_created", "timestamp": now.isoformat(), "parent_run_id": parent_run_id}
        )
        STORE.runs[run.id] = run
        command.run_id = run.id
        command.status = CommandStatus.QUEUED
        STORE.commands[command.id] = command
        return run

    def get_run(self, run_id: str) -> RunRecord | None:
        return STORE.runs.get(run_id)

    def get_run_detail(self, run_id: str) -> RunDetailResponse | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        return RunDetailResponse(**run.model_dump())


run_service = RunService()
