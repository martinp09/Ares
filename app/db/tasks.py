from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.marketing_supabase import fetch_rows, insert_rows, marketing_backend_enabled, resolve_tenant
from app.models.commands import generate_id
from app.models.tasks import TaskRecord, TaskStatus


class TasksRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = client is not None
        self.settings = settings or get_settings()

    def create_manual_call(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        title: str,
    ) -> TaskRecord:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._create_manual_call_in_supabase(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                title=title,
            )
        record = TaskRecord(
            id=generate_id("tsk"),
            run_id=contact_id,
            title=title,
            status=TaskStatus.OPEN,
            created_at=utc_now(),
        )
        with self.client.transaction() as store:
            task_rows: dict[str, TaskRecord] = getattr(store, "marketing_task_rows", {})
            task_scope: dict[str, tuple[str, str, str]] = getattr(
                store, "marketing_task_scope", {}
            )
            setattr(store, "marketing_task_rows", task_rows)
            setattr(store, "marketing_task_scope", task_scope)
            task_rows[record.id] = record
            task_scope[record.id] = (business_id, environment, contact_id)
        return record

    def _create_manual_call_in_supabase(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        title: str,
    ) -> TaskRecord:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        row = insert_rows(
            "tasks",
            [
                {
                    "business_id": tenant.business_pk,
                    "environment": tenant.environment,
                    "task_type": "manual_call",
                    "status": "open",
                    "priority": "normal",
                    "details": {"contact_external_id": contact_id, "title": title},
                }
            ],
            select="id,created_at",
            settings=self.settings,
        )[0]
        return TaskRecord(
            id=f"tsk_{row['id']}",
            run_id=contact_id,
            title=title,
            status=TaskStatus.OPEN,
            created_at=row["created_at"],
        )
