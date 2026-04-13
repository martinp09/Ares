from __future__ import annotations

from datetime import UTC, datetime

from app.models.approvals import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalRecord,
    ApprovalStatus,
)
from app.models.commands import CommandRecord, CommandStatus, generate_id
from app.services.run_service import STORE, run_service


def utc_now() -> datetime:
    return datetime.now(UTC)


class ApprovalService:
    def create_approval(self, command: CommandRecord) -> ApprovalRecord:
        approval = ApprovalRecord(
            id=generate_id("apr"),
            command_id=command.id,
            business_id=command.business_id,
            environment=command.environment,
            command_type=command.command_type,
            status=ApprovalStatus.PENDING,
            payload_snapshot=command.payload,
            created_at=utc_now(),
        )
        STORE.approvals[approval.id] = approval
        command.approval_id = approval.id
        command.status = CommandStatus.AWAITING_APPROVAL
        STORE.commands[command.id] = command
        return approval

    def approve(
        self, approval_id: str, request: ApprovalDecisionRequest
    ) -> ApprovalDecisionResponse | None:
        approval = STORE.approvals.get(approval_id)
        if approval is None:
            return None

        command = STORE.commands.get(approval.command_id)
        if command is None:
            return None

        if approval.status == ApprovalStatus.APPROVED and command.run_id is not None:
            return ApprovalDecisionResponse(approval=approval, run_id=command.run_id)

        approval.status = ApprovalStatus.APPROVED
        approval.approved_at = utc_now()
        approval.actor_id = request.actor_id
        STORE.approvals[approval.id] = approval

        run = run_service.create_run(command)
        STORE.commands[command.id] = command
        return ApprovalDecisionResponse(approval=approval, run_id=run.id)


approval_service = ApprovalService()
