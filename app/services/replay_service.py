from __future__ import annotations

from app.db.approvals import ApprovalsRepository
from app.db.client import utc_now
from app.db.commands import CommandsRepository
from app.db.runs import RunsRepository
from app.models.actors import ActorContext
from app.models.commands import CommandPolicy, CommandRecord, CommandStatus, generate_id
from app.models.runs import ReplayRequest, ReplayResponse
from app.services.replay_lineage_service import ReplayLineageService, replay_lineage_service as default_replay_lineage_service
from app.services.run_lifecycle_service import RunLifecycleService, run_lifecycle_service as default_run_lifecycle_service
from app.services.run_service import run_service


class ReplayService:
    def __init__(
        self,
        commands_repository: CommandsRepository | None = None,
        runs_repository: RunsRepository | None = None,
        approvals_repository: ApprovalsRepository | None = None,
        replay_lineage_service: ReplayLineageService | None = None,
        run_lifecycle_service: RunLifecycleService | None = None,
    ) -> None:
        self.commands_repository = commands_repository or CommandsRepository()
        self.runs_repository = runs_repository or RunsRepository()
        self.approvals_repository = approvals_repository or ApprovalsRepository()
        self.replay_lineage_service = replay_lineage_service or default_replay_lineage_service
        self.run_lifecycle_service = run_lifecycle_service or default_run_lifecycle_service

    def replay_run(
        self,
        run_id: str,
        request: ReplayRequest,
        *,
        actor_context: ActorContext,
    ) -> tuple[ReplayResponse, int] | None:
        parent_run = self.runs_repository.get(run_id)
        if parent_run is None:
            return None

        original_command = self.commands_repository.get(parent_run.command_id)
        if original_command is None:
            return None

        requested_at = utc_now()
        agent_revision_id = self.replay_lineage_service.agent_revision_id_for_run(parent_run.id)
        lineage = self.replay_lineage_service.build_lineage(
            agent_revision_id=agent_revision_id,
            parent_created_at=parent_run.created_at,
            replayed_at=requested_at,
            actor_context=actor_context,
        )

        if original_command.policy == CommandPolicy.SAFE_AUTONOMOUS:
            if agent_revision_id is not None:
                run_service.agent_execution_service.validate_dispatchable(agent_revision_id)
            replay_command = self._create_replay_command(original_command)
            try:
                child_run = run_service.create_run(
                    replay_command,
                    agent_revision_id=agent_revision_id,
                    parent_run_id=parent_run.id,
                    replay_reason=request.reason,
                    skip_dispatch_validation=True,
                )
            except Exception:
                self._discard_replay_command(replay_command)
                raise
            self.run_lifecycle_service.record_replay_lineage(
                parent_run.id,
                replay_reason=request.reason,
                triggering_actor=actor_context,
                lineage=lineage,
                child_run_id=child_run.id,
                occurred_at=requested_at,
            )
            return (
                ReplayResponse(
                    parent_run_id=parent_run.id,
                    child_run_id=child_run.id,
                    requires_approval=False,
                    replay_reason=request.reason,
                    lineage=lineage,
                ),
                201,
            )

        replay_command = self._create_replay_command(original_command)
        replay_approval = self.approvals_repository.create(
            command_id=replay_command.id,
            business_id=replay_command.business_id,
            environment=replay_command.environment,
            command_type=replay_command.command_type,
            payload_snapshot=self.replay_lineage_service.build_approval_payload_snapshot(
                replay_command.payload,
                parent_run_id=parent_run.id,
                replay_reason=request.reason,
                agent_revision_id=agent_revision_id,
                parent_created_at=parent_run.created_at,
                actor_context=actor_context,
            ),
        )
        self.commands_repository.attach_approval(replay_command.id, approval_id=replay_approval.id)
        replay_command.approval_id = replay_approval.id
        replay_command.status = CommandStatus.AWAITING_APPROVAL
        self.run_lifecycle_service.record_replay_lineage(
            parent_run.id,
            replay_reason=request.reason,
            triggering_actor=actor_context,
            lineage=lineage,
            approval_id=replay_approval.id,
            occurred_at=requested_at,
        )
        return (
            ReplayResponse(
                parent_run_id=parent_run.id,
                child_run_id=None,
                requires_approval=True,
                approval_id=replay_approval.id,
                replay_reason=request.reason,
                lineage=lineage,
            ),
            409,
        )

    def _create_replay_command(self, command: CommandRecord) -> CommandRecord:
        return self.commands_repository.create(
            business_id=command.business_id,
            environment=command.environment,
            command_type=command.command_type,
            idempotency_key=self._replay_idempotency_key(command.idempotency_key),
            payload=command.payload,
            policy=command.policy,
            status=CommandStatus.ACCEPTED,
        )

    @staticmethod
    def _replay_idempotency_key(original_idempotency_key: str) -> str:
        return f"{original_idempotency_key}:replay:{generate_id('rpk')}"

    def _discard_replay_command(self, command: CommandRecord) -> None:
        with self.commands_repository.client.transaction() as store:
            store.commands.pop(command.id, None)
            dedupe_key = (
                command.business_id,
                command.environment,
                command.command_type,
                command.idempotency_key,
            )
            store.command_keys.pop(dedupe_key, None)


replay_service = ReplayService()
