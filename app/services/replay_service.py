from __future__ import annotations

from app.models.commands import CommandPolicy
from app.models.runs import ReplayRequest, ReplayResponse
from app.services.approval_service import approval_service
from app.services.run_service import STORE, run_service


class ReplayService:
    def replay_run(self, run_id: str, request: ReplayRequest) -> tuple[ReplayResponse, int] | None:
        parent_run = STORE.runs.get(run_id)
        if parent_run is None:
            return None

        command = STORE.commands.get(parent_run.command_id)
        if command is None:
            return None

        parent_run.events.append(
            {"type": "replay_requested", "reason": request.reason, "requires_approval": None}
        )

        if command.policy == CommandPolicy.SAFE_AUTONOMOUS:
            child_run = run_service.create_run(
                command,
                parent_run_id=parent_run.id,
                replay_reason=request.reason,
            )
            parent_run.events[-1]["requires_approval"] = False
            parent_run.events[-1]["child_run_id"] = child_run.id
            return (
                ReplayResponse(
                    parent_run_id=parent_run.id,
                    child_run_id=child_run.id,
                    requires_approval=False,
                ),
                201,
            )

        replay_approval = approval_service.create_approval(command)
        parent_run.events[-1]["requires_approval"] = True
        parent_run.events[-1]["approval_id"] = replay_approval.id
        return (
            ReplayResponse(
                parent_run_id=parent_run.id,
                child_run_id=None,
                requires_approval=True,
                approval_id=replay_approval.id,
            ),
            409,
        )


replay_service = ReplayService()
