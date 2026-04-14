from __future__ import annotations

from datetime import UTC, datetime

from app.db.approvals import ApprovalsRepository
from app.db.commands import CommandsRepository
from app.db.runs import RunsRepository
from app.models.approvals import ApprovalDecisionRequest, ApprovalDecisionResponse, ApprovalRecord, ApprovalStatus
from app.models.commands import CommandRecord, CommandStatus, generate_id


def utc_now() -> datetime:
    return datetime.now(UTC)


class ApprovalService:
    def __init__(
        self,
        approvals_repository: ApprovalsRepository | None = None,
        commands_repository: CommandsRepository | None = None,
        runs_repository: RunsRepository | None = None,
    ) -> None:
        self.approvals_repository = approvals_repository or ApprovalsRepository()
        self.commands_repository = commands_repository or CommandsRepository()
        self.runs_repository = runs_repository or RunsRepository()

    def create_approval(self, command: CommandRecord) -> ApprovalRecord:
        approval = self.approvals_repository.create(
            command_id=command.id,
            business_id=command.business_id,
            environment=command.environment,
            command_type=command.command_type,
            payload_snapshot=command.payload,
        )
        command.approval_id = approval.id
        command.status = CommandStatus.AWAITING_APPROVAL
        self.commands_repository.save(command)
        return approval

    def list_approvals(
        self,
        *,
        business_id: str | int | None = None,
        environment: str | None = None,
        status: ApprovalStatus | None = ApprovalStatus.PENDING,
    ) -> list[ApprovalRecord]:
        return self.approvals_repository.list(
            business_id=business_id,
            environment=environment,
            status=status,
        )

    def approve(
        self, approval_id: str, request: ApprovalDecisionRequest
    ) -> ApprovalDecisionResponse | None:
        approval = self.approvals_repository.approve(approval_id, actor_id=request.actor_id)
        if approval is None:
            return None

        command = self.commands_repository.get(approval.command_id)
        if command is None:
            return None

        if approval.status == ApprovalStatus.APPROVED and command.run_id is not None:
            return ApprovalDecisionResponse(approval=approval, run_id=command.run_id)

        run = self.runs_repository.create(
            command_id=command.id,
            business_id=command.business_id,
            environment=command.environment,
            command_type=command.command_type,
            command_policy=command.policy,
        )
        command.run_id = run.id
        command.status = CommandStatus.QUEUED
        self.commands_repository.save(command)
        return ApprovalDecisionResponse(approval=approval, run_id=run.id)


approval_service = ApprovalService()
