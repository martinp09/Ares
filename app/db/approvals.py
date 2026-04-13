from __future__ import annotations

from typing import Any

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.approvals import ApprovalRecord, ApprovalStatus
from app.models.commands import generate_id


class ApprovalsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create(
        self,
        *,
        command_id: str,
        business_id: str,
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
        return approval

    def get(self, approval_id: str) -> ApprovalRecord | None:
        with self.client.transaction() as store:
            return store.approvals.get(approval_id)

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
