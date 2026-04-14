from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.db.client import (
    ControlPlaneClient,
    SupabaseControlPlaneClient,
    get_control_plane_client,
    register_runtime_sql_identity,
)
from app.models.commands import CommandPolicy, CommandRecord, CommandStatus


def command_status_to_sql_status(status: CommandStatus) -> str:
    sql_status_by_runtime_status = {
        CommandStatus.ACCEPTED: "queued",
        CommandStatus.AWAITING_APPROVAL: "approval_required",
        CommandStatus.QUEUED: "queued",
        CommandStatus.REJECTED: "rejected",
    }
    return sql_status_by_runtime_status[status]


def command_status_from_sql_status(status: str) -> CommandStatus:
    runtime_status_by_sql_status = {
        "queued": CommandStatus.QUEUED,
        "approval_required": CommandStatus.AWAITING_APPROVAL,
        "rejected": CommandStatus.REJECTED,
        # Commands can become run-linked in SQL with states not represented in CommandStatus.
        "approved": CommandStatus.QUEUED,
        "running": CommandStatus.QUEUED,
        "completed": CommandStatus.QUEUED,
        "failed": CommandStatus.QUEUED,
        "cancelled": CommandStatus.QUEUED,
    }
    if status not in runtime_status_by_sql_status:
        raise ValueError(f"Unsupported command SQL status: {status}")
    return runtime_status_by_sql_status[status]


def command_policy_to_sql_policy_result(policy: CommandPolicy) -> str:
    sql_policy_by_runtime_policy = {
        CommandPolicy.SAFE_AUTONOMOUS: "safe_autonomous",
        CommandPolicy.APPROVAL_REQUIRED: "approval_required",
        CommandPolicy.FORBIDDEN: "blocked",
    }
    return sql_policy_by_runtime_policy[policy]


def command_policy_from_sql_policy_result(policy_result: str) -> CommandPolicy:
    runtime_policy_by_sql_policy = {
        "safe_autonomous": CommandPolicy.SAFE_AUTONOMOUS,
        "approval_required": CommandPolicy.APPROVAL_REQUIRED,
        "blocked": CommandPolicy.FORBIDDEN,
        # Conservatively treat pending records as approval-gated until classifier output is explicit.
        "pending": CommandPolicy.APPROVAL_REQUIRED,
    }
    if policy_result not in runtime_policy_by_sql_policy:
        raise ValueError(f"Unsupported command SQL policy result: {policy_result}")
    return runtime_policy_by_sql_policy[policy_result]


def command_record_from_row(row: Mapping[str, Any]) -> CommandRecord:
    raw_policy = row.get("runtime_policy")
    if raw_policy is not None:
        policy = CommandPolicy(str(raw_policy))
    else:
        raw_policy_result = row.get("policy_result")
        if raw_policy_result is None:
            raise ValueError("Command row is missing runtime_policy/policy_result")
        policy = command_policy_from_sql_policy_result(str(raw_policy_result))

    raw_status = row.get("runtime_status")
    if raw_status is not None:
        status = CommandStatus(str(raw_status))
    else:
        raw_sql_status = row.get("status")
        if raw_sql_status is None:
            raise ValueError("Command row is missing runtime_status/status")
        status = command_status_from_sql_status(str(raw_sql_status))

    row_payload = row.get("payload")
    payload: dict[str, Any] = dict(row_payload) if isinstance(row_payload, Mapping) else {}
    created_at = row.get("created_at")

    return CommandRecord(
        id=str(row.get("runtime_id") or row["id"]),
        business_id=int(row["business_id"]),
        environment=str(row["environment"]),
        command_type=str(row["command_type"]),
        payload=payload,
        idempotency_key=str(row["idempotency_key"]),
        policy=policy,
        status=status,
        approval_id=row.get("approval_id"),
        run_id=row.get("run_id"),
        created_at=created_at if isinstance(created_at, datetime) else str(created_at),
    )


class CommandsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def _is_supabase(self) -> bool:
        return getattr(self.client, "backend", None) == "supabase"

    def _supabase_client(self) -> SupabaseControlPlaneClient:
        if not isinstance(self.client, SupabaseControlPlaneClient):
            return self.client  # type: ignore[return-value]
        return self.client

    def _hydrate_runtime_links(self, command: CommandRecord) -> CommandRecord:
        supabase = self._supabase_client()
        run_rows = supabase.select(
            "runs",
            columns="runtime_id,command_runtime_id,created_at",
            filters={"command_runtime_id": command.id},
            order="created_at.asc",
            limit=1,
        )
        approval_rows = supabase.select(
            "approvals",
            columns="runtime_id,command_runtime_id,created_at",
            filters={"command_runtime_id": command.id},
            order="created_at.desc",
            limit=1,
        )
        return command.model_copy(
            update={
                "run_id": str(run_rows[0]["runtime_id"]) if run_rows else None,
                "approval_id": str(approval_rows[0]["runtime_id"]) if approval_rows else None,
            }
        )

    def _select_supabase_command(
        self,
        *,
        runtime_id: str | None = None,
        business_id: int | None = None,
        environment: str | None = None,
        command_type: str | None = None,
        idempotency_key: str | None = None,
    ) -> CommandRecord | None:
        supabase = self._supabase_client()
        filters: dict[str, str | int] = {}
        if runtime_id is not None:
            filters["runtime_id"] = runtime_id
        if business_id is not None:
            filters["business_id"] = business_id
        if environment is not None:
            filters["environment"] = environment
        if command_type is not None:
            filters["command_type"] = command_type
        if idempotency_key is not None:
            filters["idempotency_key"] = idempotency_key

        rows = supabase.select(
            "commands",
            columns=(
                "id,runtime_id,business_id,environment,command_type,payload,"
                "idempotency_key,policy_result,runtime_policy,status,runtime_status,created_at"
            ),
            filters=filters,
            limit=1,
        )
        if not rows:
            return None

        command = command_record_from_row(rows[0])
        return self._hydrate_runtime_links(command)

    def create(
        self,
        *,
        business_id: int,
        environment: str,
        command_type: str,
        idempotency_key: str,
        payload: dict[str, Any] | None = None,
        policy: CommandPolicy,
        status: CommandStatus,
    ) -> CommandRecord:
        if self._is_supabase():
            existing = self._select_supabase_command(
                business_id=business_id,
                environment=environment,
                command_type=command_type,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
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
            supabase = self._supabase_client()
            rows = supabase.insert(
                "commands",
                rows=[
                    {
                        "runtime_id": command.id,
                        "business_id": business_id,
                        "environment": environment,
                        "command_type": command_type,
                        "payload": command.payload,
                        "idempotency_key": idempotency_key,
                        "policy_result": command_policy_to_sql_policy_result(policy),
                        "runtime_policy": policy.value,
                        "approval_required": policy == CommandPolicy.APPROVAL_REQUIRED,
                        "status": command_status_to_sql_status(status),
                        "runtime_status": status.value,
                        "source_surface": "api",
                    }
                ],
                columns=(
                    "id,runtime_id,business_id,environment,command_type,payload,idempotency_key,"
                    "policy_result,runtime_policy,status,runtime_status,created_at"
                ),
                on_conflict="business_id,environment,command_type,idempotency_key",
                ignore_duplicates=True,
            )
            if not rows:
                deduped = self._select_supabase_command(
                    business_id=business_id,
                    environment=environment,
                    command_type=command_type,
                    idempotency_key=idempotency_key,
                )
                if deduped is None:
                    raise RuntimeError("Supabase command insert deduped without an existing command row")
                return deduped.model_copy(update={"deduped": True})
            created = command_record_from_row(rows[0])
            return self._hydrate_runtime_links(created)

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
            register_runtime_sql_identity(store, table="commands", runtime_id=command.id)
            return command

    def get(self, command_id: str) -> CommandRecord | None:
        if self._is_supabase():
            return self._select_supabase_command(runtime_id=command_id)
        with self.client.transaction() as store:
            return store.commands.get(command_id)

    def save(self, command: CommandRecord) -> CommandRecord:
        if self._is_supabase():
            supabase = self._supabase_client()
            supabase.update(
                "commands",
                values={
                    "runtime_status": command.status.value,
                    "status": command_status_to_sql_status(command.status),
                    "runtime_policy": command.policy.value,
                    "policy_result": command_policy_to_sql_policy_result(command.policy),
                },
                filters={"runtime_id": command.id},
                columns=(
                    "id,runtime_id,business_id,environment,command_type,payload,idempotency_key,"
                    "policy_result,runtime_policy,status,runtime_status,created_at"
                ),
            )
            return command

        with self.client.transaction() as store:
            store.commands[command.id] = command
        return command
