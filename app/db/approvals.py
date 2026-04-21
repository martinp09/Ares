from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.control_plane_supabase import (
    control_plane_backend_enabled,
    external_id,
    fetch_rows,
    insert_rows,
    patch_rows,
    resolve_tenant,
    row_id_from_external_id,
)
from app.models.approvals import ApprovalRecord, ApprovalStatus
from app.models.commands import generate_id


class ApprovalsRepository:
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
        payload_snapshot: dict[str, Any] | None = None,
    ) -> ApprovalRecord:
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._create_in_supabase(
                command_id=command_id,
                business_id=business_id,
                environment=environment,
                payload_snapshot=payload_snapshot,
            )
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
        return approval

    def get(self, approval_id: str) -> ApprovalRecord | None:
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._get_in_supabase(approval_id)
        with self.client.transaction() as store:
            return store.approvals.get(approval_id)

    def list(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
        status: ApprovalStatus | None = None,
    ) -> list[ApprovalRecord]:
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._list_in_supabase(business_id=business_id, environment=environment, status=status)
        with self.client.transaction() as store:
            approvals = list(store.approvals.values())

        if business_id is not None:
            approvals = [approval for approval in approvals if approval.business_id == business_id]
        if environment is not None:
            approvals = [approval for approval in approvals if approval.environment == environment]
        if status is not None:
            approvals = [approval for approval in approvals if approval.status == status]
        return approvals

    def approve(self, approval_id: str, *, actor_id: str) -> ApprovalRecord | None:
        if control_plane_backend_enabled(self.settings) and not self._force_memory:
            return self._approve_in_supabase(approval_id, actor_id=actor_id)
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

    def _create_in_supabase(
        self,
        *,
        command_id: str,
        business_id: str,
        environment: str,
        payload_snapshot: dict[str, Any] | None,
    ) -> ApprovalRecord:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        row = insert_rows(
            "approvals",
            [
                {
                    "business_id": tenant.business_pk,
                    "environment": tenant.environment,
                    "command_id": row_id_from_external_id(command_id, "cmd"),
                    "approved_payload": payload_snapshot or {},
                    "status": ApprovalStatus.PENDING.value,
                }
            ],
            select="*",
            settings=self.settings,
        )[0]
        return self._record_from_supabase(row)

    def _get_in_supabase(self, approval_id: str) -> ApprovalRecord | None:
        row_id = row_id_from_external_id(approval_id, "apr")
        if row_id is None:
            return None
        rows = fetch_rows(
            "approvals",
            params={"select": "*", "id": f"eq.{row_id}", "limit": "1"},
            settings=self.settings,
        )
        return self._record_from_supabase(rows[0]) if rows else None

    def _list_in_supabase(
        self,
        *,
        business_id: str | None,
        environment: str | None,
        status: ApprovalStatus | None,
    ) -> list[ApprovalRecord]:
        params = {"select": "*", "order": "created_at.desc"}
        if business_id is not None and environment is not None:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            params["business_id"] = f"eq.{tenant.business_pk}"
            params["environment"] = f"eq.{tenant.environment}"
        elif environment is not None:
            params["environment"] = f"eq.{environment}"
        if status is not None:
            params["status"] = f"eq.{status.value}"
        rows = fetch_rows("approvals", params=params, settings=self.settings)
        return [self._record_from_supabase(row) for row in rows]

    def _approve_in_supabase(self, approval_id: str, *, actor_id: str) -> ApprovalRecord | None:
        row_id = row_id_from_external_id(approval_id, "apr")
        if row_id is None:
            return None
        rows = patch_rows(
            "approvals",
            params={"id": f"eq.{row_id}"},
            row={
                "status": ApprovalStatus.APPROVED.value,
                "approved_by": actor_id,
                "decided_at": utc_now().isoformat(),
            },
            select="*",
            settings=self.settings,
        )
        return self._record_from_supabase(rows[0]) if rows else None

    def _record_from_supabase(self, row: dict) -> ApprovalRecord:
        command_rows = fetch_rows(
            "commands",
            params={"select": "command_type", "id": f"eq.{row['command_id']}", "limit": "1"},
            settings=self.settings,
        )
        return ApprovalRecord(
            id=external_id("apr", row["id"]),
            command_id=external_id("cmd", row["command_id"]),
            business_id=str(row["business_id"]),
            environment=str(row["environment"]),
            command_type=str(command_rows[0]["command_type"]) if command_rows else "",
            status=ApprovalStatus(str(row["status"])),
            payload_snapshot=dict(row.get("approved_payload") or {}),
            created_at=row["created_at"],
            approved_at=row.get("decided_at"),
            actor_id=row.get("approved_by"),
        )
