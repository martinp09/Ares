from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib import error as url_error

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
from app.db.lead_machine_supabase import lead_machine_backend_enabled
from app.db.marketing_supabase import marketing_backend_enabled
from app.models.commands import generate_id, generate_stable_id
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType


class TasksRepository:
    def __init__(
        self,
        client: ControlPlaneClient | None = None,
        settings: Settings | None = None,
        force_memory: bool | None = None,
    ):
        self.settings = settings or get_settings()
        self.client = client or get_control_plane_client(self.settings)
        if force_memory is None:
            self._force_memory = client is not None and getattr(client, "backend", "memory") != "supabase"
        else:
            self._force_memory = force_memory

    def create(self, record: TaskRecord, *, dedupe_key: str | None = None) -> TaskRecord:
        if self._supabase_tasks_enabled():
            return self._create_in_supabase(record, dedupe_key=dedupe_key)
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
        if self._supabase_tasks_enabled():
            return self._get_in_supabase(task_id)
        with self.client.transaction() as store:
            return store.tasks.get(task_id)

    def list(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
        lead_id: str | None = None,
    ) -> list[TaskRecord]:
        if self._supabase_tasks_enabled():
            return self._list_in_supabase(business_id=business_id, environment=environment, lead_id=lead_id)
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
        if self._supabase_tasks_enabled():
            return self._update_in_supabase(task_id, updates)
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

    def _create_in_supabase(self, record: TaskRecord, *, dedupe_key: str | None = None) -> TaskRecord:
        tenant = resolve_tenant(record.business_id, record.environment, settings=self.settings)
        resolved_key = dedupe_key or record.idempotency_key
        if resolved_key is not None:
            existing_rows = self._fetch_by_idempotency_key(
                business_pk=tenant.business_pk,
                environment=tenant.environment,
                idempotency_key=resolved_key,
            )
            if existing_rows:
                return self._record_from_supabase(
                    existing_rows[0],
                    deduped=True,
                    business_scope=record.business_id,
                )
        now = utc_now()
        payload: dict[str, Any] = {
            "business_id": tenant.business_pk,
            "environment": tenant.environment,
            "run_id": row_id_from_external_id(record.run_id, "run"),
            "task_type": record.task_type.value,
            "status": record.status.value,
            "priority": record.priority.value,
            "assignee": record.assigned_to,
            "details": record.details,
            "due_at": record.due_at.isoformat() if record.due_at else None,
            "title": record.title,
            "lead_id": record.lead_id,
            "automation_run_id": record.automation_run_id,
            "source_event_id": record.source_event_id,
            "run_external_id": record.run_id,
            "idempotency_key": resolved_key,
            "created_at": record.created_at.isoformat(),
            "updated_at": now.isoformat(),
        }
        provided_id = row_id_from_external_id(record.id, "tsk")
        if provided_id is not None:
            payload["id"] = provided_id
        try:
            row = insert_rows(
                "tasks",
                [payload],
                select="*",
                settings=self.settings,
            )[0]
        except Exception as exc:
            if resolved_key is not None and self._is_duplicate_insert_error(exc):
                deduped_rows = self._fetch_by_idempotency_key(
                    business_pk=tenant.business_pk,
                    environment=tenant.environment,
                    idempotency_key=resolved_key,
                )
                if deduped_rows:
                    return self._record_from_supabase(
                        deduped_rows[0],
                        deduped=True,
                        business_scope=record.business_id,
                    )
            raise
        return self._record_from_supabase(row, business_scope=record.business_id)

    def _get_in_supabase(self, task_id: str) -> TaskRecord | None:
        row_id = row_id_from_external_id(task_id, "tsk")
        if row_id is None:
            return None
        rows = fetch_rows(
            "tasks",
            params={"select": "*", "id": f"eq.{row_id}", "limit": "1"},
            settings=self.settings,
        )
        return self._record_from_supabase(rows[0]) if rows else None

    def _list_in_supabase(
        self,
        *,
        business_id: str | None,
        environment: str | None,
        lead_id: str | None,
    ) -> list[TaskRecord]:
        params = {"select": "*", "order": "created_at.asc,id.asc"}
        business_scope: str | None = None
        rows: list[dict[str, Any]]
        if business_id is not None and environment is not None:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            params["business_id"] = f"eq.{tenant.business_pk}"
            params["environment"] = f"eq.{tenant.environment}"
            business_scope = business_id
            rows = fetch_rows("tasks", params=params, settings=self.settings)
        elif business_id is not None and business_id.isdigit():
            params["business_id"] = f"eq.{business_id}"
            business_scope = business_id
            if environment is not None:
                params["environment"] = f"eq.{environment}"
            rows = fetch_rows("tasks", params=params, settings=self.settings)
        elif business_id is not None:
            business_rows = fetch_rows(
                "businesses",
                params={"select": "business_id,environment", "slug": f"eq.{business_id}"},
                settings=self.settings,
            )
            if not business_rows:
                return []
            business_scope = business_id
            rows = []
            for business_row in business_rows:
                business_params = {
                    "select": "*",
                    "order": "created_at.asc,id.asc",
                    "business_id": f"eq.{business_row['business_id']}",
                    "environment": f"eq.{business_row['environment']}",
                }
                if lead_id is not None:
                    business_params["lead_id"] = f"eq.{lead_id}"
                rows.extend(fetch_rows("tasks", params=business_params, settings=self.settings))
        elif environment is not None:
            params["environment"] = f"eq.{environment}"
            if lead_id is not None:
                params["lead_id"] = f"eq.{lead_id}"
            rows = fetch_rows("tasks", params=params, settings=self.settings)
        else:
            if lead_id is not None:
                params["lead_id"] = f"eq.{lead_id}"
            rows = fetch_rows("tasks", params=params, settings=self.settings)
        tasks = [self._record_from_supabase(row, business_scope=business_scope) for row in rows]
        tasks.sort(key=lambda task: (task.due_at or task.created_at, task.created_at, task.id or ""))
        return tasks

    def _update_in_supabase(self, task_id: str, updates: dict[str, Any]) -> TaskRecord | None:
        row_id = row_id_from_external_id(task_id, "tsk")
        if row_id is None:
            return None
        row: dict[str, Any] = {"updated_at": utc_now().isoformat()}
        if "title" in updates:
            row["title"] = updates["title"]
        if "status" in updates:
            status = updates["status"]
            row["status"] = status.value if isinstance(status, TaskStatus) else status
        if "task_type" in updates:
            task_type = updates["task_type"]
            row["task_type"] = task_type.value if isinstance(task_type, TaskType) else task_type
        if "priority" in updates:
            priority = updates["priority"]
            row["priority"] = priority.value if isinstance(priority, TaskPriority) else priority
        if "run_id" in updates:
            run_id = updates["run_id"]
            row["run_external_id"] = run_id
            row["run_id"] = row_id_from_external_id(run_id, "run")
        if "lead_id" in updates:
            row["lead_id"] = updates["lead_id"]
        if "automation_run_id" in updates:
            row["automation_run_id"] = updates["automation_run_id"]
        if "source_event_id" in updates:
            row["source_event_id"] = updates["source_event_id"]
        if "due_at" in updates:
            due_at = updates["due_at"]
            if isinstance(due_at, datetime):
                row["due_at"] = due_at.isoformat()
            else:
                row["due_at"] = due_at
        if "assigned_to" in updates:
            row["assignee"] = updates["assigned_to"]
        if "idempotency_key" in updates:
            row["idempotency_key"] = updates["idempotency_key"]
        if "details" in updates:
            row["details"] = updates["details"]
        rows = patch_rows(
            "tasks",
            params={"id": f"eq.{row_id}"},
            row=row,
            select="*",
            settings=self.settings,
        )
        return self._record_from_supabase(rows[0]) if rows else None

    def _record_from_supabase(
        self,
        row: dict[str, Any],
        *,
        deduped: bool = False,
        business_scope: str | None = None,
    ) -> TaskRecord:
        details = row.get("details")
        details_payload = dict(details) if isinstance(details, dict) else {}
        title = str(row.get("title") or details_payload.get("title") or row.get("task_type") or "task")
        run_id = row.get("run_external_id")
        if run_id is None and row.get("run_id") is not None:
            run_id = external_id("run", row["run_id"])
        lead_id = row.get("lead_id") or details_payload.get("contact_external_id")
        created_at = row.get("created_at")
        updated_at = row.get("updated_at") or created_at
        if business_scope is None:
            business_scope = self._business_scope_from_row(row)
        return TaskRecord(
            id=external_id("tsk", row["id"]),
            business_id=business_scope,
            environment=str(row["environment"]),
            title=title,
            status=TaskStatus(str(row.get("status") or TaskStatus.OPEN.value)),
            task_type=TaskType(str(row.get("task_type") or TaskType.MANUAL_CALL.value)),
            priority=TaskPriority(str(row.get("priority") or TaskPriority.NORMAL.value)),
            run_id=run_id,
            lead_id=lead_id,
            automation_run_id=row.get("automation_run_id"),
            source_event_id=row.get("source_event_id"),
            due_at=row.get("due_at"),
            assigned_to=row.get("assignee"),
            idempotency_key=row.get("idempotency_key"),
            details=details_payload,
            created_at=created_at,
            updated_at=updated_at,
            deduped=deduped,
        )

    def _business_scope_from_row(self, row: dict[str, Any]) -> str:
        business_rows = fetch_rows(
            "businesses",
            params={
                "select": "slug,business_id",
                "business_id": f"eq.{row['business_id']}",
                "environment": f"eq.{row['environment']}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if business_rows:
            slug = business_rows[0].get("slug")
            if isinstance(slug, str) and slug.strip():
                return slug.strip()
        return str(row["business_id"])

    def _fetch_by_idempotency_key(
        self,
        *,
        business_pk: int,
        environment: str,
        idempotency_key: str,
    ) -> list[dict[str, Any]]:
        return fetch_rows(
            "tasks",
            params={
                "select": "*",
                "business_id": f"eq.{business_pk}",
                "environment": f"eq.{environment}",
                "idempotency_key": f"eq.{idempotency_key}",
                "limit": "1",
            },
            settings=self.settings,
        )

    def _supabase_tasks_enabled(self) -> bool:
        if self._force_memory:
            return False
        return (
            control_plane_backend_enabled(self.settings)
            or marketing_backend_enabled(self.settings)
            or lead_machine_backend_enabled(self.settings)
        )

    @staticmethod
    def _is_duplicate_insert_error(exc: Exception) -> bool:
        if not isinstance(exc, url_error.HTTPError):
            return False
        if exc.code == 409:
            return True
        if exc.code != 400:
            return False
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            return False
        lowered = body.lower()
        return "duplicate key" in lowered or "unique constraint" in lowered or "23505" in lowered
