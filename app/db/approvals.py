from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.db.client import ControlPlaneClient, get_control_plane_client, register_runtime_sql_identity, utc_now
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

    def create(
        self,
        *,
        command_id: str,
        business_id: int,
        environment: str,
        command_type: str,
        payload_snapshot: dict[str, Any] | None = None,
    ) -> ApprovalRecord:
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
        with self.client.transaction() as store:
            return store.approvals.get(approval_id)

    def list(
        self,
        *,
        business_id: str | int | None = None,
        environment: str | None = None,
        status: ApprovalStatus | None = None,
    ) -> list[ApprovalRecord]:
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
