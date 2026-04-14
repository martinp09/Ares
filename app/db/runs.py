from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.db.client import ControlPlaneClient, get_control_plane_client, register_runtime_sql_identity, utc_now
from app.db.commands import command_policy_from_sql_policy_result
from app.models.commands import CommandPolicy, generate_id
from app.models.runs import RunRecord, RunStatus


def run_status_to_sql_status(status: RunStatus) -> str:
    sql_status_by_runtime_status = {
        RunStatus.QUEUED: "queued",
        RunStatus.IN_PROGRESS: "running",
        RunStatus.COMPLETED: "completed",
        RunStatus.FAILED: "failed",
    }
    return sql_status_by_runtime_status[status]


def run_status_from_sql_status(status: str) -> RunStatus:
    runtime_status_by_sql_status = {
        "queued": RunStatus.QUEUED,
        "running": RunStatus.IN_PROGRESS,
        "completed": RunStatus.COMPLETED,
        "failed": RunStatus.FAILED,
        "cancelled": RunStatus.FAILED,
    }
    if status not in runtime_status_by_sql_status:
        raise ValueError(f"Unsupported run SQL status: {status}")
    return runtime_status_by_sql_status[status]


def run_record_from_row(row: Mapping[str, Any]) -> RunRecord:
    raw_runtime_policy = row.get("runtime_policy")
    if raw_runtime_policy is not None:
        command_policy = CommandPolicy(str(raw_runtime_policy))
    else:
        raw_policy_result = row.get("policy_result")
        if raw_policy_result is None:
            raise ValueError("Run row is missing runtime_policy/policy_result")
        command_policy = command_policy_from_sql_policy_result(str(raw_policy_result))

    raw_runtime_status = row.get("runtime_status")
    if raw_runtime_status is not None:
        status = RunStatus(str(raw_runtime_status))
    else:
        raw_sql_status = row.get("status")
        if raw_sql_status is None:
            raise ValueError("Run row is missing runtime_status/status")
        status = run_status_from_sql_status(str(raw_sql_status))

    raw_created_at = row.get("created_at")
    raw_updated_at = row.get("updated_at")
    if raw_created_at is None or raw_updated_at is None:
        raise ValueError("Run row is missing created_at/updated_at")

    return RunRecord(
        id=str(row.get("runtime_id") or row["id"]),
        command_id=str(row.get("command_runtime_id") or row["command_id"]),
        business_id=int(row["business_id"]),
        environment=str(row["environment"]),
        command_type=str(row["command_type"]),
        command_policy=command_policy,
        status=status,
        created_at=raw_created_at if isinstance(raw_created_at, datetime) else str(raw_created_at),
        updated_at=raw_updated_at if isinstance(raw_updated_at, datetime) else str(raw_updated_at),
        trigger_run_id=str(row["trigger_run_id"]) if row.get("trigger_run_id") is not None else None,
        parent_run_id=str(row.get("parent_runtime_id") or row.get("parent_run_id"))
        if (row.get("parent_runtime_id") is not None or row.get("parent_run_id") is not None)
        else None,
        replay_reason=str(row["replay_reason"]) if row.get("replay_reason") is not None else None,
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        error_classification=str(row["error_classification"]) if row.get("error_classification") is not None else None,
        error_message=str(row["error_message"]) if row.get("error_message") is not None else None,
        artifacts=[],
        events=[],
    )


class RunsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create(
        self,
        *,
        command_id: str,
        business_id: int,
        environment: str,
        command_type: str,
        command_policy: CommandPolicy,
        status: RunStatus = RunStatus.QUEUED,
        parent_run_id: str | None = None,
        replay_reason: str | None = None,
        trigger_run_id: str | None = None,
        created_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_classification: str | None = None,
        error_message: str | None = None,
    ) -> RunRecord:
        now = created_at or utc_now()
        run = RunRecord(
            id=generate_id("run"),
            command_id=command_id,
            business_id=business_id,
            environment=environment,
            command_type=command_type,
            command_policy=command_policy,
            status=status,
            created_at=now,
            updated_at=now,
            trigger_run_id=trigger_run_id,
            parent_run_id=parent_run_id,
            replay_reason=replay_reason,
            started_at=started_at,
            completed_at=completed_at,
            error_classification=error_classification,
            error_message=error_message,
            artifacts=[],
            events=[],
        )
        with self.client.transaction() as store:
            store.runs[run.id] = run
            register_runtime_sql_identity(store, table="runs", runtime_id=run.id)
        return run

    def get(self, run_id: str) -> RunRecord | None:
        with self.client.transaction() as store:
            return store.runs.get(run_id)
