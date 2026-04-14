from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.db.client import (
    ControlPlaneClient,
    SupabaseControlPlaneClient,
    get_control_plane_client,
    register_runtime_sql_identity,
    utc_now,
)
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
    raw_parent_runtime_id = row.get("parent_runtime_id") or row.get("parent_run_id")
    raw_replay_source_runtime_id = row.get("replay_source_runtime_id") or row.get("replay_source_run_id")

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
        parent_run_id=str(raw_parent_runtime_id) if raw_parent_runtime_id is not None else None,
        replay_source_run_id=str(raw_replay_source_runtime_id)
        if raw_replay_source_runtime_id is not None
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

    def _is_supabase(self) -> bool:
        return getattr(self.client, "backend", None) == "supabase"

    def _supabase_client(self) -> SupabaseControlPlaneClient:
        if not isinstance(self.client, SupabaseControlPlaneClient):
            return self.client  # type: ignore[return-value]
        return self.client

    def _lookup_command_row(self, *, command_runtime_id: str, business_id: int, environment: str) -> dict[str, Any] | None:
        rows = self._supabase_client().select(
            "commands",
            columns="id,runtime_id,command_type,business_id,environment",
            filters={
                "runtime_id": command_runtime_id,
                "business_id": business_id,
                "environment": environment,
            },
            limit=1,
        )
        return rows[0] if rows else None

    def _lookup_run_row(self, *, run_runtime_id: str, business_id: int, environment: str) -> dict[str, Any] | None:
        rows = self._supabase_client().select(
            "runs",
            columns=(
                "id,runtime_id,command_id,command_runtime_id,business_id,environment,parent_run_id,parent_runtime_id,"
                "replay_source_run_id,replay_source_runtime_id,replay_reason,status,runtime_status,runtime_policy,"
                "trigger_run_id,started_at,completed_at,error_classification,error_message,created_at,updated_at"
            ),
            filters={
                "runtime_id": run_runtime_id,
                "business_id": business_id,
                "environment": environment,
            },
            limit=1,
        )
        return rows[0] if rows else None

    def _resolve_runtime_run_to_sql_id(
        self, runtime_id: str | None, *, business_id: int, environment: str
    ) -> int | None:
        if runtime_id is None:
            return None
        row = self._lookup_run_row(run_runtime_id=runtime_id, business_id=business_id, environment=environment)
        if row is None:
            return None
        return int(row["id"])

    def _list_run_events(self, run_runtime_id: str) -> list[dict[str, Any]]:
        rows = self._supabase_client().select(
            "events",
            columns="id,runtime_id,run_runtime_id,event_type,payload,created_at",
            filters={"run_runtime_id": run_runtime_id},
            order="created_at.asc",
        )
        events: list[dict[str, Any]] = []
        for row in rows:
            payload = row.get("payload")
            events.append(
                {
                    "id": str(row.get("runtime_id") or row["id"]),
                    "run_id": run_runtime_id,
                    "event_type": str(row["event_type"]),
                    "payload": dict(payload) if isinstance(payload, Mapping) else {},
                    "created_at": row["created_at"],
                }
            )
        return events

    def _list_run_artifacts(self, run_runtime_id: str) -> list[dict[str, Any]]:
        rows = self._supabase_client().select(
            "artifacts",
            columns="id,runtime_id,run_runtime_id,artifact_type,payload,data,created_at",
            filters={"run_runtime_id": run_runtime_id},
            order="created_at.asc",
        )
        artifacts: list[dict[str, Any]] = []
        for row in rows:
            payload = row.get("payload")
            if not isinstance(payload, Mapping):
                fallback_payload = row.get("data")
                payload = dict(fallback_payload) if isinstance(fallback_payload, Mapping) else {}
            artifacts.append(
                {
                    "id": str(row.get("runtime_id") or row["id"]),
                    "run_id": run_runtime_id,
                    "artifact_type": str(row["artifact_type"]),
                    "payload": dict(payload),
                    "created_at": row["created_at"],
                }
            )
        return artifacts

    def _hydrate_supabase_run(self, row: Mapping[str, Any]) -> RunRecord:
        mutable = dict(row)
        if mutable.get("command_type") is None:
            command_row = self._lookup_command_row(
                command_runtime_id=str(mutable.get("command_runtime_id")),
                business_id=int(mutable["business_id"]),
                environment=str(mutable["environment"]),
            )
            if command_row is not None:
                mutable["command_type"] = command_row["command_type"]

        run = run_record_from_row(mutable)
        run.events = self._list_run_events(run.id)
        run.artifacts = self._list_run_artifacts(run.id)
        return run

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
        if self._is_supabase():
            command_row = self._lookup_command_row(
                command_runtime_id=command_id,
                business_id=business_id,
                environment=environment,
            )
            if command_row is None:
                raise ValueError(f"Cannot create run for unknown command runtime_id '{command_id}'")

            now = created_at or utc_now()
            parent_sql_id = self._resolve_runtime_run_to_sql_id(
                parent_run_id,
                business_id=business_id,
                environment=environment,
            )
            replay_source_runtime_id = parent_run_id
            replay_source_sql_id = self._resolve_runtime_run_to_sql_id(
                replay_source_runtime_id,
                business_id=business_id,
                environment=environment,
            )
            runtime_id = generate_id("run")
            inserted = self._supabase_client().insert(
                "runs",
                rows=[
                    {
                        "runtime_id": runtime_id,
                        "command_id": command_row["id"],
                        "command_runtime_id": command_id,
                        "business_id": business_id,
                        "environment": environment,
                        "parent_run_id": parent_sql_id,
                        "parent_runtime_id": parent_run_id,
                        "replay_source_run_id": replay_source_sql_id,
                        "replay_source_runtime_id": replay_source_runtime_id,
                        "replay_reason": replay_reason,
                        "trigger_run_id": trigger_run_id,
                        "status": run_status_to_sql_status(status),
                        "runtime_status": status.value,
                        "runtime_policy": command_policy.value,
                        "started_at": started_at.isoformat() if isinstance(started_at, datetime) else started_at,
                        "completed_at": completed_at.isoformat()
                        if isinstance(completed_at, datetime)
                        else completed_at,
                        "error_classification": error_classification,
                        "error_message": error_message,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    }
                ],
                columns=(
                    "id,runtime_id,command_id,command_runtime_id,business_id,environment,parent_run_id,parent_runtime_id,"
                    "replay_source_run_id,replay_source_runtime_id,replay_reason,status,runtime_status,runtime_policy,"
                    "trigger_run_id,started_at,completed_at,error_classification,error_message,created_at,updated_at"
                ),
            )
            if not inserted:
                raise RuntimeError("Supabase run insert returned no rows")
            run_row = dict(inserted[0])
            run_row["command_type"] = command_type
            return self._hydrate_supabase_run(run_row)

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
        if self._is_supabase():
            rows = self._supabase_client().select(
                "runs",
                columns=(
                    "id,runtime_id,command_id,command_runtime_id,business_id,environment,parent_run_id,parent_runtime_id,"
                    "replay_source_run_id,replay_source_runtime_id,replay_reason,status,runtime_status,runtime_policy,"
                    "trigger_run_id,started_at,completed_at,error_classification,error_message,created_at,updated_at"
                ),
                filters={"runtime_id": run_id},
                limit=1,
            )
            if not rows:
                return None
            return self._hydrate_supabase_run(rows[0])

        with self.client.transaction() as store:
            return store.runs.get(run_id)

    def save(self, run: RunRecord) -> RunRecord:
        if self._is_supabase():
            parent_sql_id = self._resolve_runtime_run_to_sql_id(
                run.parent_run_id,
                business_id=run.business_id,
                environment=run.environment,
            )
            replay_source_sql_id = self._resolve_runtime_run_to_sql_id(
                run.replay_source_run_id,
                business_id=run.business_id,
                environment=run.environment,
            )
            self._supabase_client().update(
                "runs",
                values={
                    "status": run_status_to_sql_status(run.status),
                    "runtime_status": run.status.value,
                    "runtime_policy": run.command_policy.value,
                    "trigger_run_id": run.trigger_run_id,
                    "parent_run_id": parent_sql_id,
                    "parent_runtime_id": run.parent_run_id,
                    "replay_source_run_id": replay_source_sql_id,
                    "replay_source_runtime_id": run.replay_source_run_id,
                    "replay_reason": run.replay_reason,
                    "started_at": run.started_at.isoformat() if isinstance(run.started_at, datetime) else run.started_at,
                    "completed_at": run.completed_at.isoformat()
                    if isinstance(run.completed_at, datetime)
                    else run.completed_at,
                    "error_classification": run.error_classification,
                    "error_message": run.error_message,
                    "updated_at": utc_now().isoformat(),
                },
                filters={"runtime_id": run.id},
                columns=(
                    "id,runtime_id,command_id,command_runtime_id,business_id,environment,parent_run_id,parent_runtime_id,"
                    "replay_source_run_id,replay_source_runtime_id,replay_reason,status,runtime_status,runtime_policy,"
                    "trigger_run_id,started_at,completed_at,error_classification,error_message,created_at,updated_at"
                ),
            )
            return run

        with self.client.transaction() as store:
            store.runs[run.id] = run
        return run
