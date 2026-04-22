from __future__ import annotations

from app.db.approvals import ApprovalsRepository
from app.db.commands import CommandsRepository
from app.db.host_adapter_dispatches import HostAdapterDispatchesRepository
from app.db.runs import RunsRepository
from app.models.commands import CommandPolicy
from app.models.runs import ReplayRequest, ReplayResponse
from app.services.run_service import run_service


class ReplayService:
    def __init__(
        self,
        commands_repository: CommandsRepository | None = None,
        runs_repository: RunsRepository | None = None,
        approvals_repository: ApprovalsRepository | None = None,
        host_adapter_dispatches_repository: HostAdapterDispatchesRepository | None = None,
    ) -> None:
        self.commands_repository = commands_repository or CommandsRepository()
        self.runs_repository = runs_repository or RunsRepository()
        self.approvals_repository = approvals_repository or ApprovalsRepository()
        self.host_adapter_dispatches_repository = host_adapter_dispatches_repository or HostAdapterDispatchesRepository()

    def replay_run(self, run_id: str, request: ReplayRequest) -> tuple[ReplayResponse, int] | None:
        parent_run = self.runs_repository.get(run_id)
        if parent_run is None:
            return None

        command = self.commands_repository.get(parent_run.command_id)
        if command is None:
            return None

        if command.policy == CommandPolicy.SAFE_AUTONOMOUS:
            agent_revision_id = self._agent_revision_id_for_replay(parent_run.id)
            child_run = run_service.create_run(
                command,
                agent_revision_id=agent_revision_id,
                parent_run_id=parent_run.id,
                replay_reason=request.reason,
            )
            parent_run.events.append(
                {
                    "type": "replay_requested",
                    "reason": request.reason,
                    "requires_approval": False,
                    "child_run_id": child_run.id,
                }
            )
            return (
                ReplayResponse(
                    parent_run_id=parent_run.id,
                    child_run_id=child_run.id,
                    requires_approval=False,
                    replay_reason=request.reason,
                ),
                201,
            )

        replay_approval = self.approvals_repository.create(
            command_id=command.id,
            business_id=command.business_id,
            environment=command.environment,
            command_type=command.command_type,
            payload_snapshot=command.payload,
        )
        parent_run.events.append(
            {
                "type": "replay_requested",
                "reason": request.reason,
                "requires_approval": True,
                "approval_id": replay_approval.id,
            }
        )
        return (
            ReplayResponse(
                parent_run_id=parent_run.id,
                child_run_id=None,
                requires_approval=True,
                approval_id=replay_approval.id,
                replay_reason=request.reason,
            ),
            409,
        )

    def _agent_revision_id_for_replay(self, run_id: str) -> str | None:
        dispatch = self.host_adapter_dispatches_repository.get_by_run_id(run_id)
        if dispatch is None:
            return None
        return dispatch.agent_revision_id


replay_service = ReplayService()
