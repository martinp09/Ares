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
from app.models.approvals import ApprovalRecord, ApprovalStatus
from app.models.commands import generate_id


def approval_status_from_sql_status(status: str) -> ApprovalStatus:
    runtime_status_by_sql_status = {
        "pending": ApprovalStatus.PENDING,
        "approved": ApprovalStatus.APPROVED,
        "rejected": ApprovalStatus.REJECTED,
        "expired": ApprovalStatus.REJECTED,
    }
    if status not in runtime_status_by_sql_status:
        raise ValueError(f"Unsupported approval SQL status: {status}")
    return runtime_status_by_sql_status[status]


def approval_record_from_row(row: Mapping[str, Any]) -> ApprovalRecord:
    raw_created_at = row.get("created_at")
    if raw_created_at is None:
        raise ValueError("Approval row is missing created_at")

    raw_approved_at = row.get("approved_at") or row.get("decided_at")
    actor_id = row.get("actor_id") or row.get("approved_by")
    raw_payload = row.get("payload_snapshot")
    payload_snapshot: dict[str, Any] = dict(raw_payload) if isinstance(raw_payload, Mapping) else {}

    return ApprovalRecord(
        id=str(row.get("runtime_id") or row["id"]),
        command_id=str(row.get("command_runtime_id") or row["command_id"]),
        business_id=int(row["business_id"]),
        environment=str(row["environment"]),
        command_type=str(row["command_type"]),
        status=approval_status_from_sql_status(str(row["status"])),
        payload_snapshot=payload_snapshot,
        created_at=raw_created_at if isinstance(raw_created_at, datetime) else str(raw_created_at),
        approved_at=raw_approved_at if isinstance(raw_approved_at, datetime) else raw_approved_at,
        actor_id=str(actor_id) if actor_id is not None else None,
    )


class ApprovalsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def _is_supabase(self) -> bool:
        return getattr(self.client, "backend", None) == "supabase"

    def _supabase_client(self) -> SupabaseControlPlaneClient:
        if not isinstance(self.client, SupabaseControlPlaneClient):
            return self.client  # type: ignore[return-value]
        return self.client

    def _resolve_command_row(
        self,
        *,
        command_runtime_id: str | None = None,
        command_sql_id: int | None = None,
        business_id: int,
        environment: str,
    ) -> dict[str, Any] | None:
        supabase = self._supabase_client()
        filters: dict[str, str | int] = {
            "business_id": business_id,
            "environment": environment,
        }
        if command_runtime_id is not None:
            filters["runtime_id"] = command_runtime_id
        if command_sql_id is not None:
            filters["id"] = command_sql_id
        rows = supabase.select(
            "commands",
            columns="id,runtime_id,command_type,business_id,environment",
            filters=filters,
            limit=1,
        )
        return rows[0] if rows else None

    def _approval_record_from_supabase_row(self, row: Mapping[str, Any]) -> ApprovalRecord:
        mutable_row: dict[str, Any] = dict(row)
        if mutable_row.get("command_type") is None or mutable_row.get("command_runtime_id") is None:
            command_row = self._resolve_command_row(
                command_runtime_id=str(mutable_row.get("command_runtime_id"))
                if mutable_row.get("command_runtime_id") is not None
                else None,
                command_sql_id=int(mutable_row["command_id"]) if mutable_row.get("command_id") is not None else None,
                business_id=int(mutable_row["business_id"]),
                environment=str(mutable_row["environment"]),
            )
            if command_row is not None:
                if mutable_row.get("command_runtime_id") is None:
                    mutable_row["command_runtime_id"] = command_row.get("runtime_id")
                if mutable_row.get("command_type") is None:
                    mutable_row["command_type"] = command_row.get("command_type")
        return approval_record_from_row(mutable_row)

    def create(
        self,
        *,
        command_id: str,
        business_id: int,
        environment: str,
        command_type: str,
        payload_snapshot: dict[str, Any] | None = None,
    ) -> ApprovalRecord:
        if self._is_supabase():
            supabase = self._supabase_client()
            command_row = self._resolve_command_row(
                command_runtime_id=command_id,
                business_id=business_id,
                environment=environment,
            )
            if command_row is None:
                raise ValueError(f"Cannot create approval for unknown command runtime_id '{command_id}'")

            runtime_id = generate_id("apr")
            created_at = utc_now()
            rows = supabase.insert(
                "approvals",
                rows=[
                    {
                        "runtime_id": runtime_id,
                        "command_runtime_id": command_id,
                        "business_id": business_id,
                        "environment": environment,
                        "command_id": command_row["id"],
                        "status": ApprovalStatus.PENDING.value,
                        "payload_snapshot": payload_snapshot or {},
                        "actor_id": None,
                        "approved_at": None,
                        "approval_surface": "hermes",
                        "approved_payload": payload_snapshot or {},
                        "created_at": created_at.isoformat(),
                    }
                ],
                columns=(
                    "id,runtime_id,command_id,command_runtime_id,business_id,environment,status,"
                    "payload_snapshot,created_at,approved_at,decided_at,actor_id,approved_by"
                ),
            )
            if not rows:
                raise RuntimeError("Supabase approval insert returned no rows")
            approval_row = dict(rows[0])
            approval_row["command_type"] = command_type
            return self._approval_record_from_supabase_row(approval_row)

        approval = ApprovalRecord(
            id=generate_id("apr"),
            command_id=command_id,
            business_id=business_id,
            environment=environment,
            command_type=command_type,
            status=ApprovalStatus.PENDING,
            payload_snapshot=payload_snapshot or {},
            created_at=utc_now(),
        )
        with self.client.transaction() as store:
            store.approvals[approval.id] = approval
            register_runtime_sql_identity(store, table="approvals", runtime_id=approval.id)
        return approval

    def get(self, approval_id: str) -> ApprovalRecord | None:
        if self._is_supabase():
            rows = self._supabase_client().select(
                "approvals",
                columns=(
                    "id,runtime_id,command_id,command_runtime_id,business_id,environment,status,"
                    "payload_snapshot,created_at,approved_at,decided_at,actor_id,approved_by"
                ),
                filters={"runtime_id": approval_id},
                limit=1,
            )
            if not rows:
                return None
            return self._approval_record_from_supabase_row(rows[0])
        with self.client.transaction() as store:
            return store.approvals.get(approval_id)

    def list(
        self,
        *,
        business_id: str | int | None = None,
        environment: str | None = None,
        status: ApprovalStatus | None = None,
    ) -> list[ApprovalRecord]:
        if self._is_supabase():
            filters: dict[str, str | int] = {}
            normalized_business_id = _normalize_business_id(business_id)
            if normalized_business_id is not None:
                if not isinstance(normalized_business_id, int):
                    return []
                filters["business_id"] = normalized_business_id
            if environment is not None:
                filters["environment"] = environment
            if status is not None:
                filters["status"] = status.value

            rows = self._supabase_client().select(
                "approvals",
                columns=(
                    "id,runtime_id,command_id,command_runtime_id,business_id,environment,status,"
                    "payload_snapshot,created_at,approved_at,decided_at,actor_id,approved_by"
                ),
                filters=filters,
                order="created_at.desc",
            )
            return [self._approval_record_from_supabase_row(row) for row in rows]

        with self.client.transaction() as store:
            approvals = list(store.approvals.values())

        normalized_business_id = _normalize_business_id(business_id)
        if business_id is not None:
            approvals = [
                approval for approval in approvals if _normalize_business_id(approval.business_id) == normalized_business_id
            ]
        if environment is not None:
            approvals = [approval for approval in approvals if approval.environment == environment]
        if status is not None:
            approvals = [approval for approval in approvals if approval.status == status]
        return approvals

    def approve(self, approval_id: str, *, actor_id: str) -> ApprovalRecord | None:
        if self._is_supabase():
            existing = self.get(approval_id)
            if existing is None:
                return None
            if existing.status == ApprovalStatus.APPROVED:
                return existing

            approved_at = utc_now().isoformat()
            rows = self._supabase_client().update(
                "approvals",
                values={
                    "status": ApprovalStatus.APPROVED.value,
                    "actor_id": actor_id,
                    "approved_by": actor_id,
                    "approved_at": approved_at,
                    "decided_at": approved_at,
                },
                filters={"runtime_id": approval_id},
                columns=(
                    "id,runtime_id,command_id,command_runtime_id,business_id,environment,status,"
                    "payload_snapshot,created_at,approved_at,decided_at,actor_id,approved_by"
                ),
            )
            if not rows:
                return None
            return self._approval_record_from_supabase_row(rows[0])

        with self.client.transaction() as store:
            approval = store.approvals.get(approval_id)
            if approval is None:
                return None
            if approval.status == ApprovalStatus.APPROVED:
                return approval

            approved_at = utc_now()
            approved = approval.model_copy(
                update={
                    "status": ApprovalStatus.APPROVED,
                    "actor_id": actor_id,
                    "approved_at": approved_at,
                }
            )
            store.approvals[approval_id] = approved
            return approved


def _normalize_business_id(value: str | int | None) -> str | int | None:
    if value is None or isinstance(value, int):
        return value
    try:
        return int(value)
    except ValueError:
        return value
