from __future__ import annotations

from datetime import datetime

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.commands import CommandsRepository
from app.db.control_plane_supabase import (
    control_plane_backend_enabled,
    external_id,
    fetch_rows,
    insert_rows,
    patch_rows,
    resolve_tenant,
    row_id_from_external_id,
)
from app.models.commands import CommandPolicy, generate_id
from app.models.runs import RunRecord, RunStatus


class RunsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = client or get_control_plane_client(self.settings)
        self._force_memory = client is not None

    def create(
        self,
        *,
        command_id: str,
        business_id: str,
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
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._create_in_supabase(
                command_id=command_id,
                business_id=business_id,
                environment=environment,
                command_type=command_type,
                command_policy=command_policy,
                status=status,
                parent_run_id=parent_run_id,
                replay_reason=replay_reason,
                trigger_run_id=trigger_run_id,
                created_at=created_at,
                started_at=started_at,
                completed_at=completed_at,
                error_classification=error_classification,
                error_message=error_message,
            )
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
        return run

    def get(self, run_id: str) -> RunRecord | None:
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._get_in_supabase(run_id)
        with self.client.transaction() as store:
            return store.runs.get(run_id)

    def save(self, run: RunRecord) -> RunRecord:
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._save_in_supabase(run)
        with self.client.transaction() as store:
            store.runs[run.id] = run
            return run

    def _create_in_supabase(
        self,
        *,
        command_id: str,
        business_id: str,
        environment: str,
        command_type: str,
        command_policy: CommandPolicy,
        status: RunStatus,
        parent_run_id: str | None,
        replay_reason: str | None,
        trigger_run_id: str | None,
        created_at: datetime | None,
        started_at: datetime | None,
        completed_at: datetime | None,
        error_classification: str | None,
        error_message: str | None,
    ) -> RunRecord:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        payload = {
            "business_id": tenant.business_pk,
            "environment": tenant.environment,
            "command_id": row_id_from_external_id(command_id, "cmd"),
            "parent_run_id": row_id_from_external_id(parent_run_id, "run"),
            "replay_reason": replay_reason,
            "trigger_run_id": trigger_run_id,
            "status": self._status_to_db(status),
            "started_at": started_at.isoformat() if started_at else None,
            "completed_at": completed_at.isoformat() if completed_at else None,
            "error_classification": error_classification,
            "error_message": error_message,
        }
        if created_at is not None:
            payload["created_at"] = created_at.isoformat()
            payload["updated_at"] = created_at.isoformat()
        row = insert_rows("runs", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row, command_type=command_type, command_policy=command_policy)

    def _get_in_supabase(self, run_id: str) -> RunRecord | None:
        row_id = row_id_from_external_id(run_id, "run")
        if row_id is None:
            return None
        rows = fetch_rows(
            "runs",
            params={"select": "*", "id": f"eq.{row_id}", "limit": "1"},
            settings=self.settings,
        )
        return self._record_from_supabase(rows[0]) if rows else None

    def _save_in_supabase(self, run: RunRecord) -> RunRecord:
        row_id = row_id_from_external_id(run.id, "run")
        if row_id is None:
            return run
        rows = patch_rows(
            "runs",
            params={"id": f"eq.{row_id}"},
            row={
                "status": self._status_to_db(run.status),
                "trigger_run_id": run.trigger_run_id,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "error_classification": run.error_classification,
                "error_message": run.error_message,
            },
            select="*",
            settings=self.settings,
        )
        return self._record_from_supabase(rows[0]) if rows else run

    def _record_from_supabase(
        self,
        row: dict,
        *,
        command_type: str | None = None,
        command_policy: CommandPolicy | None = None,
    ) -> RunRecord:
        command_row = fetch_rows(
            "commands",
            params={"select": "command_type,policy_result", "id": f"eq.{row['command_id']}", "limit": "1"},
            settings=self.settings,
        )
        events = fetch_rows(
            "events",
            params={"select": "*", "run_id": f"eq.{row['id']}", "order": "created_at.asc"},
            settings=self.settings,
        )
        artifacts = fetch_rows(
            "artifacts",
            params={"select": "*", "run_id": f"eq.{row['id']}", "order": "created_at.asc"},
            settings=self.settings,
        )
        if command_row:
            command_type = str(command_row[0]["command_type"])
            command_policy = CommandsRepository._policy_from_db(str(command_row[0]["policy_result"]))
        return RunRecord(
            id=external_id("run", row["id"]),
            command_id=external_id("cmd", row["command_id"]),
            business_id=str(row["business_id"]),
            environment=str(row["environment"]),
            command_type=command_type or "",
            command_policy=command_policy or CommandPolicy.FORBIDDEN,
            status=self._status_from_db(str(row["status"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            trigger_run_id=row.get("trigger_run_id"),
            parent_run_id=external_id("run", row["parent_run_id"]) if row.get("parent_run_id") is not None else None,
            replay_reason=row.get("replay_reason"),
            started_at=row.get("started_at"),
            completed_at=row.get("completed_at"),
            error_classification=row.get("error_classification"),
            error_message=row.get("error_message"),
            artifacts=[self._artifact_from_supabase(item) for item in artifacts],
            events=[self._event_from_supabase(item) for item in events],
        )

    @staticmethod
    def _event_from_supabase(row: dict) -> dict:
        return {
            "id": external_id("evt", row["id"]),
            "run_id": external_id("run", row["run_id"]) if row.get("run_id") is not None else None,
            "event_type": row["event_type"],
            "payload": dict(row.get("payload") or {}),
            "created_at": row["created_at"],
        }

    @staticmethod
    def _artifact_from_supabase(row: dict) -> dict:
        return {
            "id": external_id("art", row["id"]),
            "run_id": external_id("run", row["run_id"]) if row.get("run_id") is not None else None,
            "artifact_type": row["artifact_type"],
            "payload": dict(row.get("data") or {}),
            "created_at": row["created_at"],
        }

    @staticmethod
    def _status_to_db(status: RunStatus) -> str:
        if status == RunStatus.IN_PROGRESS:
            return "running"
        return status.value

    @staticmethod
    def _status_from_db(value: str) -> RunStatus:
        if value == "running":
            return RunStatus.IN_PROGRESS
        return RunStatus(value)
