from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.db.client import ControlPlaneClient, get_control_plane_client, register_runtime_sql_identity
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
        with self.client.transaction() as store:
            return store.commands.get(command_id)
