from __future__ import annotations

from typing import Any

from app.db.client import ControlPlaneClient, get_control_plane_client
from app.models.commands import CommandPolicy, CommandRecord, CommandStatus


class CommandsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create(
        self,
        *,
        business_id: str,
        environment: str,
        command_type: str,
        idempotency_key: str,
        payload: dict[str, Any] | None = None,
        policy: CommandPolicy,
        status: CommandStatus,
    ) -> CommandRecord:
        dedupe_key = (business_id, environment, command_type, idempotency_key)
        with self.client.transaction() as store:
            existing_id = store.command_keys.get(dedupe_key)
            if existing_id is not None:
                existing = store.commands[existing_id]
                return existing.model_copy(update={"deduped": True})

            command = CommandRecord(
                business_id=business_id,
                environment=environment,
                command_type=command_type,
                idempotency_key=idempotency_key,
                payload=payload or {},
                policy=policy,
                status=status,
            )
            store.commands[command.id] = command
            store.command_keys[dedupe_key] = command.id
            return command

    def get(self, command_id: str) -> CommandRecord | None:
        with self.client.transaction() as store:
            return store.commands.get(command_id)
