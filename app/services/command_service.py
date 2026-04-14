from __future__ import annotations

from app.db.commands import CommandsRepository
from app.models.commands import CommandCreateRequest, CommandIngestResponse, CommandPolicy, CommandStatus
from app.policies.classifier import apply_policy_precedence
from app.services.approval_service import approval_service
from app.services.run_service import run_service


POLICY_BY_COMMAND: dict[str, CommandPolicy] = {
    "run_market_research": CommandPolicy.SAFE_AUTONOMOUS,
    "create_campaign_brief": CommandPolicy.SAFE_AUTONOMOUS,
    "draft_campaign_assets": CommandPolicy.SAFE_AUTONOMOUS,
    "propose_launch": CommandPolicy.APPROVAL_REQUIRED,
    "publish_campaign": CommandPolicy.APPROVAL_REQUIRED,
}


class CommandService:
    def __init__(self, commands_repository: CommandsRepository | None = None) -> None:
        self.commands_repository = commands_repository or CommandsRepository()

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

        command = self.commands_repository.create(
            business_id=request.business_id,
            environment=request.environment,
            command_type=request.command_type,
            idempotency_key=request.idempotency_key,
            payload=request.payload,
            policy=policy,
            status=CommandStatus.ACCEPTED,
        )
        if command.deduped:
            return CommandIngestResponse(**command.model_dump()), 200

        if policy == CommandPolicy.SAFE_AUTONOMOUS:
            run = run_service.create_run(command)
            command.run_id = run.id
            command.status = CommandStatus.QUEUED
            self.commands_repository.save(command)
        else:
            approval = approval_service.create_approval(command)
            command.approval_id = approval.id
            command.status = CommandStatus.AWAITING_APPROVAL
            self.commands_repository.save(command)

        return CommandIngestResponse(**command.model_dump()), 201


command_service = CommandService()
