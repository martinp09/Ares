from __future__ import annotations

from app.db.commands import CommandsRepository
from app.models.commands import CommandCreateRequest, CommandIngestResponse, CommandPolicy, CommandStatus
from app.policies.classifier import apply_policy_precedence
from app.services.agent_execution_service import agent_execution_service as default_agent_execution_service
from app.services.approval_service import approval_service
from app.services.runtime_observability_service import runtime_observability_service
from app.services.run_service import run_service


POLICY_BY_COMMAND: dict[str, CommandPolicy] = {
    "run_market_research": CommandPolicy.SAFE_AUTONOMOUS,
    "create_campaign_brief": CommandPolicy.SAFE_AUTONOMOUS,
    "draft_campaign_assets": CommandPolicy.SAFE_AUTONOMOUS,
    "propose_launch": CommandPolicy.APPROVAL_REQUIRED,
    "publish_campaign": CommandPolicy.APPROVAL_REQUIRED,
}


class CommandService:
    def __init__(
        self,
        commands_repository: CommandsRepository | None = None,
        agent_execution_service=default_agent_execution_service,
    ) -> None:
        self.commands_repository = commands_repository or CommandsRepository()
        self.agent_execution_service = agent_execution_service

    def classify(self, command_type: str) -> CommandPolicy:
        return POLICY_BY_COMMAND.get(command_type, CommandPolicy.FORBIDDEN)

    def create_command(
        self,
        request: CommandCreateRequest,
        *,
        policy_override: CommandPolicy | None = None,
    ) -> tuple[CommandIngestResponse, int]:
        base_policy = self.classify(request.command_type)
        policy = apply_policy_precedence(base_policy, policy_override) if policy_override is not None else base_policy
        if policy == CommandPolicy.FORBIDDEN:
            raise ValueError(f"Unsupported or forbidden command_type '{request.command_type}'")
        if policy == CommandPolicy.SAFE_AUTONOMOUS and request.agent_revision_id is not None:
            existing = self.commands_repository.get_by_idempotency_key(
                business_id=request.business_id,
                environment=request.environment,
                command_type=request.command_type,
                idempotency_key=request.idempotency_key,
            )
            if existing is not None:
                deduped = existing.model_copy(update={"deduped": True})
                runtime_observability_service.nonfatal(
                    runtime_observability_service.record_command_invoked,
                    deduped,
                    deduped=True,
                    agent_revision_id=deduped.agent_revision_id,
                )
                return CommandIngestResponse(**deduped.model_dump()), 200
            self.agent_execution_service.validate_dispatchable(request.agent_revision_id)

        command = self.commands_repository.create(
            business_id=request.business_id,
            environment=request.environment,
            command_type=request.command_type,
            idempotency_key=request.idempotency_key,
            payload=request.payload,
            agent_revision_id=request.agent_revision_id,
            policy=policy,
            status=CommandStatus.ACCEPTED,
        )
        if command.deduped:
            runtime_observability_service.nonfatal(
                runtime_observability_service.record_command_invoked,
                command,
                deduped=True,
                agent_revision_id=command.agent_revision_id,
            )
            return CommandIngestResponse(**command.model_dump()), 200

        runtime_observability_service.nonfatal(
            runtime_observability_service.record_command_invoked,
            command,
            agent_revision_id=request.agent_revision_id,
        )
        if policy == CommandPolicy.SAFE_AUTONOMOUS:
            run = run_service.create_run(command, agent_revision_id=request.agent_revision_id)
            command = self.commands_repository.attach_run(command.id, run_id=run.id) or command.model_copy(
                update={"run_id": run.id, "status": CommandStatus.QUEUED}
            )
        else:
            approval = approval_service.create_approval(command)
            command = self.commands_repository.attach_approval(
                command.id,
                approval_id=approval.id,
            ) or command.model_copy(
                update={"approval_id": approval.id, "status": CommandStatus.AWAITING_APPROVAL}
            )

        return CommandIngestResponse(**command.model_dump()), 201


command_service = CommandService()
