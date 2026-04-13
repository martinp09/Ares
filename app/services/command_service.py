from __future__ import annotations

from app.models.commands import (
    CommandCreateRequest,
    CommandIngestResponse,
    CommandPolicy,
    CommandRecord,
    CommandStatus,
)
from app.services.approval_service import approval_service
from app.services.run_service import STORE, run_service


POLICY_BY_COMMAND: dict[str, CommandPolicy] = {
    "run_market_research": CommandPolicy.SAFE_AUTONOMOUS,
    "create_campaign_brief": CommandPolicy.SAFE_AUTONOMOUS,
    "draft_campaign_assets": CommandPolicy.SAFE_AUTONOMOUS,
    "propose_launch": CommandPolicy.APPROVAL_REQUIRED,
    "publish_campaign": CommandPolicy.APPROVAL_REQUIRED,
}


class CommandService:
    def classify(self, command_type: str) -> CommandPolicy:
        return POLICY_BY_COMMAND.get(command_type, CommandPolicy.FORBIDDEN)

    def create_command(self, request: CommandCreateRequest) -> tuple[CommandIngestResponse, int]:
        dedupe_key = (
            request.business_id,
            request.environment,
            request.command_type,
            request.idempotency_key,
        )
        existing_id = STORE.command_keys.get(dedupe_key)
        if existing_id is not None:
            existing = STORE.commands[existing_id]
            deduped = existing.model_copy(update={"deduped": True})
            return CommandIngestResponse(**deduped.model_dump()), 200

        policy = self.classify(request.command_type)
        if policy == CommandPolicy.FORBIDDEN:
            raise ValueError(f"Unsupported or forbidden command_type '{request.command_type}'")

        command = CommandRecord(
            business_id=request.business_id,
            environment=request.environment,
            command_type=request.command_type,
            idempotency_key=request.idempotency_key,
            payload=request.payload,
            policy=policy,
            status=CommandStatus.ACCEPTED,
        )

        if policy == CommandPolicy.SAFE_AUTONOMOUS:
            run = run_service.create_run(command)
            command.run_id = run.id
            command.status = CommandStatus.QUEUED
        else:
            approval = approval_service.create_approval(command)
            command.approval_id = approval.id
            command.status = CommandStatus.AWAITING_APPROVAL

        STORE.commands[command.id] = command
        STORE.command_keys[dedupe_key] = command.id
        return CommandIngestResponse(**command.model_dump()), 201


command_service = CommandService()
