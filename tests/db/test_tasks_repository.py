from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.tasks import TasksRepository
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType


def build_repository() -> TasksRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return TasksRepository(client)


def test_create_dedupes_by_business_environment_and_idempotency_key() -> None:
    repository = build_repository()

    first = repository.create(
        TaskRecord(
            business_id="limitless",
            environment="dev",
            title="Review reply",
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_REVIEW,
            priority=TaskPriority.HIGH,
            lead_id="lead_123",
            idempotency_key="task-001",
        )
    )
    second = repository.create(
        TaskRecord(
            business_id="limitless",
            environment="dev",
            title="Review reply",
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_REVIEW,
            priority=TaskPriority.HIGH,
            lead_id="lead_123",
            idempotency_key="task-001",
        )
    )

    assert first.id == second.id
    assert second.deduped is True


def test_create_manual_call_stays_compatible_with_existing_marketing_flow() -> None:
    repository = build_repository()

    task = repository.create_manual_call(
        business_id="limitless",
        environment="dev",
        contact_id="ctc_123",
        title="Call lead after reply",
    )

    assert task.status == TaskStatus.OPEN
    assert task.task_type == TaskType.MANUAL_CALL
    assert task.lead_id == "ctc_123"
