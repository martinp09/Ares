from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client
from app.db.control_plane_supabase import (
    control_plane_backend_enabled,
    external_id,
    fetch_rows,
    insert_rows,
    patch_rows,
    resolve_tenant,
    row_id_from_external_id,
)
from app.models.commands import CommandPolicy, CommandRecord, CommandStatus


class CommandsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = client or get_control_plane_client(self.settings)
        self._force_memory = client is not None

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
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._create_in_supabase(
                business_id=business_id,
                environment=environment,
                command_type=command_type,
                idempotency_key=idempotency_key,
                payload=payload,
                policy=policy,
                status=status,
            )
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
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._get_in_supabase(command_id)
        with self.client.transaction() as store:
            return store.commands.get(command_id)

    def get_by_idempotency_key(
        self,
        *,
        business_id: str,
        environment: str,
        command_type: str,
        idempotency_key: str,
    ) -> CommandRecord | None:
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._get_by_idempotency_key_in_supabase(
                business_id=business_id,
                environment=environment,
                command_type=command_type,
                idempotency_key=idempotency_key,
            )
        dedupe_key = (business_id, environment, command_type, idempotency_key)
        with self.client.transaction() as store:
            existing_id = store.command_keys.get(dedupe_key)
            if existing_id is None:
                return None
            return store.commands.get(existing_id)

    def attach_run(self, command_id: str, *, run_id: str) -> CommandRecord | None:
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._patch_in_supabase(command_id, status=CommandStatus.QUEUED)
        with self.client.transaction() as store:
            command = store.commands.get(command_id)
            if command is None:
                return None
            updated = command.model_copy(update={"run_id": run_id, "status": CommandStatus.QUEUED})
            store.commands[command_id] = updated
            return updated

    def attach_approval(self, command_id: str, *, approval_id: str) -> CommandRecord | None:
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._patch_in_supabase(command_id, status=CommandStatus.AWAITING_APPROVAL)
        with self.client.transaction() as store:
            command = store.commands.get(command_id)
            if command is None:
                return None
            updated = command.model_copy(
                update={"approval_id": approval_id, "status": CommandStatus.AWAITING_APPROVAL}
            )
            store.commands[command_id] = updated
            return updated

    def _create_in_supabase(
        self,
        *,
        business_id: str,
        environment: str,
        command_type: str,
        idempotency_key: str,
        payload: dict[str, Any] | None,
        policy: CommandPolicy,
        status: CommandStatus,
    ) -> CommandRecord:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        rows = fetch_rows(
            "commands",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "command_type": f"eq.{command_type}",
                "idempotency_key": f"eq.{idempotency_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if rows:
            return self._record_from_supabase(rows[0], deduped=True)

        row = insert_rows(
            "commands",
            [
                {
                    "business_id": tenant.business_pk,
                    "environment": tenant.environment,
                    "command_type": command_type,
                    "payload": payload or {},
                    "idempotency_key": idempotency_key,
                    "policy_result": self._policy_to_db(policy),
                    "approval_required": policy == CommandPolicy.APPROVAL_REQUIRED,
                    "status": self._status_to_db(status),
                }
            ],
            select="*",
            settings=self.settings,
        )[0]
        return self._record_from_supabase(row)

    def _get_in_supabase(self, command_id: str) -> CommandRecord | None:
        row_id = row_id_from_external_id(command_id, "cmd")
        if row_id is None:
            return None
        rows = fetch_rows(
            "commands",
            params={"select": "*", "id": f"eq.{row_id}", "limit": "1"},
            settings=self.settings,
        )
        return self._record_from_supabase(rows[0]) if rows else None

    def _get_by_idempotency_key_in_supabase(
        self,
        *,
        business_id: str,
        environment: str,
        command_type: str,
        idempotency_key: str,
    ) -> CommandRecord | None:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        rows = fetch_rows(
            "commands",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "command_type": f"eq.{command_type}",
                "idempotency_key": f"eq.{idempotency_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        return self._record_from_supabase(rows[0]) if rows else None

    def _patch_in_supabase(self, command_id: str, *, status: CommandStatus) -> CommandRecord | None:
        row_id = row_id_from_external_id(command_id, "cmd")
        if row_id is None:
            return None
        rows = patch_rows(
            "commands",
            params={"id": f"eq.{row_id}"},
            row={"status": self._status_to_db(status)},
            select="*",
            settings=self.settings,
        )
        return self._record_from_supabase(rows[0]) if rows else None

    def _record_from_supabase(self, row: dict, *, deduped: bool = False) -> CommandRecord:
        command_id = int(row["id"])
        approval_rows = fetch_rows(
            "approvals",
            params={
                "select": "id,status,created_at",
                "command_id": f"eq.{command_id}",
                "order": "created_at.desc",
                "limit": "1",
            },
            settings=self.settings,
        )
        run_rows = fetch_rows(
            "runs",
            params={
                "select": "id,created_at",
                "command_id": f"eq.{command_id}",
                "order": "created_at.desc",
                "limit": "1",
            },
            settings=self.settings,
        )
        return CommandRecord(
            id=external_id("cmd", row["id"]),
            business_id=str(row["business_id"]),
            environment=str(row["environment"]),
            command_type=str(row["command_type"]),
            payload=dict(row.get("payload") or {}),
            idempotency_key=str(row["idempotency_key"]),
            policy=self._policy_from_db(str(row.get("policy_result") or "pending")),
            status=self._status_from_db(str(row.get("status") or "queued")),
            approval_id=external_id("apr", approval_rows[0]["id"]) if approval_rows else None,
            run_id=external_id("run", run_rows[0]["id"]) if run_rows else None,
            deduped=deduped,
            created_at=row["created_at"],
        )

    @staticmethod
    def _policy_to_db(policy: CommandPolicy) -> str:
        if policy == CommandPolicy.SAFE_AUTONOMOUS:
            return "safe_autonomous"
        if policy == CommandPolicy.APPROVAL_REQUIRED:
            return "approval_required"
        return "blocked"

    @staticmethod
    def _policy_from_db(value: str) -> CommandPolicy:
        if value == "safe_autonomous":
            return CommandPolicy.SAFE_AUTONOMOUS
        if value == "approval_required":
            return CommandPolicy.APPROVAL_REQUIRED
        return CommandPolicy.FORBIDDEN

    @staticmethod
    def _status_to_db(status: CommandStatus) -> str:
        if status == CommandStatus.AWAITING_APPROVAL:
            return "approval_required"
        if status == CommandStatus.REJECTED:
            return "rejected"
        return "queued"

    @staticmethod
    def _status_from_db(value: str) -> CommandStatus:
        if value == "approval_required":
            return CommandStatus.AWAITING_APPROVAL
        if value == "rejected":
            return CommandStatus.REJECTED
        return CommandStatus.QUEUED
