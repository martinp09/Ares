from __future__ import annotations

from app.db.tasks import TasksRepository
from app.models.lead_events import LeadEventRecord
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType


class LeadTaskService:
    def __init__(self, tasks_repository: TasksRepository | None = None) -> None:
        self.tasks_repository = tasks_repository or TasksRepository()

    def create_task_for_event(
        self,
        *,
        business_id: str,
        environment: str,
        lead_id: str | None,
        automation_run_id: str | None,
        event: LeadEventRecord,
        assigned_to: str | None = None,
    ) -> TaskRecord | None:
        if event.event_type != "lead.email.sent" or not lead_id:
            return None
        return self.tasks_repository.create(
            TaskRecord(
                business_id=business_id,
                environment=environment,
                lead_id=lead_id,
                automation_run_id=automation_run_id,
                source_event_id=event.id,
                title="Call lead after confirmed cold email send",
                status=TaskStatus.OPEN,
                task_type=TaskType.MANUAL_CALL,
                priority=TaskPriority.HIGH,
                due_at=event.event_timestamp,
                assigned_to=assigned_to,
                idempotency_key=f"lead-task:{event.idempotency_key}",
                details={
                    "provider": event.provider_name,
                    "provider_event_type": event.metadata.get("provider_event_type"),
                    "canonical_event_type": event.event_type,
                },
            )
        )


lead_task_service = LeadTaskService()
