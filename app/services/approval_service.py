from __future__ import annotations

from datetime import UTC, datetime

from app.db.approvals import ApprovalsRepository
from app.db.commands import CommandsRepository
from app.db.runs import RunsRepository
from app.models.actors import ActorContext
from app.models.approvals import ApprovalDecisionRequest, ApprovalDecisionResponse, ApprovalRecord, ApprovalStatus
from app.models.commands import CommandRecord, CommandStatus
from app.services.replay_lineage_service import ReplayLineageService, replay_lineage_service as default_replay_lineage_service
from app.services.runtime_observability_service import runtime_observability_service
from app.services.run_lifecycle_service import RunLifecycleService, run_lifecycle_service as default_run_lifecycle_service
from app.services.run_service import run_service


def utc_now() -> datetime:
    return datetime.now(UTC)


class ApprovalService:
    def __init__(
        self,
        approvals_repository: ApprovalsRepository | None = None,
        commands_repository: CommandsRepository | None = None,
        runs_repository: RunsRepository | None = None,
        replay_lineage_service: ReplayLineageService | None = None,
        run_lifecycle_service: RunLifecycleService | None = None,
    ) -> None:
        self.approvals_repository = approvals_repository or ApprovalsRepository()
        self.commands_repository = commands_repository or CommandsRepository()
        self.runs_repository = runs_repository or RunsRepository()
        self.replay_lineage_service = replay_lineage_service or default_replay_lineage_service
        self.run_lifecycle_service = run_lifecycle_service or default_run_lifecycle_service

    def create_approval(
        self,
        command: CommandRecord,
        *,
        payload_snapshot: dict | None = None,
    ) -> ApprovalRecord:
        approval = self.approvals_repository.create(
            command_id=command.id,
            business_id=command.business_id,
            environment=command.environment,
            command_type=command.command_type,
            payload_snapshot=payload_snapshot if payload_snapshot is not None else command.payload,
        )
        self.commands_repository.attach_approval(command.id, approval_id=approval.id)
        command.approval_id = approval.id
        command.status = CommandStatus.AWAITING_APPROVAL
        runtime_observability_service.nonfatal(
            runtime_observability_service.record_approval_created,
            approval,
            agent_revision_id=command.agent_revision_id,
        )
        return approval

    def list_approvals(
        self,
        *,
        business_id: str | None = None,
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
        prior_approval = self.approvals_repository.get(approval_id)
        approval = self.approvals_repository.approve(approval_id, actor_id=request.actor_id)
        if approval is None:
            return None

        command = self.commands_repository.get(approval.command_id)
        if command is None:
            return None

        if approval.status == ApprovalStatus.APPROVED and command.run_id is not None:
            return ApprovalDecisionResponse(approval=approval, run_id=command.run_id)

        if prior_approval is None or prior_approval.status != ApprovalStatus.APPROVED:
            runtime_observability_service.nonfatal(
                runtime_observability_service.record_approval_approved,
                approval,
                agent_revision_id=command.agent_revision_id,
            )

        replay_metadata = self.replay_lineage_service.approval_metadata(approval.payload_snapshot)
        if replay_metadata is not None:
            occurred_at = approval.approved_at or utc_now()
            actor_context = ActorContext(
                org_id=replay_metadata.triggering_actor.org_id,
                actor_id=replay_metadata.triggering_actor.actor_id,
                actor_type=replay_metadata.triggering_actor.actor_type,
            )
            lineage = self.replay_lineage_service.build_lineage(
                agent_revision_id=replay_metadata.agent_revision_id,
                parent_created_at=replay_metadata.parent_created_at,
                replayed_at=occurred_at,
                actor_context=actor_context,
            )
            run = run_service.create_run(
                command,
                agent_revision_id=replay_metadata.agent_revision_id,
                parent_run_id=replay_metadata.parent_run_id,
                replay_reason=replay_metadata.replay_reason,
            )
            self.run_lifecycle_service.record_replay_child_lineage(
                run.id,
                parent_run_id=replay_metadata.parent_run_id,
                replay_reason=replay_metadata.replay_reason,
                triggering_actor=actor_context,
                lineage=lineage,
                occurred_at=occurred_at,
            )
            self.run_lifecycle_service.record_replay_parent_resolution(
                replay_metadata.parent_run_id,
                child_run_id=run.id,
                approval_id=approval.id,
                replay_reason=replay_metadata.replay_reason,
                triggering_actor=actor_context,
                lineage=lineage,
                occurred_at=occurred_at,
            )
            return ApprovalDecisionResponse(approval=approval, run_id=run.id)

        run = run_service.create_run(command, observability_agent_revision_id=command.agent_revision_id)
        return ApprovalDecisionResponse(approval=approval, run_id=run.id)


approval_service = ApprovalService()
