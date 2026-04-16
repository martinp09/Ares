from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.marketing_supabase import insert_rows, marketing_backend_enabled, resolve_tenant
from app.models.commands import generate_id, generate_stable_id
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType


class TasksRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = client is not None
        self.settings = settings or get_settings()

    def create(self, record: TaskRecord, *, dedupe_key: str | None = None) -> TaskRecord:
        now = utc_now()
        resolved_key = dedupe_key or record.idempotency_key
        with self.client.transaction() as store:
            if resolved_key is not None:
                lookup_key = (record.business_id, record.environment, resolved_key)
                existing_id = store.task_keys.get(lookup_key)
                if existing_id is not None:
                    existing = store.tasks[existing_id]
                    return existing.model_copy(update={"deduped": True})
            else:
                lookup_key = None

            task_id = record.id or (
                generate_stable_id("tsk", record.business_id, record.environment, resolved_key)
                if resolved_key is not None
                else generate_id("tsk")
            )
            created = record.model_copy(update={"id": task_id, "updated_at": now})
            store.tasks[task_id] = created
            if lookup_key is not None:
                store.task_keys[lookup_key] = task_id
            return created

    def get(self, task_id: str) -> TaskRecord | None:
        with self.client.transaction() as store:
            return store.tasks.get(task_id)

    def list_for_lead(self, lead_id: str) -> list[TaskRecord]:
        with self.client.transaction() as store:
            tasks = [task for task in store.tasks.values() if task.lead_id == lead_id]
        tasks.sort(key=lambda task: (task.due_at or task.created_at, task.created_at, task.id or ""))
        return tasks

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
            business_id=business_id,
            environment=environment,
            run_id=contact_id,
            lead_id=contact_id,
            title=title,
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_CALL,
            priority=TaskPriority.NORMAL,
            created_at=utc_now(),
        )
        return self.create(record)

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
            business_id=business_id,
            environment=environment,
            run_id=contact_id,
            lead_id=contact_id,
            title=title,
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_CALL,
            priority=TaskPriority.NORMAL,
            created_at=row["created_at"],
            updated_at=row["created_at"],
        )
