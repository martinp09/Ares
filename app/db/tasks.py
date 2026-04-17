from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.marketing_supabase import (
    fetch_rows,
    insert_rows,
    marketing_backend_enabled,
    resolve_tenant,
)
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

    def list(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
        lead_id: str | None = None,
    ) -> list[TaskRecord]:
        with self.client.transaction() as store:
            tasks = list(store.tasks.values())
        if business_id is not None:
            tasks = [task for task in tasks if task.business_id == business_id]
        if environment is not None:
            tasks = [task for task in tasks if task.environment == environment]
        if lead_id is not None:
            tasks = [task for task in tasks if task.lead_id == lead_id]
        tasks.sort(key=lambda task: (task.due_at or task.created_at, task.created_at, task.id or ""))
        return tasks

    def list_for_lead(self, lead_id: str) -> list[TaskRecord]:
        return self.list(lead_id=lead_id)

    def update(self, task_id: str, updates: dict[str, Any]) -> TaskRecord | None:
        now = utc_now()
        with self.client.transaction() as store:
            existing = store.tasks.get(task_id)
            if existing is None:
                return None
            updated = existing.model_copy(update={**updates, "updated_at": now})
            store.tasks[task_id] = updated
            return updated

    def create_manual_call(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        title: str,
        dedupe_key: str | None = None,
    ) -> TaskRecord:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._create_manual_call_in_supabase(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                title=title,
                dedupe_key=dedupe_key,
            )
        resolved_dedupe_key = dedupe_key or f"manual_call:{contact_id}:{title}"
        record = TaskRecord(
            business_id=business_id,
            environment=environment,
            run_id=contact_id,
            lead_id=contact_id,
            title=title,
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_CALL,
            priority=TaskPriority.NORMAL,
            idempotency_key=resolved_dedupe_key,
            created_at=utc_now(),
        )
        return self.create(record, dedupe_key=resolved_dedupe_key)

    def _create_manual_call_in_supabase(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        title: str,
        dedupe_key: str | None = None,
    ) -> TaskRecord:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        resolved_dedupe_key = dedupe_key or f"manual_call:{contact_id}:{title}"
        existing_rows = fetch_rows(
            "tasks",
            params={
                "select": "id,created_at",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "task_type": "eq.manual_call",
                "status": "eq.open",
                "idempotency_key": f"eq.{resolved_dedupe_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if existing_rows:
            row = existing_rows[0]
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
                idempotency_key=resolved_dedupe_key,
                created_at=row["created_at"],
                updated_at=row["created_at"],
                deduped=True,
            )
        row = insert_rows(
            "tasks",
            [
                {
                    "business_id": tenant.business_pk,
                    "environment": tenant.environment,
                    "task_type": "manual_call",
                    "status": "open",
                    "priority": "normal",
                    "idempotency_key": resolved_dedupe_key,
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
            idempotency_key=resolved_dedupe_key,
            created_at=row["created_at"],
            updated_at=row["created_at"],
        )
